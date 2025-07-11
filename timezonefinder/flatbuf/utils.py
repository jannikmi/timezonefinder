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


def write_polygon_collection_flatbuffer(
    file_path: Path, polygons: List[np.ndarray]
) -> int:
    """Write a collection of polygons to a flatbuffer file using a single coordinate vector.

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
        coords = polygon.ravel()  # Flatten x and y coordinates into a single vector

        # Create coords vector
        PolygonStartCoordsVector(builder, len(coords))
        for coord in reversed(coords):
            builder.PrependUint32(int(coord))
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

    return file_path.stat().st_size


def read_polygon_collection_flatbuffer(file_path: Path) -> Tuple[int, Callable]:
    """Read a collection of polygons from a flatbuffer file using a single coordinate vector.

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
        coords = poly.CoordsAsNumpy()
        return coords.reshape(2, -1)  # Reshape into (2, n) format for x and y

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
