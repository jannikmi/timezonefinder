#!/usr/bin/env python3

"""Generate deterministic, committed benchmark input fixtures.

Benchmark numbers are only comparable between two runs (or two commits) if
they execute the exact same workload. This script draws that workload once,
with a fixed seed, and writes it to ``tests/fixtures/benchmarks/`` so it can
be committed and reused verbatim by ``scripts/check_speed_*.py``.

Usage:
    uv run python scripts/generate_benchmark_fixtures.py [--seed N] [--output-dir PATH]

Running the script twice with the same seed and output directory must
produce byte-identical files (verified by ``tests/test_benchmark_fixtures.py``).

The on-land/shortcut classification and ``pip_inputs`` polygon IDs are derived
from the currently installed boundary data, so the fixtures are pinned to the
repo-root ``DATA_VERSION`` file (recorded in ``metadata.json``). ``tests/auxiliaries.py``'s
loader refuses to load fixtures generated against a different data version.
``update_data.sh`` calls this script automatically after regenerating the
data, so ``make data`` keeps both in sync; run this script directly only when
just the fixtures (not the boundary data) need refreshing.
"""

import argparse
import json
import random
import sys
import warnings
from pathlib import Path

import numpy as np

# NOTE: timezonefinder internally uses the int-keyed H3 API (see
# timezonefinder.py: `from h3.api import numpy_int as h3`). shortcut_mapping
# keys are ints, so the plain (string-keyed) `h3` package must not be used
# here or every lookup below would silently miss.
from h3.api import numpy_int as h3

# allow running this script directly (`python scripts/generate_benchmark_fixtures.py`)
# without the project root being on sys.path already
_PROJECT_ROOT_STR = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT_STR not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT_STR)

from scripts.configs import DEBUG  # noqa: E402
from tests.auxiliaries import (  # noqa: E402
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
    BENCHMARK_FIXTURES_DIR,
    BENCHMARK_FIXTURES_METADATA_PATH,
    DATA_VERSION_FILE,
    ON_LAND_POINTS_FIXTURE,
    PIP_INPUTS_FIXTURE,
    PIP_STRATA_FIXTURE,
    RANDOM_POINTS_FIXTURE,
    UNIQUE_SHORTCUT_POINTS_FIXTURE,
    boundaries,
    get_rnd_query_pt,
)
from timezonefinder import TimezoneFinder  # noqa: E402
from timezonefinder.configs import SHORTCUT_H3_RES  # noqa: E402
from timezonefinder.utils import coord2int  # noqa: E402

DEFAULT_SEED = 42
DEFAULT_OUTPUT_DIR = BENCHMARK_FIXTURES_DIR
FIXTURE_VERSION = 1

N_RANDOM_POINTS = 10_000
N_ON_LAND_POINTS = 10_000
N_UNIQUE_SHORTCUT_POINTS = 5_000
N_AMBIGUOUS_SHORTCUT_POINTS = 5_000
N_PIP_INPUTS = 10_000

# order matters: index is the integer code stored in pip_strata.npy
PIP_STRATA = ("small", "medium", "large")
# polygon vertex-count percentiles splitting polygons into the strata above
PIP_STRATA_PERCENTILES = (50, 90)


def generate_random_points(rng: random.Random, n: int) -> list[tuple[float, float]]:
    print(f"generating {n:,} random points...")
    return [get_rnd_query_pt(rng) for _ in range(n)]


def generate_on_land_points(
    tf: TimezoneFinder, rng: random.Random, n: int
) -> list[tuple[float, float]]:
    print(
        f"generating {n:,} on-land points (rejection sampling, this takes a while)..."
    )
    points: list[tuple[float, float]] = []
    attempts = 0
    while len(points) < n:
        lng, lat = get_rnd_query_pt(rng)
        attempts += 1
        if tf.timezone_at_land(lng=lng, lat=lat) is not None:
            points.append((lng, lat))
    print(f"  found {n:,} on-land points in {attempts:,} attempts")
    return points


def generate_shortcut_points(
    tf: TimezoneFinder,
    rng: random.Random,
    n_unique: int,
    n_ambiguous: int,
) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """Classify random points by whether their H3 shortcut resolves to a
    unique zone (no PIP needed) or an ambiguous polygon array (PIP path)."""
    print(
        f"generating {n_unique:,} unique-shortcut and {n_ambiguous:,} "
        "ambiguous-shortcut points..."
    )
    unique_points: list[tuple[float, float]] = []
    ambiguous_points: list[tuple[float, float]] = []
    attempts = 0
    while len(unique_points) < n_unique or len(ambiguous_points) < n_ambiguous:
        lng, lat = get_rnd_query_pt(rng)
        attempts += 1
        hex_id = h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES)
        shortcut_value = tf.shortcut_mapping.get(hex_id)
        match shortcut_value:
            case None:
                continue
            case int():
                if len(unique_points) < n_unique:
                    unique_points.append((lng, lat))
            case _:
                if len(ambiguous_points) < n_ambiguous:
                    ambiguous_points.append((lng, lat))
    print(
        f"  classified {n_unique + n_ambiguous:,} shortcut points in {attempts:,} attempts"
    )
    return unique_points, ambiguous_points


