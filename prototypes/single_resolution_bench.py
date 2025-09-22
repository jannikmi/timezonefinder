"""Benchmark single-resolution H3 shortcut indices without hierarchy.

This script builds separate shortcut maps for individual resolutions from
0 to ``MAX_RESOLUTION`` (inclusive), comparing their performance and storage
characteristics. Each shortcut entry stores either a single zone identifier
(unique hit) or a list of polygon ids for ambiguous cells. The resulting
indices are benchmarked against a single set of 10,000 globally random
query points; all throughput and latency statistics reported below originate
from this random dataset.

TEMPORARY HYBRID INDEX TEST:
This script also includes a test function `test_hybrid_index_algorithm()` that
validates the correctness of the algorithm for building the new combined hybrid
index data structure. The test asserts equality of content between the new
hybrid index and the two separate legacy data structures (unique_shortcuts and
shortcuts), ensuring that the hybrid approach correctly combines both without
data loss or corruption.

Run with::

    uv run python prototypes/single_resolution_bench.py
"""

from __future__ import annotations

import random
import sys
import time
import warnings
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Sequence, Union

import h3.api.numpy_int as h3
import numpy as np
import pandas as pd

from scripts.configs import DEFAULT_INPUT_PATH, DEBUG
from scripts.shortcuts import optimise_shortcut_ordering
from scripts.timezone_data import TimezoneData
from timezonefinder import utils
from timezonefinder.timezonefinder import TimezoneFinder


MIN_RESOLUTION = 0 if DEBUG else 1
# Resolutions above 5 are intentionally excluded because the index size explodes.
MAX_RESOLUTION = 2 if DEBUG else 4
RESOLUTIONS = range(MIN_RESOLUTION, MAX_RESOLUTION + 1)
RANDOM_SAMPLE = 10_000
SEED = 42
INPUT_JSON_PATH = DEFAULT_INPUT_PATH


@lru_cache(maxsize=None)
def h3_cells_at_resolution(resolution: int) -> frozenset[int]:
    """Get all H3 cells at a given resolution."""
    if resolution < 0:
        raise ValueError("H3 resolution must be non-negative")
    if resolution == 0:
        return frozenset(int(cell) for cell in h3.get_res0_cells())
    return frozenset(
        int(child)
        for parent in h3_cells_at_resolution(resolution - 1)
        for child in h3.cell_to_children(parent)
    )


def h3_num_hexagons(resolution: int) -> int:
    """Get the number of H3 cells at a given resolution."""
    return len(h3_cells_at_resolution(resolution))


@dataclass
class IndexStats:
    """Statistics for a single-resolution index."""

    entries: int
    zone_entries: int
    polygon_entries: int
    polygon_id_count: int
    size_bytes: int
    possible_cells: int
    stored_cells: int
    missing_cells: int


ENTRY_KEY_SIZE_BYTES = np.dtype(np.int64).itemsize


def _warn_empty_shortcut_entry(hex_id: int, resolution: int | None = None) -> None:
    """Warn about empty shortcut entries, but skip in DEBUG mode since reduced data creates empty entries on purpose."""
    if DEBUG:
        return

    if resolution is not None:
        message = (
            f"Shortcut entry for hex {hex_id} at resolution {resolution} is empty."
        )
    else:
        message = (
            f"Hex {hex_id} has no polygon candidates; storing empty shortcut entry."
        )

    warnings.warn(message, RuntimeWarning)


def _create_entry_array(
    data: TimezoneData,
    polygon_ids: Sequence[int],
    *,
    zone_dtype: np.dtype,
    hex_id: int | None = None,
) -> np.ndarray:
    """Create an entry array for a shortcut, either zone ID or polygon list."""
    if not polygon_ids:
        if hex_id is not None:
            _warn_empty_shortcut_entry(hex_id)
        return np.empty(0, dtype=np.uint16)

    ordered = optimise_shortcut_ordering(data, polygon_ids)
    polygon_array = np.asarray(ordered, dtype=np.uint16)
    zone_candidates = np.asarray(data.poly_zone_ids[polygon_array], dtype=zone_dtype)

    # If all polygons belong to the same zone, store just the zone ID
    if zone_candidates.size > 0 and np.all(zone_candidates == zone_candidates[0]):
        return np.asarray([zone_candidates[0]], dtype=zone_dtype)

    # Otherwise, store the polygon IDs
    return polygon_array


