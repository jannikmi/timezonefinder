"""Tests for the deterministic benchmark fixtures and their loader/generator.

Covers:
- seeded variants of the random test-input generators stay reproducible
  while the unseeded (default) variants keep drawing from global ``random``
- the fixture loader API (tests/auxiliaries.py) raises clear, actionable
  errors when fixtures are missing or stale, and loads the committed
  fixtures correctly
- the generator script (scripts/generate_benchmark_fixtures.py) is
  idempotent: same seed -> byte-identical files
"""

import json
import math
import random

import numpy as np
import pytest

from scripts import generate_benchmark_fixtures as fixture_gen
from scripts.configs import read_data_version
from tests.auxiliaries import (
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
    BENCHMARK_FIXTURES_METADATA_PATH,
    FIXTURE_VERSION,
    ON_LAND_POINTS_FIXTURE,
    PIP_INPUTS_FIXTURE,
    PIP_STRATA,
    PIP_STRATA_FIXTURE,
    RANDOM_POINTS_FIXTURE,
    UNIQUE_SHORTCUT_POINTS_FIXTURE,
    BenchmarkFixtureError,
    boundaries,
    get_pip_test_input,
    get_rnd_poly_int,
    get_rnd_query_pt,
    get_rnd_query_pt_area_weighted,
    group_pip_inputs_by_stratum,
    load_benchmark_points,
    load_pip_inputs,
    load_pip_strata,
)
from timezonefinder.configs import (
    MAX_LAT_VAL,
    MAX_LAT_VAL_INT,
    MAX_LNG_VAL,
    MAX_LNG_VAL_INT,
)

pytestmark = pytest.mark.unit


#######################
# SEEDED GENERATORS
#######################


def test_get_rnd_query_pt_seeded_is_reproducible():
    a = [get_rnd_query_pt(random.Random(42)) for _ in range(20)]
    b = [get_rnd_query_pt(random.Random(42)) for _ in range(20)]
    assert a == b


def test_get_rnd_query_pt_seeded_differs_for_other_seed():
    a = [get_rnd_query_pt(random.Random(1)) for _ in range(20)]
    b = [get_rnd_query_pt(random.Random(2)) for _ in range(20)]
    assert a != b


def test_get_rnd_query_pt_unseeded_within_valid_range():
    for _ in range(20):
        lng, lat = get_rnd_query_pt()
        assert -MAX_LNG_VAL <= lng <= MAX_LNG_VAL
        assert -MAX_LAT_VAL <= lat <= MAX_LAT_VAL


def test_get_rnd_poly_int_seeded_is_reproducible():
    a = [get_rnd_poly_int(random.Random(42)).shape for _ in range(20)]
    b = [get_rnd_poly_int(random.Random(42)).shape for _ in range(20)]
    assert a == b


def test_get_pip_test_input_seeded_is_reproducible():
    rng_a = random.Random(42)
    rng_b = random.Random(42)
    for _ in range(20):
        x1, y1, poly1 = get_pip_test_input(rng_a)
        x2, y2, poly2 = get_pip_test_input(rng_b)
        assert (x1, y1) == (x2, y2)
        assert np.array_equal(poly1, poly2)


#######################
# FIXTURE LOADER
#######################


def test_load_benchmark_points_missing_fixture_raises(monkeypatch, tmp_path):
    monkeypatch.setattr("tests.auxiliaries.BENCHMARK_FIXTURES_DIR", tmp_path)
    monkeypatch.setattr(
        "tests.auxiliaries.BENCHMARK_FIXTURES_METADATA_PATH",
        tmp_path / BENCHMARK_FIXTURES_METADATA_PATH.name,
    )
    with pytest.raises(BenchmarkFixtureError, match="make benchmark-fixtures"):
        load_benchmark_points(RANDOM_POINTS_FIXTURE)


