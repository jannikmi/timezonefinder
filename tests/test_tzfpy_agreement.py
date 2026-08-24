"""The interpretation `scripts/measure_tzfpy_agreement.py` puts on two answers.

The measurement itself needs `tzfpy`, which lives in the `compare` dependency
group and is deliberately absent from the CI test environment. What is worth
covering is not the counting but the two rules that make the counts mean
anything - the overlapping-zone split and the matched-release guard - and
neither needs the package installed.

There is deliberately no test asserting a disagreement *rate*. That number is a
property of whichever `tzfpy` release is installed, so such a test would fail
because someone else shipped - the same reason the comparison benchmarks stay
off the trend chart (see `benchmarks/test_comparison.py`).
"""

import pytest

from scripts.measure_tzfpy_agreement import (
    AGREE,
    OVERLAP_POLICY,
    SUBSTANTIVE,
    AgreementCounts,
    _require_matching_dataset,
    classify,
    count_agreement,
)
from scripts.configs import read_data_version


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
