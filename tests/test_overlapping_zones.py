"""``timezones_at``: every zone containing the point, not only the one that wins.

The dataset ships genuinely overlapping zones, and every other lookup collapses them
to one answer. Two seams therefore need pinning, and they fail in opposite directions:

* **Agreement with ``timezone_at``.** The list is contracted to *contain* that
  method's answer - that membership is what stops the two contradicting each other -
  and, more strongly, to put it first. Nothing in the implementation enforces either
  half: both follow from the candidate order the lookup itself walks, and from
  mirroring that method's untested final-zone fallback. So the stronger first-element
  form is asserted over every committed fixture point rather than argued.
* **Completeness.** A candidate loop that stops early under-reports, and under-reporting
  is invisible: the answer still looks like a plausible list. The reference below
  recomputes the set the obvious slow way, through the same candidate enumeration
  ``certain_timezone_at`` uses, and the two must agree point for point.
"""

import pytest

from tests.auxiliaries import (
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
    ON_LAND_POINTS_FIXTURE,
    RANDOM_POINTS_FIXTURE,
    UNIQUE_SHORTCUT_POINTS_FIXTURE,
    load_benchmark_points,
)
from timezonefinder import TimezoneFinder, timezones_at
from timezonefinder.utils import coord2int

# enough points to reach every branch without turning a unit test into a sweep; the
# exhaustive comparison over all four fixtures is the ``slow`` test at the bottom
SAMPLE_SIZE = 300

FIXTURES = [
    RANDOM_POINTS_FIXTURE,
    ON_LAND_POINTS_FIXTURE,
    UNIQUE_SHORTCUT_POINTS_FIXTURE,
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
]

# One fixture coordinate per overlapping pair the usage docs list, with the answer in
# the order ``timezones_at`` returns it. These are answers from the packaged dataset,
# not constants: an upstream boundary release can move a point out of an overlap or
# redraw the overlap itself, and the fix is then to re-derive the coordinates rather
# than to relax the assertion. Keeping them explicit is what makes such a move visible.
DOCUMENTED_OVERLAPS = [
    ((90.72353647972255, 41.594051370907486), ["Asia/Urumqi", "Asia/Shanghai"]),
    ((28.154147689103695, 9.938006916873361), ["Africa/Khartoum", "Africa/Juba"]),
    ((35.15351018550692, 31.81505481089291), ["Asia/Jerusalem", "Asia/Hebron"]),
    ((40.352666891144224, 43.20807558055672), ["Asia/Tbilisi", "Europe/Moscow"]),
    ((-131.52704835958153, 54.63833689596523), ["America/Sitka", "America/Vancouver"]),
    (
        (-73.2873055661675, -49.685353605083144),
        ["America/Punta_Arenas", "America/Argentina/Rio_Gallegos"],
    ),
]


@pytest.fixture(scope="module")
def tf(timezonefinder_disk: TimezoneFinder) -> TimezoneFinder:
    """The shared session instance, under the name these tests read better with."""
    return timezonefinder_disk


def reference_zones(tf: TimezoneFinder, lng: float, lat: float) -> list[str]:
    """Every containing zone, computed the obvious way: test every candidate.

    Deliberately not a second copy of the method's own short-circuits - it walks
    ``_iter_boundaries_in_shortcut``, which is what ``certain_timezone_at`` walks, and
    tests all of it. A test that reimplemented the early exits would pass for the same
    reason a broken implementation does.
    """
    x = coord2int(lng)
    y = coord2int(lat)
    names: list[str] = []
    for boundary_id in tf._iter_boundaries_in_shortcut(lng=lng, lat=lat):
        if not tf.inside_of_polygon(boundary_id, x, y):
            continue
        name = tf.zone_name_from_boundary_id(boundary_id)
        if name not in names:
            names.append(name)
    return names


@pytest.mark.unit
@pytest.mark.parametrize("fixture_name", FIXTURES)
def test_the_first_zone_is_what_timezone_at_answers(
    tf: TimezoneFinder, fixture_name: str
):
    """The ordering contract, over real coordinates from every stratum."""
    for lng, lat in load_benchmark_points(fixture_name)[:SAMPLE_SIZE]:
        zones = tf.timezones_at(lng=lng, lat=lat)
        expected = tf.timezone_at(lng=lng, lat=lat)
        assert zones[0] == expected, (
            f"timezones_at({lng}, {lat}) = {zones}, but timezone_at answers "
            f"{expected!r}. The first element is contracted to be that answer."
        )


