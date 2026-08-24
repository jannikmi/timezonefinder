"""What the coordinate encoding actually resolves, against what the package claims.

Every page that describes this library states a resolution - ``~1 cm`` in ``README.rst``,
``docs/index.rst``, ``docs/alternatives.rst`` and ``docs/data_format.rst``, ``~1.1 cm`` in
``docs/architecture.rst`` and ``CLAUDE.md``. None of them is generated, so all of them go
stale silently if the scaling ever changes.

These tests deliberately **do not** grep those files for their wording. A test that
asserts a string fails on every rewording and passes on every change that keeps the
wording. What is asserted instead is the band the prose commits to: that the resolution
derived from ``COORD2INT_FACTOR`` really is of the order the pages say, that the worst
case really is at the equator, and that the error really is a whole step rather than
half of one - which is a property of ``coord2int`` truncating, not of the scale factor,
and is what makes ``~1.1 cm`` right where ``~0.6 cm`` would be wrong.

The second half is about the *input* dtype, which is a different question: what a caller
has to hand the package for the packaged precision to survive the call.
"""

import math

import numpy as np
import pytest

from timezonefinder import TimezoneFinder, utils
from timezonefinder.configs import (
    COORD2INT_FACTOR,
    MAX_LAT_VAL,
    MAX_LNG_VAL,
    NR_BYTES_I,
)

#: the packaged encoding: signed ``NR_BYTES_I``-byte integers scaled by COORD2INT_FACTOR
STORED_DTYPE = np.int32


@pytest.mark.unit
def test_the_stored_encoding_resolves_about_a_centimetre_at_the_equator():
    """The figure every page quotes. A band rather than an exact value, because the
    pages say "~1 cm" and "~1.1 cm" and both have to stay true; anything that moved the
    scaling to millimetres or decimetres makes all of them wrong at once."""
    step_m = utils.degrees_to_metres(utils.coordinate_resolution(STORED_DTYPE))

    assert 0.005 < step_m < 0.02, (
        f"the stored encoding resolves {step_m * 100:.3f} cm, which no longer reads as "
        '"~1 cm". Every page stating a resolution has to be updated with it.'
    )
    # the tighter figure architecture.rst and CLAUDE.md commit to
    assert round(step_m * 100, 1) == 1.1


@pytest.mark.unit
def test_the_scale_factor_is_a_tenth_of_a_microdegree_not_a_microdegree():
    """``configs.py`` used to call 10^7 "microdegree precision", which understates it
    tenfold: a microdegree is 10^-6 degrees and one step is 10^-7."""
    step_deg = utils.coordinate_resolution(STORED_DTYPE)

    assert step_deg == pytest.approx(1e-7)
    assert step_deg == pytest.approx(0.1 * 1e-6), "one step is a tenth of a microdegree"


@pytest.mark.unit
def test_the_worst_case_is_the_equator():
    """ "minimum accuracy at the equator" is a claim about *longitude*: its degree is
    longest there and shrinks with cos(latitude), so the equator bounds the ground error
    of a fixed angular step everywhere else."""
    step = utils.coordinate_resolution(STORED_DTYPE)
    at_equator = utils.degrees_to_metres(step)

    for latitude in (23.5, 45.0, 60.0, 80.0):
        assert utils.degrees_to_metres(step, at_latitude=latitude) < at_equator


@pytest.mark.unit
def test_the_error_is_a_whole_step_because_the_conversion_truncates():
    """Why the claim is ~1.1 cm and not ~0.56 cm.

    ``coord2int`` truncates toward zero rather than rounding, so a coordinate can be a
    whole step away from its stored form instead of half a step. Rounding would halve
    the worst case and make every quoted figure conservative by 2x - a change worth
    noticing, since it would silently invalidate the arithmetic above.
    """
    step = utils.coordinate_resolution(STORED_DTYPE)
    # a value just under the next representable step still stores as the lower one
    just_under = 1.0 + step * 0.99
    assert utils.coord2int(just_under) == utils.coord2int(1.0)

    worst = max(
        abs(value - utils.int2coord(utils.coord2int(value)))
        for value in np.random.default_rng(0).uniform(-MAX_LNG_VAL, MAX_LNG_VAL, 20_000)
    )
    assert worst > step / 2, "a rounding conversion would never exceed half a step"
    assert worst <= step


@pytest.mark.unit
def test_the_stored_integer_width_spans_the_globe_at_that_scale():
    """The scale factor and the integer width are one choice, not two: 180 degrees times
    10^7 has to fit, and it uses 84 % of the int32 range."""
    needed = int(MAX_LNG_VAL * COORD2INT_FACTOR)
    assert np.iinfo(STORED_DTYPE).max >= needed
    assert np.dtype(STORED_DTYPE).itemsize == NR_BYTES_I
    # int16 is nowhere near, which is what the helper reports rather than a step
    with pytest.raises(ValueError, match="cannot hold a scaled coordinate"):
        utils.coordinate_resolution(np.int16)


@pytest.mark.unit
def test_a_float_dtype_is_measured_where_it_is_worst():
    """A float's spacing grows with magnitude, so a resolution quoted for one has to say
    where. The default is the largest valid longitude, which is the worst case."""
    at_default = utils.coordinate_resolution(np.float32)
    at_max_lng = utils.coordinate_resolution(np.float32, at_degrees=MAX_LNG_VAL)
    assert at_default == at_max_lng
    assert utils.coordinate_resolution(np.float32, at_degrees=13.4) < at_max_lng
    # the sign of the coordinate cannot change how finely it is resolved
    assert (
        utils.coordinate_resolution(np.float32, at_degrees=-MAX_LNG_VAL) == at_max_lng
    )