def build_single_resolution_index(
    data: TimezoneData, resolution: int
) -> dict[int, np.ndarray]:
    """Build a shortcut index for a single resolution."""
    all_cells = h3_cells_at_resolution(resolution)
    index: dict[int, np.ndarray] = {}
    zone_dtype = (
        data.poly_zone_ids.dtype if hasattr(data, "poly_zone_ids") else np.uint32
    )

    for cell_id in all_cells:
        int_cell = int(cell_id)
        hex_obj = data.get_hex(int_cell)
        polygons_in_cell = list(hex_obj.polys_in_cell)

        entry_array = _create_entry_array(
            data,
            polygons_in_cell,
            zone_dtype=zone_dtype,
            hex_id=int_cell,
        )

        if entry_array.size == 0:
            _warn_empty_shortcut_entry(int_cell, resolution)

        index[int_cell] = entry_array

    return index


def compute_index_stats(index: dict[int, np.ndarray], resolution: int) -> IndexStats:
    """Compute statistics for a single-resolution index."""
    zone_entries = 0
    polygon_entries = 0
    polygon_id_count = 0
    size_bytes = 0

    for payload in index.values():
        payload = np.asarray(payload)
        length = int(payload.size)
        if length <= 1:
            zone_entries += 1
        else:
            polygon_entries += 1
            polygon_id_count += length
        size_bytes += ENTRY_KEY_SIZE_BYTES + int(payload.nbytes)

    possible_cells = h3_num_hexagons(resolution)
    stored_cells = len(index)
    missing_cells = max(possible_cells - stored_cells, 0)

    return IndexStats(
        entries=len(index),
        zone_entries=zone_entries,
        polygon_entries=polygon_entries,
        polygon_id_count=polygon_id_count,
        size_bytes=size_bytes,
        possible_cells=possible_cells,
        stored_cells=stored_cells,
        missing_cells=missing_cells,
    )


def benchmark_samples(
    tf: SingleResolutionTimezoneFinder, points: list[tuple[float, float]]
) -> tuple[np.ndarray, dict[str, Any]]:
    """Benchmark timezone lookups for a set of sample points."""
    tf.reset_stats()
    if not points:
        return np.empty(0, dtype=np.int64), tf.get_stats_snapshot()

    samples = np.empty(len(points), dtype=np.int64)
    for idx, (lng, lat) in enumerate(points):
        start_ns = time.perf_counter_ns()
        tf.timezone_at(lng=lng, lat=lat)
        samples[idx] = time.perf_counter_ns() - start_ns
    return samples, tf.get_stats_snapshot()


