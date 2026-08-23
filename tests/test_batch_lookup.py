"""Tests for the batch lookups ``timezone_ids_at`` / ``timezone_names_at``.

The seam that matters is **agreement with the scalar path**. A batch answer is not a new
computation: it is the same lookup with its prologue hoisted out of the loop, so any
divergence from ``timezone_at`` is a defect by definition and no other assertion can
substitute for comparing the two over real coordinates.

The rest pins what only the batch API has: the shapes it rejects, the ``on_invalid``
policies, and the sentinel that stands where the scalar method answers ``None``.
"""

import numpy as np
import pytest

from tests.auxiliaries import (
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
    ON_LAND_POINTS_FIXTURE,
    RANDOM_POINTS_FIXTURE,
    UNIQUE_SHORTCUT_POINTS_FIXTURE,
    load_benchmark_points,
)
from tests.locations import TEST_LOCATIONS
from timezonefinder import (
    NO_ZONE_ID,
    TimezoneFinder,
    TimezoneFinderL,
    timezone_ids_at,
    timezone_names_at,
)
from timezonefinder.shortcut_index import ABSENT, slot_of
from timezonefinder.timezonefinder import ZONE_ID_RESULT_DTYPE

# enough points to reach every branch without turning a unit test into a sweep; the
# exhaustive comparison over all four fixtures is the ``slow`` test at the bottom
SAMPLE_SIZE = 300

FIXTURES = [
    RANDOM_POINTS_FIXTURE,
    ON_LAND_POINTS_FIXTURE,
    UNIQUE_SHORTCUT_POINTS_FIXTURE,
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
]


@pytest.fixture(scope="module", params=[TimezoneFinder, TimezoneFinderL])
def finder(request):
    """Both finders: the batch path is inherited, the ambiguous fallback is not."""
    with request.param(in_memory=True) as instance:
        yield instance


def _axes(points):
    return [lng for lng, _ in points], [lat for _, lat in points]


@pytest.mark.unit
@pytest.mark.parametrize("fixture_name", FIXTURES)
def test_batch_names_agree_with_the_scalar_lookup(finder, fixture_name):
    points = load_benchmark_points(fixture_name)[:SAMPLE_SIZE]
    lngs, lats = _axes(points)

    expected = [finder.timezone_at(lng=lng, lat=lat) for lng, lat in points]
    assert finder.timezone_names_at(lngs=lngs, lats=lats) == expected


@pytest.mark.unit
def test_batch_ids_and_names_describe_the_same_answers(finder):
    points = load_benchmark_points(RANDOM_POINTS_FIXTURE)[:SAMPLE_SIZE]
    lngs, lats = _axes(points)

    zone_ids = finder.timezone_ids_at(lngs=lngs, lats=lats)
    names = finder.timezone_names_at(lngs=lngs, lats=lats)

    assert [
        None if zone_id < 0 else finder.zone_name_from_id(int(zone_id))
        for zone_id in zone_ids
    ] == names


@pytest.mark.unit
def test_the_documented_test_locations_come_back_unchanged(finder):
    lats = [lat for lat, _, _, _ in TEST_LOCATIONS]
    lngs = [lng for _, lng, _, _ in TEST_LOCATIONS]
    expected = [
        finder.timezone_at(lng=lng, lat=lat)
        for lng, lat in zip(lngs, lats, strict=True)
    ]
    assert finder.timezone_names_at(lngs=lngs, lats=lats) == expected


@pytest.mark.unit
def test_the_answer_dtype_is_the_declared_one(finder):
    zone_ids = finder.timezone_ids_at(lngs=[13.358], lats=[52.5061])
    assert zone_ids.dtype == ZONE_ID_RESULT_DTYPE
    # int16 would truncate the upper half of the stored uint16 zone ids
    assert zone_ids.dtype.itemsize >= 4


@pytest.mark.unit
def test_an_empty_batch_answers_empty(finder):
    assert finder.timezone_ids_at(lngs=[], lats=[]).shape == (0,)
    assert finder.timezone_names_at(lngs=[], lats=[]) == []


@pytest.mark.unit
@pytest.mark.parametrize(
    "container", [list, tuple, np.array], ids=["list", "tuple", "ndarray"]
)
def test_any_array_like_is_accepted(finder, container):
    """An API only numpy users can call would make everyone else write the loop first."""
    lngs = container([13.358, 2.3522])
    lats = container([52.5061, 48.8566])
    assert finder.timezone_names_at(lngs=lngs, lats=lats) == [
        finder.timezone_at(lng=13.358, lat=52.5061),
        finder.timezone_at(lng=2.3522, lat=48.8566),
    ]


@pytest.mark.unit
def test_the_caller_s_arrays_are_left_alone(finder):
    """The zero-copy path passes the caller's buffer straight through, so nothing may
    write into it - a lookup that scaled coordinates in place would corrupt the input."""
    lngs = np.array([13.358, 2.3522], dtype=np.float64)
    lats = np.array([52.5061, 48.8566], dtype=np.float64)
    finder.timezone_ids_at(lngs=lngs, lats=lats)
    assert lngs.tolist() == [13.358, 2.3522]
    assert lats.tolist() == [52.5061, 48.8566]


@pytest.mark.unit
def test_axes_of_different_length_are_rejected(finder):
    with pytest.raises(ValueError, match="same number of coordinates"):
        finder.timezone_ids_at(lngs=[1.0, 2.0], lats=[1.0])