@pytest.mark.unit
def test_float64_resolves_far_finer_than_the_stored_encoding():
    """Which is what makes it the right input dtype: the conversion to the stored form
    loses nothing the caller had."""
    stored = utils.coordinate_resolution(STORED_DTYPE)
    float64_worst = utils.coordinate_resolution(np.float64, at_degrees=MAX_LNG_VAL)

    assert float64_worst < stored / 1e6
    # and the scaled value itself is an exact float64 integer, so the scaling step in
    # coord2int introduces no error of its own
    assert MAX_LNG_VAL * COORD2INT_FACTOR < 2**53


@pytest.mark.unit
def test_float32_is_far_coarser_than_the_data_it_would_query():
    """The reason ``float32`` is upcast rather than used, and the number behind the
    caveat in ``docs/1_usage.rst``."""
    stored = utils.coordinate_resolution(STORED_DTYPE)
    f32_worst = utils.coordinate_resolution(np.float32, at_degrees=MAX_LNG_VAL)

    assert f32_worst > 100 * stored
    assert 1.0 < utils.degrees_to_metres(f32_worst) < 3.0, (
        "the ~1.7 m figure the usage docs quote for float32 at the antimeridian"
    )
    # 180 * 10^7 is past float32's exact-integer range, so the scaling would be lossy too
    assert MAX_LNG_VAL * COORD2INT_FACTOR > 2**24


@pytest.mark.unit
def test_latitude_is_bounded_by_the_same_step():
    """Both axes share one scale factor, so the latitude bound follows from the same
    arithmetic - and a degree of latitude is never longer than one of longitude at the
    equator, so the equator figure bounds it too."""
    assert MAX_LAT_VAL < MAX_LNG_VAL
    assert int(MAX_LAT_VAL * COORD2INT_FACTOR) < np.iinfo(STORED_DTYPE).max


@pytest.mark.unit
def test_degrees_to_metres_agrees_with_the_wgs84_circumference():
    """One degree of longitude at the equator, from the published semi-major axis."""
    circumference = 2 * math.pi * utils.EARTH_EQUATORIAL_RADIUS_M
    assert utils.degrees_to_metres(1.0) == pytest.approx(circumference / 360)
    assert utils.degrees_to_metres(1.0) == pytest.approx(111_319.49, abs=0.01)
    assert utils.degrees_to_metres(1.0, at_latitude=60.0) == pytest.approx(
        utils.degrees_to_metres(1.0) / 2, rel=1e-6
    )


@pytest.mark.unit
@pytest.mark.parametrize("dtype", [np.complex128, np.bool_, np.str_])
def test_a_dtype_that_cannot_carry_a_coordinate_is_refused(dtype):
    with pytest.raises(TypeError, match="not as"):
        utils.coordinate_resolution(dtype)


@pytest.mark.unit
@pytest.mark.parametrize(
    "dtype, step_deg, ground_m",
    [
        (np.int32, 1.0e-07, 0.0111),
        (np.float64, 2.8e-14, 3.2e-09),
        (np.float32, 1.5e-05, 1.70),
        (np.float16, 1.25e-01, 13_915.0),
    ],
    ids=["int32", "float64", "float32", "float16"],
)
def test_the_dtype_comparison_table_in_the_docs_still_holds(dtype, step_deg, ground_m):
    """``docs/data_format.rst`` states these four rows exactly, which it is allowed to:
    they follow from ``COORD2INT_FACTOR`` and from IEEE 754, not from the packaged data,
    so a data update cannot move them. A change to the scale factor can, and this is
    what would notice."""
    step = utils.coordinate_resolution(dtype, at_degrees=MAX_LNG_VAL)
    assert step == pytest.approx(step_deg, rel=0.02)
    assert utils.degrees_to_metres(step) == pytest.approx(ground_m, rel=0.02)


# --- what the input dtype costs a caller ------------------------------------------


@pytest.mark.unit
def test_a_float32_batch_is_accepted_and_upcast():
    """Not rejected: the caller rounded before calling, and upcasting is lossless from
    there. What it costs is a copy and whatever precision was already gone."""
    lngs = np.array([13.358, 2.3522], dtype=np.float32)
    lats = np.array([52.5061, 48.8566], dtype=np.float32)

    with TimezoneFinder() as tf:
        assert tf.timezone_names_at(lngs=lngs, lats=lats) == [
            tf.timezone_at(lng=float(lngs[0]), lat=float(lats[0])),
            tf.timezone_at(lng=float(lngs[1]), lat=float(lats[1])),
        ]


@pytest.mark.unit
def test_float32_input_can_answer_with_the_wrong_side_of_a_border():
    """The caveat the usage docs state, demonstrated rather than asserted in prose.

    A point half a metre inside one zone is attributed to its neighbour when the
    coordinate arrives as ``float32``, because one ULP there is larger than that. This
    is the whole reason the docs tell a caller to hand over ``float64``: this library's
    stated priority is accuracy at borders, and ``float32`` forfeits it exactly there.
    """
    with TimezoneFinder() as tf:
        lat = 32.455144
        low, high = 139.51, 139.53
        zone_low = tf.timezone_at(lng=low, lat=lat)
        assert zone_low != tf.timezone_at(lng=high, lat=lat), (
            "the bracket no longer straddles a border - pick another"
        )
        for _ in range(60):
            middle = (low + high) / 2
            if tf.timezone_at(lng=middle, lat=lat) == zone_low:
                low = middle
            else:
                high = middle

        half_a_metre = 0.5 / utils.degrees_to_metres(1.0)
        inside = low - half_a_metre
        assert tf.timezone_at(lng=inside, lat=lat) == zone_low
        assert tf.timezone_at(lng=float(np.float32(inside)), lat=lat) != zone_low