def stratify_polygons_by_size() -> dict[str, np.ndarray]:
    """Split all polygon ids into small/medium/large buckets by vertex count."""
    n_polygons = len(boundaries)
    sizes = np.fromiter(
        (boundaries.coords_of(i).shape[1] for i in range(n_polygons)),
        dtype=np.int64,
        count=n_polygons,
    )
    p_low, p_high = np.percentile(sizes, PIP_STRATA_PERCENTILES)
    small_ids = np.where(sizes <= p_low)[0]
    medium_ids = np.where((sizes > p_low) & (sizes <= p_high))[0]
    large_ids = np.where(sizes > p_high)[0]
    strata = {"small": small_ids, "medium": medium_ids, "large": large_ids}
    for name, ids in strata.items():
        print(f"  stratum '{name}': {len(ids):,} polygons")
    return strata


def generate_pip_inputs(rng: random.Random, n: int) -> tuple[np.ndarray, np.ndarray]:
    """Generate (x, y, polygon_id) PIP benchmark inputs, stratified by
    polygon size so small/medium/large can be reported separately."""
    print(f"generating {n:,} stratified point-in-polygon inputs...")
    strata = stratify_polygons_by_size()

    pip_inputs = np.empty((n, 3), dtype=np.int64)
    pip_strata = np.empty(n, dtype=np.uint8)
    for i in range(n):
        stratum_code = i % len(PIP_STRATA)
        stratum_name = PIP_STRATA[stratum_code]
        poly_id = rng.choice(strata[stratum_name])
        lng, lat = get_rnd_query_pt(rng)
        x, y = coord2int(lng), coord2int(lat)
        pip_inputs[i] = (x, y, poly_id)
        pip_strata[i] = stratum_code
    return pip_inputs, pip_strata


def write_points_fixture(
    output_dir: Path, name: str, points: list[tuple[float, float]]
):
    arr = np.array(points, dtype=np.float64)
    np.save(output_dir / f"{name}.npy", arr)


def generate(
    seed: int,
    output_dir: Path,
    n_random: int = N_RANDOM_POINTS,
    n_on_land: int = N_ON_LAND_POINTS,
    n_unique: int = N_UNIQUE_SHORTCUT_POINTS,
    n_ambiguous: int = N_AMBIGUOUS_SHORTCUT_POINTS,
    n_pip: int = N_PIP_INPUTS,
) -> None:
    """Generate one full set of benchmark fixtures into ``output_dir``.

    The ``n_*`` arguments default to the production fixture sizes; tests pass
    smaller values to exercise (and diff) the generation logic quickly.
    """
    if DEBUG:
        warnings.warn(
            "scripts.configs.DEBUG is True: SHORTCUT_H3_RES is overridden for data "
            "generation scripts and the fixtures produced now are not valid for "
            "normal (non-debug) benchmark runs."
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    tf = TimezoneFinder(in_memory=True)

    random_points = generate_random_points(rng, n_random)
    write_points_fixture(output_dir, RANDOM_POINTS_FIXTURE, random_points)

    on_land_points = generate_on_land_points(tf, rng, n_on_land)
    write_points_fixture(output_dir, ON_LAND_POINTS_FIXTURE, on_land_points)

    unique_points, ambiguous_points = generate_shortcut_points(
        tf, rng, n_unique, n_ambiguous
    )
    write_points_fixture(output_dir, UNIQUE_SHORTCUT_POINTS_FIXTURE, unique_points)
    write_points_fixture(
        output_dir, AMBIGUOUS_SHORTCUT_POINTS_FIXTURE, ambiguous_points
    )

    pip_inputs, pip_strata = generate_pip_inputs(rng, n_pip)
    np.save(output_dir / f"{PIP_INPUTS_FIXTURE}.npy", pip_inputs)
    np.save(output_dir / f"{PIP_STRATA_FIXTURE}.npy", pip_strata)

    metadata = {
        "fixture_version": FIXTURE_VERSION,
        "seed": seed,
        "debug": DEBUG,
        "data_version": DATA_VERSION_FILE.read_text(encoding="utf-8").strip(),
        "shortcut_h3_res": SHORTCUT_H3_RES,
        "pip_strata": list(PIP_STRATA),
        "pip_strata_percentiles": list(PIP_STRATA_PERCENTILES),
        "counts": {
            RANDOM_POINTS_FIXTURE: len(random_points),
            ON_LAND_POINTS_FIXTURE: len(on_land_points),
            UNIQUE_SHORTCUT_POINTS_FIXTURE: len(unique_points),
            AMBIGUOUS_SHORTCUT_POINTS_FIXTURE: len(ambiguous_points),
            PIP_INPUTS_FIXTURE: len(pip_inputs),
        },
    }
    metadata_path = output_dir / BENCHMARK_FIXTURES_METADATA_PATH.name
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2, sort_keys=True)
        f.write("\n")

    print(f"\nWrote benchmark fixtures to {output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate deterministic benchmark input fixtures."
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Random seed for fixture generation (default: {DEFAULT_SEED})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory to write fixture files to (default: {DEFAULT_OUTPUT_DIR})",
    )
    args = parser.parse_args()
    generate(args.seed, args.output_dir)


if __name__ == "__main__":
    main()