@pytest.mark.unit
@pytest.mark.parametrize("fixture_name", FIXTURES)
def test_it_reports_every_containing_zone(tf: TimezoneFinder, fixture_name: str):
    """Completeness against the slow reference, which stops at nothing."""
    for lng, lat in load_benchmark_points(fixture_name)[:SAMPLE_SIZE]:
        assert set(tf.timezones_at(lng=lng, lat=lat)) == set(
            reference_zones(tf, lng, lat)
        ), f"timezones_at({lng}, {lat}) disagrees with a full candidate scan"


@pytest.mark.unit
@pytest.mark.parametrize("coords, expected", DOCUMENTED_OVERLAPS)
def test_the_documented_overlaps_are_reported(
    tf: TimezoneFinder, coords: tuple[float, float], expected: list[str]
):
    """Each pair ``docs/1_usage.rst`` names really is reachable in the packaged data.

    The point of the method is that these are not hypothetical, so a released dataset
    that no longer places any of them in two zones should be noticed here.
    """
    lng, lat = coords
    assert tf.timezones_at(lng=lng, lat=lat) == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    "coords, expected",
    [
        ((13.358, 52.5061), ["Europe/Berlin"]),
        ((87.6168, 43.8256), ["Asia/Urumqi", "Asia/Shanghai"]),
    ],
)
def test_the_documented_examples_return_what_they_annotate(
    tf: TimezoneFinder, coords: tuple[float, float], expected: list[str]
):
    """The snippets in the docstring and in ``docs/1_usage.rst`` state their results."""
    lng, lat = coords
    assert tf.timezones_at(lng=lng, lat=lat) == expected


@pytest.mark.unit
def test_a_unique_zone_cell_is_answered_without_touching_geometry(
    tf: TimezoneFinder, monkeypatch: pytest.MonkeyPatch
):
    """The documented cost claim, asserted rather than described.

    A cell one zone covers is answered from the shortcut index alone. Nothing else
    pins that: testing the zone's polygons would return the same name and only cost
    time, so a regression here is silent.
    """

    def fail(*args, **kwargs):
        raise AssertionError("a unique-zone cell must not reach the geometry")

    points = load_benchmark_points(UNIQUE_SHORTCUT_POINTS_FIXTURE)[:SAMPLE_SIZE]
    monkeypatch.setattr(TimezoneFinder, "inside_of_polygon", fail)
    for lng, lat in points:
        assert len(tf.timezones_at(lng=lng, lat=lat)) == 1


@pytest.mark.unit
def test_the_south_pole_falls_back_to_the_untested_final_zone(tf: TimezoneFinder):
    """Where no candidate contains the point, ``timezone_at``'s answer is still first.

    The pole is the reproducible case the usage docs already name: polygon vertices
    meet there, so ``certain_timezone_at`` matches nothing. ``timezone_at`` answers
    with the final candidate's zone without testing it, and this method agrees rather
    than answering the empty list - which is the one branch where the two could have
    contradicted each other.
    """
    assert tf.certain_timezone_at(lng=0.0, lat=-90.0) is None
    assert tf.timezones_at(lng=0.0, lat=-90.0) == ["Antarctica/McMurdo"]
    assert tf.timezone_at(lng=0.0, lat=-90.0) == "Antarctica/McMurdo"


@pytest.mark.unit
@pytest.mark.parametrize("fixture_name", FIXTURES)
def test_the_answer_names_each_zone_once(tf: TimezoneFinder, fixture_name: str):
    """Zones, not polygons: several polygons of one zone containing the point is one entry.

    ``set(...)`` in the completeness test above would hide a duplicate, so the list
    shape is asserted separately from its contents.
    """
    for lng, lat in load_benchmark_points(fixture_name)[:SAMPLE_SIZE]:
        zones = tf.timezones_at(lng=lng, lat=lat)
        assert len(zones) == len(set(zones)), f"{zones} at ({lng}, {lat})"


@pytest.mark.unit
def test_the_global_function_answers_the_same(tf: TimezoneFinder):
    """The module-level convenience delegates to the shared instance."""
    for coords, expected in DOCUMENTED_OVERLAPS:
        lng, lat = coords
        assert timezones_at(lng=lng, lat=lat) == expected


@pytest.mark.slow
@pytest.mark.parametrize("fixture_name", FIXTURES)
def test_every_committed_point_agrees_with_timezone_at_and_the_full_scan(
    tf: TimezoneFinder, fixture_name: str
):
    """The unit tests above over the whole fixture rather than a sample of it.

    Both invariants at once, because the sweep is what costs: walking every candidate
    of 30,000 points is minutes of point-in-polygon work, and the two assertions share
    all of it.
    """
    for lng, lat in load_benchmark_points(fixture_name):
        zones = tf.timezones_at(lng=lng, lat=lat)
        assert zones[0] == tf.timezone_at(lng=lng, lat=lat)
        assert set(zones) == set(reference_zones(tf, lng, lat))
