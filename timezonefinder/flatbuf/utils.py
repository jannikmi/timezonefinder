"""
Centralized utility functions for working with FlatBuffers in the timezonefinder project.
"""

import flatbuffers
import numpy as np
from pathlib import Path
from typing import List, Tuple

from timezonefinder.configs import BOUNDARIES_BINARY, DEFAULT_DATA_DIR, HOLE_BINARY
from timezonefinder.flatbuf.Polygon import (
    PolygonStart,
    PolygonEnd,
    PolygonAddCoords,
    PolygonStartCoordsVector,
)
from timezonefinder.flatbuf.PolygonCollection import (
    PolygonCollection,
    PolygonCollectionStart,
    PolygonCollectionEnd,
    PolygonCollectionAddPolygons,
    PolygonCollectionStartPolygonsVector,
)


def flatten_polygon_coords(polygon: np.ndarray) -> np.ndarray:
    """Convert polygon coordinates from shape (2, N) to a flattened [x0, y0, x1, y1, ...] array.

    Args:
        polygon: Array of polygon coordinates with shape (2, N)
                where the first row contains x coordinates and the second row contains y coordinates

    Returns:
        Flattened 1D array of coordinates in the format [x0, y0, x1, y1, ...]
    """
    return polygon.ravel(order="F")


def reshape_to_polygon_coords(coords: np.ndarray) -> np.ndarray:
    """Reshape flattened coordinates to the format (2, N).

    Args:
        coords: Flattened 1D array of coordinates in the format [x0, y0, x1, y1, ...]

    Returns:
        Array of polygon coordinates with shape (2, N)
        where the first row contains x coordinates and the second row contains y coordinates
    """
    return coords.reshape(2, -1, order="F")


def get_boundaries_path(data_dir: Path = DEFAULT_DATA_DIR) -> Path:
    """Return the path to the boundaries flatbuffer file."""
    return data_dir / BOUNDARIES_BINARY


def get_holes_path(data_dir: Path = DEFAULT_DATA_DIR) -> Path:
    """Return the path to the holes flatbuffer file."""
    return data_dir / HOLE_BINARY


def write_polygon_collection_flatbuffer(
    file_path: Path, polygons: List[np.ndarray]
) -> int:
    """Write a collection of polygons to a flatbuffer file using a single coordinate vector.

    Args:
        file_path: Path to save the flatbuffer file
        polygons: List of polygon coordinates as numpy arrays with shape (2, N)
                  where the first row contains x coordinates and the second row contains y coordinates

    Returns:
        The size of the written file in bytes
    """
    print(f"writing {len(polygons)} polygons to binary file {file_path}")
    builder = flatbuffers.Builder(0)
    polygon_offsets = []

    # Create each polygon and store its offset
    for polygon in polygons:
        # Flatten coordinates to [x0, y0, x1, y1, ...] format
        coords = flatten_polygon_coords(polygon)

        # Create coords vector
        PolygonStartCoordsVector(builder, len(coords))
        for coord in reversed(coords):
            builder.PrependInt32(int(coord))  # Use signed 32-bit integer
        coords_offset = builder.EndVector()

        # Create polygon
        PolygonStart(builder)
        PolygonAddCoords(builder, coords_offset)  # Use Coords for combined vector
        polygon_offsets.append(PolygonEnd(builder))

    # Create polygon vector
    PolygonCollectionStartPolygonsVector(builder, len(polygon_offsets))
    for offset in reversed(polygon_offsets):
        builder.PrependUOffsetTRelative(offset)
    polygons_offset = builder.EndVector()

    # Create root table
    PolygonCollectionStart(builder)
    PolygonCollectionAddPolygons(builder, polygons_offset)
    collection_offset = PolygonCollectionEnd(builder)

    # Finish buffer
    builder.Finish(collection_offset)

    # Write to file
    with open(file_path, "wb") as f:
        buf = builder.Output()
        f.write(buf)

    size_in_bytes = file_path.stat().st_size
    size_in_mb = size_in_bytes / (1024**2)
    print(f"the binary file takes up {size_in_mb:.2f} MB")
    return size_in_bytes


def write_polygon_flatbuffers(
    output_path: Path, polygons: List[np.ndarray], holes: List[np.ndarray]
) -> Tuple[int, int]:
    """Write boundary polygons and hole polygons to separate flatbuffer files.

    Args:
        output_path: Directory to save the flatbuffer files
        polygons: List of boundary polygons
        holes: List of hole polygons

    Returns:
        Tuple of (boundaries_size, holes_size) in bytes
    """
    boundaries_file = get_boundaries_path(output_path)
    holes_file = get_holes_path(output_path)
    boundary_size = write_polygon_collection_flatbuffer(boundaries_file, polygons)
    holes_size = write_polygon_collection_flatbuffer(holes_file, holes)
    return boundary_size, holes_size


def get_collection_data(file):
    """Load boundary or hole polygons from FlatBuffers collections."""
    file.seek(0)
    buf = file.read()
    return PolygonCollection.GetRootAs(buf, 0)


def get_collection_length(file):
    """Get the number of polygons in a FlatBuffers collection."""
    collection = get_collection_data(file)
    return collection.PolygonsLength()


def read_polygon_array_from_binary(file, idx):
    """Read a polygon's coordinates from a FlatBuffers collection."""
    collection = get_collection_data(file)
    poly = collection.Polygons(idx)
    coords = poly.CoordsAsNumpy()
    # Reshape to (2, N) format
    return reshape_to_polygon_coords(coords)
