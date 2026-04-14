import flatbuffers
import mmap
import numpy as np
from pathlib import Path
from typing import List, Union

from timezonefinder.configs import DEFAULT_DATA_DIR
from timezonefinder.flatbuf.generated.polygons.Polygon import (
    PolygonStart,
    PolygonEnd,
    PolygonAddCoords,
    PolygonStartCoordsVector,
)
from timezonefinder.flatbuf.generated.polygons.PolygonCollection import (
    PolygonCollection,
    PolygonCollectionStart,
    PolygonCollectionEnd,
    PolygonCollectionAddPolygons,
    PolygonCollectionStartPolygonsVector,
)
from timezonefinder.flatbuf.io.compression import (
    compress_file,
    decompress_mmap,
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


def get_coordinate_path(data_dir: Path = DEFAULT_DATA_DIR) -> Path:
    """Return the path to the boundaries flatbuffer file."""
    return data_dir / "coordinates.fbs"


def get_coordinate_path_compressed(data_dir: Path = DEFAULT_DATA_DIR) -> Path:
    """Return the path to the compressed boundaries flatbuffer file."""
    return data_dir / "coordinates.fbs.zst"


def write_polygon_collection_flatbuffer(
    file_path: Path, polygons: List[np.ndarray], compress: bool = True
) -> None:
    """Write a collection of polygons to a flatbuffer file using a single coordinate vector.

    Args:
        file_path: Path to save the flatbuffer file
        polygons: List of polygon coordinates as numpy arrays with shape (2, N)
                  where the first row contains x coordinates and the second row contains y coordinates
        compress: Whether to compress the output file using zstandard (default True)

    Returns:
        None
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

    # Compress if requested
    if compress:
        compressed_path = Path(str(file_path) + ".zst")
        compress_file(file_path, compressed_path)
        print(f"Compressed {file_path} to {compressed_path}")
        # Keep original uncompressed file for backwards compatibility
        # (it will be used as fallback if decompression fails)


def get_polygon_collection(buf: Union[bytes, mmap.mmap]) -> PolygonCollection:
    """Load a PolygonCollection from bytes or memory-mapped file.

    Handles both compressed and uncompressed data transparently.

    Args:
        buf: A binary stream, memory-mapped file, or bytes containing the flatbuffer data.
             Can be compressed with zstandard or uncompressed.

    Returns: PolygonCollection
    """
    # If it's a memory-mapped file, we may need to decompress it
    if isinstance(buf, mmap.mmap):
        # Check for zstandard magic number (0x28, 0xb5, 0x2f, 0xfd)
        header = buf[:4]
        if header == b'\x28\xb5\x2f\xfd':
            # It's compressed, decompress it
            buf = decompress_mmap(buf)
    elif isinstance(buf, bytes):
        # Check for zstandard magic number
        if buf[:4] == b'\x28\xb5\x2f\xfd':
            # It's compressed, decompress it
            from timezonefinder.flatbuf.io.compression import decompress_bytes
            buf = decompress_bytes(buf)

    return PolygonCollection.GetRootAs(buf, 0)


def read_polygon_array_from_binary(
    poly_collection: PolygonCollection, idx: int
) -> np.ndarray:
    """Read a polygon's coordinates from a FlatBuffers collection."""
    # value checks not required as this is a private function
    # processed polygon indices are expected to be in range
    # nr_polygons = collection.PolygonsLength()
    # if idx >= nr_polygons:
    #     raise IndexError(
    #         f"Index {idx} out of bounds for collection with {nr_polygons} polygons."
    #     )
    poly = poly_collection.Polygons(idx)
    coords = poly.CoordsAsNumpy()  # flat 1D array of coordinates
    # Reshape to (2, N) format
    return reshape_to_polygon_coords(coords)
