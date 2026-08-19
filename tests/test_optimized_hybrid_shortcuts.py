"""Comprehensive unit tests for optimized hybrid shortcuts FlatBuffer schemas."""

import tempfile
import threading
from pathlib import Path

import numpy as np
import pytest
from h3.api import numpy_int as h3

from timezonefinder import TimezoneFinder, TimezoneFinderL
from timezonefinder.configs import SHORTCUT_H3_RES
from timezonefinder.flatbuf.io.hybrid_shortcuts import (
    SHORTCUT_SCHEMAS,
    ShortcutSchema,
    get_hybrid_shortcut_file_path,
    read_hybrid_shortcuts_binary,
    write_hybrid_shortcuts_flatbuffers,
)
from timezonefinder.utils import coord2int

SCHEMA_IDS = [schema.dtype_name for schema in SHORTCUT_SCHEMAS]


def schema_of(zone_id_dtype: np.dtype) -> ShortcutSchema:
    """Return the registry entry for a dtype, so no test restates a zone id limit."""
    return next(s for s in SHORTCUT_SCHEMAS if s.zone_id_dtype == zone_id_dtype)


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
        """Return a factory that creates a unique temp file path per call (thread-safe)."""

        def factory():
            return self._create_temp_file(zone_id_dtype, str(threading.get_ident()))

        yield factory

    def _create_test_data(self, zone_id_dtype):
        """Helper to create test data appropriate for the given dtype."""
        max_zone_id = schema_of(zone_id_dtype).max_zone_id

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
        # the reader picks its schema from this marker, hence not a plain ".bin"
        suffix += f"_{schema_of(zone_id_dtype).dtype_name}.bin"
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

    @pytest.mark.parallel_threads_limit("auto")
    def test_write_read_roundtrip(
        self, sample_hybrid_data, zone_id_dtype, temp_file_path
    ):
        """Test that data can be written and read back correctly."""
        path = temp_file_path()
        try:
            read_data = self._write_and_read_roundtrip(
                sample_hybrid_data, zone_id_dtype, path
            )
            self._validate_data_matches(sample_hybrid_data, read_data)
        finally:
            path.unlink(missing_ok=True)

    def test_file_path_generation(self, zone_id_dtype):
        """Test that file paths are generated correctly based on dtype."""
        test_dir = Path("/tmp/test")
        file_path = get_hybrid_shortcut_file_path(zone_id_dtype, test_dir)

        if zone_id_dtype.itemsize == 1:
            assert file_path.name == "hybrid_shortcuts_uint8.bin"
        else:
            assert file_path.name == "hybrid_shortcuts_uint16.bin"

        assert file_path.parent == test_dir

    @pytest.mark.parametrize("schema", SHORTCUT_SCHEMAS, ids=SCHEMA_IDS)
    def test_generated_file_name_round_trips(self, schema, tmp_path):
        """A file written to its generated path must be readable from that path.

        Every other round-trip test names its own scratch file, so the two halves of
        this contract were never checked against each other: the writer derives the
        name from the zone id width, and the reader recovers that width from the name.
        Drop the marker from one side and the failure only shows up at load time, on
        the shipped binary.

        Storing ``max_zone_id`` also pins the registry's limit to what the schema can
        actually hold - a value one too large would be rejected by the writer.
        """
        unique_hex, list_hex = 0x85283473FFFFFFF, 0x8528344FFFFFFFF
        data = {unique_hex: schema.max_zone_id, list_hex: [1, 2, 3]}

        path = get_hybrid_shortcut_file_path(schema.zone_id_dtype, tmp_path)
        assert path.name == schema.file_name
        write_hybrid_shortcuts_flatbuffers(data, schema.zone_id_dtype, path)

        read_back = read_hybrid_shortcuts_binary(path)
        assert int(read_back[unique_hex]) == schema.max_zone_id
        np.testing.assert_array_equal(
            read_back[list_hex], np.array([1, 2, 3], dtype=np.uint16)
        )

    def test_zone_id_validation(self, zone_id_dtype, temp_file_path):
        """Test that zone IDs are validated against dtype limits."""
        path = temp_file_path()
        try:
            max_value = (2 ** (zone_id_dtype.itemsize * 8)) - 1

            # Test data with zone ID exceeding dtype limits
            invalid_data = {
                0x85283473FFFFFFF: max_value + 1,  # Exceeds limit
            }

            with pytest.raises(ValueError, match="exceeds.*maximum"):
                write_hybrid_shortcuts_flatbuffers(invalid_data, zone_id_dtype, path)

        finally:
            path.unlink(missing_ok=True)

    @pytest.mark.parallel_threads_limit("auto")
    def test_empty_data(self, zone_id_dtype, temp_file_path):
        """Test handling of empty data."""
        path = temp_file_path()
        try:
            empty_data = {}
            read_data = self._write_and_read_roundtrip(empty_data, zone_id_dtype, path)
            assert len(read_data) == 0
        finally:
            path.unlink(missing_ok=True)

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
        max_zone_id = schema_of(zone_id_dtype).max_zone_id

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

    def test_file_name_carries_no_schema_information(self, tmp_path):
        """A name with no zone id marker is read all the same.

        The schema comes from the identifier stamped into the buffer, so the reader
        does not need the name to say anything. Rejection of a buffer whose identifier
        is missing or foreign lives in ``tests/test_flatbuf_format_guard.py``.
        """
        path = tmp_path / "hybrid_shortcuts.bin"
        write_hybrid_shortcuts_flatbuffers(
            {0x85283473FFFFFFF: 42}, np.dtype("<u1"), path
        )

        assert read_hybrid_shortcuts_binary(path) == {0x85283473FFFFFFF: 42}

    @pytest.mark.parallel_threads_limit("auto")
    def test_single_element_arrays_round_trip(self, zone_id_dtype, temp_file_path):
        """The format preserves a one-element polygon array rather than collapsing it.

        Single-element arrays should not be produced in the first place - a lone polygon with a
        unique timezone belongs in the shortcut as a zone id - but where they do occur the
        serialisation round-trips them unchanged, which is what this pins.

        This test demonstrates that the current shortcut generation logic produces
        single-element arrays when it should optimize them to store zone IDs directly.
        This is the issue that the len(shortcut_value) == 1 case in timezonefinder.py
        is designed to handle.

        TODO: When the shortcut generation logic is optimized to detect single polygons
        with unique timezones and store their zone ID directly, this test should be
        updated to assert that single-element arrays do NOT occur.
        """
        path = temp_file_path()
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
            read_data = self._write_and_read_roundtrip(test_data, zone_id_dtype, path)

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
            path.unlink(missing_ok=True)


