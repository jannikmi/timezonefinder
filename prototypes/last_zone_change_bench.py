"""Benchmark for precomputing last-zone-change indices on realistic queries.

Run via: ``uv run python scripts/prototypes/last_zone_change_bench.py``.

We mirror the access patterns from ``scripts/check_speed_timezone_finding.py``
to understand whether storing the ``last_zone_change_idx`` per shortcut helps.

The script collects two datasets of query coordinates (10k "on land" and 10k
random), runs the baseline code path that calls
``utils.get_last_change_idx`` on the fly, and compares it to three
precomputation strategies:

* ``dict`` – current prototype with a ``dict[int, int]`` lookup.
* ``tuple`` – assumes the index is stored alongside each shortcut entry (no
  extra lookup required).

For each dataset it reports per-applicable-query and amortised costs plus
storage estimates. Latest findings (on the shipped dataset):

* On-land amortised cost drops from ~236 ns (baseline) to ~184 ns with the
  tuple approach; dict gives ~226 ns. Random traffic shows a similar ~40 ns
  win.
* Absolute improvement in ``timezone_at`` throughput is <1 % because the
  PIP step still dominates the 5–8 µs per query budget.
* The tuple approach is the only one that meaningfully improves lookup cost.

Findings:
For “on land” traffic, caching the index alongside the shortcut entry (the tuple approach) cuts the applicable lookups from ~807 ns down to ~657 ns. Once you factor in that only ~28 % of queries actually need that index, the amortised gain is about 40–50 ns per call.
For uniformly random traffic, the amortised gain is ~38 ns per call.
TimezoneFinder.timezone_at() spends roughly 5–8 µs per query (the current line profiles show ~7.7 µs on land and ~5.4 µs on random). Shaving 40 ns off the hot path therefore translates to well under 1 % end-to-end improvement—below the noise floor of the full benchmark and unlikely to show up as a measurable bump in points/sec.

So technically the tuple approach is faster for the specific operation, but in practice the overall throughput is dominated by the point-in-polygon work.
"""

from __future__ import annotations

import statistics
import time
from typing import Iterable, Sequence

import numpy as np

import random

from timezonefinder.configs import (
    DEFAULT_DATA_DIR,
    SHORTCUT_H3_RES,
    MAX_LAT_VAL,
    MAX_LNG_VAL,
)
from timezonefinder.flatbuf.io.shortcuts import (
    get_shortcut_file_path,
    read_shortcuts_binary,
)
from timezonefinder.np_binary_helpers import get_zone_ids_path, read_per_polygon_vector
from timezonefinder import utils
from timezonefinder.timezonefinder import TimezoneFinder
from h3.api import numpy_int as h3


def build_precomputed_indices(
    shortcuts: dict[int, np.ndarray],
    zone_ids: np.ndarray,
) -> dict[int, int]:
    """Return hex -> last_zone_change_idx mapping."""

    result: dict[int, int] = {}
    for hex_id, poly_ids in shortcuts.items():
        if len(poly_ids) == 0:
            result[hex_id] = 0
            continue
        zones = zone_ids[poly_ids]
        result[hex_id] = int(utils.get_last_change_idx(zones))
    return result


def collect_points(
    tf: TimezoneFinder, count: int, on_land: bool
) -> list[tuple[float, float]]:
    """Collect query points similar to the check_speed_timezone_finding benchmark."""

    points: list[tuple[float, float]] = []
    attempts = 0
    while len(points) < count:
        lng = random.uniform(-MAX_LNG_VAL, MAX_LNG_VAL)
        lat = random.uniform(-MAX_LAT_VAL, MAX_LAT_VAL)
        attempts += 1
        if not on_land or tf.timezone_at_land(lng=lng, lat=lat) is not None:
            points.append((lng, lat))
    return points


def build_cases(
    tf: TimezoneFinder, points: Iterable[tuple[float, float]]
) -> list[tuple[int, np.ndarray]]:
    """Return (hex_id, polygon_ids) for queries that need last_change_idx."""

    cases: list[tuple[int, np.ndarray]] = []
    for lng, lat in points:
        hex_id = h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES)
        poly_ids = tf.shortcut_mapping[hex_id]
        if len(poly_ids) <= 1:
            continue
        unique_zone_id = tf.unique_shortcut_zone_ids.get(hex_id)
        if unique_zone_id is not None:
            continue
        cases.append((hex_id, poly_ids))
    return cases