@pytest.mark.unit
def test_a_pair_array_is_rejected_rather_than_read_positionally(finder):
    """An (N, 2) array would have to be read by column position, and a swapped pair is
    still a valid coordinate for most of the populated world - so the mistake would
    return a real but wrong timezone. Refuse the shape instead of guessing."""
    pairs = np.array([[13.358, 52.5061], [2.3522, 48.8566]])
    with pytest.raises(ValueError, match="one-dimensional"):
        finder.timezone_ids_at(lngs=pairs, lats=pairs)


@pytest.mark.unit
def test_non_numeric_input_raises_type_error(finder):
    with pytest.raises(TypeError):
        finder.timezone_ids_at(lngs=["thirteen"], lats=[52.5061])


@pytest.mark.unit
@pytest.mark.parametrize(
    "lng, lat",
    [
        (181.0, 0.0),
        (0.0, 91.0),
        (float("nan"), 0.0),
        (0.0, float("inf")),
    ],
    ids=["lng_too_large", "lat_too_large", "nan", "inf"],
)
def test_out_of_bounds_coordinates_raise_by_default(finder, lng, lat):
    """The default matches the scalar methods; NaN and infinity are out of bounds too."""
    with pytest.raises(ValueError, match="invalid coordinate at index 1"):
        finder.timezone_ids_at(lngs=[13.358, lng], lats=[52.5061, lat])


@pytest.mark.unit
def test_the_raised_error_names_the_escape_hatch(finder):
    """Discovering ``on_invalid`` should not require reading the source."""
    with pytest.raises(ValueError, match="on_invalid"):
        finder.timezone_ids_at(lngs=[999.0], lats=[0.0])


@pytest.mark.unit
def test_skip_answers_every_valid_coordinate(finder):
    lngs = [13.358, 999.0, 2.3522, float("nan")]
    lats = [52.5061, 0.0, 48.8566, 0.0]

    zone_ids = finder.timezone_ids_at(lngs=lngs, lats=lats, on_invalid="skip")
    names = finder.timezone_names_at(lngs=lngs, lats=lats, on_invalid="skip")

    assert zone_ids[1] == NO_ZONE_ID
    assert zone_ids[3] == NO_ZONE_ID
    assert names[1] is None
    assert names[3] is None
    assert names[0] == finder.timezone_at(lng=13.358, lat=52.5061)
    assert names[2] == finder.timezone_at(lng=2.3522, lat=48.8566)


@pytest.mark.unit
def test_skipping_does_not_shift_the_remaining_answers(finder):
    """One answer per input coordinate, in input order - the property a caller zipping
    the result back against its own rows depends on."""
    points = load_benchmark_points(RANDOM_POINTS_FIXTURE)[:SAMPLE_SIZE]
    lngs, lats = _axes(points)
    # every third coordinate replaced by an unanswerable one
    spoilt_lngs = [999.0 if i % 3 == 0 else lng for i, lng in enumerate(lngs)]

    names = finder.timezone_names_at(lngs=spoilt_lngs, lats=lats, on_invalid="skip")

    assert len(names) == len(points)
    for i, (lng, lat) in enumerate(points):
        if i % 3 == 0:
            assert names[i] is None
        else:
            assert names[i] == finder.timezone_at(lng=lng, lat=lat)


@pytest.mark.unit
def test_an_unknown_policy_is_rejected(finder):
    with pytest.raises(ValueError, match="unknown on_invalid policy"):
        finder.timezone_ids_at(lngs=[13.358], lats=[52.5061], on_invalid="ignore")


@pytest.mark.unit
def test_a_cell_no_zone_covers_answers_the_same_as_the_scalar_lookup():
    """The packaged data covers every cell (ocean zones), so this is the branch custom
    data reaches and the packaged data cannot. One slot is blanked to reach it, and the
    point of the test is that both paths agree on what an uncovered cell means."""
    lng, lat = 13.358, 52.5061
    with TimezoneFinder(in_memory=True) as tf:
        from h3.api import numpy_int as h3

        from timezonefinder.configs import SHORTCUT_H3_RES

        slot = slot_of(h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES))
        assert tf.shortcuts.table[slot] != ABSENT, "the cell is covered to begin with"
        tf.shortcuts.table[slot] = ABSENT

        assert tf.timezone_at(lng=lng, lat=lat) is None
        assert tf.timezone_ids_at(lngs=[lng], lats=[lat])[0] == NO_ZONE_ID
        assert tf.timezone_names_at(lngs=[lng], lats=[lat]) == [None]


@pytest.mark.unit
def test_the_global_functions_answer_like_an_instance():
    lngs = [13.358, 2.3522, 1.0]
    lats = [52.5061, 48.8566, 50.5]
    with TimezoneFinder() as tf:
        assert timezone_names_at(lngs=lngs, lats=lats) == tf.timezone_names_at(
            lngs=lngs, lats=lats
        )
        assert np.array_equal(
            timezone_ids_at(lngs=lngs, lats=lats),
            tf.timezone_ids_at(lngs=lngs, lats=lats),
        )


@pytest.mark.slow
@pytest.mark.parametrize("fixture_name", FIXTURES)
def test_batch_and_scalar_agree_over_every_committed_point(finder, fixture_name):
    """The full sweep the sampled test above is a cheap stand-in for."""
    points = load_benchmark_points(fixture_name)
    lngs, lats = _axes(points)
    expected = [finder.timezone_at(lng=lng, lat=lat) for lng, lat in points]
    assert finder.timezone_names_at(lngs=lngs, lats=lats) == expected