def test_load_pip_inputs_missing_fixture_raises(monkeypatch, tmp_path):
    monkeypatch.setattr("tests.auxiliaries.BENCHMARK_FIXTURES_DIR", tmp_path)
    monkeypatch.setattr(
        "tests.auxiliaries.BENCHMARK_FIXTURES_METADATA_PATH",
        tmp_path / BENCHMARK_FIXTURES_METADATA_PATH.name,
    )
    with pytest.raises(BenchmarkFixtureError, match="make benchmark-fixtures"):
        load_pip_inputs()


def test_load_benchmark_points_debug_mismatch_raises(monkeypatch, tmp_path):
    metadata_path = tmp_path / BENCHMARK_FIXTURES_METADATA_PATH.name
    metadata_path.write_text(json.dumps({"debug": True, "pip_strata": []}))
    (tmp_path / f"{RANDOM_POINTS_FIXTURE}.npy").touch()
    monkeypatch.setattr("tests.auxiliaries.BENCHMARK_FIXTURES_DIR", tmp_path)
    monkeypatch.setattr(
        "tests.auxiliaries.BENCHMARK_FIXTURES_METADATA_PATH", metadata_path
    )
    monkeypatch.setattr("tests.auxiliaries.DEBUG", False)
    with pytest.raises(BenchmarkFixtureError, match="DEBUG"):
        load_benchmark_points(RANDOM_POINTS_FIXTURE)


def test_load_benchmark_points_data_version_mismatch_raises(monkeypatch, tmp_path):
    metadata_path = tmp_path / BENCHMARK_FIXTURES_METADATA_PATH.name
    metadata_path.write_text(
        json.dumps({"debug": False, "data_version": "2000a", "pip_strata": []})
    )
    (tmp_path / f"{RANDOM_POINTS_FIXTURE}.npy").touch()
    monkeypatch.setattr("tests.auxiliaries.BENCHMARK_FIXTURES_DIR", tmp_path)
    monkeypatch.setattr(
        "tests.auxiliaries.BENCHMARK_FIXTURES_METADATA_PATH", metadata_path
    )
    monkeypatch.setattr("tests.auxiliaries.DEBUG", False)
    with pytest.raises(BenchmarkFixtureError, match="data_version|DATA_VERSION"):
        load_benchmark_points(RANDOM_POINTS_FIXTURE)


def _write_metadata(tmp_path, monkeypatch, **overrides):
    """Metadata that clears the DEBUG and data_version checks, so the
    rejection under test is the one that fires rather than an earlier one."""
    metadata_path = tmp_path / BENCHMARK_FIXTURES_METADATA_PATH.name
    metadata = {
        "debug": False,
        "data_version": read_data_version(),
        "fixture_version": FIXTURE_VERSION,
        "point_sampler": get_rnd_query_pt_area_weighted.__name__,
        "pip_strata": [],
    }
    metadata.update(overrides)
    metadata_path.write_text(json.dumps(metadata))
    (tmp_path / f"{RANDOM_POINTS_FIXTURE}.npy").touch()
    monkeypatch.setattr("tests.auxiliaries.BENCHMARK_FIXTURES_DIR", tmp_path)
    monkeypatch.setattr(
        "tests.auxiliaries.BENCHMARK_FIXTURES_METADATA_PATH", metadata_path
    )
    monkeypatch.setattr("tests.auxiliaries.DEBUG", False)


def test_load_benchmark_points_fixture_version_mismatch_raises(monkeypatch, tmp_path):
    # fixtures produced by older generation logic (different sampler, counts
    # or rng ordering) describe a workload the current code does not assume
    _write_metadata(tmp_path, monkeypatch, fixture_version=FIXTURE_VERSION - 1)
    with pytest.raises(BenchmarkFixtureError, match="fixture logic version"):
        load_benchmark_points(RANDOM_POINTS_FIXTURE)


def test_load_benchmark_points_sampler_mismatch_raises(monkeypatch, tmp_path):
    _write_metadata(tmp_path, monkeypatch, point_sampler="get_rnd_query_pt")
    with pytest.raises(BenchmarkFixtureError, match="point sampler"):
        load_benchmark_points(RANDOM_POINTS_FIXTURE)


