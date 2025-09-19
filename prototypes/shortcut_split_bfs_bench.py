"""Benchmark hierarchical H3 shortcut indices with combined zone/polygon entries.

This script builds hierarchical shortcut maps for every start resolution from
0 to ``MAX_RESOLUTION`` (inclusive). Each shortcut entry stores either a single
zone identifier (unique hit) or a list of polygon ids for ambiguous cells. The
resulting index is benchmarked against the baseline ``TimezoneFinder`` using
10,000 "on land" points and 10,000 globally random points, and the output
summarises throughput, shortcut hit statistics, storage costs, and comparisons
with single-resolution indexes.

Run with::

    uv run python prototypes/shortcut_split_bfs_bench.py
"""

from __future__ import annotations

import random
import statistics
import sys
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence
from functools import lru_cache

import h3.api.numpy_int as h3
import numpy as np

from scripts.configs import DEFAULT_INPUT_PATH
from scripts.shortcuts import optimise_shortcut_ordering
from scripts.timezone_data import TimezoneData
from timezonefinder import utils
from timezonefinder.timezonefinder import TimezoneFinder

# Resolutions above 5 are intentionally excluded because the index size explodes.
MAX_RESOLUTION = 5
START_RESOLUTIONS = range(MAX_RESOLUTION + 1)
ON_LAND_SAMPLE = 10_000
RANDOM_SAMPLE = 10_000
SEED = 42
INPUT_JSON_PATH = DEFAULT_INPUT_PATH


@lru_cache(maxsize=None)
def h3_cells_at_resolution(resolution: int) -> frozenset[int]:
    if resolution < 0:
        raise ValueError("H3 resolution must be non-negative")
    if resolution == 0:
        return frozenset(int(cell) for cell in h3.get_res0_cells())
    parent_cells = h3_cells_at_resolution(resolution - 1)
    children: set[int] = set()
    for parent in parent_cells:
        for child in h3.cell_to_children(parent):
            children.add(int(child))
    return frozenset(children)


def h3_num_hexagons(resolution: int) -> int:
    return len(h3_cells_at_resolution(resolution))


@dataclass
class BFSConfig:
    start_res: int
    max_depth: int = MAX_RESOLUTION


def snapshot_stats(stats: dict[str, Any]) -> dict[str, Any]:
    copied = dict(stats)
    res_checks = copied.get("res_checks")
    if res_checks is not None:
        copied["res_checks"] = dict(res_checks)
    return copied


@dataclass
class EvaluationResult:
    start_res: int
    index: dict[int, dict[int, np.ndarray]]
    stats: IndexStats
    on_land_mean: float
    on_land_std: float
    on_land_stats: dict[str, Any]
    random_mean: float
    random_std: float
    random_stats: dict[str, Any]
    checks_per_res: dict[int, float]
    single_res_metrics: dict[int, ResolutionBenchmark]


@dataclass
class ResolutionBenchmark:
    on_land_mean: float
    on_land_std: float
    on_land_stats: dict[str, Any]
    random_mean: float
    random_std: float
    random_stats: dict[str, Any]
    checks_per_res: dict[int, float]
    size_bytes: int
    stats: IndexStats


@dataclass
class IndexStats:
    entries_per_res: dict[int, int]
    zone_entries_per_res: dict[int, int]
    polygon_entries_per_res: dict[int, int]
    polygon_id_counts_per_res: dict[int, int]
    size_per_res: dict[int, int]
    total_size_bytes: int
    possible_counts_per_res: dict[int, int]
    stored_counts_per_res: dict[int, int]
    missing_counts_per_res: dict[int, int]


def _create_entry_array(
    data: TimezoneData,
    polygon_ids: Sequence[int],
) -> tuple[np.ndarray | None, bool]:
    if not polygon_ids:
        return None, True

    ordered = optimise_shortcut_ordering(data, polygon_ids)
    polygon_array = np.asarray(ordered, dtype=np.uint32)
    zone_candidates = data.poly_zone_ids[polygon_array]
    zone_candidates = np.asarray(zone_candidates, dtype=np.uint32)

    if zone_candidates.size > 0 and np.all(zone_candidates == zone_candidates[0]):
        zone_entry = np.asarray([zone_candidates[0]], dtype=np.uint32)
        return zone_entry, True

    return polygon_array, False


