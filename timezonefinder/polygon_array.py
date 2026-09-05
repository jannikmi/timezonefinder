from collections.abc import Iterable
from pathlib import Path

import numpy as np

from timezonefinder.configs import POLYGON_BLOCK_SIZE, IntegerLike

from timezonefinder import utils
from timezonefinder.block_payload import decode_ring, derive_payload_offsets
from timezonefinder.coord_accessors import AbstractCoordAccessor, create_coord_accessor
from timezonefinder.flatbuf.io.polygons import (
    get_coordinate_path,
)
from timezonefinder.np_binary_helpers import (
    get_block_bases_path,
    get_block_offsets_path,
    get_block_ranges_path,
    get_block_widths_path,
    get_nr_vertices_path,
    get_poly_ref_path,
    get_xmax_path,
    get_xmin_path,
    get_ymax_path,
    get_ymin_path,
    read_per_polygon_vector,
)


class PolygonArray:
    xmin: np.ndarray
    xmax: np.ndarray
    ymin: np.ndarray
    ymax: np.ndarray
    #: the same four columns and the vertex count, read through a buffer view so that
    #: indexing yields a Python ``int`` - see ``__init__`` for what that is worth
    _xmin_ints: memoryview
    _xmax_ints: memoryview
    _ymin_ints: memoryview
    _ymax_ints: memoryview
    _nr_vertices_ints: memoryview
    block_ranges: np.ndarray
    block_offsets: list[int]
    block_bases: np.ndarray
    block_widths: np.ndarray
    block_payload_offsets: np.ndarray
    nr_vertices: np.ndarray
    coordinates: AbstractCoordAccessor

    def __init__(
        self,
        data_location: str | Path,
        in_memory: bool = False,
    ):
        """
        Initialize the PolygonArray.
        :param data_location: The path to the binary data files to use.
        :param in_memory: Whether to completely read and keep the coordinate data in memory as numpy.
        """
        self.in_memory = in_memory
        self.data_location: Path = Path(data_location)

        xmin_path = get_xmin_path(self.data_location)
        xmax_path = get_xmax_path(self.data_location)
        ymin_path = get_ymin_path(self.data_location)
        ymax_path = get_ymax_path(self.data_location)

        # read all per polygon vectors directly into memory (no matter the memory mode)
        self.xmin = read_per_polygon_vector(xmin_path)
        self.xmax = read_per_polygon_vector(xmax_path)
        self.ymin = read_per_polygon_vector(ymin_path)
        self.ymax = read_per_polygon_vector(ymax_path)

        coordinate_file_path = get_coordinate_path(self.data_location)
        # Initialize the appropriate coordinate accessor based on memory mode.
        # Built before the block index is read, deliberately: this is where the layout
        # marker is checked, and a layout 1 directory has to be rejected by name rather
        # than by the missing index files below.
        self.coordinates = create_coord_accessor(coordinate_file_path, self.in_memory)

        # The latitude block index: one [min, max] pair per block of POLYGON_BLOCK_SIZE
        # vertices, all rings' blocks in one flat array, addressed by `block_offsets`.
        #
        # Read into memory in both modes, like the bbox vectors above and unlike the
        # coordinates. It is ~0.5 MB against 63 MB of coordinates, and the point of it
        # is to decide *without* touching the coordinates which pages of them have to be
        # faulted in at all - so mapping it would spend the fetch it exists to avoid.
        #
        # One array for the whole collection rather than one per ring: a per-ring list
        # would be ~1.3 ms of construction and 1,322 objects to save a slice per
        # point-in-polygon call, on a path that reaches this at most ~1.05 times per
        # ambiguous query.
        self.block_ranges = read_per_polygon_vector(
            get_block_ranges_path(self.data_location)
        )
        # Nothing writes to the ranges after this point and every lookup shares them,
        # which is what lets one finder serve concurrent readers. Saying so to numpy
        # makes the kernels' read-only eager signatures describe the truth rather than
        # tolerate it.
        self.block_ranges.flags.writeable = False
        block_offsets = read_per_polygon_vector(
            get_block_offsets_path(self.data_location)
        )
        # The offsets become plain Python ints, which is worth ~100 ns of every
        # point-in-polygon test: reaching the kernel with two ``numpy.uint32`` bounds
        # costs 217 ns against 117 ns with ``int`` ones, because each is unboxed through
        # ``__index__``. The file stores the narrow unsigned column - its width is
        # checked where the data is built and over what ships
        # (``timezonefinder._data_integrity.validate_block_index``), the only place a
        # stored width can be checked at all.
        self.block_offsets: list[int] = block_offsets.tolist()

        # The per-block coordinate frames: the x origin and both bit widths, which with
        # the latitude index's own lower bound are what turn a block's payload words back
        # into coordinates. The y origin is that lower bound and is not stored again. Resident in both
        # modes like the ranges above and for the same reason - together they are ~1 MB
        # against a 38 MB payload, and a lookup consults them to decide which pages of
        # that payload it has to touch at all.
        self.block_bases = read_per_polygon_vector(
            get_block_bases_path(self.data_location)
        )
        self.block_widths = read_per_polygon_vector(
            get_block_widths_path(self.data_location)
        )
        # How many vertices each ring holds, which a packed payload's length no longer
        # says: the byte count depends on the widths, so the ragged last block's size
        # cannot be read back out of it.
        self.nr_vertices = read_per_polygon_vector(
            get_nr_vertices_path(self.data_location)
        )

        # The columns a candidate is read from, as buffer views. Indexing a numpy array
        # yields a 0-d numpy scalar; indexing a memoryview over the same bytes yields a
        # Python ``int`` - which is the ~100 ns per read the ``block_offsets``
        # conversion above is about, paid four times in ``outside_bbox`` and once in
        # ``_pip_at`` for every candidate polygon a query tests.
        #
        # A view rather than the ``.tolist()`` that conversion used, because this is 1.3k
        # entries per column rather than a header: measured over the packaged
        # boundaries, five lists cost **+333 KiB** of construction heap where five views
        # cost **+1.5 KiB**, on the mode whose purpose is to stay small and whose
        # ``init_heap`` is a tracked benchmark. It also keeps one statement of each
        # column instead of two that can disagree.
        #
        # A numpy integer indexes a memoryview fine, so no caller converts anything;
        # what it requires is native byte order, which ``np.load`` gives on the
        # little-endian platforms the packaged ``<i4`` files and the C kernel reading the
        # payload as native ``unsigned int`` already assume throughout. On a big-endian
        # one this raises here rather than answering wrongly.
        self._xmin_ints = memoryview(self.xmin)
        self._xmax_ints = memoryview(self.xmax)
        self._ymin_ints = memoryview(self.ymin)
        self._ymax_ints = memoryview(self.ymax)
        self._nr_vertices_ints = memoryview(self.nr_vertices)
        # Where each block's residuals start, derived rather than stored - the widths
        # and the vertex counts already say it. Made absolute against the coordinate
        # buffer here, so the kernels take one array and no per-ring rebasing.
        self.block_payload_offsets = derive_payload_offsets(
            self.nr_vertices,
            self.block_widths,
            block_offsets,
            POLYGON_BLOCK_SIZE,
        )
        self.block_payload_offsets += np.repeat(
            self.coordinates.word_offsets, np.diff(block_offsets.astype(np.int64))
        ).astype(self.block_payload_offsets.dtype)

        # Nothing writes to any of these after this point and every lookup shares them,
        # which is what lets one finder serve concurrent readers. Saying so to numpy
        # makes the kernels' read-only eager signatures describe the truth rather than
        # tolerate it.
        for array in (self.block_bases, self.block_widths, self.block_payload_offsets):
            array.flags.writeable = False

        # What the backend needs to reach the payload, wrapped once. On the C backend
        # this is five ``ffi.from_buffer`` calls at ~0.30 us each - a fifth of a whole
        # point-in-polygon test, which is why they happen here and not per lookup.
        #
        # The kernel is captured here too, and deliberately in the same place: what
        # ``packed_buffers`` returns is whatever the bound backend's factory made, so a
        # kernel from the other path handed these buffers is a segfault rather than a
        # wrong answer. Reading ``utils.inside_polygon_packed`` per call instead would
        # let the two drift apart between construction and lookup - which is exactly
        # what a benchmark or test that binds the other path does, and what
        # ``scripts/assert_acceleration_path.py`` could previously only warn about in a
        # comment. Holding both on the instance makes the pairing structural, and lets
        # two collections on different backends coexist in one process.
        self.packed = utils.packed_buffers(
            self.coordinates.words,
            self.block_ranges,
            self.block_bases,
            self.block_widths,
            self.block_payload_offsets,
        )
        self.pip_kernel = utils.inside_polygon_packed

    def __del__(self) -> None:
        """Clean up resources when the object is destroyed.

        Tolerates a partially initialised instance, as ``FileCoordAccessor.cleanup``
        does: ``__init__`` can raise between reading the bbox vectors and building the
        coordinate accessor - a data directory whose coordinate file the layout guard
        rejects does exactly that - and ``__del__`` still runs on the half-built object.
        Deleting a never-assigned attribute would raise inside ``__del__``, which Python
        can only report as an unraisable exception on stderr: noise that tells the user
        nothing about the real error already propagating out of ``__init__``.
        """
        for attr in (
            # the wrapped buffers first: on the C backend they hold the mapping open,
            # and the accessor below is what closes it
            "packed",
            "coordinates",
            "xmin",
            "xmax",
            "ymin",
            "ymax",
            "_xmin_ints",
            "_xmax_ints",
            "_ymin_ints",
            "_ymax_ints",
            "_nr_vertices_ints",
            "block_ranges",
            "block_offsets",
            "block_bases",
            "block_widths",
            "block_payload_offsets",
            "nr_vertices",
        ):
            if hasattr(self, attr):
                delattr(self, attr)

    def __len__(self) -> int:
        """
        Get the number of polygons in the collection.
        :return: Number of polygons
        """
        return len(self.xmin)

    def outside_bbox(self, poly_id: IntegerLike, x: int, y: int) -> bool:
        """
        Check if a point is outside the bounding box of a polygon.

        :param poly_id: Polygon ID
        :param x: X-coordinate of the point
        :param y: Y-coordinate of the point
        :return: True if the point is outside the boundaries, False otherwise
        """
        # the buffer views, not the arrays: this runs once per candidate polygon and
        # each read here would otherwise build a numpy scalar (see ``__init__``)
        if x > self._xmax_ints[poly_id]:
            return True
        if x < self._xmin_ints[poly_id]:
            return True
        if y > self._ymax_ints[poly_id]:
            return True
        if y < self._ymin_ints[poly_id]:
            return True
        return False

    def coords_of(self, idx: IntegerLike) -> np.ndarray:
        """
        Get the polygon coordinates for the given index.

        Decodes the ring's payload, which is the only place an absolute coordinate is
        rebuilt: the point-in-polygon path stays in each block's own frame and never
        materialises one. Costs an allocation and a pass over the ring, so it serves
        ``get_geometry()`` and the integrity checks rather than a lookup.

        Args:
            idx: The polygon index

        Returns:
            A numpy array containing the polygon coordinates
        """
        return self._decode(idx)

    def _decode(self, idx: IntegerLike) -> np.ndarray:
        """Decode the ring this collection stores at ``idx``.

        ``idx`` is a *storage* index: for holes that is not the hole id, which is what
        :meth:`HoleArray.coords_of` resolves before calling this.
        """
        start = self.block_offsets[idx]
        stop = self.block_offsets[idx + 1]
        ring = decode_ring(
            self.coordinates[idx],
            self.block_bases[start:stop],
            self.block_ranges[start:stop],
            self.block_widths[start:stop],
            self._nr_vertices_ints[idx],
            POLYGON_BLOCK_SIZE,
        )
        # Read-only although this array is freshly allocated and owned by the caller,
        # unlike every other array a finder hands out. Under polygon layout 2 this was a
        # view onto the mapping and had to be; keeping it read-only now is a choice, so
        # that `get_geometry()` answers the same way in both layouts and a caller who
        # wants to modify a ring copies it deliberately rather than discovering that a
        # format change made writes stick.
        ring.flags.writeable = False
        return ring

    def block_ranges_of(self, idx: IntegerLike) -> np.ndarray:
        """Get the latitude block ranges of the ring stored for the given index.

        Keyed exactly like :meth:`coords_of`, which is what makes the pair safe: the
        index describes the ring that method returns, and any collection that resolves
        ids differently (:class:`HoleArray` does) has to resolve for both or a lookup
        silently filters one ring by another's latitudes.

        Not used by :meth:`pip`, which reaches the same ranges through the collection's
        flat array; this is for the build-time and test callers that want one ring's.

        :param idx: The polygon index
        :return: A ``(nr_blocks, 2)`` view of ``[min, max]`` latitude per block
        """
        return self._block_ranges_at(idx)

    def _block_ranges_at(self, idx: IntegerLike) -> np.ndarray:
        """The block ranges of the ring this collection stores at ``idx``.

        A *storage* index, as :meth:`_decode` takes: the resolution :class:`HoleArray`
        performs happens once, above this, and calling the public method again with an
        already-resolved index would perform it twice.
        """
        return self.block_ranges[self.block_offsets[idx] : self.block_offsets[idx + 1]]

    def pip(self, poly_id: IntegerLike, x: int, y: int) -> bool:
        """
        Point in polygon (PIP) test.

        :param poly_id: Polygon ID
        :param x: X-coordinate of the point
        :param y: Y-coordinate of the point
        :return: True if the point is inside the polygon, False otherwise
        """
        return self._pip_at(poly_id, x, y)

    def _pip_at(self, idx: IntegerLike, x: int, y: int) -> bool:
        """The point-in-polygon test against the ring this collection stores at ``idx``.

        Nothing is sliced and no ring is decoded: the kernel is handed this collection's
        whole payload and the four per-block columns, and finds the ring by where its
        blocks start. :class:`HoleArray` overrides which collection answers, not this.

        ``self.pip_kernel`` rather than ``utils.inside_polygon_packed``: the kernel and
        the buffers below it were captured together, and only the pair is safe.
        """
        start = self.block_offsets[idx]
        return self.pip_kernel(
            x,
            y,
            # the view, so the kernel is handed a Python ``int`` rather than a
            # ``numpy.uint32`` it would unbox through ``__index__`` - the same reason
            # ``block_offsets`` above is a list of ``int``
            self._nr_vertices_ints[idx],
            POLYGON_BLOCK_SIZE,
            start,
            self.block_offsets[idx + 1] - start,
            *self.packed,
        )

    def pip_with_bbox_check(self, poly_id: IntegerLike, x: int, y: int) -> bool:
        """
        Point in polygon (PIP) test with bounding box check.

        :param poly_id: Polygon ID
        :param x: X-coordinate of the point
        :param y: Y-coordinate of the point
        :return: True if the point is inside the polygon, False otherwise
        """
        if self.outside_bbox(poly_id, x, y):
            return False
        return self.pip(poly_id, x, y)

    def in_any_polygon(self, poly_ids: Iterable[int], x: int, y: int) -> bool:
        """
        Check if a point is inside any of the specified polygons.

        :param poly_ids: An iterable of polygon IDs
        :param x: X-coordinate of the point
        :param y: Y-coordinate of the point
        :return: True if the point is inside any polygon, False otherwise
        """
        for poly_id in poly_ids:
            if self.pip_with_bbox_check(poly_id, x, y):
                return True
        return False


