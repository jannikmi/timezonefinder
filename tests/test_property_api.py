"""Property-based tests for the public timezone-lookup API.

Uses ``hypothesis`` to exercise ``timezone_at``, ``timezone_at_land``,
``unique_timezone_at``, ``certain_timezone_at`` and ``get_geometry``
with randomly generated coordinates, complementing the example-based
tests in ``tests/main_test.py``.

The lookup functions are comparatively expensive (polygon-in-point
checks), so every test in this module is marked as ``slow``. The
``_LOOKUP_SETTINGS`` keep the deadline permissive and silence the
``too_slow`` health check; ``max_examples`` is left at the hypothesis
default but can be reduced locally for faster feedback.
"""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from timezonefinder import (
    TimezoneFinder,
    certain_timezone_at,
    get_geometry,
    timezone_at,
    timezone_at_land,
    unique_timezone_at,
)

# Mark all tests in this module as slow
pytestmark = pytest.mark.slow

# A single shared TimezoneFinder instance gives access to the canonical list
# of valid timezone names without paying for singleton lookups in every test.
_TF = TimezoneFinder()
_VALID_NAMES = frozenset(_TF.timezone_names)

# Finite in-range coordinates. NaN/Inf are excluded because they are invalid
# inputs that the API rejects with ValueError.
_VALID_LNG = st.floats(
    min_value=-180.0, max_value=180.0, allow_nan=False, allow_infinity=False
)
_VALID_LAT = st.floats(
    min_value=-90.0, max_value=90.0, allow_nan=False, allow_infinity=False
)

# Finite floats strictly outside the valid range (bounds are inclusive).
_OUT_OF_RANGE_LNG = st.floats(allow_nan=False, allow_infinity=False).filter(
    lambda x: not (-180.0 <= x <= 180.0)
)
_OUT_OF_RANGE_LAT = st.floats(allow_nan=False, allow_infinity=False).filter(
    lambda x: not (-90.0 <= x <= 90.0)
)

# NaN / Inf are only a few distinct values, so construct them directly.
_NAN = st.just(float("nan"))
_INF = st.sampled_from([float("inf"), float("-inf")])

# Invalid values for each axis. A value like 91.0 is a valid longitude but an
# invalid latitude, so the two axes need separate strategies.
_INVALID_LNG = st.one_of(_OUT_OF_RANGE_LNG, _NAN, _INF)
_INVALID_LAT = st.one_of(_OUT_OF_RANGE_LAT, _NAN, _INF)

# A valid timezone name drawn from the known list.
_TIMEZONE_NAME = st.sampled_from(sorted(_VALID_NAMES))

# Use hypothesis defaults for max_examples. Reduce max_examples locally
# for faster feedback during development.
_LOOKUP_SETTINGS = settings(
    # max_examples=None,
    deadline=None,
    suppress_health_check=(HealthCheck.too_slow,),
)


def _is_known_timezone(result: object) -> bool:
    """A lookup result is either None or a known timezone name."""
    return result is None or (isinstance(result, str) and result in _VALID_NAMES)


@_LOOKUP_SETTINGS
@given(lng=_VALID_LNG, lat=_VALID_LAT)
def test_timezone_at_returns_known_timezone_or_none(lng, lat):
    """timezone_at yields None or a name from the canonical timezone list."""
    result = timezone_at(lng=lng, lat=lat)
    assert _is_known_timezone(result)


@_LOOKUP_SETTINGS
@given(lng=_VALID_LNG, lat=_VALID_LAT)
def test_timezone_at_land_returns_known_timezone_or_none(lng, lat):
    """timezone_at_land yields None or a known land timezone name."""
    result = timezone_at_land(lng=lng, lat=lat)
    assert _is_known_timezone(result)


@_LOOKUP_SETTINGS
@given(lng=_VALID_LNG, lat=_VALID_LAT)
def test_unique_timezone_at_returns_known_timezone_or_none(lng, lat):
    """unique_timezone_at yields None or a known timezone name."""
    result = unique_timezone_at(lng=lng, lat=lat)
    assert _is_known_timezone(result)