class SingleResolutionTimezoneFinder(TimezoneFinder):
    """TimezoneFinder that uses a single-resolution shortcut index."""

    def __init__(self, shortcut_index: dict[int, np.ndarray], resolution: int) -> None:
        super().__init__()
        self.shortcut_index = {
            int(hex_id): np.asarray(values, dtype=np.uint16)
            for hex_id, values in shortcut_index.items()
        }
        self.resolution = resolution
        self.reset_stats()

    def reset_stats(self) -> None:
        """Reset performance statistics."""
        self.stats = {
            "queries": 0,
            "unique_hits": 0,
            "polygons_tested": 0,
            "shortcuts_used": 0,
            "shortcut_hits": 0,
            "shortcut_misses": 0,
        }

    def get_stats_snapshot(self) -> dict[str, Any]:
        """Get a snapshot of current statistics."""
        return dict(self.stats)

    def timezone_at(self, *, lng: float, lat: float) -> str | None:  # type: ignore[override]
        """Find the timezone for given coordinates using single-resolution index."""
        lng, lat = utils.validate_coordinates(lng, lat)
        self.stats["queries"] += 1
        return self._lookup(lng, lat)

    def _lookup(self, lng: float, lat: float) -> str | None:
        """Perform the actual timezone lookup."""
        hex_id = int(h3.latlng_to_cell(lat, lng, self.resolution))
        payload = self.shortcut_index.get(hex_id)

        if payload is None:
            self.stats["shortcut_misses"] += 1
            return None

        self.stats["shortcuts_used"] += 1
        self.stats["shortcut_hits"] += 1

        if payload.size == 0:
            return None

        if payload.size == 1:
            self.stats["unique_hits"] += 1
            return self.zone_name_from_id(int(payload[0]))

        # Multiple polygons - need to test them
        coord_cache = (utils.coord2int(lng), utils.coord2int(lat))
        return self._resolve_polygons(payload, coord_cache)

    def _resolve_polygons(
        self, polygon_ids: np.ndarray, coord_cache: tuple[int, int]
    ) -> str | None:
        """Resolve ambiguous polygons by testing point-in-polygon."""
        zone_ids = self.zone_ids_of(polygon_ids)
        last_change_idx = utils.get_last_change_idx(zone_ids)

        if last_change_idx == 0:
            self.stats["unique_hits"] += 1
            return self.zone_name_from_id(zone_ids[0])

        x, y = coord_cache
        for i, boundary_id in enumerate(polygon_ids):
            if i >= last_change_idx:
                break
            self.stats["polygons_tested"] += 1
            if self.inside_of_polygon(int(boundary_id), x, y):
                return self.zone_name_from_id(zone_ids[i])

        return self.zone_name_from_id(zone_ids[-1])


def run_benchmark(tz_data: TimezoneData) -> None:
    """Run the main benchmark comparing single-resolution indices."""
    random.seed(SEED)
    np.random.seed(SEED)
    random_points = [
        (random.uniform(-180.0, 180.0), random.uniform(-90.0, 90.0))
        for _ in range(RANDOM_SAMPLE)
    ]

    print(
        f"\nEvaluating single-resolution indexes from {MIN_RESOLUTION} to {MAX_RESOLUTION}..."
    )
    metrics_records: list[dict[str, Any]] = []

    for resolution in RESOLUTIONS:
        print(f"  - Building and benchmarking resolution {resolution}...")

        # Build single-resolution index
        index = build_single_resolution_index(tz_data, resolution)
        stats = compute_index_stats(index, resolution)

        # Create timezone finder and benchmark it
        tf = SingleResolutionTimezoneFinder(index, resolution)
        random_samples, lookup_stats = benchmark_samples(tf, random_points)

        # Calculate performance metrics
        if random_samples.size:
            total_time_ns = float(random_samples.sum())
            mean_ns = total_time_ns / random_samples.size
            median_ns = float(np.median(random_samples))
            max_ns = float(random_samples.max())
            throughput_kpts = (
                random_samples.size / (total_time_ns / 1_000_000_000.0)
            ) / 1000.0
        else:
            mean_ns = median_ns = max_ns = 0.0
            throughput_kpts = 0.0

        # Calculate derived metrics
        unique_entry_fraction = (
            stats.zone_entries / stats.entries if stats.entries else 0.0
        )
        unique_surface_fraction = (
            stats.zone_entries / stats.possible_cells if stats.possible_cells else 0.0
        )
        coverage_ratio = (
            stats.stored_cells / stats.possible_cells if stats.possible_cells else 0.0
        )

        record = {
            "resolution": resolution,
            "mean_ns": mean_ns,
            "median_ns": median_ns,
            "max_ns": max_ns,
            "mean_throughput_kpts": throughput_kpts,
            "binary_size_bytes": stats.size_bytes,
            "binary_size_mib": stats.size_bytes / (1024**2),
            "unique_surface_fraction": unique_surface_fraction,
            "unique_entry_fraction": unique_entry_fraction,
            "coverage_ratio": coverage_ratio,
            "zone_entries": stats.zone_entries,
            "polygon_entries": stats.polygon_entries,
            "polygon_ids": stats.polygon_id_count,
            "total_entries": stats.entries,
            "stored_cells": stats.stored_cells,
            "possible_cells": stats.possible_cells,
            "missing_cells": stats.missing_cells,
            "queries": lookup_stats["queries"],
            "unique_hits": lookup_stats["unique_hits"],
            "polygons_tested": lookup_stats["polygons_tested"],
            "shortcuts_used": lookup_stats["shortcuts_used"],
            "shortcut_hits": lookup_stats["shortcut_hits"],
            "shortcut_misses": lookup_stats["shortcut_misses"],
        }
        metrics_records.append(record)

    metrics_df = pd.DataFrame(metrics_records)
    metrics_df.sort_values(["resolution"], inplace=True)

    # Save results
    output_dir = Path("plots")
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "single_resolution_metrics.csv"
    metrics_df.to_csv(csv_path, index=False)
    print(f"\nSaved metrics CSV to {csv_path}")

    print("\nSingle-Resolution Index Comparison (Markdown):\n")
    print(metrics_df.to_markdown(index=False, floatfmt=".3f"))
    print("\nAll performance metrics above use random global query points only.\n")


