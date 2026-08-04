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
import random

import numpy as np
import pytest

from scripts import generate_benchmark_fixtures as fixture_gen
from tests.auxiliaries import (
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
    BENCHMARK_FIXTURES_METADATA_PATH,
    ON_LAND_POINTS_FIXTURE,
    RANDOM_POINTS_FIXTURE,
    UNIQUE_SHORTCUT_POINTS_FIXTURE,
    BenchmarkFixtureError,
    boundaries,
    get_pip_test_input,
    get_rnd_poly_int,
    get_rnd_query_pt,
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
    assert set(strata) == {"small", "medium", "large"}


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