def build_hierarchical_index(
    data: TimezoneData,
    cfg: BFSConfig,
) -> dict[int, dict[int, np.ndarray]]:
    queue: deque[tuple[int, int]] = deque(
        (0, int(res0_hex)) for res0_hex in h3.get_res0_cells()
    )
    hierarchical: dict[int, dict[int, np.ndarray]] = defaultdict(dict)

    while queue:
        res, hex_id = queue.popleft()
        if res > cfg.max_depth:
            continue

        entries_for_res = hierarchical[res]
        if hex_id in entries_for_res:
            continue

        hex_obj = data.get_hex(hex_id)
        polygons_in_cell = list(hex_obj.polys_in_cell)
        entry_array, is_unique = _create_entry_array(data, polygons_in_cell)

        if res >= cfg.start_res and entry_array is not None:
            entries_for_res[hex_id] = entry_array

        if (not is_unique) and polygons_in_cell and res < cfg.max_depth:
            for child in h3.cell_to_children(hex_id):
                queue.append((res + 1, int(child)))

    return {res: dict(entries) for res, entries in hierarchical.items()}


def compute_index_stats(index: dict[int, dict[int, np.ndarray]]) -> IndexStats:
    entries_per_res: dict[int, int] = {}
    zone_entries_per_res: dict[int, int] = {}
    polygon_entries_per_res: dict[int, int] = {}
    polygon_id_counts_per_res: dict[int, int] = {}
    size_per_res: dict[int, int] = {}
    possible_counts_per_res: dict[int, int] = {}
    stored_counts_per_res: dict[int, int] = {}
    missing_counts_per_res: dict[int, int] = {}

    total_size_bytes = 0

    for res in range(MAX_RESOLUTION + 1):
        entries = index.get(res, {})
        zone_entries = 0
        polygon_entries = 0
        polygon_id_count = 0
        size_bytes = 0

        for payload in entries.values():
            payload = np.asarray(payload)
            length = int(payload.size)
            if length <= 1:
                zone_entries += 1
                size_bytes += 1
            else:
                polygon_entries += 1
                polygon_id_count += length
                size_bytes += 2 * length

        entries_per_res[res] = len(entries)
        zone_entries_per_res[res] = zone_entries
        polygon_entries_per_res[res] = polygon_entries
        polygon_id_counts_per_res[res] = polygon_id_count
        size_per_res[res] = size_bytes
        total_size_bytes += size_bytes

        possible = h3_num_hexagons(res)
        possible_counts_per_res[res] = possible
        stored_counts_per_res[res] = len(entries)
        missing_counts_per_res[res] = max(possible - len(entries), 0)

    return IndexStats(
        entries_per_res=entries_per_res,
        zone_entries_per_res=zone_entries_per_res,
        polygon_entries_per_res=polygon_entries_per_res,
        polygon_id_counts_per_res=polygon_id_counts_per_res,
        size_per_res=size_per_res,
        total_size_bytes=total_size_bytes,
        possible_counts_per_res=possible_counts_per_res,
        stored_counts_per_res=stored_counts_per_res,
        missing_counts_per_res=missing_counts_per_res,
    )


def extract_single_resolution(
    index: dict[int, dict[int, np.ndarray]], res: int
) -> dict[int, dict[int, np.ndarray]]:
    if res not in index:
        return {}
    return {res: dict(index[res])}


def collect_random_points(
    tf: TimezoneFinder, count: int, on_land: bool
) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    while len(points) < count:
        lng = random.uniform(-180.0, 180.0)
        lat = random.uniform(-90.0, 90.0)
        if not on_land or tf.timezone_at_land(lng=lng, lat=lat) is not None:
            points.append((lng, lat))
    return points