# Share of an area-uniform sample lying above |60| latitude: 1 - sin(60 deg).
# The naive uniform-in-latitude sampler yields 33.3% instead, so this is what
# actually catches a regression to `get_rnd_query_pt` in the generator -
# `test_load_benchmark_points_loads_committed_fixtures` below only bounds
# checks the coordinates and cannot notice a distribution change at all.
EXPECTED_HIGH_LAT_SHARE = 1 - math.sin(math.radians(60))
# ~4 sigma over 10,000 points: fails on the naive sampler by a mile, but
# never flakes on a legitimate reseed
HIGH_LAT_SHARE_TOLERANCE = 0.015


def test_committed_random_points_are_area_uniform():
    points = load_benchmark_points(RANDOM_POINTS_FIXTURE)
    high_lat_share = sum(1 for _, lat in points if abs(lat) > 60) / len(points)
    assert high_lat_share == pytest.approx(
        EXPECTED_HIGH_LAT_SHARE, abs=HIGH_LAT_SHARE_TOLERANCE
    ), (
        f"{high_lat_share:.1%} of the committed random points lie above |60| "
        f"latitude, but an area-uniform sample gives {EXPECTED_HIGH_LAT_SHARE:.1%}. "
        "The fixtures were probably generated with `get_rnd_query_pt` (uniform "
        "in latitude, oversamples the poles ~2.5x) rather than "
        "`get_rnd_query_pt_area_weighted`."
    )


@pytest.mark.parametrize(
    "name,expected_count",
    [
        (RANDOM_POINTS_FIXTURE, 10_000),
        (ON_LAND_POINTS_FIXTURE, 10_000),
        (UNIQUE_SHORTCUT_POINTS_FIXTURE, 5_000),
        (AMBIGUOUS_SHORTCUT_POINTS_FIXTURE, 5_000),
    ],
)
def test_load_benchmark_points_loads_committed_fixtures(name, expected_count):
    points = load_benchmark_points(name)
    assert len(points) == expected_count
    for lng, lat in points:
        assert -MAX_LNG_VAL <= lng <= MAX_LNG_VAL
        assert -MAX_LAT_VAL <= lat <= MAX_LAT_VAL


def test_load_pip_inputs_loads_committed_fixture():
    pip_inputs = load_pip_inputs()
    assert len(pip_inputs) == 10_000
    max_poly_id = len(boundaries) - 1
    for x, y, poly_id in pip_inputs:
        assert -MAX_LNG_VAL_INT <= x <= MAX_LNG_VAL_INT
        assert -MAX_LAT_VAL_INT <= y <= MAX_LAT_VAL_INT
        assert 0 <= poly_id <= max_poly_id


def test_load_pip_inputs_rejects_out_of_range_polygon_ids(monkeypatch):
    # simulate the currently loaded boundary data having fewer polygons than
    # the committed fixture references (e.g. after a data update where
    # DATA_VERSION was, hypothetically, not bumped)
    class _TinyBoundaries:
        def __len__(self):
            return 1

    monkeypatch.setattr("tests.auxiliaries.boundaries", _TinyBoundaries())
    with pytest.raises(BenchmarkFixtureError, match="polygon id"):
        load_pip_inputs()


def test_load_pip_strata_matches_pip_inputs():
    pip_inputs = load_pip_inputs()
    strata = load_pip_strata()
    assert len(strata) == len(pip_inputs)
    assert set(strata) == set(PIP_STRATA)


#######################
# PIP STRATUM GROUPING
#######################

# small enough to keep these fast; the grouping is size-independent, and the
# production BATCH_SIZE is exercised whenever the benchmark suite runs
GROUPING_BATCH_SIZE = 5