def time_lookup(
    tf: TimezoneFinder,
    cases: Sequence[tuple[int, np.ndarray]],
    mode: str,
    *,
    dict_lookup: dict[int, int] | None = None,
    tuple_values: Sequence[int] | None = None,
    repeats: int = 5,
) -> float:
    """Return mean nanoseconds per applicable lookup for the chosen strategy."""

    durations: list[float] = []
    for _ in range(repeats):
        start = time.perf_counter()
        acc = 0
        for idx, (hex_id, poly_ids) in enumerate(cases):
            zone_ids = tf.zone_ids_of(poly_ids)
            if mode == "baseline":
                acc += utils.get_last_change_idx(zone_ids)
            elif mode == "dict":
                acc += dict_lookup[hex_id]  # type: ignore[index]
            elif mode == "tuple":
                acc += tuple_values[idx]  # type: ignore[index]
            else:
                raise ValueError(mode)
        end = time.perf_counter()
        durations.append((end - start) / max(len(cases), 1))
    mean = statistics.mean(durations)
    return mean * 1e9


def main() -> None:
    data_dir = DEFAULT_DATA_DIR
    print(f"Using data directory: {data_dir}")

    shortcuts = read_shortcuts_binary(get_shortcut_file_path(data_dir))
    zone_ids = read_per_polygon_vector(get_zone_ids_path(data_dir))

    print("Building precomputed last-change indices...")
    precomputed = build_precomputed_indices(shortcuts, zone_ids)
    print(f"Computed {len(precomputed):,} entries")

    # correctness spot-check
    mismatches = 0
    for hex_id, poly_ids in list(shortcuts.items())[:10_000]:
        zones = zone_ids[poly_ids]
        expected = utils.get_last_change_idx(zones)
        if precomputed[hex_id] != expected:
            mismatches += 1
            break
    if mismatches:
        raise AssertionError("Precomputed indices do not match runtime computation")

    print("Collecting realistic query samples (10k on land, 10k random)...")
    random.seed(42)
    np.random.seed(42)
    tf = TimezoneFinder()
    on_land_points = collect_points(tf, 10_000, on_land=True)
    random_points = collect_points(tf, 10_000, on_land=False)

    datasets = {
        "on_land": on_land_points,
        "random": random_points,
    }

    for name, pts in datasets.items():
        cases = build_cases(tf, pts)
        applicable = len(cases)
        if applicable == 0:
            print(f"\nDataset '{name}': no multi-zone shortcuts encountered; skipping")
            continue
        tuple_values = [precomputed[hex_id] for hex_id, _ in cases]

        baseline_ns = time_lookup(tf, cases, "baseline")
        dict_ns = time_lookup(tf, cases, "dict", dict_lookup=precomputed)
        tuple_ns = time_lookup(
            tf,
            cases,
            "tuple",
            tuple_values=tuple_values,
        )
        total_queries = len(pts)
        baseline_overall = baseline_ns * applicable / total_queries
        dict_overall = dict_ns * applicable / total_queries
        tuple_overall = tuple_ns * applicable / total_queries

        print(f"\nDataset '{name}'")
        print(f"  total queries            : {total_queries:,}")
        print(f"  requiring last_change_idx: {applicable:,}")
        print(
            "  per applicable query     : "
            f"baseline {baseline_ns:8.2f} ns | dict {dict_ns:8.2f} ns | "
            f"tuple {tuple_ns:8.2f} ns"
        )
        print(
            "  amortised per query      : "
            f"baseline {baseline_overall:8.2f} ns | dict {dict_overall:8.2f} ns | "
            f"tuple {tuple_overall:8.2f} ns"
        )

    # storage estimates: dictionary integers vs potential FlatBuffer array
    bytes_per_entry = 8 + 2  # approx: uint64 key + uint16 value (typical range)
    dict_payload = len(precomputed) * bytes_per_entry
    array_payload = len(precomputed) * 2  # storing uint16 values densely

    print("\nStorage footprint estimates")
    print(f"  dict payload (rough): {dict_payload:,} bytes")
    print(f"  compact array payload: {array_payload:,} bytes")
    print("  tuple-with-polygons  : ~0 bytes extra (stored alongside shortcut entry)")


if __name__ == "__main__":
    main()