class HierarchicalTimezoneFinder(TimezoneFinder):
    def __init__(
        self,
        hierarchical_shortcuts: dict[int, dict[int, np.ndarray]],
        *,
        max_depth: int,
    ) -> None:
        super().__init__()
        self.hierarchical_shortcuts = {
            res: {
                int(hex_id): np.asarray(values, dtype=np.uint32)
                for hex_id, values in entries.items()
            }
            for res, entries in hierarchical_shortcuts.items()
        }
        self.resolutions_desc = sorted(self.hierarchical_shortcuts.keys(), reverse=True)
        self.max_depth = max_depth
        self.single_resolution_res = (
            self.resolutions_desc[0] if len(self.resolutions_desc) == 1 else None
        )
        self.reset_stats()

    def reset_stats(self) -> None:
        self.stats = {
            "queries": 0,
            "unique_hits": 0,
            "polygons_tested": 0,
            "shortcuts_used": 0,
            "res_checks": defaultdict(int),
        }

    def timezone_at(self, *, lng: float, lat: float) -> str | None:  # type: ignore[override]
        lng, lat = utils.validate_coordinates(lng, lat)
        self.stats["queries"] += 1

        if self.single_resolution_res is not None:
            return self._lookup_single(lng, lat, self.single_resolution_res)

        for res in self.resolutions_desc:
            mapping = self.hierarchical_shortcuts.get(res)
            if not mapping:
                continue
            hex_id = int(h3.latlng_to_cell(lat, lng, res))
            possible_boundaries = mapping.get(hex_id)
            if possible_boundaries is None:
                continue

            self.stats["shortcuts_used"] += 1
            self.stats["res_checks"][res] += 1

            if possible_boundaries.size <= 1:
                if possible_boundaries.size == 1:
                    self.stats["unique_hits"] += 1
                    zone_id = int(possible_boundaries[0])
                    return self.zone_name_from_id(zone_id)
                continue

            zone_ids = self.zone_ids_of(possible_boundaries)
            last_change_idx = utils.get_last_change_idx(zone_ids)
            if last_change_idx == 0:
                self.stats["unique_hits"] += 1
                return self.zone_name_from_id(zone_ids[0])

            x = utils.coord2int(lng)
            y = utils.coord2int(lat)
            for i, boundary_id in enumerate(possible_boundaries):
                if i >= last_change_idx:
                    break
                self.stats["polygons_tested"] += 1
                if self.inside_of_polygon(int(boundary_id), x, y):
                    zone_id = zone_ids[i]
                    return self.zone_name_from_id(zone_id)

            zone_id = zone_ids[-1]
            return self.zone_name_from_id(zone_id)

        return None

    def _lookup_single(self, lng: float, lat: float, res: int) -> str | None:
        mapping = self.hierarchical_shortcuts.get(res)
        if not mapping:
            return None
        hex_id = int(h3.latlng_to_cell(lat, lng, res))
        payload = mapping.get(hex_id)
        if payload is None:
            return None
        self.stats["shortcuts_used"] += 1
        self.stats["res_checks"][res] += 1

        if payload.size <= 1:
            if payload.size == 1:
                self.stats["unique_hits"] += 1
                return self.zone_name_from_id(int(payload[0]))
            return None

        zone_ids = self.zone_ids_of(payload)
        last_change_idx = utils.get_last_change_idx(zone_ids)
        if last_change_idx == 0:
            self.stats["unique_hits"] += 1
            return self.zone_name_from_id(zone_ids[0])

        x = utils.coord2int(lng)
        y = utils.coord2int(lat)
        for i, boundary_id in enumerate(payload):
            if i >= last_change_idx:
                break
            self.stats["polygons_tested"] += 1
            if self.inside_of_polygon(int(boundary_id), x, y):
                zone_id = zone_ids[i]
                return self.zone_name_from_id(zone_id)

        zone_id = zone_ids[-1]
        return self.zone_name_from_id(zone_id)


def benchmark(
    tf: TimezoneFinder, points: list[tuple[float, float]]
) -> tuple[float, float]:
    timings = []
    for _ in range(3):
        start = time.perf_counter()
        for lng, lat in points:
            _ = tf.timezone_at(lng=lng, lat=lat)
        end = time.perf_counter()
        timings.append((end - start) / len(points))
    mean = statistics.mean(timings)
    stdev = statistics.stdev(timings) if len(timings) > 1 else 0.0
    return mean, stdev


