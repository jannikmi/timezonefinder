"""What a lookup answers on the -180° meridian and the -90° parallel.

No polygon owns a point on either line. A kernel gives a point on a boundary to the
polygon whose interior lies immediately west of it, or south of it where the boundary
runs east-west - ``tests/test_point_in_polygon_boundary_convention.py`` pins that - and
nothing lies west of -180° or south of -90°. Tested as spelled, such a point falls
through every candidate: ``certain_timezone_at`` answers ``None``, and ``timezone_at``
the shortcut index's untested final zone, which on the meridian owns neither side of it
at a few percent of latitudes. So a lookup reads -180° as +180°, the same meridian, and
-90° as the point one unit north, the same pole (``utils.query2int``). One physical point
then answers one zone whichever spelling it arrives in, and the answer is a property of
the point rather than of the index.

What fails silently if this regresses is the answer at a coordinate callers really send -
-180 is a common spelling of the antimeridian - and nothing else in the suite asserts what
one answers.
"""

import numpy as np
import pytest

from timezonefinder import TimezoneFinder, TimezoneFinderL, utils
from timezonefinder.configs import (
    INT2COORD_FACTOR,
    MAX_LAT_VAL_INT,
    MAX_LNG_VAL_INT,
    MIN_LAT_VAL_INT,
)

pytestmark = pytest.mark.unit

# Every 0.01° of the meridian, the grid the answers were measured on before the rewrite;
# every 0.1° of the pole, each of them a spelling of the same physical point.
MERIDIAN_LATS = [i / 100 for i in range(-9000, 9001)]
POLE_LNGS = [i / 10 for i in range(-1800, 1801)]


@pytest.fixture(scope="module")
def tf_l() -> TimezoneFinderL:
    return TimezoneFinderL()


def test_query2int_reads_each_line_as_the_spelling_a_polygon_owns():
    assert utils.query2int(-180.0, 12.5) == (MAX_LNG_VAL_INT, utils.coord2int(12.5))
    assert utils.query2int(-180.0, 12.5) == utils.query2int(180.0, 12.5)
    assert utils.query2int(33.0, -90.0) == (utils.coord2int(33.0), MIN_LAT_VAL_INT + 1)
    assert utils.query2int(-180.0, -90.0) == (MAX_LNG_VAL_INT, MIN_LAT_VAL_INT + 1)
    # the polygons west and south of +180° and +90° already own the points there
    assert utils.query2int(180.0, 90.0) == (MAX_LNG_VAL_INT, MAX_LAT_VAL_INT)


def test_the_shortcut_index_puts_both_spellings_in_one_cell(tf: TimezoneFinder):
    """The index's half of the contract, which the rewrite cannot reach.

    A lookup answering from a cell a single zone covers tests no polygon, and
    ``TimezoneFinderL`` never does, so both spellings agree there only if the index
    already maps them to one entry. A replacement index has to keep that - by wrapping
    -180° to +180°'s column rather than clamping it to the first one, for instance.
    """
    shortcuts = tf.shortcuts
    meridian = [
        lat
        for lat in MERIDIAN_LATS
        if shortcuts.entry_at(-180.0, lat) != shortcuts.entry_at(180.0, lat)
    ]
    assert meridian == []
    one_unit_north = -90.0 + INT2COORD_FACTOR
    pole = [
        lng
        for lng in POLE_LNGS
        if shortcuts.entry_at(lng, -90.0) != shortcuts.entry_at(lng, one_unit_north)
    ]
    assert pole == []


def test_a_meridian_point_answers_alike_in_both_spellings(
    tf: TimezoneFinder, tf_l: TimezoneFinderL
):
    """Every method, and ``certain_timezone_at`` never ``None``: the packaged data covers
    the meridian, so equality with ``timezone_at`` also shows its untested final zone is
    not what answers there."""
    differing = []
    for lat in MERIDIAN_LATS:
        zone = tf.timezone_at(lng=-180.0, lat=lat)
        west = (
            zone,
            tf.timezones_at(lng=-180.0, lat=lat),
            tf.certain_timezone_at(lng=-180.0, lat=lat),
            tf_l.timezone_at(lng=-180.0, lat=lat),
        )
        east = (
            tf.timezone_at(lng=180.0, lat=lat),
            tf.timezones_at(lng=180.0, lat=lat),
            tf.certain_timezone_at(lng=180.0, lat=lat),
            tf_l.timezone_at(lng=180.0, lat=lat),
        )
        if west != east or west[2] != zone:
            differing.append((lat, west, east))
    assert differing == []


def test_every_spelling_of_the_south_pole_answers_one_zone(
    tf: TimezoneFinder, tf_l: TimezoneFinderL
):
    answers = {
        (
            tf.timezone_at(lng=lng, lat=-90.0),
            tuple(tf.timezones_at(lng=lng, lat=-90.0)),
            tf.certain_timezone_at(lng=lng, lat=-90.0),
            tf_l.timezone_at(lng=lng, lat=-90.0),
        )
        for lng in POLE_LNGS
    }
    assert len(answers) == 1
    ((zone, zones, certain, _),) = answers
    assert certain == zone
    assert zones[0] == zone


def test_the_batch_lookups_read_both_lines_as_the_scalar_ones_do(
    tf: TimezoneFinder, tf_l: TimezoneFinderL
):
    """The batch path resolves an ambiguous cell through its own loop over the points,
    so it is held to the scalar answers at the spelling a polygon owns."""
    lats = np.array(MERIDIAN_LATS)
    west = np.full(lats.size, -180.0)
    for finder in (tf, tf_l):
        assert finder.timezone_names_at(lngs=west, lats=lats) == [
            finder.timezone_at(lng=180.0, lat=lat) for lat in MERIDIAN_LATS
        ]
    lngs = np.array(POLE_LNGS)
    south = np.full(lngs.size, -90.0)
    for finder in (tf, tf_l):
        assert (
            finder.timezone_names_at(lngs=lngs, lats=south)
            == [finder.timezone_at(lng=0.0, lat=-90.0 + INT2COORD_FACTOR)] * lngs.size
        )
