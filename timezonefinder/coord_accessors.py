"""
Coordinate accessors for timezonefinder.

This module provides classes for accessing polygon coordinates
either directly from file or from preloaded memory.
"""

from abc import ABC, abstractmethod
import mmap
from pathlib import Path
from typing import BinaryIO

import numpy as np

from timezonefinder import utils
from timezonefinder.configs import IntegerLike
from timezonefinder.flatbuf.generated.polygons.PolygonCollection import (
    PolygonCollection,
)
from timezonefinder.flatbuf.io.polygons import (
    get_polygon_collection,
    read_polygon_array_from_binary,
)


class AbstractCoordAccessor(ABC):
    """Abstract base class defining the interface for coordinate accessors."""

    @abstractmethod
    def __init__(self, coordinate_file_path: Path):
        """
        Initialize the coordinate accessor.

        Args:
            coordinate_file_path: Path to the coordinate file
        """
        pass

    @abstractmethod
    def __getitem__(self, idx: IntegerLike) -> np.ndarray:
        """
        Get the polygon coordinates for the given index.

        Args:
            idx: The polygon index. Numpy integers are accepted as well as
                ``int``: polygon ids reach this call straight out of the
                shortcut arrays, so requiring ``int`` would mean an added
                conversion per candidate polygon on the lookup fast path.

        Returns:
            A numpy array containing the polygon coordinates
        """
        pass

    @abstractmethod
    def __len__(self) -> int:
        """
        Get the number of polygons stored in the coordinate file.

        Not the number of polygon *ids* in the collection using it: the holes file
        stores only the rings that are not references to a boundary polygon.
        """
        pass

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
    """Accessor that reads polygon coordinates from the file on demand."""

    def __init__(self, coordinate_file_path: Path):
        """
        Initialize the file-based coordinate accessor.

        Args:
            coordinate_file_path: Path to the coordinate file
        """
        self.coordinate_file_path = coordinate_file_path
        # Initialize file resources using proper resource management.
        try:
            # Use memory-mapped file for on-demand reading
            self.coord_file: BinaryIO = open(self.coordinate_file_path, "rb")
            # Create memory map
            self.coord_buf: mmap.mmap = mmap.mmap(
                self.coord_file.fileno(), 0, access=mmap.ACCESS_READ
            )
            self.polygon_collection: PolygonCollection = get_polygon_collection(
                self.coord_buf, self.coordinate_file_path
            )
        except Exception:
            # Clean up any partially initialized resources
            self.cleanup()
            raise

    def __getitem__(self, idx: IntegerLike) -> np.ndarray:
        """
        Get the polygon coordinates for the given index.

        Args:
            idx: The polygon index

        Returns:
            A numpy array containing the polygon coordinates
        """
        return read_polygon_array_from_binary(self.polygon_collection, idx)

    def __len__(self) -> int:
        return self.polygon_collection.PolygonsLength()

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
        # Note: closing coord_buf is refused while polygon arrays handed out by
        # __getitem__ are still alive, since those are zero-copy views onto the mmap.
        # close_resource suppresses the resulting BufferError (unmapping underneath a
        # live view would leave it dangling).
        close_resource(getattr(self, "coord_file", None))
        close_resource(getattr(self, "coord_buf", None))

        # Drop our own references regardless of whether the close succeeded. If it was
        # refused, these are the only remaining owners besides the caller's views, so
        # releasing them lets the mapping go as soon as the last view is dropped rather
        # than pinning it for the lifetime of this accessor.
        # polygon_collection owns no resources itself, but keeps coord_buf alive.
        for attr in ("polygon_collection", "coord_buf", "coord_file"):
            if hasattr(self, attr):
                delattr(self, attr)


class MemoryCoordAccessor(AbstractCoordAccessor):
    """Accessor that preloads all polygon coordinates into memory."""

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

        # Get number of polygons
        num_polygons = polygon_collection.PolygonsLength()

        # Preload all polygons. The key type mirrors __getitem__: numpy integers
        # hash and compare equal to the plain ints stored here, so a np.int64
        # lookup hits the same entry without a conversion.
        self.polygons: dict[IntegerLike, np.ndarray] = {}
        for idx in range(num_polygons):
            self.polygons[idx] = read_polygon_array_from_binary(polygon_collection, idx)

        # Once polygons are loaded, we don't need to keep polygon_collection or coord_buf references
        # They'll be garbage collected

    def __getitem__(self, idx: IntegerLike) -> np.ndarray:
        """
        Get the polygon coordinates for the given index.

        Args:
            idx: The polygon index

        Returns:
            A numpy array containing the polygon coordinates
        """
        return self.polygons[idx]

    def __len__(self) -> int:
        return len(self.polygons)

    def cleanup(self) -> None:
        """Drop the preloaded polygons. Unlike the file-backed sibling, nothing to close.

        Not safe to call twice, and not safe on a partially initialised instance: both
        raise ``AttributeError``, which ``__del__`` turns into an ignored-exception
        message on stderr. ``FileCoordAccessor.cleanup`` tolerates both (see
        ``test_repeated_cleanup_with_live_view_does_not_raise``); aligning this one is a
        behaviour change, so it is left as is until something actually needs it.
        """
        del self.polygons


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
