"""What `scripts/measure_tzfpy_agreement.py` does before it counts anything.

The measurement itself needs `tzfpy`, which lives in the `compare` dependency
group and is deliberately absent from the CI test environment. What is worth
covering is not the counting but the parts that decide what the counts *mean*:
the overlapping-zone split, the matched-release guard, and the geometry that
places a probe a stated number of metres from a border. None of them needs the
package installed.

There is deliberately no test asserting a disagreement *rate*. That number is a
property of whichever `tzfpy` release is installed, so such a test would fail
because someone else shipped - the same reason the comparison benchmarks stay
off the trend chart (see `benchmarks/test_comparison.py`).
"""

import numpy as np
import pytest

from scripts.measure_tzfpy_agreement import (
    AGREE,
    METRES_PER_DEGREE_LATITUDE,
    METRES_PER_DEGREE_LONGITUDE,
    OVERLAP_POLICY,
    SUBSTANTIVE,
    AgreementCounts,
    BorderSite,
    _require_matching_dataset,
    classify,
    count_agreement,
    edge_vectors,
    probes_at,
)
from scripts.configs import read_data_version
from timezonefinder.configs import COORD2INT_FACTOR


def _ring(*vertices: tuple[float, float]) -> np.ndarray:
    """The `(2, n)` int32 layout the packaged boundary files store."""
    return np.array(
        [
            [round(lng * COORD2INT_FACTOR) for lng, _ in vertices],
            [round(lat * COORD2INT_FACTOR) for _, lat in vertices],
        ],
        dtype=np.int32,
    )


class _FakeTzfpy:
    def __init__(self, data_version: str) -> None:
        self._data_version = data_version

    def data_version(self) -> str:
        return self._data_version


@pytest.mark.unit
def test_the_same_answer_is_agreement() -> None:
    assert classify("Europe/Berlin", "Europe/Berlin", ["Europe/Berlin"]) == AGREE


@pytest.mark.unit
def test_a_different_pick_from_the_same_overlap_is_not_a_geometry_difference() -> None:
    # the dominant case in practice: Asia/Urumqi sits inside Asia/Shanghai in the
    # source data, and each package names one of them. Counting these as
    # disagreements is what makes the raw rate an order of magnitude too high.
    assert (
        classify("Asia/Urumqi", "Asia/Shanghai", ["Asia/Shanghai", "Asia/Urumqi"])
        == OVERLAP_POLICY
    )


@pytest.mark.unit
def test_a_zone_the_other_package_does_not_hold_is_substantive() -> None:
    # the coastline case: this package answers from the source polygon, the
    # other from a simplification that puts the point offshore
    assert classify("Pacific/Auckland", "Etc/GMT-12", ["Etc/GMT-12"]) == SUBSTANTIVE


@pytest.mark.unit
def test_no_answer_of_ours_is_substantive() -> None:
    # `timezone_at` returns None only when nothing covers the point; it cannot
    # be "in" the other package's set, and silently reading it as agreement
    # would hide exactly the gaps this measurement is looking for
    assert classify(None, "Etc/GMT-12", ["Etc/GMT-12"]) == SUBSTANTIVE


@pytest.mark.unit
def test_the_three_verdicts_are_counted_apart() -> None:
    points = [(0.0, 0.0), (1.0, 1.0), (2.0, 2.0), (3.0, 3.0)]
    ours = {
        (0.0, 0.0): "Europe/Berlin",
        (1.0, 1.0): "Asia/Urumqi",
        (2.0, 2.0): "Pacific/Auckland",
        (3.0, 3.0): "Europe/Berlin",
    }
    theirs_first = {
        (0.0, 0.0): "Europe/Berlin",
        (1.0, 1.0): "Asia/Shanghai",
        (2.0, 2.0): "Etc/GMT-12",
        (3.0, 3.0): "Europe/Berlin",
    }
    theirs_all = {
        (0.0, 0.0): ["Europe/Berlin"],
        (1.0, 1.0): ["Asia/Shanghai", "Asia/Urumqi"],
        (2.0, 2.0): ["Etc/GMT-12"],
        (3.0, 3.0): ["Europe/Berlin"],
    }
    counts = count_agreement(
        points,
        lambda lng, lat: ours[(lng, lat)],
        lambda lng, lat: theirs_first[(lng, lat)],
        lambda lng, lat: theirs_all[(lng, lat)],
    )
    assert counts.total == 4
    assert counts.overlap_policy == 1
    assert counts.substantive == 1
    # what a bare `timezone_at` vs `get_tz` comparison would have reported
    assert counts.first_answer_disagreements == 2
    assert counts.examples == ((2.0, 2.0, "Pacific/Auckland", ("Etc/GMT-12",)),)