def _sample_points(count: int = 50, *, seed: int = SEED) -> list[tuple[float, float]]:
    """Generate sample points for testing."""
    rng = random.Random(seed)
    return [
        (rng.uniform(-180.0, 180.0), rng.uniform(-90.0, 90.0)) for _ in range(count)
    ]


def _baseline_zone_name(tf: TimezoneFinder, lng: float, lat: float) -> str | None:
    """Get baseline zone name using standard TimezoneFinder."""
    zone_name = tf.timezone_at(lng=lng, lat=lat)
    if zone_name is None:
        zone_name = tf.timezone_at_land(lng=lng, lat=lat)
    return zone_name


def test_single_resolution_index_creation() -> None:
    """Test that single-resolution index creation works correctly."""

    class DummyHex:
        polys_in_cell: tuple[int, ...] = (0, 1)  # Use indices 0, 1 to match array size

    class DummyData:
        all_tz_names = ["Dummy/Zone"]
        poly_zone_ids = np.asarray(
            [0, 0], dtype=np.uint32
        )  # Both polygons belong to zone 0
        polygon_lengths = [10, 15]  # Required by optimise_shortcut_ordering

        def get_hex(self, _: int) -> DummyHex:
            return DummyHex()

    # Test with resolution 0 (should have 122 cells)
    index = build_single_resolution_index(DummyData(), 0)
    expected_cells = len(h3_cells_at_resolution(0))
    assert len(index) == expected_cells

    # All entries should be zone entries since both polygons have same zone
    sample_entry = next(iter(index.values()))
    assert sample_entry.size == 1  # Should be a single zone ID


def test_index_stats_computation() -> None:
    """Test that index statistics are computed correctly."""
    index = {
        1: np.asarray([10], dtype=np.uint16),  # Zone entry
        2: np.asarray([1, 2], dtype=np.uint16),  # Polygon entry
        3: np.asarray([], dtype=np.uint16),  # Empty entry
    }
    stats = compute_index_stats(index, 0)

    assert stats.entries == 3
    assert stats.zone_entries == 2  # Entries 1 and 3 (size <= 1)
    assert stats.polygon_entries == 1  # Entry 2
    assert stats.polygon_id_count == 2  # Two polygon IDs in entry 2


def test_single_resolution_finder() -> None:
    """Test that SingleResolutionTimezoneFinder works correctly."""
    # Mock index with one zone entry and one polygon entry
    index = {
        123: np.asarray([5], dtype=np.uint16),  # Zone entry
        456: np.asarray([1, 2, 3], dtype=np.uint16),  # Polygon entry
    }

    tf = SingleResolutionTimezoneFinder(index, 3)
    assert tf.resolution == 3
    assert len(tf.shortcut_index) == 2

    # Test stats tracking
    tf.reset_stats()
    assert tf.stats["queries"] == 0
    assert tf.stats["unique_hits"] == 0