def _labelled_inputs(strata: list[str]) -> list[tuple[int, int, int]]:
    """PIP inputs for the given labels, all pointing at polygon 0."""
    return [(0, 0, 0) for _ in strata]


def test_group_pip_inputs_by_stratum_fills_every_stratum():
    grouped = group_pip_inputs_by_stratum(
        load_pip_inputs(), load_pip_strata(), GROUPING_BATCH_SIZE
    )
    assert set(grouped) == set(PIP_STRATA)
    for bucket in grouped.values():
        assert len(bucket) == GROUPING_BATCH_SIZE


def test_group_pip_inputs_by_stratum_rejects_length_mismatch():
    strata = [PIP_STRATA[0]] * GROUPING_BATCH_SIZE
    with pytest.raises(ValueError, match=PIP_STRATA_FIXTURE):
        group_pip_inputs_by_stratum(
            _labelled_inputs(strata)[:-1], strata, GROUPING_BATCH_SIZE
        )


def test_group_pip_inputs_by_stratum_rejects_unknown_stratum():
    strata = ["enormous"] * GROUPING_BATCH_SIZE
    with pytest.raises(ValueError, match="unknown strata"):
        group_pip_inputs_by_stratum(
            _labelled_inputs(strata), strata, GROUPING_BATCH_SIZE
        )


def test_group_pip_inputs_by_stratum_rejects_missing_stratum():
    # a stratum absent from the fixture altogether: it never becomes a key, so
    # only an expectation stated up front can notice it is gone
    present, first_missing = PIP_STRATA[0], PIP_STRATA[1]
    strata = [present] * GROUPING_BATCH_SIZE
    with pytest.raises(ValueError, match=f"'{first_missing}' entries"):
        group_pip_inputs_by_stratum(
            _labelled_inputs(strata), strata, GROUPING_BATCH_SIZE
        )


def test_group_pip_inputs_by_stratum_rejects_short_stratum():
    strata = [stratum for stratum in PIP_STRATA for _ in range(GROUPING_BATCH_SIZE)]
    with pytest.raises(ValueError, match=PIP_INPUTS_FIXTURE):
        group_pip_inputs_by_stratum(
            _labelled_inputs(strata), strata, GROUPING_BATCH_SIZE + 1
        )


def test_benchmark_fixtures_dir_is_committed():
    # sanity check that the fixtures actually live where the loader expects
    assert BENCHMARK_FIXTURES_METADATA_PATH.exists()


#######################
# GENERATOR IDEMPOTENCY
#######################


@pytest.mark.slow
def test_generator_is_idempotent_for_same_seed(tmp_path):
    out_a = tmp_path / "run_a"
    out_b = tmp_path / "run_b"

    # small counts to keep this fast; the logic under test is identical
    # regardless of size
    kwargs = dict(
        seed=7, n_random=50, n_on_land=20, n_unique=20, n_ambiguous=20, n_pip=30
    )
    fixture_gen.generate(output_dir=out_a, **kwargs)
    fixture_gen.generate(output_dir=out_b, **kwargs)

    files_a = sorted(p.name for p in out_a.iterdir())
    files_b = sorted(p.name for p in out_b.iterdir())
    assert files_a == files_b

    for name in files_a:
        assert (out_a / name).read_bytes() == (out_b / name).read_bytes(), (
            f"{name} differs between two runs with the same seed"
        )


@pytest.mark.slow
def test_generator_differs_for_different_seed(tmp_path):
    out_a = tmp_path / "run_a"
    out_b = tmp_path / "run_b"

    kwargs = dict(n_random=50, n_on_land=20, n_unique=20, n_ambiguous=20, n_pip=30)
    fixture_gen.generate(seed=1, output_dir=out_a, **kwargs)
    fixture_gen.generate(seed=2, output_dir=out_b, **kwargs)

    random_points_filename = f"{RANDOM_POINTS_FIXTURE}.npy"
    assert (out_a / random_points_filename).read_bytes() != (
        out_b / random_points_filename
    ).read_bytes()