def evaluate_start_resolution(
    data: TimezoneData,
    cfg: BFSConfig,
    *,
    on_land_points: list[tuple[float, float]],
    random_points: list[tuple[float, float]],
) -> EvaluationResult:
    index = build_hierarchical_index(data, cfg)
    stats = compute_index_stats(index)

    on_land_stats: dict[str, Any] = {}
    random_stats: dict[str, Any] = {}
    on_land_mean = float("nan")
    on_land_std = 0.0
    random_mean = float("nan")
    random_std = 0.0
    checks_per_res: dict[int, float] = {}
    single_metrics: dict[int, ResolutionBenchmark] = {}

    if index:
        hierarchical_tf = HierarchicalTimezoneFinder(index, max_depth=cfg.max_depth)

        hierarchical_tf.reset_stats()
        on_land_mean, on_land_std = benchmark(hierarchical_tf, on_land_points)
        on_land_stats = snapshot_stats(hierarchical_tf.stats)

        hierarchical_tf.reset_stats()
        random_mean, random_std = benchmark(hierarchical_tf, random_points)
        random_stats = snapshot_stats(hierarchical_tf.stats)
        random_queries = max(random_stats.get("queries", 1), 1)
        checks_per_res = {
            res: total_checks / random_queries
            for res, total_checks in random_stats.get("res_checks", {}).items()
        }

    for res in sorted(index.keys()):
        single_map = extract_single_resolution(index, res)
        single_stats = compute_index_stats(single_map)
        single_tf = HierarchicalTimezoneFinder(single_map, max_depth=res)

        single_tf.reset_stats()
        single_on_land_mean, single_on_land_std = benchmark(single_tf, on_land_points)
        single_on_land_stats = snapshot_stats(single_tf.stats)

        single_tf.reset_stats()
        single_random_mean, single_random_std = benchmark(single_tf, random_points)
        single_random_stats = snapshot_stats(single_tf.stats)
        single_random_queries = max(single_random_stats.get("queries", 1), 1)
        single_checks = {
            r: cnt / single_random_queries
            for r, cnt in single_random_stats.get("res_checks", {}).items()
        }

        single_metrics[res] = ResolutionBenchmark(
            on_land_mean=single_on_land_mean,
            on_land_std=single_on_land_std,
            on_land_stats=single_on_land_stats,
            random_mean=single_random_mean,
            random_std=single_random_std,
            random_stats=single_random_stats,
            checks_per_res=single_checks,
            size_bytes=single_stats.total_size_bytes,
            stats=single_stats,
        )

    return EvaluationResult(
        start_res=cfg.start_res,
        index=index,
        stats=stats,
        on_land_mean=on_land_mean,
        on_land_std=on_land_std,
        on_land_stats=on_land_stats,
        random_mean=random_mean,
        random_std=random_std,
        random_stats=random_stats,
        checks_per_res=checks_per_res,
        single_res_metrics=single_metrics,
    )


