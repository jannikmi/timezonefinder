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


# ``is_valid_lat`` / ``is_valid_lng`` are plain Python functions rather than ``njit`` ones,
# because a scalar comparison is not worth a dispatch boundary. The compiled vectorised
# forms the converter uses live in ``scripts/utils_numba.py`` and *inline* the same
# comparison, because numba cannot call a pure-Python function from nopython mode - so the
# two forms have to keep agreeing. A bound corrected in one and not the other would let
# the converter store a coordinate a query then refuses, or the reverse, and nothing else
# compares them.


@pytest.mark.unit
@given(lat=st.one_of(_VALID_LAT, _OUT_OF_RANGE_LAT, _NAN, _INF))
def test_scalar_and_vectorised_latitude_bounds_agree(lat):
    import numpy as np

    from scripts.utils_numba import is_valid_lat_vec

    assert utils.is_valid_lat(lat) == is_valid_lat_vec(np.array([lat]))


@pytest.mark.unit
@given(lng=st.one_of(_VALID_LNG, _OUT_OF_RANGE_LNG, _NAN, _INF))
def test_scalar_and_vectorised_longitude_bounds_agree(lng):
    import numpy as np

    from scripts.utils_numba import is_valid_lng_vec

    assert utils.is_valid_lng(lng) == is_valid_lng_vec(np.array([lng]))


@pytest.mark.unit
@given(lng=_VALID_LNG, lat=_VALID_LAT)
def test_coord2int_matches_the_scaling_it_performs(lng, lat):
    """``coord2int`` lost its ``njit`` decorator, and with it the ``i4`` return cast.

    Under numba that cast wrapped an out-of-range product into int32 silently, where the
    no-numba configuration a plain ``pip install`` gives never did - so the two backends
    disagreed for inputs outside the validated domain. They agree now, and this pins the
    truncation itself: toward zero, on both signs.
    """
    from timezonefinder.configs import COORD2INT_FACTOR

    assert utils.coord2int(lng) == int(lng * COORD2INT_FACTOR)
    assert utils.coord2int(lat) == int(lat * COORD2INT_FACTOR)
    assert utils.coord2int(-abs(lng)) == -utils.coord2int(abs(lng))


# The value range below the validated one is deliberate: `coord2int` used to be an
# ``njit`` function with an ``i4`` return signature, so under numba an out-of-range
# product wrapped into int32 while the no-numba configuration a plain ``pip install``
# gives returned the exact value. That is a wrong answer that reports success -
# ``coord2int(300.0)`` came back as -1,294,967,296, a *negative* longitude for a
# positive input - and it differed by backend, so no single-backend run could see it.
# Nothing on the query path could reach it, because `validate_coordinates` runs first;
# `scripts/hex_utils.py` and `scripts/generate_benchmark_fixtures.py` call it without
# that guard. The decorator is gone and both backends are exact now, which is what this
# pins - the property tests above cannot, because they are bounded to the validated
# domain, i.e. exactly the range where the two forms agreed.
_OUT_OF_DOMAIN = st.floats(
    min_value=-1e9, max_value=1e9, allow_nan=False, allow_infinity=False
).filter(lambda x: abs(x) > 180.0)


@pytest.mark.unit
@given(value=_OUT_OF_DOMAIN)
def test_coord2int_does_not_wrap_outside_the_valid_coordinate_range(value):
    from timezonefinder.configs import COORD2INT_FACTOR

    scaled = utils.coord2int(value)
    assert scaled == int(value * COORD2INT_FACTOR)
    # the wrap this replaced always changed the magnitude, and could flip the sign
    assert abs(scaled) >= abs(int(180.0 * COORD2INT_FACTOR))
    assert (scaled < 0) == (value < 0)


@pytest.mark.unit
def test_coord2int_is_exact_where_the_int32_form_wrapped():
    """The two values that made the old backend divergence visible."""
    assert utils.coord2int(300.0) == 3_000_000_000
    assert utils.coord2int(1e6) == 10_000_000_000_000