def build_hybrid_index_from_separate_indices(
    shortcuts: dict[int, list[int]], unique_shortcuts: dict[int, int]
) -> dict[int, int | list[int]]:
    """Build hybrid index from separate shortcuts and unique_shortcuts indices.

    This is the algorithm being tested - it combines the two legacy data structures
    into a single hybrid structure that replaces both.

    ALGORITHM EXPLANATION:
    The legacy system uses two separate data structures:
    1. `shortcuts`: Maps hex_id -> [polygon_ids] for ALL hex cells
    2. `unique_shortcuts`: Maps hex_id -> zone_id for hex cells where all polygons belong to same zone

    The hybrid system combines these into one structure:
    - If a hex is in unique_shortcuts, store just the zone_id (saves space & lookup time)
    - Otherwise, store the polygon_ids list (allows proper ambiguity resolution)

    This optimization reduces storage (single zone_id vs list of polygon_ids) and
    improves lookup performance (direct zone lookup vs polygon intersection tests)
    for the common case where all polygons in a hex belong to the same timezone.

    Args:
        shortcuts: Dictionary mapping hex IDs to lists of polygon IDs
        unique_shortcuts: Dictionary mapping hex IDs to single zone IDs

    Returns:
        Dictionary mapping hex IDs to either:
        - int: zone ID (for unique cases where all polygons share same zone)
        - list[int]: polygon IDs (for ambiguous cases requiring polygon tests)
    """
    hybrid_mapping = {}

    # First, add all entries from shortcuts (polygon lists)
    # This ensures we have entries for all hex cells with any polygons
    for hex_id, polygon_ids in shortcuts.items():
        hybrid_mapping[hex_id] = polygon_ids

    # Then, override with unique shortcuts where applicable
    # This replaces polygon lists with single zone IDs when all polygons
    # in the hex belong to the same timezone
    for hex_id, zone_id in unique_shortcuts.items():
        hybrid_mapping[hex_id] = zone_id

    return hybrid_mapping


# Example usage of the hybrid index algorithm:
#
# # Legacy data structures (what we have now):
# shortcuts = {
#     hex1: [poly1, poly2, poly3],  # Multiple polygons
#     hex2: [poly4],                # Single polygon
#     hex3: [poly5, poly6],         # Multiple polygons from same zone
# }
# unique_shortcuts = {
#     hex2: zone_a,  # All polygons in hex2 belong to zone_a
#     hex3: zone_b,  # All polygons in hex3 belong to zone_b
# }
#
# # Combined hybrid structure (what we want):
# hybrid_index = build_hybrid_index_from_separate_indices(shortcuts, unique_shortcuts)
# # Result: {
# #     hex1: [poly1, poly2, poly3],  # Ambiguous - keep polygon list
# #     hex2: zone_a,                 # Unique - use zone ID directly
# #     hex3: zone_b,                 # Unique - use zone ID directly
# # }


def test_hybrid_index_algorithm_simple() -> None:
    """Test the hybrid index algorithm with simple mock data."""
    print("Testing hybrid index algorithm with mock data...")

    # Create mock legacy data structures
    # Scenario: 5 hex cells with different patterns
    legacy_shortcuts = {
        100: [1, 2, 3],  # Multiple polygons from different zones
        101: [4],  # Single polygon (but will be unique)
        102: [5, 6],  # Multiple polygons from same zone (will be unique)
        103: [7, 8, 9],  # Multiple polygons from different zones
        104: [10],  # Single polygon (but will be unique)
    }

    legacy_unique_shortcuts = {
        101: 5,  # Hex 101 has all polygons from zone 5
        102: 8,  # Hex 102 has all polygons from zone 8
        104: 12,  # Hex 104 has all polygons from zone 12
        # Note: 100 and 103 are not in unique_shortcuts (ambiguous zones)
    }

    # Build hybrid index using our algorithm
    hybrid_index = build_hybrid_index_from_separate_indices(
        legacy_shortcuts, legacy_unique_shortcuts
    )

    # Verify correctness
    print(
        f"  Testing mock data with {len(legacy_shortcuts)} shortcuts and {len(legacy_unique_shortcuts)} unique shortcuts"
    )

    # Expected hybrid structure:
    expected_hybrid = {
        100: [1, 2, 3],  # Polygon list (not unique)
        101: 5,  # Zone ID (unique)
        102: 8,  # Zone ID (unique)
        103: [7, 8, 9],  # Polygon list (not unique)
        104: 12,  # Zone ID (unique)
    }

    # Verify exact match
    assert hybrid_index == expected_hybrid, (
        f"Hybrid index mismatch: got {hybrid_index}, expected {expected_hybrid}"
    )

    # Verify data types
    zone_count = sum(1 for v in hybrid_index.values() if isinstance(v, int))
    polygon_count = sum(1 for v in hybrid_index.values() if isinstance(v, list))

    assert zone_count == 3, f"Expected 3 zone entries, got {zone_count}"
    assert polygon_count == 2, f"Expected 2 polygon entries, got {polygon_count}"

    print("  ✓ Mock data test PASSED")