class HoleArray(PolygonArray):
    """Holes, whose geometry may be a reference to an identical boundary polygon.

    Nearly every hole in the packaged data is an enclave: the upstream builder cuts a
    hole into the surrounding zone with exactly the ring it uses as the enclave zone's
    own boundary polygon, so the two rings are identical vertex for vertex. Storing
    such a hole as a reference to that boundary is a pure storage change - the ring
    handed to the point-in-polygon test is the same one either way.

    ``poly_ref`` is a dense ``int32`` vector, one entry per hole id, with the sign
    carrying the discriminant:

    ==========  ==========================================================
    ``v >= 0``  the ring *is* boundary polygon ``v``
    ``v < 0``   the ring is stored inline, at index ``-(v + 1)`` of this
                collection's own coordinate file
    ==========  ==========================================================

    Both index spaces are dense and start at 0, so the sign alone cannot separate
    them: without the offset, inline ring 0 would encode as ``-0 == 0`` and collide
    with boundary polygon 0. ``-(v + 1)`` is the usual packing (it is ``~v``); biasing
    the non-negative side instead would only move the offset, not remove it.

    Hole ids stay dense, so ``hole_registry`` and every caller above ``coords_of`` are
    untouched, and the bbox vectors stay valid verbatim - a referenced ring is
    identical, so its bbox already equals the boundary's. ``outside_bbox``, the hot
    path, keeps reading a flat array with no indirection at all.

    ``poly_ref.npy`` is required rather than optional: the layout it belongs to has
    never been released, so there is no older data directory to stay compatible with,
    and a hole directory lacking it is not an older format but an unreadable one.

    Nothing here checks that the reference vector agrees with the coordinate file. That
    the packaged data is coherent is established once, by the build - see
    ``timezonefinder._data_integrity.validate_hole_references``, which the converter runs over
    what it wrote and the test suite runs over the packaged binaries. Re-deriving it in
    every user's process would re-answer a settled question on a latency-sensitive path.
    """

    def __init__(
        self,
        data_location: str | Path,
        boundaries: PolygonArray,
        in_memory: bool = False,
    ):
        """
        :param data_location: The path to the binary hole data files to use.
        :param boundaries: The boundary polygons that references resolve against. Held
            by reference, which keeps them alive for at least as long as this array.
        :param in_memory: Whether to completely read and keep the coordinate data in memory.
        """
        super().__init__(data_location=data_location, in_memory=in_memory)
        self.boundaries = boundaries
        # Required, not optional. Every directory the converter writes has one, and a
        # hole directory without it cannot be interpreted: the coordinate file holds
        # only the inline rings, so hole ids do not index it. Reading it unguarded
        # means a missing file raises naming itself, rather than costing an
        # `exists()` on every construction to say the same thing.
        self.poly_ref = read_per_polygon_vector(get_poly_ref_path(self.data_location))
        # read through a buffer view for the reason the base class's bbox columns are:
        # ``_resolve`` runs on every hole a candidate owns and this is its one read
        self._poly_ref_ints = memoryview(self.poly_ref)

    def _resolve(self, idx: IntegerLike) -> tuple[PolygonArray, int]:
        """Which collection holds this hole id's ring, and where.

        The one place the reference vector is read, because every accessor below has to
        agree on the answer: hole ids and boundary polygon ids are two dense spaces
        starting at 0, so a resolution that disagrees with another still answers, with
        some other ring. What that produces is a ring filtered against latitudes it has
        nothing to do with - blocks holding the crossing edges skipped, and a wrong
        answer for the handful of points that fall in them. It reads as noise rather
        than as a failure: keying this collection's own index by boundary ids answered
        6 of 5,000 points wrongly while everything else passed.

        :param idx: The hole id
        :return: the collection that stores the ring, and its index inside it
        """
        ref = self._poly_ref_ints[idx]
        if ref >= 0:
            return self.boundaries, ref
        return self, -(ref + 1)

    def coords_of(self, idx: IntegerLike) -> np.ndarray:
        """
        Get the hole coordinates for the given hole id, resolving a reference if needed.

        :param idx: The hole id
        :return: A numpy array containing the hole coordinates
        """
        collection, storage_idx = self._resolve(idx)
        return collection._decode(storage_idx)

    def block_ranges_of(self, idx: IntegerLike) -> np.ndarray:
        """Get the block ranges of the ring this hole id resolves to.

        :param idx: The hole id
        :return: A ``(nr_blocks, 2)`` view of ``[min, max]`` latitude per block
        """
        collection, storage_idx = self._resolve(idx)
        return collection._block_ranges_at(storage_idx)

    def pip(self, poly_id: IntegerLike, x: int, y: int) -> bool:
        """Point in polygon (PIP) test against the ring this hole id resolves to.

        :param poly_id: The hole id
        :param x: X-coordinate of the point
        :param y: Y-coordinate of the point
        :return: True if the point is inside the hole, False otherwise
        """
        collection, storage_idx = self._resolve(poly_id)
        return collection._pip_at(storage_idx, x, y)

    def __del__(self) -> None:
        """Clean up resources when the object is destroyed.

        Drops the boundaries reference *before* the base class tears this array down, so
        no half-deleted state is one that still resolves references: afterwards
        ``coords_of`` raises ``AttributeError`` instead of reading through a boundaries
        array whose own accessor may already be gone.
        """
        if hasattr(self, "_poly_ref_ints"):
            del self._poly_ref_ints
        if hasattr(self, "poly_ref"):
            del self.poly_ref
        if hasattr(self, "boundaries"):
            del self.boundaries
        super().__del__()
