"""Tests for the scalar zone-id lookups and their name-returning siblings.

The id methods are the same lookup with the final name conversion omitted. Agreement
with the established scalar name methods is therefore their central contract; the
batch comparison separately pins that the singular and plural id APIs resolve the same
zone.
"""

import pytest
from h3.api import numpy_int as h3

from tests.auxiliaries import (
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
    RANDOM_POINTS_FIXTURE,
    UNIQUE_SHORTCUT_POINTS_FIXTURE,
    load_benchmark_points,
)
from timezonefinder import (
    NO_ZONE_ID,
    TimezoneFinder,
    TimezoneFinderL,
    timezone_at,
    timezone_at_land,
    timezone_id_at,
    timezone_id_at_land,
)
from timezonefinder.configs import SHORTCUT_H3_RES
from timezonefinder.shortcut_index import ABSENT, ShortcutIndex, slot_of

SAMPLE_SIZE = 300
FIXTURES = (
    RANDOM_POINTS_FIXTURE,
    UNIQUE_SHORTCUT_POINTS_FIXTURE,
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
)
FINDERS = (
    pytest.param(lambda: TimezoneFinder(in_memory=True), id="TimezoneFinder"),
    pytest.param(TimezoneFinderL, id="TimezoneFinderL"),
)


@pytest.fixture(scope="module", params=FINDERS)
def finder(request):
    """Both finders share the scalar id implementation but resolve ambiguity differently."""
    with request.param() as instance:
        yield instance


def _name_of(finder, zone_id: int | None) -> str | None:
    if zone_id is None:
        return None
    assert isinstance(zone_id, int)
    return finder.zone_name_from_id(zone_id)


@pytest.mark.unit
@pytest.mark.parametrize("fixture_name", FIXTURES)
def test_scalar_ids_and_names_describe_the_same_answers(finder, fixture_name):
    points = load_benchmark_points(fixture_name)[:SAMPLE_SIZE]
    for lng, lat in points:
        zone_id = finder.timezone_id_at(lng=lng, lat=lat)
        assert _name_of(finder, zone_id) == finder.timezone_at(lng=lng, lat=lat)


@pytest.mark.unit
@pytest.mark.parametrize("fixture_name", FIXTURES)
def test_scalar_and_single_element_batch_ids_agree(finder, fixture_name):
    points = load_benchmark_points(fixture_name)[:SAMPLE_SIZE]
    for lng, lat in points:
        scalar = finder.timezone_id_at(lng=lng, lat=lat)
        batch = int(finder.timezone_ids_at(lngs=[lng], lats=[lat])[0])
        assert (NO_ZONE_ID if scalar is None else scalar) == batch


@pytest.mark.unit
def test_land_ids_and_names_describe_the_same_answers(finder):
    for lng, lat in ((13.358, 52.5061), (-30.0, 0.0)):
        zone_id = finder.timezone_id_at_land(lng=lng, lat=lat)
        assert _name_of(finder, zone_id) == finder.timezone_at_land(lng=lng, lat=lat)


@pytest.mark.unit
def test_overlap_id_is_the_canonical_first_zone(timezonefinder_in_memory):
    """The overlap API contracts its first answer to the regular lookup's winner."""
    finder = timezonefinder_in_memory
    lng, lat = 87.6168, 43.8256
    zone_id = finder.timezone_id_at(lng=lng, lat=lat)
    assert zone_id is not None
    assert finder.zone_name_from_id(zone_id) == finder.timezones_at(lng=lng, lat=lat)[0]


@pytest.mark.unit
def test_an_uncovered_cell_answers_none_in_both_scalar_forms():
    """Reach the custom-data-only ABSENT branch by blanking one copied index slot."""
    lng, lat = 13.358, 52.5061
    with TimezoneFinder(in_memory=True) as finder:
        slot = slot_of(h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES))
        assert finder.shortcuts.table[slot] != ABSENT
        table = finder.shortcuts.table.copy()
        table[slot] = ABSENT
        finder.shortcuts = ShortcutIndex(
            table,
            finder.shortcuts.starts,
            finder.shortcuts.ends,
            finder.shortcuts.last_change,
            finder.shortcuts.payload,
        )

        assert finder.timezone_id_at(lng=lng, lat=lat) is None
        assert finder.timezone_id_at_land(lng=lng, lat=lat) is None
        assert finder.timezone_at(lng=lng, lat=lat) is None
        assert finder.timezone_at_land(lng=lng, lat=lat) is None


@pytest.mark.unit
def test_global_scalar_id_functions_match_the_global_name_functions():
    with TimezoneFinder() as finder:
        for lng, lat in ((13.358, 52.5061), (-30.0, 0.0)):
            zone_id = timezone_id_at(lng=lng, lat=lat)
            land_zone_id = timezone_id_at_land(lng=lng, lat=lat)
            assert _name_of(finder, zone_id) == timezone_at(lng=lng, lat=lat)
            assert _name_of(finder, land_zone_id) == timezone_at_land(lng=lng, lat=lat)
