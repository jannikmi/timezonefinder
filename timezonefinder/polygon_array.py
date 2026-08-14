from collections.abc import Iterable
from pathlib import Path

import numpy as np

from timezonefinder.configs import IntegerLike

from timezonefinder import utils
from timezonefinder.coord_accessors import AbstractCoordAccessor, create_coord_accessor
from timezonefinder.flatbuf.io.polygons import (
    get_coordinate_path,
)
from timezonefinder.np_binary_helpers import (
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
        # Initialize the appropriate coordinate accessor based on memory mode
        self.coordinates = create_coord_accessor(coordinate_file_path, self.in_memory)

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
        for attr in ("coordinates", "xmin", "xmax", "ymin", "ymax"):
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
        if x > self.xmax[poly_id]:
            return True
        if x < self.xmin[poly_id]:
            return True
        if y > self.ymax[poly_id]:
            return True
        if y < self.ymin[poly_id]:
            return True
        return False

    def coords_of(self, idx: IntegerLike) -> np.ndarray:
        """
        Get the polygon coordinates for the given index.

        Args:
            idx: The polygon index

        Returns:
            A numpy array containing the polygon coordinates
        """
        return self.coordinates[idx]

    def pip(self, poly_id: IntegerLike, x: int, y: int) -> bool:
        """
        Point in polygon (PIP) test.

        :param poly_id: Polygon ID
        :param x: X-coordinate of the point
        :param y: Y-coordinate of the point
        :return: True if the point is inside the polygon, False otherwise
        """
        polygon = self.coords_of(poly_id)
        return utils.inside_polygon(x, y, polygon)

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
    ``scripts/data_integrity.validate_hole_references``, which the converter runs over
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

    def coords_of(self, idx: IntegerLike) -> np.ndarray:
        """
        Get the hole coordinates for the given hole id, resolving a reference if needed.

        :param idx: The hole id
        :return: A numpy array containing the hole coordinates
        """
        ref = int(self.poly_ref[idx])
        if ref >= 0:
            return self.boundaries.coords_of(ref)
        return self.coordinates[-(ref + 1)]

    def __del__(self) -> None:
        """Clean up resources when the object is destroyed.

        Drops the boundaries reference *before* the base class tears this array down, so
        no half-deleted state is one that still resolves references: afterwards
        ``coords_of`` raises ``AttributeError`` instead of reading through a boundaries
        array whose own accessor may already be gone.
        """
        if hasattr(self, "poly_ref"):
            del self.poly_ref
        if hasattr(self, "boundaries"):
            del self.boundaries
        super().__del__()
