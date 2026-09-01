"""
Coordinate accessors for timezonefinder.

Both accessors serve the same thing - a polygon collection's whole packed payload as
one ``uint32`` array, plus where each ring's words begin in it - and differ only in
where those words live: a memory map, or a copy on the heap. Since polygon layout 3
that is the whole difference between the two memory modes, because a ring is decoded
per lookup either way (``timezonefinder/block_payload.py``); before it, the in-memory
mode additionally held every ring pre-decoded, which is what made it a different code
path rather than a different buffer.
"""

from abc import ABC, abstractmethod
import mmap
from pathlib import Path
from typing import BinaryIO

import numpy as np

from timezonefinder import utils
from timezonefinder.block_payload import PAYLOAD_WORD_DTYPE
from timezonefinder.configs import IntegerLike
from timezonefinder.flatbuf.generated.polygons.PolygonCollection import (
    PolygonCollection,
)
from timezonefinder.flatbuf.io.polygons import (
    derive_payload_offset_table,
    get_polygon_collection,
    read_payload_at,
)


class AbstractCoordAccessor(ABC):
    """Abstract base class defining the interface for coordinate accessors."""

    #: The collection's whole payload, as words. What the point-in-polygon kernels are
    #: given: they address a block absolutely, so nothing is sliced per lookup.
    words: np.ndarray
    #: Where each ring's payload begins in :attr:`words`, and how long it is.
    word_offsets: np.ndarray
    word_lengths: np.ndarray

    @abstractmethod
    def __init__(self, coordinate_file_path: Path):
        """
        Initialize the coordinate accessor.

        Args:
            coordinate_file_path: Path to the coordinate file
        """
        pass

    def __getitem__(self, idx: IntegerLike) -> np.ndarray:
        """
        Get the packed payload of the ring stored at the given index.

        Args:
            idx: The polygon index. Numpy integers are accepted as well as
                ``int``: polygon ids reach this call straight out of the
                shortcut arrays, so requiring ``int`` would mean an added
                conversion per candidate polygon on the lookup fast path.

        Returns:
            A zero-copy view of that ring's payload words. Decoding it needs the block
            frames, which the owning :class:`~timezonefinder.polygon_array.PolygonArray`
            holds - see its ``coords_of``.
        """
        return read_payload_at(
            self.words, self.word_offsets[idx], self.word_lengths[idx]
        )

    def __len__(self) -> int:
        """
        Get the number of polygons stored in the coordinate file.

        Not the number of polygon *ids* in the collection using it: the holes file
        stores only the rings that are not references to a boundary polygon.
        """
        return len(self.word_offsets)

    def __del__(self) -> None:
        """
        Ensure resources are cleaned up when the object is destroyed.
        """
        self.cleanup()

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources."""
        pass


class FileCoordAccessor(AbstractCoordAccessor):
    """Accessor that reads polygon payloads from the memory-mapped file."""

    def __init__(self, coordinate_file_path: Path):
        """
        Initialize the file-based coordinate accessor.

        Args:
            coordinate_file_path: Path to the coordinate file
        """
        self.coordinate_file_path = coordinate_file_path
        # Initialize file resources using proper resource management.
        try:
            # Unbuffered: nothing reads payloads through this object - the mapping
            # below serves them - and the offset table's scattered header reads are 6x
            # slower through a buffer that every seek discards.
            self.coord_file: BinaryIO = open(
                self.coordinate_file_path, "rb", buffering=0
            )
            # Create memory map
            self.coord_buf: mmap.mmap = mmap.mmap(
                self.coord_file.fileno(), 0, access=mmap.ACCESS_READ
            )
            collection: PolygonCollection = get_polygon_collection(
                self.coord_buf, self.coordinate_file_path
            )
            # Where each ring's payload lives, resolved once and eagerly.
            #
            # Eagerly on purpose, and NOT because the table is cheap to build. Polygon
            # payloads are not optional-path data: a `TimezoneFinder` exists to test
            # points against polygons, and every query that is not answered outright by
            # a unique-zone shortcut cell reaches this accessor. There is no population
            # of callers who never need the table, so deferring it would move a certain
            # cost to the first query rather than avoid it - and would buy that with a
            # per-fetch `is None` branch on the hot path and a write to `self` from a
            # lookup, which is exactly what a shared instance being safe for concurrent
            # reads currently rests on: every attribute is assigned here or in
            # `cleanup()`, and nothing on the lookup path mutates state. The lazy rule
            # that governs `zone_positions` (read only by `certain_timezone_at` and
            # `get_geometry`, which the `timezone_at` majority never calls) is the
            # opposite case, not a precedent for this one.
            #
            # Read through the file rather than the mapping: the header words sit next
            # to the polygons they describe, so walking them through the mapping would
            # fault in a page per polygon and inflate the resident set of a finder that
            # has answered nothing yet. The collection is not kept either - everything
            # read after this point is addressed by offset.
            self.word_offsets, self.word_lengths = derive_payload_offset_table(
                collection, self.coord_file
            )
            self.word_offsets.flags.writeable = False
            self.word_lengths.flags.writeable = False
            # The mapping seen as words. A view, so it neither copies nor faults
            # anything in; what makes it valid is that the writer pads the file to a
            # whole number of words and FlatBuffers aligns the vectors inside it. Read
            # only by construction, since the mapping is.
            self.words = np.frombuffer(self.coord_buf, dtype=PAYLOAD_WORD_DTYPE)
        except Exception:
            # Clean up any partially initialized resources
            self.cleanup()
            raise

    def cleanup(self) -> None:
        """Clean up resources.

        Safe to call repeatedly and on a partially initialised instance. The accessor
        must not be used afterwards: the underlying buffers are released.
        """
        # At termination utils may have been tidied up. If we're terminating we don't need to
        # worry about closing file handles so just avoid an exception.
        close_resource = getattr(utils, "close_resource", None)
        if close_resource is None:
            return

        # close_resource already ignores None and common close errors.
        # Note: closing coord_buf is refused while the word view or any payload view
        # handed out by __getitem__ is still alive, since those are zero-copy views onto
        # the mmap. close_resource suppresses the resulting BufferError (unmapping
        # underneath a live view would leave it dangling).
        close_resource(getattr(self, "coord_file", None))
        close_resource(getattr(self, "coord_buf", None))

        # Drop our own references regardless of whether the close succeeded. If it was
        # refused, these are the only remaining owners besides the caller's views, so
        # releasing them lets the mapping go as soon as the last view is dropped rather
        # than pinning it for the lifetime of this accessor.
        # The offset table is plain integers owning their own storage - it references
        # nothing and is dropped only so a cleaned-up accessor has no usable state left.
        for attr in (
            "words",
            "word_offsets",
            "word_lengths",
            "coord_buf",
            "coord_file",
        ):
            if hasattr(self, attr):
                delattr(self, attr)


class MemoryCoordAccessor(AbstractCoordAccessor):
    """Accessor that keeps the whole payload on the heap instead of mapping it."""

    def __init__(self, coordinate_file_path: Path):
        """
        Initialize the memory-based coordinate accessor.

        Args:
            coordinate_file_path: Path to the coordinate file
        """
        # Read entire file into memory
        with open(coordinate_file_path, "rb") as f:
            coord_buf = f.read()

        # Initialize polygon collection
        polygon_collection = get_polygon_collection(coord_buf, coordinate_file_path)

        # Resolve every ring's position in one pass. Going through the generated
        # accessors per polygon reads the same bytes but rebuilds the vtable walk 1300
        # times, which is most of this loop's cost.
        self.word_offsets, self.word_lengths = derive_payload_offset_table(
            polygon_collection
        )
        self.word_offsets.flags.writeable = False
        self.word_lengths.flags.writeable = False
        # A view onto the copy above, which is what keeps this alive; no polygon is
        # decoded here. Preloading decoded rings would hold 63 MB where the packed
        # payload holds 38 - and would decode every ring in the collection to serve the
        # handful a query reaches. Read only by construction, since a `bytes` is.
        self.words = np.frombuffer(coord_buf, dtype=PAYLOAD_WORD_DTYPE)

    def cleanup(self) -> None:
        """Drop the payload. Unlike the file-backed sibling, nothing to close.

        Not safe to call twice, and not safe on a partially initialised instance: both
        raise ``AttributeError``, which ``__del__`` turns into an ignored-exception
        message on stderr. ``FileCoordAccessor.cleanup`` tolerates both (see
        ``test_repeated_cleanup_with_live_view_does_not_raise``); aligning this one is a
        behaviour change, so it is left as is until something actually needs it.
        """
        del self.words


def create_coord_accessor(
    coordinate_file_path: Path, in_memory: bool
) -> AbstractCoordAccessor:
    """
    Factory function to create the appropriate coordinate accessor.

    Args:
        coordinate_file_path: Path to the coordinate file
        in_memory: Whether to use in-memory mode

    Returns:
        An instance of a coordinate accessor
    """
    if in_memory:
        return MemoryCoordAccessor(coordinate_file_path)
    else:
        return FileCoordAccessor(coordinate_file_path)
