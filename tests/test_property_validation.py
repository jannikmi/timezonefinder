"""Property-based tests for coordinate validation functions.

Uses ``hypothesis`` to exercise the full finite input space of
``validate_coordinates``, ``validate_lat``, and ``validate_lng``,
complementing the example-based tests in ``tests/utils_test.py``.
"""

import pytest
from hypothesis import given, strategies as st

from timezonefinder import utils


# Finite in-range coordinates. allow_nan=False and allow_infinity=False are
# mandatory: otherwise hypothesis would emit NaN/Inf, which are invalid, and
# the "valid" properties below would fail.
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

# NaN / Inf are only a few distinct values, so construct them directly instead
# of generating many floats only to filter most of them away.
_NAN = st.just(float("nan"))
_INF = st.sampled_from([float("inf"), float("-inf")])

# Pairs where at least one coordinate is NaN (resp. Inf); the other is valid.
_NAN_PAIR = st.one_of(
    st.tuples(_NAN, _VALID_LAT),
    st.tuples(_VALID_LNG, _NAN),
    st.tuples(_NAN, _NAN),
)
_INF_PAIR = st.one_of(
    st.tuples(_INF, _VALID_LAT),
    st.tuples(_VALID_LNG, _INF),
    st.tuples(_INF, _INF),
)


@pytest.mark.unit
@given(lng=_VALID_LNG, lat=_VALID_LAT)
def test_validate_coordinates_accepts_valid(lng, lat):
    """Valid finite in-range coordinates pass through unchanged as floats."""
    result = utils.validate_coordinates(lng=lng, lat=lat)
    assert result == (lng, lat)
    assert isinstance(result[0], float)
    assert isinstance(result[1], float)


@pytest.mark.unit
@given(lng=_OUT_OF_RANGE_LNG, lat=_VALID_LAT)
def test_validate_coordinates_rejects_out_of_range_lng(lng, lat):
    """Finite longitude outside [-180, 180] raises ValueError."""
    with pytest.raises(ValueError):
        utils.validate_coordinates(lng=lng, lat=lat)


@pytest.mark.unit
@given(lng=_VALID_LNG, lat=_OUT_OF_RANGE_LAT)
def test_validate_coordinates_rejects_out_of_range_lat(lng, lat):
    """Finite latitude outside [-90, 90] raises ValueError."""
    with pytest.raises(ValueError):
        utils.validate_coordinates(lng=lng, lat=lat)


@pytest.mark.unit
@given(pair=_NAN_PAIR)
def test_validate_coordinates_rejects_nan(pair):
    """NaN in either coordinate raises ValueError."""
    lng, lat = pair
    with pytest.raises(ValueError):
        utils.validate_coordinates(lng=lng, lat=lat)


@pytest.mark.unit
@given(pair=_INF_PAIR)
def test_validate_coordinates_rejects_inf(pair):
    """Infinity in either coordinate raises ValueError."""
    lng, lat = pair
    with pytest.raises(ValueError):
        utils.validate_coordinates(lng=lng, lat=lat)


@pytest.mark.unit
@given(lat=st.one_of(_OUT_OF_RANGE_LAT, _NAN, _INF))
def test_validate_lat_rejects_invalid(lat):
    """validate_lat rejects out-of-range, NaN, and infinity latitude."""
    with pytest.raises(ValueError):
        utils.validate_lat(lat=lat)


@pytest.mark.unit
@given(lng=st.one_of(_OUT_OF_RANGE_LNG, _NAN, _INF))
def test_validate_lng_rejects_invalid(lng):
    """validate_lng rejects out-of-range, NaN, and infinity longitude."""
    with pytest.raises(ValueError):
        utils.validate_lng(lng=lng)