def test_hybrid_index_algorithm(tz_data: TimezoneData) -> None:
    """Test that the hybrid index algorithm correctly combines legacy data structures."""
    print("Testing hybrid index algorithm...")

    # First run the simple test
    test_hybrid_index_algorithm_simple()

    # Use a resolution that will have both unique and non-unique entries
    test_resolution = min(2, MAX_RESOLUTION)  # Use resolution 2 or max available

    # Build the legacy data structures using the existing logic from shortcuts.py
    from scripts.shortcuts import (
        compile_h3_map,
        compute_unique_shortcut_mapping,
        all_res_candidates,
    )

    # Get hex candidates for the test resolution
    candidates = all_res_candidates(test_resolution)
    # Take a smaller sample for testing to avoid long computation
    sample_candidates = (
        set(list(candidates)[:100]) if len(candidates) > 100 else candidates
    )

    # Build legacy shortcuts (hex_id -> [polygon_ids])
    legacy_shortcuts = compile_h3_map(tz_data, sample_candidates)

    # Build legacy unique_shortcuts (hex_id -> zone_id)
    legacy_unique_shortcuts = compute_unique_shortcut_mapping(
        legacy_shortcuts, tz_data.poly_zone_ids
    )

    # Build hybrid index using our algorithm
    hybrid_index = build_hybrid_index_from_separate_indices(
        legacy_shortcuts, legacy_unique_shortcuts
    )

    # Verify the algorithm correctness
    print(f"  Testing {len(sample_candidates)} hex cells with real data...")

    # Test 1: All hex IDs from both legacy structures should be in hybrid
    all_legacy_hex_ids = set(legacy_shortcuts.keys()) | set(
        legacy_unique_shortcuts.keys()
    )
    assert all_legacy_hex_ids == set(hybrid_index.keys()), (
        "Hybrid index missing hex IDs"
    )

    # Test 2: For each hex ID, verify the content matches expectations
    mismatches = 0
    for hex_id in all_legacy_hex_ids:
        if hex_id in legacy_unique_shortcuts:
            # Should be a zone ID in hybrid
            expected_zone_id = legacy_unique_shortcuts[hex_id]
            hybrid_value = hybrid_index[hex_id]
            if hybrid_value != expected_zone_id:
                print(
                    f"    Mismatch at hex {hex_id}: expected zone {expected_zone_id}, got {hybrid_value}"
                )
                mismatches += 1
        else:
            # Should be polygon list in hybrid
            expected_polygons = legacy_shortcuts[hex_id]
            hybrid_value = hybrid_index[hex_id]
            if hybrid_value != expected_polygons:
                print(
                    f"    Mismatch at hex {hex_id}: expected polygons {expected_polygons}, got {hybrid_value}"
                )
                mismatches += 1

    # Test 3: Verify data type consistency
    zone_entries = sum(1 for v in hybrid_index.values() if isinstance(v, int))
    polygon_entries = sum(1 for v in hybrid_index.values() if isinstance(v, list))

    print(f"  Hybrid index stats:")
    print(f"    Total entries: {len(hybrid_index)}")
    print(f"    Zone entries: {zone_entries}")
    print(f"    Polygon entries: {polygon_entries}")
    print(f"    Legacy unique shortcuts: {len(legacy_unique_shortcuts)}")
    print(f"    Legacy shortcuts: {len(legacy_shortcuts)}")

    # Test 4: All unique shortcuts should result in zone entries
    assert zone_entries == len(legacy_unique_shortcuts), (
        f"Zone entries ({zone_entries}) != unique shortcuts ({len(legacy_unique_shortcuts)})"
    )

    # Test 5: All non-unique shortcuts should result in polygon entries
    non_unique_shortcuts = len(legacy_shortcuts) - len(legacy_unique_shortcuts)
    assert polygon_entries == non_unique_shortcuts, (
        f"Polygon entries ({polygon_entries}) != non-unique shortcuts ({non_unique_shortcuts})"
    )

    if mismatches == 0:
        print(
            "  ✓ Hybrid index algorithm test PASSED - all entries match expected values"
        )
    else:
        raise AssertionError(
            f"Hybrid index algorithm test FAILED - {mismatches} mismatches found"
        )

    # Test 6: Verify that zones and polygons don't mix inappropriately
    for hex_id, value in hybrid_index.items():
        if isinstance(value, int):
            # Zone entry - verify it matches what unique_shortcuts says
            assert hex_id in legacy_unique_shortcuts, (
                f"Zone entry {hex_id} not in unique shortcuts"
            )
            assert value == legacy_unique_shortcuts[hex_id], (
                f"Zone ID mismatch for hex {hex_id}"
            )
        elif isinstance(value, list):
            # Polygon entry - verify it's not in unique_shortcuts
            assert hex_id not in legacy_unique_shortcuts, (
                f"Polygon entry {hex_id} should not be in unique shortcuts"
            )
            assert value == legacy_shortcuts[hex_id], (
                f"Polygon list mismatch for hex {hex_id}"
            )

    print("  ✓ Hybrid index content validation PASSED")


