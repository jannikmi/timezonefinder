import pytest
import numpy as np
from timezonefinder.flatbuf.shortcut_utils import (
    write_shortcuts_flatbuffers,
    read_shortcuts_binary,
    get_shortcut_file_path,
)


def test_write_and_read_shortcuts(tmp_path):
    """Test writing and reading shortcuts to and from a FlatBuffer binary file."""
    # Sample shortcut mapping
    shortcut_mapping = {
        12345: [1, 2, 3],
        67890: [4, 5, 6, 7],
        11111: [8, 9],
    }

    # Write the shortcuts to a temporary file
    write_shortcuts_flatbuffers(shortcut_mapping, output_path=tmp_path)

    # Verify the file exists and is non-empty
    output_file = get_shortcut_file_path(tmp_path)
    assert output_file.exists(), "Output file was not created."
    assert output_file.stat().st_size > 0, "Output file is empty."

    # Read the shortcuts back from the file
    read_mapping = read_shortcuts_binary(output_file)

    # Verify the read mapping matches the original
    assert len(read_mapping) == len(shortcut_mapping), "Mismatch in number of entries."
    for hex_id, poly_ids in shortcut_mapping.items():
        np.testing.assert_array_equal(
            read_mapping[hex_id],
            np.array(poly_ids, dtype=np.uint16),
            f"Mismatch for hex_id {hex_id}.",
        )


if __name__ == "__main__":
    pytest.main([__file__])