def run_benchmark() -> None:
    data_path = Path(INPUT_JSON_PATH)
    if not data_path.exists():
        print(f"Input JSON does not exist: {data_path}", file=sys.stderr)
        return

    print("Loading timezone data...")
    tz_data = TimezoneData.from_path(data_path)

    print("\nInitialising baseline TimezoneFinder...")
    baseline_tf = TimezoneFinder()

    random.seed(SEED)
    np.random.seed(SEED)
    on_land_points = collect_random_points(baseline_tf, ON_LAND_SAMPLE, on_land=True)
    random_points = collect_random_points(baseline_tf, RANDOM_SAMPLE, on_land=False)

    print("\nBenchmarking baseline...")
    base_on_land_mean, _ = benchmark(baseline_tf, on_land_points)
    base_random_mean, _ = benchmark(baseline_tf, random_points)

    results: list[EvaluationResult] = []
    print("\nBuilding hierarchical indexes...")
    for start_res in START_RESOLUTIONS:
        print(f"  - start resolution {start_res}")
        cfg = BFSConfig(start_res=start_res, max_depth=MAX_RESOLUTION)
        result = evaluate_start_resolution(
            tz_data,
            cfg,
            on_land_points=on_land_points,
            random_points=random_points,
        )
        results.append(result)

    def fmt_ns(mean: float) -> float:
        return mean * 1e9

    def format_row(
        name: str,
        base_mean: float,
        hier_mean: float,
        stats: dict[str, Any],
    ) -> str:
        queries = max(stats.get("queries", 1), 1)
        unique_rate = stats.get("unique_hits", 0) / queries
        polys_per_query = stats.get("polygons_tested", 0) / queries
        speedup = base_mean / hier_mean if hier_mean else float("nan")
        return (
            f"| {name} | {fmt_ns(base_mean):>9.1f} | {fmt_ns(hier_mean):>12.1f} | "
            f"{speedup:>7.3f} | {unique_rate:>13.2%} | {polys_per_query:>21.2f} |"
        )

    print("\n# Hierarchical Shortcut Benchmark")
    print()
    requested = ", ".join(str(res) for res in START_RESOLUTIONS)
    print(f"*Input JSON:* `{data_path}`")
    print(f"*Max resolution:* {MAX_RESOLUTION}")
    print(f"*Start resolutions:* {requested}")
    print()

    for result in results:
        stats = result.stats
        total_entries = sum(stats.entries_per_res.values())
        total_zone_entries = sum(stats.zone_entries_per_res.values())
        total_polygon_entries = sum(stats.polygon_entries_per_res.values())
        total_polygon_ids = sum(stats.polygon_id_counts_per_res.values())
        total_possible = sum(stats.possible_counts_per_res.values())
        total_stored = sum(stats.stored_counts_per_res.values())
        total_missing = sum(stats.missing_counts_per_res.values())
        coverage_ratio = (total_stored / total_possible) if total_possible else 0.0
        size_mib = stats.total_size_bytes / (1024 * 1024)

        print(f"## Start resolution {result.start_res}\n")
        print(f"*Total size:* {size_mib:.2f} MiB")
        print(
            f"*Entries:* {total_entries:,} (zones: {total_zone_entries:,}, polygons: {total_polygon_entries:,}, polygon ids: {total_polygon_ids:,})"
        )
        print(
            f"*Coverage:* {total_stored:,} / {total_possible:,} cells ({coverage_ratio:.2%})"
            + ("  ⚠️" if total_missing else "")
        )
        print()

        print("### Throughput (ns/query)\n")
        print(
            "| Dataset | Baseline | Hierarchical | Speedup | Unique hit rate | Polygons tested/query |"
        )
        print(
            "|---------|----------|--------------|---------|-----------------|-----------------------|"
        )
        print(
            format_row(
                "On land", base_on_land_mean, result.on_land_mean, result.on_land_stats
            )
        )
        print(
            format_row(
                "Random", base_random_mean, result.random_mean, result.random_stats
            )
        )
        print()

        if result.checks_per_res:
            print("### Average shortcut checks per query (random dataset)\n")
            print("| Resolution | Checks/query |")
            print("|-----------:|-------------:|")
            for res, avg in sorted(result.checks_per_res.items()):
                print(f"| {res:>10} | {avg:>11.2f} |")
            print()

        print("### Resolutions and entry composition\n")
        print(
            "| Resolution | Zone entries | Polygon entries | Polygon ids | Stored | Possible | Size bytes |"
        )
        print(
            "|-----------:|-------------:|----------------:|------------:|-------:|----------:|-----------:|"
        )
        for res in range(MAX_RESOLUTION + 1):
            zones = stats.zone_entries_per_res.get(res, 0)
            polygons = stats.polygon_entries_per_res.get(res, 0)
            polygon_ids = stats.polygon_id_counts_per_res.get(res, 0)
            stored = stats.stored_counts_per_res.get(res, 0)
            possible = stats.possible_counts_per_res.get(res, 0)
            size_bytes = stats.size_per_res.get(res, 0)
            print(
                f"| {res:>10} | {zones:>13} | {polygons:>14} | {polygon_ids:>10} | {stored:>6} | {possible:>8} | {size_bytes:>11} |"
            )
        print()

        if result.single_res_metrics:
            print("### Single-resolution counterparts (random dataset)\n")
            print(
                "| Resolution | Hier ns/query | Single ns/query | Speedup (single/hier) | "
                "Hier checks/query | Single checks/query | Single size MiB |"
            )
            print(
                "|-----------:|--------------:|----------------:|----------------------:|"
                "------------------:|--------------------:|-----------------:|"
            )
            for res in sorted(result.single_res_metrics.keys()):
                single = result.single_res_metrics[res]
                hier_ns = fmt_ns(result.random_mean)
                single_ns = fmt_ns(single.random_mean)
                speed = (
                    single.random_mean / result.random_mean
                    if result.random_mean
                    else float("nan")
                )
                hier_checks = result.checks_per_res.get(res, 0.0)
                single_checks = single.checks_per_res.get(res, 0.0)
                single_mib = single.size_bytes / (1024 * 1024)
                print(
                    f"| {res:>10} | {hier_ns:>12.1f} | {single_ns:>14.1f} | "
                    f"{speed:>22.3f} | {hier_checks:>18.2f} | {single_checks:>20.2f} | {single_mib:>15.2f} |"
                )
            print()

            print("### Single-resolution counterparts (on land dataset)\n")
            print(
                "| Resolution | Hier ns/query | Single ns/query | Speedup (single/hier) |"
            )
            print(
                "|-----------:|--------------:|----------------:|----------------------:|"
            )
            for res in sorted(result.single_res_metrics.keys()):
                single = result.single_res_metrics[res]
                hier_ns = fmt_ns(result.on_land_mean)
                single_ns = fmt_ns(single.on_land_mean)
                speed = (
                    single.on_land_mean / result.on_land_mean
                    if result.on_land_mean
                    else float("nan")
                )
                print(
                    f"| {res:>10} | {hier_ns:>12.1f} | {single_ns:>14.1f} | {speed:>22.3f} |"
                )
            print()

    if len(results) > 1:
        print("## Start resolution comparison\n")
        print(
            "| Start res | Size MiB | Zone entries | Polygon entries | Polygon ids | Coverage | On land ns | Speedup | Random ns | Speedup | Checks/query (res) |"
        )
        print(
            "|----------:|---------:|-------------:|----------------:|------------:|---------:|-----------:|--------:|----------:|--------:|---------------------:|"
        )
        for result in results:
            stats = result.stats
            size_mib = stats.total_size_bytes / (1024 * 1024)
            total_zone_entries = sum(stats.zone_entries_per_res.values())
            total_polygon_entries = sum(stats.polygon_entries_per_res.values())
            total_polygon_ids = sum(stats.polygon_id_counts_per_res.values())
            total_possible = sum(stats.possible_counts_per_res.values())
            total_stored = sum(stats.stored_counts_per_res.values())
            coverage_ratio = (total_stored / total_possible) if total_possible else 0.0
            land_speedup = (
                base_on_land_mean / result.on_land_mean
                if result.on_land_mean
                else float("nan")
            )
            random_speedup = (
                base_random_mean / result.random_mean
                if result.random_mean
                else float("nan")
            )
            checks_repr = (
                ", ".join(
                    f"r{res}:{avg:.2f}"
                    for res, avg in sorted(result.checks_per_res.items())
                )
                or "-"
            )
            print(
                f"| {result.start_res:>9} | {size_mib:>7.2f} | {total_zone_entries:>13} | {total_polygon_entries:>16} | {total_polygon_ids:>10} | {coverage_ratio:>7.2%} | "
                f"{fmt_ns(result.on_land_mean):>10.1f} | {land_speedup:>7.3f} | {fmt_ns(result.random_mean):>9.1f} | {random_speedup:>7.3f} | {checks_repr:>19} |"
            )
        print()