@pytest.mark.unit
def test_rates_are_percentages_and_an_empty_class_is_not_a_division_error() -> None:
    counts = AgreementCounts(total=5000, overlap_policy=160, substantive=3)
    assert counts.rate(counts.substantive) == pytest.approx(0.06)
    assert AgreementCounts(total=0, overlap_policy=0, substantive=0).rate(0) == 0.0


@pytest.mark.unit
def test_a_matching_release_is_what_makes_the_measurement_attributable() -> None:
    packaged = read_data_version()
    assert _require_matching_dataset(_FakeTzfpy(packaged)) == packaged


@pytest.mark.unit
def test_a_different_boundary_release_refuses_to_report() -> None:
    # a border that moved between two upstream releases is not geometry that was
    # simplified, and reporting it as one would be the whole error this guards
    with pytest.raises(SystemExit, match="no measurement to take"):
        _require_matching_dataset(_FakeTzfpy("1999a"))


@pytest.mark.unit
def test_an_edge_is_measured_in_metres_along_the_ring() -> None:
    # a degree of longitude on the equator, as one edge of a closed ring
    _, _, east, north, length = edge_vectors(_ring((0.0, 0.0), (1.0, 0.0)))
    assert length[0] == pytest.approx(METRES_PER_DEGREE_LONGITUDE, rel=1e-6)
    assert east[0] == pytest.approx(METRES_PER_DEGREE_LONGITUDE, rel=1e-6)
    assert north[0] == pytest.approx(0.0, abs=1e-6)
    # the ring closes, so the second edge is the return leg
    assert length[1] == pytest.approx(METRES_PER_DEGREE_LONGITUDE, rel=1e-6)


@pytest.mark.unit
def test_a_degree_of_longitude_shortens_towards_the_pole() -> None:
    _, _, _, _, equator = edge_vectors(_ring((0.0, 0.0), (1.0, 0.0)))
    _, _, _, _, sixty = edge_vectors(_ring((0.0, 60.0), (1.0, 60.0)))
    assert sixty[0] == pytest.approx(equator[0] * 0.5, rel=1e-3)


@pytest.mark.unit
def test_the_seam_of_a_ring_that_wraps_the_antimeridian_has_no_length() -> None:
    # the jump from +179.9 to -179.9 is where the ring closes, not a piece of
    # border half the planet long - weighting by it would put most of the
    # sample on a line nobody can stand next to
    _, _, _, _, length = edge_vectors(
        _ring((179.9, 10.0), (-179.9, 10.0), (-179.9, 11.0), (179.9, 11.0))
    )
    assert length[0] == 0.0
    assert length[2] == 0.0
    assert length[1] > 0.0 and length[3] > 0.0


@pytest.mark.unit
def test_a_probe_lands_the_stated_distance_either_side_of_the_site() -> None:
    site = BorderSite(lng=0.0, lat=0.0, normal_east=0.0, normal_north=1.0)
    north, south = probes_at(site, 1000.0)
    assert north[0] == pytest.approx(0.0)
    assert north[1] == pytest.approx(1000.0 / METRES_PER_DEGREE_LATITUDE)
    assert south[1] == pytest.approx(-north[1])


@pytest.mark.unit
def test_the_longitude_offset_grows_with_latitude() -> None:
    # 100 m east is twice as many degrees at 60 degrees north as at the equator,
    # and getting this wrong would silently mislabel every column of the sweep
    at_equator = probes_at(
        BorderSite(lng=0.0, lat=0.0, normal_east=1.0, normal_north=0.0), 100.0
    )
    at_sixty = probes_at(
        BorderSite(lng=0.0, lat=60.0, normal_east=1.0, normal_north=0.0), 100.0
    )
    assert at_equator[0][0] == pytest.approx(100.0 / METRES_PER_DEGREE_LONGITUDE)
    assert at_sixty[0][0] == pytest.approx(2 * at_equator[0][0], rel=1e-3)


@pytest.mark.unit
def test_a_probe_pushed_off_the_globe_is_dropped_rather_than_wrapped() -> None:
    # a site on the last polygon before the pole, probed outwards: a latitude
    # of 90.001 is not a coordinate, and `timezone_at` would reject it
    site = BorderSite(lng=0.0, lat=89.9999, normal_east=0.0, normal_north=1.0)
    assert len(probes_at(site, 1000.0)) == 1