@pytest.mark.unit
class TestSingleElementShortcutArraysAtRuntime:
    """Drive the real lookup path over a shortcut cell holding a one-element array.

    Nothing in the binary format forbids one - the test above round-trips it - so the
    runtime has to resolve it even though the generator is expected to collapse such a
    cell into a bare zone id.

    Replaces ``test_runtime_handling_of_single_element_arrays``, which built a local
    ``MockTimezoneFinder`` and then asserted that mock's own arithmetic, touching no
    library code, and whose docstring named ``_timezone_id_from_shortcut`` - a method
    that no longer exists.
    """

    LNG, LAT = -74.0059, 40.7128  # New York

    @staticmethod
    def _point_at(hex_id: int) -> dict[str, float]:
        """Query kwargs for a point inside ``hex_id`` - its own centre."""
        lat, lng = h3.cell_to_latlng(hex_id)
        return {"lng": lng, "lat": lat}

    @classmethod
    def _override(cls, finder, boundary_id: int, hex_id: int | None = None) -> int:
        """Point a cell at exactly one boundary polygon. Returns the cell."""
        if hex_id is None:
            hex_id = h3.latlng_to_cell(cls.LAT, cls.LNG, SHORTCUT_H3_RES)
        finder.shortcut_mapping[hex_id] = np.array([boundary_id], dtype=np.uint16)
        return hex_id

    @pytest.mark.parametrize("finder_cls", [TimezoneFinder, TimezoneFinderL])
    def test_resolves_to_the_zone_of_that_polygon(self, finder_cls):
        """One candidate means no ambiguity left to resolve, so its zone is the answer.

        ``TimezoneFinder.timezone_at`` reaches this without a point-in-polygon test:
        ``get_last_change_idx`` returns 0 for a one-element array, the candidate loop
        breaks immediately and the trailing "last possible zone" return takes over.
        """
        with finder_cls() as finder:
            boundary_id = 0
            expected = finder.zone_name_from_boundary_id(boundary_id)
            query = {"lng": self.LNG, "lat": self.LAT}
            assert finder.timezone_at(**query) != expected, (
                "precondition: the point must not already resolve to that zone, "
                "otherwise this passes without the override taking effect"
            )

            self._override(finder, boundary_id)

            assert finder.timezone_at(**query) == expected

    @pytest.mark.parametrize("finder_cls", [TimezoneFinder, TimezoneFinderL])
    def test_is_never_reported_as_a_unique_zone(self, finder_cls):
        """Unique cells are stored as a bare int, so an array is by definition not one.

        Starts from a cell the real data *does* report as unique, so the ``None`` below
        is caused by the array rather than by the cell having been ambiguous anyway.
        """
        with finder_cls() as finder:
            unique_hex_id = next(
                hex_id
                for hex_id, value in finder.shortcut_mapping.items()
                if isinstance(value, int)
            )
            query = self._point_at(unique_hex_id)
            assert finder.unique_timezone_at(**query) is not None

            self._override(finder, 0, hex_id=unique_hex_id)

            assert finder.unique_timezone_at(**query) is None

    def test_certain_timezone_at_still_checks_the_geometry(self):
        """The exhaustive lookup must not inherit the shortcut above.

        It iterates the array and runs the real point-in-polygon test, so a lone
        candidate whose bounding box excludes the point yields no match at all.
        """
        with TimezoneFinder() as finder:
            query = {"lng": self.LNG, "lat": self.LAT}
            x, y = coord2int(self.LNG), coord2int(self.LAT)
            distant_boundary_id = next(
                i
                for i in range(finder.nr_of_polygons)
                if finder.boundaries.outside_bbox(i, x, y)
            )
            assert finder.certain_timezone_at(**query) is not None

            self._override(finder, distant_boundary_id)

            assert finder.certain_timezone_at(**query) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
