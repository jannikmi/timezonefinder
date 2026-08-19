import flatbuffers
import mmap
import numpy as np
from pathlib import Path
from typing import Final

from timezonefinder.configs import DEFAULT_DATA_DIR, IntegerLike
from timezonefinder.flatbuf.io.layout import incompatible_layout_error
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
    PolygonCollectionAddLayoutVersion,
    PolygonCollectionStartPolygonsVector,
)

# FlatBuffers file identifier (bytes 4-8), answering "is this a timezonefinder
# polygon file at all?". Files written before this marker existed carry none.
POLYGON_FILE_IDENTIFIER: Final[bytes] = b"TZFP"

# What a polygon collection file means. Absent in pre-guard files, which read back as
# the FlatBuffers default 0, so those files self-identify without special casing.
#
#   0 = coordinates interleaved [x0, y0, x1, y1, ...], every hole ring stored inline
#   1 = coordinates in per-axis blocks [x0...xN-1, y0...yN-1], and a *hole* collection
#       holds only the rings that are not a verbatim copy of a boundary polygon, with
#       holes/poly_ref.npy mapping hole ids onto them
#
# Deliberately NOT tied to the package version: bump it only when what the file means
# changes, never for an ordinary release. Data compiled by any version that writes a
# given layout stays readable by any version that reads it, so a `bin_file_location`
# directory does not have to be regenerated on upgrade.
#
# Layout 1 covers both the per-axis encoding and the hole reference encoding because
# they ship together: neither has appeared in a release, so no version in the wild
# reads or writes layout 1, and giving the second change a version of its own would
# rewrite every packaged coordinate file to distinguish states that never coexisted.
POLYGON_LAYOUT_VERSION: Final[int] = 1


def flatten_polygon_coords(polygon: np.ndarray) -> np.ndarray:
    """Convert polygon coordinates from shape (2, N) to a flat [x0...xN-1, y0...yN-1] array.

    All x coordinates are stored first, followed by all y coordinates, so that each
    axis forms one contiguous block on disk.

    Args:
        polygon: Array of polygon coordinates with shape (2, N)
                where the first row contains x coordinates and the second row contains y coordinates

    Returns:
        Flattened 1D array of coordinates in the format [x0...xN-1, y0...yN-1]
    """
    # C order ravels row by row, i.e. all of row 0 (x) then all of row 1 (y).
    # Kept layout-agnostic on purpose: an F-ordered input still ravels to the same
    # result (via a copy), so the writer cannot silently emit the interleaved layout.
    return polygon.ravel(order="C")


def reshape_to_polygon_coords(coords: np.ndarray) -> np.ndarray:
    """Reshape flattened coordinates to the format (2, N).

    Returns a **view** onto ``coords`` whose rows are each C-contiguous: row 0 is the
    leading x block, row 1 the trailing y block. That is what keeps ``coords_of()``
    zero-copy, and both acceleration backends depend on it - the C extension rejects a
    strided row outright, and the Numba kernel's eager signature requires C order.

    Args:
        coords: Flattened 1D array of coordinates in the format [x0...xN-1, y0...yN-1]

    Returns:
        Array of polygon coordinates with shape (2, N)
        where the first row contains x coordinates and the second row contains y coordinates
    """
    return coords.reshape(2, -1)


def get_coordinate_path(data_dir: Path = DEFAULT_DATA_DIR) -> Path:
    """Return the path to the boundaries flatbuffer file.

    ``.bin`` rather than ``.fbs``: the latter is the FlatBuffers *schema* extension,
    and a schema is what ``timezonefinder/flatbuf/schemas/`` holds. This is a
    serialised buffer, which says what it is through its file identifier
    (``POLYGON_FILE_IDENTIFIER``) rather than through its name.
    """
    return data_dir / "coordinates.bin"


def write_polygon_collection_flatbuffer(
    file_path: Path, polygons: list[np.ndarray]
) -> None:
    """Write a collection of polygons to a flatbuffer file using a single coordinate vector.

    Args:
        file_path: Path to save the flatbuffer file
        polygons: List of polygon coordinates as numpy arrays with shape (2, N)
                  where the first row contains x coordinates and the second row contains y coordinates

    Returns:
        None
    """
    print(f"writing {len(polygons)} polygons to binary file {file_path}")
    builder = flatbuffers.Builder(0)
    polygon_offsets = []

    # Create each polygon and store its offset
    for polygon in polygons:
        # Flatten coordinates to [x0...xN-1, y0...yN-1] format
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
    PolygonCollectionAddLayoutVersion(builder, POLYGON_LAYOUT_VERSION)
    collection_offset = PolygonCollectionEnd(builder)

    # Finish buffer, stamping the identifier so readers can tell this file apart
    # from one written before the coordinate layout changed
    builder.Finish(collection_offset, file_identifier=POLYGON_FILE_IDENTIFIER)

    # Write to file
    with open(file_path, "wb") as f:
        buf = builder.Output()
        f.write(buf)


def _incompatible_layout_error(
    found_version: int, file_path: Path | None
) -> ValueError:
    """Build the error raised for coordinate data this version cannot read."""
    return incompatible_layout_error(
        "polygon coordinate file", found_version, POLYGON_LAYOUT_VERSION, file_path
    )


def get_polygon_collection(
    buf: bytes | mmap.mmap, file_path: Path | None = None
) -> PolygonCollection:
    """Load a PolygonCollection from a buffer, rejecting incompatible coordinate data.

    The layout changed without any change to the container: same file name,
    same schema, same vector lengths, values still plausible int32. Parsing such a file
    succeeds and returns wrong timezones silently, so the layout markers are checked
    here rather than trusted. This runs once per accessor construction, never per
    lookup, and does not touch the coordinate vectors - the zero-copy path is unaffected.

    Args:
        buf: A binary stream or memory-mapped file containing the flatbuffer data.
        file_path: Where ``buf`` came from, named in the error message. Optional so
            in-memory buffers can be checked too.

    Returns: PolygonCollection

    Raises:
        ValueError: if the buffer was written by an incompatible timezonefinder version.
    """
    if not PolygonCollection.PolygonCollectionBufferHasIdentifier(buf, 0):
        # Written before the identifier existed, i.e. the interleaved layout.
        # Reported as version 0 rather than as a corrupt file, since that is what
        # it actually is for everyone who will ever hit this.
        raise _incompatible_layout_error(0, file_path)
    collection = PolygonCollection.GetRootAs(buf, 0)
    version = collection.LayoutVersion()
    if version != POLYGON_LAYOUT_VERSION:
        raise _incompatible_layout_error(version, file_path)
    return collection


def read_polygon_array_from_binary(
    poly_collection: PolygonCollection, idx: IntegerLike
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
    coords = poly.CoordsAsNumpy()  # flat 1D array: all x values, then all y values
    # Reshape to a (2, N) view with contiguous rows
    return reshape_to_polygon_coords(coords)