def test_compute_index_stats_counts() -> None:
    index = {
        0: {
            1: np.asarray([10], dtype=np.uint32),
            2: np.asarray([1, 2], dtype=np.uint32),
        },
        1: {3: np.asarray([4, 5, 6], dtype=np.uint32)},
    }
    stats = compute_index_stats(index)
    assert stats.zone_entries_per_res[0] == 1
    assert stats.polygon_entries_per_res[0] == 1
    assert stats.size_per_res[0] == 1 + 2 * 2
    assert stats.polygon_entries_per_res[1] == 1
    assert stats.polygon_id_counts_per_res[1] == 3


def test_extract_single_resolution() -> None:
    index = {
        0: {1: np.asarray([7], dtype=np.uint32)},
        2: {5: np.asarray([9, 10], dtype=np.uint32)},
    }
    extracted = extract_single_resolution(index, 2)
    assert 2 in extracted and 0 not in extracted
    assert extracted[2][5].tolist() == [9, 10]


def test_snapshot_stats_copies_nested_dict() -> None:
    stats = {"res_checks": {0: 1}}
    snap = snapshot_stats(stats)
    assert snap == {"res_checks": {0: 1}}
    snap["res_checks"][0] = 99
    assert stats["res_checks"][0] == 1


def run_tests() -> None:
    tests = [
        test_compute_index_stats_counts,
        test_extract_single_resolution,
        test_snapshot_stats_copies_nested_dict,
    ]
    for test in tests:
        test()
    print("All tests passed.")


RUN_TESTS = False


if __name__ == "__main__":
    if RUN_TESTS:
        run_tests()
    run_benchmark()
