"""Benchmark hierarchical H3 shortcut indices with combined zone/polygon entries.

This script builds hierarchical shortcut maps for every start resolution from
0 to ``MAX_RESOLUTION`` (inclusive). Each shortcut entry stores either a single
zone identifier (unique hit) or a list of polygon ids for ambiguous cells. The
resulting index is benchmarked against a single set of 10,000 globally random
query points; all throughput and latency statistics reported below originate
from this random dataset.

Run with::

    uv run python prototypes/shortcut_split_bfs_bench.py
"""

from __future__ import annotations

import random
import sys
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Sequence

import h3.api.numpy_int as h3
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.configs import DEFAULT_INPUT_PATH
from scripts.shortcuts import optimise_shortcut_ordering
from scripts.timezone_data import TimezoneData
from timezonefinder import utils
from timezonefinder.timezonefinder import TimezoneFinder

# Resolutions above 5 are intentionally excluded because the index size explodes.
MAX_RESOLUTION = 7
MIN_RESOLUTION = (
    4  # resolution 0 (122 cells) offers no unique-zone benefit in DEBUG dataset
)
RESOLUTIONS = range(MIN_RESOLUTION, MAX_RESOLUTION + 1)
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
    min_res: int
    max_res: int = MAX_RESOLUTION


def snapshot_stats(stats: dict[str, Any]) -> dict[str, Any]:
    copied = dict(stats)
    res_checks = copied.get("res_checks")
    if res_checks is not None:
        copied["res_checks"] = dict(res_checks)
    return copied


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
    is_unique: bool,
) -> np.ndarray | None:
    if not polygon_ids:
        return None

    ordered = optimise_shortcut_ordering(data, polygon_ids)
    polygon_array = np.asarray(ordered, dtype=np.uint16)

    if is_unique:
        zone_candidates = data.poly_zone_ids[polygon_array]
        zone_candidates = np.asarray(zone_candidates, dtype=np.uint16)
        if zone_candidates.size > 0:
            zone_entry = np.asarray([zone_candidates[0]], dtype=np.uint16)
            return zone_entry

    return polygon_array


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
        if res > cfg.max_res:
            continue

        entries_for_res = hierarchical[res]
        if hex_id in entries_for_res:
            continue

        hex_obj = data.get_hex(hex_id)
        zones_in_cell = hex_obj.zones_in_cell
        is_unique = len(zones_in_cell) <= 1
        polygons_in_cell = list(hex_obj.polys_in_cell)
        entry_array = _create_entry_array(data, polygons_in_cell, is_unique)

        if cfg.min_res <= res <= cfg.max_res and entry_array is not None:
            entries_for_res[hex_id] = entry_array

        if (not is_unique) and polygons_in_cell and res < cfg.max_res:
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


def aggregate_stats_for_range(
    stats: IndexStats, min_res: int, max_res: int
) -> dict[str, float]:
    zone_entries = 0
    polygon_entries = 0
    polygon_ids = 0
    total_entries = 0
    stored_cells = 0
    possible_cells = 0
    size_bytes = 0
    unique_surface_fraction = 0.0

    for res in range(min_res, max_res + 1):
        zone = stats.zone_entries_per_res.get(res, 0)
        polygon = stats.polygon_entries_per_res.get(res, 0)
        possible = stats.possible_counts_per_res.get(res, 0)
        stored = stats.stored_counts_per_res.get(res, 0)

        zone_entries += zone
        polygon_entries += polygon
        total_entries += zone + polygon
        stored_cells += stored
        possible_cells += possible
        polygon_ids += stats.polygon_id_counts_per_res.get(res, 0)
        size_bytes += stats.size_per_res.get(res, 0)

        if possible:
            unique_surface_fraction += zone / possible

    unique_entry_fraction = zone_entries / total_entries if total_entries else 0.0
    coverage_ratio = stored_cells / possible_cells if possible_cells else 0.0

    return {
        "zone_entries": zone_entries,
        "polygon_entries": polygon_entries,
        "polygon_ids": polygon_ids,
        "total_entries": total_entries,
        "stored_cells": stored_cells,
        "possible_cells": possible_cells,
        "size_bytes": size_bytes,
        "unique_surface_fraction": unique_surface_fraction,
        "unique_entry_fraction": unique_entry_fraction,
        "coverage_ratio": coverage_ratio,
    }


