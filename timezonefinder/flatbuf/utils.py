"""
Centralized utility functions for working with FlatBuffers in the timezonefinder project.
"""

import flatbuffers
import numpy as np
from pathlib import Path
from typing import List, Tuple, Callable

from timezonefinder.flatbuf.Polygon import (
    PolygonStart,
    PolygonEnd,
    PolygonAddXCoords,
    PolygonAddYCoords,
    PolygonStartXCoordsVector,
    PolygonStartYCoordsVector,
)
from timezonefinder.flatbuf.PolygonCollection import (
    PolygonCollection,
    PolygonCollectionStart,
    PolygonCollectionEnd,
    PolygonCollectionAddPolygons,
    PolygonCollectionStartPolygonsVector,
)


def write_polygon_collection_flatbuffer(
    file_path: Path, polygons: List[np.ndarray]
) -> int:
    """Write a collection of polygons to a flatbuffer file.

    Args:
        file_path: Path to save the flatbuffer file
        polygons: List of polygon coordinates as numpy arrays

    Returns:
        The size of the written file in bytes
    """
    builder = flatbuffers.Builder(0)
    polygon_offsets = []

    # Create each polygon and store its offset
    for polygon in polygons:
        x_coords, y_coords = polygon

        # Create x_coords vector
        PolygonStartXCoordsVector(builder, len(x_coords))
        for x in reversed(x_coords):
            builder.PrependUint32(int(x))
        x_coords_offset = builder.EndVector()

        # Create y_coords vector
        PolygonStartYCoordsVector(builder, len(y_coords))
        for y in reversed(y_coords):
            builder.PrependUint32(int(y))
        y_coords_offset = builder.EndVector()

        # Create polygon
        PolygonStart(builder)
        PolygonAddXCoords(builder, x_coords_offset)
        PolygonAddYCoords(builder, y_coords_offset)
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

    return file_path.stat().st_size


def read_polygon_collection_flatbuffer(file_path: Path) -> Tuple[int, Callable]:
    """Read a collection of polygons from a flatbuffer file.

    Args:
        file_path: Path to the flatbuffer file

    Returns:
        A tuple with the number of polygons and a function to retrieve a polygon by index
    """
    with open(file_path, "rb") as f:
        buf = f.read()
    collection = PolygonCollection.GetRootAs(buf, 0)
    n = collection.PolygonsLength()

    def get_poly(idx):
        poly = collection.Polygons(idx)
        m = poly.XCoordsLength()
        # Use more efficient NumPy array access when available
        if hasattr(poly, "XCoordsAsNumpy"):
            x_coords = poly.XCoordsAsNumpy()
            y_coords = poly.YCoordsAsNumpy()
        else:
            x_coords = np.array([poly.XCoords(i) for i in range(m)], dtype=np.uint32)
            y_coords = np.array([poly.YCoords(i) for i in range(m)], dtype=np.uint32)
        return np.stack([x_coords, y_coords])

    return n, get_poly


def write_all_polygons_flatbuffers(
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
    boundaries_file = output_path / "boundaries.fbs"
    holes_file = output_path / "holes.fbs"

    print(f"Writing {len(polygons)} boundary polygons to {boundaries_file}")
    boundary_size = write_polygon_collection_flatbuffer(boundaries_file, polygons)

    print(f"Writing {len(holes)} hole polygons to {holes_file}")
    holes_size = write_polygon_collection_flatbuffer(holes_file, holes)

    return boundary_size, holes_size
