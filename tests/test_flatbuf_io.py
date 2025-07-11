import numpy as np
import pytest
from timezonefinder.flatbuf.utils import (
    write_polygon_collection_flatbuffer,
    get_collection_length,
    read_polygon_array_from_binary,
)


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
    output_file = tmp_path / "polygons.fbs"

    # Write polygons to a single binary file
    boundaries_size = write_polygon_collection_flatbuffer(output_file, polygons)

    # Verify file size is non-zero
    assert boundaries_size > 0, "File size should be greater than zero."

    # Read back the data
    with open(output_file, "rb") as f:
        assert get_collection_length(f) == len(polygons), (
            "Mismatch in number of polygons."
        )
        for idx, original_polygon in enumerate(polygons):
            read_polygon = read_polygon_array_from_binary(f, idx)
            np.testing.assert_array_equal(
                read_polygon, original_polygon, "Polygon mismatch."
            )


if __name__ == "__main__":
    pytest.main([__file__])