def benchmark_samples(
    tf: HierarchicalTimezoneFinder, points: list[tuple[float, float]]
) -> tuple[np.ndarray, dict[str, Any]]:
    tf.reset_stats()
    if not points:
        return np.empty(0, dtype=np.int64), snapshot_stats(tf.stats)

    samples = np.empty(len(points), dtype=np.int64)
    for idx, (lng, lat) in enumerate(points):
        start_ns = time.perf_counter_ns()
        tf.timezone_at(lng=lng, lat=lat)
        samples[idx] = time.perf_counter_ns() - start_ns
    return samples, snapshot_stats(tf.stats)


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
                int(hex_id): np.asarray(values, dtype=np.uint16)
                for hex_id, values in entries.items()
            }
            for res, entries in hierarchical_shortcuts.items()
        }
        self.resolutions_desc = sorted(self.hierarchical_shortcuts.keys(), reverse=True)
        self.max_depth = max_depth
        self._single_res = (
            self.resolutions_desc[0] if len(self.resolutions_desc) == 1 else None
        )
        self._lookup_fn = (
            self._lookup_single if self._single_res is not None else self._lookup_multi
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
        return self._lookup_fn(lng, lat)

    def _lookup_single(self, lng: float, lat: float) -> str | None:
        res = self._single_res
        if res is None:
            return None
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

    def _lookup_multi(self, lng: float, lat: float) -> str | None:
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


def run_benchmark() -> None:
    data_path = Path(INPUT_JSON_PATH)
    if not data_path.exists():
        print(f"Input JSON does not exist: {data_path}", file=sys.stderr)
        return

    print("Loading timezone data...")
    tz_data = TimezoneData.from_path(data_path)

    random.seed(SEED)
    np.random.seed(SEED)
    random_points = [
        (random.uniform(-180.0, 180.0), random.uniform(-90.0, 90.0))
        for _ in range(RANDOM_SAMPLE)
    ]

    total_combinations = sum(
        1 for min_res in RESOLUTIONS for max_res in range(min_res, MAX_RESOLUTION + 1)
    )

    metrics_records: list[dict[str, Any]] = []
    print("\nEvaluating hierarchical indexes across resolution ranges...")
    combo_index = 1
    for min_res in RESOLUTIONS:
        for max_res in range(min_res, MAX_RESOLUTION + 1):
            print(
                f"  - Combination {combo_index}/{total_combinations}: min_res={min_res}, max_res={max_res}"
            )
            combo_index += 1

            cfg = BFSConfig(min_res=min_res, max_res=max_res)
            index = build_hierarchical_index(tz_data, cfg)
            stats = compute_index_stats(index)
            aggregated = aggregate_stats_for_range(stats, min_res, max_res)

            tf = HierarchicalTimezoneFinder(index, max_depth=max_res)
            random_samples, _ = benchmark_samples(tf, random_points)

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

            record = {
                "min_res": min_res,
                "max_res": max_res,
                "mean_ns": mean_ns,
                "median_ns": median_ns,
                "max_ns": max_ns,
                "mean_throughput_kpts": throughput_kpts,
                "binary_size_bytes": aggregated["size_bytes"],
                "unique_surface_fraction": aggregated["unique_surface_fraction"],
                "unique_entry_fraction": aggregated["unique_entry_fraction"],
                "zone_entries": aggregated["zone_entries"],
                "polygon_entries": aggregated["polygon_entries"],
                "polygon_ids": aggregated["polygon_ids"],
                "total_entries": aggregated["total_entries"],
                "coverage_ratio": aggregated["coverage_ratio"],
                "stored_cells": aggregated["stored_cells"],
                "possible_cells": aggregated["possible_cells"],
            }
            for res, count in tf.stats["res_checks"].items():
                record[f"res_checks_r{res}"] = count
            metrics_records.append(record)

    metrics_df = pd.DataFrame(metrics_records)
    metrics_df.sort_values(["min_res", "max_res"], inplace=True)

    for res in RESOLUTIONS:
        col = f"res_checks_r{res}"
        if col not in metrics_df.columns:
            metrics_df[col] = 0
        else:
            metrics_df[col] = metrics_df[col].fillna(0)

    metrics_df["binary_size_mib"] = metrics_df["binary_size_bytes"] / (1024**2)

    output_dir = Path("plots")
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "hierarchical_metrics.csv"
    metrics_df.to_csv(csv_path, index=False)
    print(f"\nSaved metrics CSV to {csv_path}")

    print("\nMetrics table (Markdown):\n")
    print(metrics_df.to_markdown(index=False, floatfmt=".3f"))
    print("\nAll performance metrics above use random global query points only.\n")

    heatmap_specs = [
        ("mean_throughput_kpts", "Average throughput (random queries; k/s)"),
        ("median_ns", "Median latency (random queries; ns)"),
        ("max_ns", "Max latency (random queries; ns)"),
        ("binary_size_mib", "Binary size (MiB)"),
        ("unique_surface_fraction", "Unique surface fraction (sum)"),
        ("unique_entry_fraction", "Unique entry fraction"),
    ]

    for res in RESOLUTIONS:
        heatmap_specs.append(
            (f"res_checks_r{res}", f"Shortcut checks at resolution {res}")
        )

    sns.set_theme(style="white")
    print("\nGenerating heatmaps...")
    for column, title in heatmap_specs:
        pivot = metrics_df.pivot(index="min_res", columns="max_res", values=column)
        pivot = pivot.reindex(index=sorted(metrics_df["min_res"].unique()))
        pivot = pivot.reindex(columns=sorted(metrics_df["max_res"].unique()))

        mask = np.zeros_like(pivot, dtype=bool)
        for i, min_res in enumerate(pivot.index):
            for j, max_res in enumerate(pivot.columns):
                if max_res < min_res:
                    mask[i, j] = True

        plt.figure(figsize=(8, 6))
        sns.heatmap(
            pivot,
            mask=mask,
            cmap="viridis",
            annot=False,
            cbar_kws={"label": title},
        )
        plt.title(title)
        plt.xlabel("max_res")
        plt.ylabel("min_res")
        plt.tight_layout()
        heatmap_path = output_dir / f"heatmap_{column}.png"
        plt.savefig(heatmap_path, dpi=200)
        plt.close()
        print(f"  - Saved {heatmap_path}")


def test_compute_index_stats_counts() -> None:
    index = {
        0: {
            1: np.asarray([10], dtype=np.uint16),
            2: np.asarray([1, 2], dtype=np.uint16),
        },
        1: {3: np.asarray([4, 5, 6], dtype=np.uint16)},
    }
    stats = compute_index_stats(index)
    assert stats.zone_entries_per_res[0] == 1
    assert stats.polygon_entries_per_res[0] == 1
    assert stats.size_per_res[0] == 1 + 2 * 2
    assert stats.polygon_entries_per_res[1] == 1
    assert stats.polygon_id_counts_per_res[1] == 3


def test_extract_single_resolution() -> None:
    index = {
        0: {1: np.asarray([7], dtype=np.uint16)},
        2: {5: np.asarray([9, 10], dtype=np.uint16)},
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
