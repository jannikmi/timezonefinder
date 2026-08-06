"""tests for the hex cell boundary correction used when compiling shortcuts"""

import pytest

from scripts.hex_utils import get_corrected_hex_boundaries
from timezonefinder.configs import MAX_LAT_VAL, MAX_LNG_VAL
from timezonefinder.utils_numba import coord2int

MAX_LAT_INT = coord2int(MAX_LAT_VAL)
MAX_LNG_INT = coord2int(MAX_LNG_VAL)


def corrected(
    lngs: list[float],
    lats: list[float],
    surr_n_pole: bool = False,
    surr_s_pole: bool = False,
):
    """Call the helper with degree inputs, as ``Hex.from_id`` does with scaled ints."""
    return get_corrected_hex_boundaries(
        [coord2int(lng) for lng in lngs],
        [coord2int(lat) for lat in lats],
        surr_n_pole,
        surr_s_pole,
    )


@pytest.mark.unit
def test_ordinary_cell_keeps_the_extreme_coordinates():
    """A cell away from the poles and the antimeridian is its own bounding box."""
    bounds, x_overflow = corrected([10.0, 12.0, 11.0], [50.0, 52.0, 51.0])

    assert not x_overflow
    assert bounds.xmin == coord2int(10.0)
    assert bounds.xmax == coord2int(12.0)
    assert bounds.ymin == coord2int(50.0)
    assert bounds.ymax == coord2int(52.0)


@pytest.mark.unit
def test_boundaries_field_order_is_xmax_xmin_ymax_ymin():
    """``Boundaries`` is built positionally, with max before min on each axis.

    Pinned separately because the constructor takes four same-typed ints, so
    swapping a pair stays type-correct and would only surface as wrong shortcuts.
    """
    bounds, _ = corrected([-3.0, 4.0], [-5.0, 6.0])

    assert tuple(bounds) == (
        coord2int(4.0),
        coord2int(-3.0),
        coord2int(6.0),
        coord2int(-5.0),
    )


@pytest.mark.unit
def test_antimeridian_crossing_widens_longitudes_to_the_full_range():
    """A span wider than 180 degrees means the cell wraps, not that it is huge.

    min/max then pick the points closest to the +-180 boundary rather than the
    ones furthest apart, so no longitude may be excluded by the pre-filter.
    """
    bounds, x_overflow = corrected([-179.0, 179.0], [10.0, 12.0])

    assert x_overflow
    assert bounds.xmin == -MAX_LNG_INT
    assert bounds.xmax == MAX_LNG_INT
    # latitudes are unaffected by an x overflow
    assert bounds.ymin == coord2int(10.0)
    assert bounds.ymax == coord2int(12.0)


@pytest.mark.unit
def test_north_pole_cell_clips_ymax_and_widens_longitudes():
    bounds, x_overflow = corrected([10.0, 20.0], [80.0, 85.0], surr_n_pole=True)

    # the cell reaches the pole even though no vertex does
    assert bounds.ymax == MAX_LAT_INT
    assert bounds.ymin == coord2int(80.0)
    assert bounds.xmin == -MAX_LNG_INT
    assert bounds.xmax == MAX_LNG_INT
    # widening longitudes for a pole cell is not an antimeridian crossing
    assert not x_overflow


@pytest.mark.unit
def test_south_pole_cell_clips_ymin_and_widens_longitudes():
    bounds, x_overflow = corrected([10.0, 20.0], [-85.0, -80.0], surr_s_pole=True)

    assert bounds.ymin == -MAX_LAT_INT
    assert bounds.ymax == coord2int(-80.0)
    assert bounds.xmin == -MAX_LNG_INT
    assert bounds.xmax == MAX_LNG_INT
    assert not x_overflow


@pytest.mark.unit
def test_latitude_span_of_a_whole_hemisphere_is_rejected():
    """No h3 cell spans 90 degrees of latitude; such input is a coordinate mix-up."""
    with pytest.raises(AssertionError, match="latitude difference"):
        corrected([10.0, 20.0], [-45.0, 45.0])
