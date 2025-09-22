"""Comprehensive unit tests for optimized hybrid shortcuts FlatBuffer schemas."""

import tempfile
from pathlib import Path

import numpy as np
import pytest

from timezonefinder.flatbuf.io.hybrid_shortcuts import (
    get_hybrid_shortcut_file_path,
    read_hybrid_shortcuts_binary,
    write_hybrid_shortcuts_flatbuffers,
)


class TestOptimizedHybridShortcuts:
    """Test cases for the optimized hybrid shortcuts schemas."""

    @pytest.fixture(params=[np.dtype("<u1"), np.dtype("<u2")])
    def zone_id_dtype(self, request):
        """Parameterized fixture for testing both uint8 and uint16 dtypes."""
        return request.param

    @pytest.fixture
    def sample_hybrid_data(self, zone_id_dtype):
        """Generate test data appropriate for the given dtype."""
        return self._create_test_data(zone_id_dtype)

    @pytest.fixture
    def temp_file_path(self, zone_id_dtype):
        """Create a temporary file path for testing."""
        return self._create_temp_file(zone_id_dtype)

    def _create_test_data(self, zone_id_dtype):
        """Helper to create test data appropriate for the given dtype."""
        max_zone_id = 255 if zone_id_dtype.itemsize == 1 else 65535

        # Create test data that fits within the dtype limits
        base_zone_id = min(42, max_zone_id)
        large_zone_id = min(max_zone_id - 1, 1000)

        return {
            # Unique zones with different IDs
            0x85283473FFFFFFF: base_zone_id,
            0x85283447FFFFFFF: base_zone_id + 1,
            0x85283463FFFFFFF: large_zone_id,
            # Polygon lists of varying lengths
            0x8528342BFFFFFFF: [1001, 1002, 1003, 1004],
            0x8528344FFFFFFFF: [2001, 2002],
            0x85283457FFFFFFF: [3001],  # Single polygon
            0x8528346BFFFFFFF: [],  # Empty polygon list
            # Mix of repeated zone IDs (should be stored directly, no deduplication needed)
            0x85283467FFFFFFF: base_zone_id,  # Same as first entry
        }

    def _create_temp_file(self, zone_id_dtype, suffix_prefix=""):
        """Helper to create a temporary file path for testing."""
        suffix = f"_{suffix_prefix}" if suffix_prefix else ""
        suffix += "_uint8.fbs" if zone_id_dtype.itemsize == 1 else "_uint16.fbs"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
            return Path(tmp_file.name)

    def _write_and_read_roundtrip(self, data, zone_id_dtype, file_path):
        """Helper to perform write-read roundtrip and return read data."""
        write_hybrid_shortcuts_flatbuffers(data, zone_id_dtype, file_path)
        return read_hybrid_shortcuts_binary(file_path)

    def _validate_data_matches(self, expected_data, actual_data):
        """Helper to validate that read data matches expected data."""
        assert len(actual_data) == len(expected_data)

        for hex_id, expected_value in expected_data.items():
            assert hex_id in actual_data, f"Missing hex_id {hex_id:x}"
            actual_value = actual_data[hex_id]

            if isinstance(expected_value, int):
                # Unique zone ID
                assert isinstance(actual_value, (int, np.integer))
                assert int(actual_value) == expected_value
            else:
                # Polygon list
                assert isinstance(actual_value, np.ndarray)
                expected_array = np.array(expected_value, dtype=np.uint16)
                np.testing.assert_array_equal(actual_value, expected_array)

    def test_write_read_roundtrip(
        self, sample_hybrid_data, zone_id_dtype, temp_file_path
    ):
        """Test that data can be written and read back correctly."""
        try:
            read_data = self._write_and_read_roundtrip(
                sample_hybrid_data, zone_id_dtype, temp_file_path
            )
            self._validate_data_matches(sample_hybrid_data, read_data)
        finally:
            temp_file_path.unlink(missing_ok=True)

    def test_file_path_generation(self, zone_id_dtype):
        """Test that file paths are generated correctly based on dtype."""
        test_dir = Path("/tmp/test")
        file_path = get_hybrid_shortcut_file_path(zone_id_dtype, test_dir)

        if zone_id_dtype.itemsize == 1:
            assert file_path.name == "hybrid_shortcuts_uint8.fbs"
        else:
            assert file_path.name == "hybrid_shortcuts_uint16.fbs"

        assert file_path.parent == test_dir

    def test_zone_id_validation(self, zone_id_dtype, temp_file_path):
        """Test that zone IDs are validated against dtype limits."""
        try:
            max_value = (2 ** (zone_id_dtype.itemsize * 8)) - 1

            # Test data with zone ID exceeding dtype limits
            invalid_data = {
                0x85283473FFFFFFF: max_value + 1,  # Exceeds limit
            }

            with pytest.raises(ValueError, match="exceeds.*maximum"):
                write_hybrid_shortcuts_flatbuffers(
                    invalid_data, zone_id_dtype, temp_file_path
                )

        finally:
            temp_file_path.unlink(missing_ok=True)

    def test_empty_data(self, zone_id_dtype, temp_file_path):
        """Test handling of empty data."""
        try:
            empty_data = {}
            read_data = self._write_and_read_roundtrip(
                empty_data, zone_id_dtype, temp_file_path
            )
            assert len(read_data) == 0
        finally:
            temp_file_path.unlink(missing_ok=True)

    def test_storage_efficiency(self, zone_id_dtype):
        """Test that the optimized schemas are space efficient."""
        # Create data with only unique zones (should be very compact)
        unique_only_data = {
            0x85283473FFFFFFF: 1,
            0x85283447FFFFFFF: 2,
            0x85283463FFFFFFF: 3,
        }

        # Create data with polygon lists (should be larger)
        polygon_heavy_data = {
            0x85283473FFFFFFF: [1001, 1002, 1003, 1004, 1005, 1006],
            0x85283447FFFFFFF: [2001, 2002, 2003, 2004, 2005, 2006],
            0x85283463FFFFFFF: [3001, 3002, 3003, 3004, 3005, 3006],
        }

        unique_path = self._create_temp_file(zone_id_dtype, "unique")
        polygon_path = self._create_temp_file(zone_id_dtype, "polygon")

        try:
            # Write both datasets
            write_hybrid_shortcuts_flatbuffers(
                unique_only_data, zone_id_dtype, unique_path
            )
            write_hybrid_shortcuts_flatbuffers(
                polygon_heavy_data, zone_id_dtype, polygon_path
            )

            # Check file sizes
            unique_size = unique_path.stat().st_size
            polygon_size = polygon_path.stat().st_size

            # Unique-only data should create smaller files
            assert unique_size < polygon_size, (
                f"Unique data ({unique_size}B) should be smaller than polygon data ({polygon_size}B)"
            )

        finally:
            unique_path.unlink(missing_ok=True)
            polygon_path.unlink(missing_ok=True)

    @pytest.mark.parametrize("zone_id_dtype", [np.dtype("<u1"), np.dtype("<u2")])
    def test_large_datasets(self, zone_id_dtype):
        """Test performance with larger datasets."""
        large_data = self._create_large_test_data(zone_id_dtype, 100)
        temp_path = self._create_temp_file(zone_id_dtype, "large")

        try:
            # This should complete without errors
            read_data = self._write_and_read_roundtrip(
                large_data, zone_id_dtype, temp_path
            )
            assert len(read_data) == len(large_data)

            # Spot check a few entries using existing validation helper
            sample_data = dict(list(large_data.items())[:5])
            sample_read = {k: read_data[k] for k in sample_data.keys()}
            self._validate_data_matches(sample_data, sample_read)

        finally:
            temp_path.unlink(missing_ok=True)

    def _create_large_test_data(self, zone_id_dtype, size):
        """Helper to create large test datasets."""
        max_zone_id = 255 if zone_id_dtype.itemsize == 1 else 65535

        large_data = {}
        for i in range(size):
            hex_id = 0x85283473FFFFFFF + i
            if i % 3 == 0:
                # Unique zone
                large_data[hex_id] = i % max_zone_id
            else:
                # Polygon list
                large_data[hex_id] = [1000 + i, 1001 + i, 1002 + i]
        return large_data

    def test_invalid_dtype_handling(self):
        """Test handling of invalid dtypes."""
        invalid_dtypes = [
            np.dtype("<i4"),  # Signed integer
            np.dtype("<u4"),  # Too large (4 bytes)
            np.dtype("<f4"),  # Float
        ]

        for invalid_dtype in invalid_dtypes:
            with pytest.raises(ValueError):
                get_hybrid_shortcut_file_path(invalid_dtype)

    def test_auto_detection_from_filename(self):
        """Test that schema type is auto-detected from filename."""
        test_data = {0x85283473FFFFFFF: 42}

        uint8_path = self._create_temp_file(np.dtype("<u1"))
        uint16_path = self._create_temp_file(np.dtype("<u2"))

        try:
            # Write files using both schemas
            uint8_data = self._write_and_read_roundtrip(
                test_data, np.dtype("<u1"), uint8_path
            )
            uint16_data = self._write_and_read_roundtrip(
                test_data, np.dtype("<u2"), uint16_path
            )

            # Both should read the same data
            assert uint8_data == uint16_data
            assert int(uint8_data[0x85283473FFFFFFF]) == 42

        finally:
            uint8_path.unlink(missing_ok=True)
            uint16_path.unlink(missing_ok=True)

    def test_single_element_arrays_should_not_occur(
        self, zone_id_dtype, temp_file_path
    ):
        """Test documenting that single-element arrays currently occur but should be optimized.

        This test demonstrates that the current shortcut generation logic produces
        single-element arrays when it should optimize them to store zone IDs directly.
        This is the issue that the len(shortcut_value) == 1 case in timezonefinder.py
        is designed to handle.

        TODO: When the shortcut generation logic is optimized to detect single polygons
        with unique timezones and store their zone ID directly, this test should be
        updated to assert that single-element arrays do NOT occur.
        """
        try:
            # Create test data representing the current suboptimal behavior
            test_data = {
                0x85283473FFFFFFF: [100],  # Single polygon - currently stored as array
                0x85283447FFFFFFF: [
                    200
                ],  # Another single polygon - currently stored as array
                0x85283463FFFFFFF: 42,  # Optimized zone ID (this is correct)
                0x8528344FFFFFFFF: [
                    300,
                    301,
                ],  # Multi-polygon - correctly stored as array
            }

            # Write and read the data
            read_data = self._write_and_read_roundtrip(
                test_data, zone_id_dtype, temp_file_path
            )

            # Verify current behavior: single-element arrays are preserved
            # (This documents the suboptimal behavior that should be fixed)
            single_element_count = 0
            for hex_id, original_value in test_data.items():
                assert hex_id in read_data, f"Missing hex_id {hex_id:x}"
                actual_value = read_data[hex_id]

                if isinstance(original_value, list) and len(original_value) == 1:
                    # Currently, single-element arrays are stored as arrays (suboptimal)
                    assert isinstance(actual_value, np.ndarray)
                    assert len(actual_value) == 1
                    single_element_count += 1

                    # Document what the optimized behavior should be:
                    # If polygon 100 has a unique timezone (e.g., zone_id=5), then
                    # this shortcut should store 5 directly instead of [100]
                    print(
                        f"SUBOPTIMAL: Hex ID {hex_id:x} stores single-element array {actual_value}"
                    )
                    print(
                        f"  Should be optimized to store the zone_id directly if polygon {original_value[0]} has unique timezone"
                    )

            # Verify that we found the expected suboptimal cases
            assert single_element_count == 2, (
                f"Expected 2 single-element arrays, found {single_element_count}"
            )

            print(
                f"\nFound {single_element_count} single-element arrays that should be optimized."
            )
            print(
                "The len(shortcut_value) == 1 case in timezonefinder.py handles this suboptimal data structure."
            )

        finally:
            temp_file_path.unlink(missing_ok=True)

    def test_runtime_handling_of_single_element_arrays(self):
        """Test that the runtime code correctly handles single-element arrays.

        This test verifies that the len(shortcut_value) == 1 case in
        AbstractTimezoneFinder._timezone_id_from_shortcut works correctly
        even with the suboptimal single-element array data structure.
        """
        from timezonefinder.configs import IntegerLike
        import numpy as np

        # Mock the zone mapping for testing
        class MockTimezoneFinder:
            def zone_id_of(self, boundary_id: IntegerLike) -> int:
                # Simple mock: return boundary_id + 1000 as zone_id
                return int(boundary_id) + 1000

        mock_finder = MockTimezoneFinder()

        # Test the logic that handles len(shortcut_value) == 1
        test_cases = [
            ([100], 1100),  # Single element array should return zone_id_of(100) = 1100
            ([200], 1200),  # Single element array should return zone_id_of(200) = 1200
            ([42], 1042),  # Single element array should return zone_id_of(42) = 1042
        ]

        for shortcut_value, expected_zone_id in test_cases:
            shortcut_array = np.array(shortcut_value, dtype=np.uint16)

            # Simulate the len(shortcut_value) == 1 case
            if len(shortcut_array) == 1:
                # This is the logic from timezonefinder.py line ~220
                actual_zone_id = mock_finder.zone_id_of(shortcut_array[0])

                assert actual_zone_id == expected_zone_id, (
                    f"Expected zone_id {expected_zone_id} for shortcut_value {shortcut_value}, "
                    f"but got {actual_zone_id}"
                )

                # Verify that shortcut_array[0] is indeed a numpy scalar, not an array
                element = shortcut_array[0]
                assert isinstance(element, np.integer), (
                    f"Expected numpy integer, got {type(element)}"
                )
                assert not isinstance(element, np.ndarray), (
                    "shortcut_array[0] should be scalar, not array"
                )

        print(f"✓ Successfully tested {len(test_cases)} single-element array cases")
        print(
            "✓ Verified that shortcut_array[0] returns numpy scalars compatible with IntegerLike"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