@_LOOKUP_SETTINGS
@given(lng=_VALID_LNG, lat=_VALID_LAT)
def test_certain_timezone_at_returns_known_timezone_or_none(lng, lat):
    """certain_timezone_at yields None or a known timezone name."""
    result = certain_timezone_at(lng=lng, lat=lat)
    assert _is_known_timezone(result)


@_LOOKUP_SETTINGS
@given(lng=_VALID_LNG, lat=_VALID_LAT)
def test_certain_timezone_at_implies_timezone_at(lng, lat):
    """A certain hit implies the regular lookup agrees.

    The reverse does not always hold near the poles, where the shortcut
    used by timezone_at can still resolve a name that the exhaustive
    certain_timezone_at misses, so only this direction is asserted.
    """
    certain = certain_timezone_at(lng=lng, lat=lat)
    if certain is not None:
        assert timezone_at(lng=lng, lat=lat) == certain


@_LOOKUP_SETTINGS
@given(lng=_VALID_LNG, lat=_VALID_LAT)
def test_timezone_at_land_is_subset_of_timezone_at(lng, lat):
    """A land hit implies the regular lookup returns the same name."""
    land = timezone_at_land(lng=lng, lat=lat)
    if land is not None:
        assert timezone_at(lng=lng, lat=lat) == land


@_LOOKUP_SETTINGS
@given(lng=_VALID_LNG, lat=_VALID_LAT)
def test_unique_timezone_at_implies_timezone_at(lng, lat):
    """An unambiguous shortcut hit implies the full lookup agrees."""
    unique = unique_timezone_at(lng=lng, lat=lat)
    if unique is not None:
        assert timezone_at(lng=lng, lat=lat) == unique


@_LOOKUP_SETTINGS
@given(lng=_VALID_LNG, lat=_VALID_LAT)
def test_lookups_are_deterministic(lng, lat):
    """Repeated calls with the same coordinates return identical results."""
    assert timezone_at(lng=lng, lat=lat) == timezone_at(lng=lng, lat=lat)
    assert timezone_at_land(lng=lng, lat=lat) == timezone_at_land(lng=lng, lat=lat)
    assert unique_timezone_at(lng=lng, lat=lat) == unique_timezone_at(lng=lng, lat=lat)
    assert certain_timezone_at(lng=lng, lat=lat) == certain_timezone_at(
        lng=lng, lat=lat
    )


@pytest.mark.parametrize(
    "func",
    [timezone_at, timezone_at_land, unique_timezone_at, certain_timezone_at],
)
@_LOOKUP_SETTINGS
@given(coord=_INVALID_LNG)
def test_lookup_functions_reject_invalid_longitude(func, coord):
    """Invalid longitude values raise ValueError for every lookup function."""
    with pytest.raises(ValueError):
        func(lng=coord, lat=0.0)


@pytest.mark.parametrize(
    "func",
    [timezone_at, timezone_at_land, unique_timezone_at, certain_timezone_at],
)
@_LOOKUP_SETTINGS
@given(coord=_INVALID_LAT)
def test_lookup_functions_reject_invalid_latitude(func, coord):
    """Invalid latitude values raise ValueError for every lookup function."""
    with pytest.raises(ValueError):
        func(lng=0.0, lat=coord)


@_LOOKUP_SETTINGS
@given(name=_TIMEZONE_NAME, coords_as_pairs=st.booleans())
def test_get_geometry_returns_non_empty_for_known_timezone(name, coords_as_pairs):
    """Every known timezone name has a non-empty polygon geometry."""
    result = get_geometry(tz_name=name, coords_as_pairs=coords_as_pairs)
    assert isinstance(result, list)
    assert len(result) > 0


@_LOOKUP_SETTINGS
@given(name=_TIMEZONE_NAME)
def test_get_geometry_by_id_matches_by_name(name):
    """Looking up by tz_id (index) returns the same geometry as by name."""
    tf = TimezoneFinder()
    tz_id = tf.timezone_names.index(name)
    by_name = get_geometry(tz_name=name, use_id=False)
    by_id = get_geometry(tz_id=tz_id, use_id=True)
    assert by_name == by_id


@_LOOKUP_SETTINGS
@given(name=_TIMEZONE_NAME)
def test_get_geometry_is_deterministic(name):
    """Repeated geometry lookups return identical structures."""
    assert get_geometry(tz_name=name) == get_geometry(tz_name=name)
