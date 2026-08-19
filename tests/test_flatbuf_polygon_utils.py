import struct
import numpy as np
import pytest
from timezonefinder.flatbuf.io.polygons import (
    get_polygon_collection,
    write_polygon_collection_flatbuffer,
    read_polygon_array_from_binary,
    flatten_polygon_coords,
    reshape_to_polygon_coords,
)
from timezonefinder.utils import close_resource


@pytest.mark.parametrize(
    "polygons",
    [
        [
            # Example polygons with separate x and y coordinates
            np.array([[0, 1, 2], [3, 4, 5]]),
            np.array([[6, 7, 8, 9], [10, 11, 12, 13]]),
        ],
    ],
)
def test_single_polygon_collection_round_trip(tmp_path, polygons):
    """Test that writing and reading a single polygon collection gives the same results."""
    # Define output path
    output_file = tmp_path / "polygons.bin"

    # Write polygons to a single binary file
    write_polygon_collection_flatbuffer(output_file, polygons)

    assert output_file.exists(), "Output file should exist after writing."
    assert output_file.stat().st_size > 0, "Output file should be non-empty."

    with open(output_file, "rb") as file:
        # Read the binary file and verify the polygons
        buffer = file.read()
    poly_collection = get_polygon_collection(buffer)
    for idx, original_polygon in enumerate(polygons):
        read_polygon = read_polygon_array_from_binary(poly_collection, idx)
        np.testing.assert_array_equal(
            read_polygon, original_polygon, "Polygon mismatch."
        )

    with pytest.raises(struct.error):
        # Attempt to read a polygon with an out-of-bounds index
        read_polygon = read_polygon_array_from_binary(poly_collection, idx + 1)

    close_resource(buffer)
    close_resource(file)


@pytest.mark.parametrize(
    "polygon",
    [
        # Test with different shapes and values
        np.array([[0, 1, 2], [3, 4, 5]]),  # 2x3 array
        np.array([[6, 7, 8, 9], [10, 11, 12, 13]]),  # 2x4 array
        np.array([[100, 200], [300, 400]]),  # 2x2 array
        np.array([[1000], [2000]]),  # 2x1 array
        np.array(
            [[-10, -20, -30, -40, -50], [60, 70, 80, 90, 100]]
        ),  # 2x5 array with negative values
    ],
)
def test_coordinate_transformation_functions(polygon):
    """Test that flatten_polygon_coords and reshape_to_polygon_coords are inverses of each other."""
    # Test polygon -> flattened -> polygon round trip
    flattened = flatten_polygon_coords(polygon)
    reconstructed = reshape_to_polygon_coords(flattened)
    np.testing.assert_array_equal(
        reconstructed,
        polygon,
        "Reconstructed polygon does not match the original after flattening and reshaping.",
    )

    # Verify the flattened structure: [x0...xN-1, y0...yN-1]
    expected_flat = np.concatenate([polygon[0], polygon[1]])
    np.testing.assert_array_equal(
        flattened,
        expected_flat,
        "Flattened array structure does not match expected [x0...xN-1, y0...yN-1] pattern.",
    )

    n = polygon.shape[1]
    np.testing.assert_array_equal(
        flattened[:n], polygon[0], "Leading block is not the x coordinates."
    )
    np.testing.assert_array_equal(
        flattened[n:], polygon[1], "Trailing block is not the y coordinates."
    )

    # Verify dimensions
    assert flattened.shape[0] == polygon.shape[0] * polygon.shape[1], (
        "Flattened shape is incorrect"
    )
    assert reconstructed.shape == polygon.shape, (
        "Reconstructed shape does not match original"
    )

    # Both acceleration backends require contiguous rows: the C extension rejects a
    # strided row, the Numba kernel's eager signature demands C order.
    assert reconstructed.flags["C_CONTIGUOUS"], "Reconstructed array is not contiguous"
    assert reconstructed[0].flags["C_CONTIGUOUS"], "x row is not contiguous"
    assert reconstructed[1].flags["C_CONTIGUOUS"], "y row is not contiguous"


@pytest.mark.unit
@pytest.mark.parametrize(
    "polygons",
    [
        [
            np.array([[0, 1, 2], [3, 4, 5]]),
            np.array([[100, 200], [300, 400]]),
            np.array([[-10, -20, -30, -40, -50], [60, 70, 80, 90, 100]]),
        ],
    ],
)
def test_on_disk_coordinate_layout(tmp_path, polygons):
    """The bytes on disk hold one axis after the other, checked without the reader.

    Going through ``read_polygon_array_from_binary`` cannot catch a flatten/reshape
    pair that is wrong in mutually cancelling ways - every round trip still passes.
    Reading the raw vector back is the only thing that pins the wire format down.
    """
    output_file = tmp_path / "polygons.bin"
    write_polygon_collection_flatbuffer(output_file, polygons)

    with open(output_file, "rb") as file:
        buffer = file.read()
    poly_collection = get_polygon_collection(buffer)

    for idx, polygon in enumerate(polygons):
        raw = poly_collection.Polygons(idx).CoordsAsNumpy()
        np.testing.assert_array_equal(
            raw,
            np.concatenate([polygon[0], polygon[1]]),
            "On-disk coordinate vector is not stored one axis at a time.",
        )

    close_resource(buffer)


if __name__ == "__main__":
    pytest.main([__file__])