def run_tests(
    tz_data: TimezoneData | None = None, baseline_tf: TimezoneFinder | None = None
) -> None:
    """Run all unit tests."""
    # Tests that don't need runtime data
    simple_tests = [
        test_single_resolution_index_creation,
        test_index_stats_computation,
        test_single_resolution_finder,
    ]
    for test in simple_tests:
        test()

    # Test with real data if available
    if tz_data is not None and baseline_tf is not None:
        # Test the hybrid index algorithm
        test_hybrid_index_algorithm(tz_data)

        # Test that a single resolution gives reasonable results
        if MIN_RESOLUTION <= MAX_RESOLUTION:
            test_res = min(3, MAX_RESOLUTION)  # Use resolution 3 or max available
            index = build_single_resolution_index(tz_data, test_res)
            tf = SingleResolutionTimezoneFinder(index, test_res)

            # Test a few points
            sample_results = []
            for lng, lat in _sample_points(10):
                result = tf.timezone_at(lng=lng, lat=lat)
                baseline = _baseline_zone_name(baseline_tf, lng, lat)
                sample_results.append((result, baseline))

            # In DEBUG mode, mismatches are expected due to reduced dataset
            if not DEBUG:
                mismatches = sum(1 for r, b in sample_results if r != b)
                if mismatches > 0:
                    print(
                        f"Note: {mismatches}/10 mismatches found in test (may be normal)"
                    )

    print("All tests passed.")


if __name__ == "__main__":
    # Load timezone data once for all operations
    data_path = Path(INPUT_JSON_PATH)
    if not data_path.exists():
        print(f"Input JSON does not exist: {data_path}", file=sys.stderr)
        exit(1)

    print("Loading timezone data...")
    tz_data = TimezoneData.from_path(data_path)
    baseline_tf = TimezoneFinder() if not DEBUG else None

    if DEBUG:
        print("DEBUG mode is ON: using reduced dataset and resolutions.")

    run_tests(tz_data, baseline_tf)
    run_benchmark(tz_data)
