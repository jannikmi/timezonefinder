"""What `scripts/measure_tzfpy_agreement.py` does before and after it counts.

The measurement itself needs `tzfpy`, which lives in the `compare` dependency
group and is deliberately absent from the CI test environment. What is worth
covering is not the counting but the parts that decide what the counts *mean* -
the overlapping-zone split, the matched-release guard, which borders count as a
land zone's - and the chart the docs page embeds. None of them needs the
package installed. The geometry that places a point a stated distance from a
border is `tests/test_border_sampling.py`.

There is deliberately no test asserting a disagreement *rate*. That number is a
property of whichever `tzfpy` release is installed, so such a test would fail
because someone else shipped - the same reason the comparison benchmarks stay
off the trend chart (see `benchmarks/test_comparison.py`).
"""

import json
import xml.etree.ElementTree as ElementTree

import numpy as np
import pytest

from scripts.border_sampling import Candidate
from scripts.configs import DOC_ROOT, read_data_version
from scripts.measure_tzfpy_agreement import (
    AGREE,
    CHART_PATH,
    OVERLAP_POLICY,
    SUBSTANTIVE,
    AgreementCounts,
    ChartPoint,
    DistanceResult,
    Measurement,
    _require_matching_dataset,
    axis_bound,
    axis_ticks,
    borders_a_land_zone,
    chart_point,
    classify,
    count_agreement,
    escape_svg_text,
    format_distance,
    is_decade,
    render_chart,
)


class _FakeTzfpy:
    def __init__(self, data_version: str) -> None:
        self._data_version = data_version

    def data_version(self) -> str:
        return self._data_version


def _counts(total: int, substantive: int) -> AgreementCounts:
    return AgreementCounts(total=total, overlap_policy=0, substantive=substantive)


def _measurement(*rates: tuple[float, int, int]) -> Measurement:
    """A synthetic sweep. Both groups hold 100 points, so a count is a percent."""
    return Measurement(
        data_version="2026c",
        tzfpy_version="1.3.3",
        by_distance=tuple(
            DistanceResult(
                distance_m=distance,
                drawn=2 * 100,
                all_borders=_counts(100, every),
                land_borders=_counts(100, land),
            )
            for distance, every, land in rates
        ),
        by_point_class={},
    )


@pytest.mark.unit
def test_the_same_answer_is_agreement() -> None:
    assert classify("Europe/Berlin", "Europe/Berlin", ["Europe/Berlin"]) == AGREE


@pytest.mark.unit
def test_a_different_pick_from_the_same_overlap_is_not_a_geometry_difference() -> None:
    # the dominant case away from borders: Asia/Urumqi sits inside Asia/Shanghai
    # in the source data, and each package names one of them. Counting these as
    # disagreements is what makes a raw rate an order of magnitude too high
    assert (
        classify("Asia/Urumqi", "Asia/Shanghai", ["Asia/Shanghai", "Asia/Urumqi"])
        == OVERLAP_POLICY
    )


@pytest.mark.unit
def test_a_zone_the_other_package_does_not_hold_is_substantive() -> None:
    # the border case: this package answers from the source polygon, the other
    # from a simplification of it that puts the point on the far side
    assert classify("Europe/Dublin", "Europe/London", ["Europe/London"]) == SUBSTANTIVE


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
        (2.0, 2.0): "Europe/Dublin",
        (3.0, 3.0): "Europe/Berlin",
    }
    theirs_first = {
        (0.0, 0.0): "Europe/Berlin",
        (1.0, 1.0): "Asia/Shanghai",
        (2.0, 2.0): "Europe/London",
        (3.0, 3.0): "Europe/Berlin",
    }
    theirs_all = {
        (0.0, 0.0): ["Europe/Berlin"],
        (1.0, 1.0): ["Asia/Shanghai", "Asia/Urumqi"],
        (2.0, 2.0): ["Europe/London"],
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
    assert counts.examples == ((2.0, 2.0, "Europe/Dublin", ("Europe/London",)),)


@pytest.mark.unit
def test_rates_are_percentages_and_an_empty_group_is_not_a_division_error() -> None:
    counts = AgreementCounts(total=2000, overlap_policy=10, substantive=524)
    assert counts.rate(counts.substantive) == pytest.approx(26.2)
    assert AgreementCounts(total=0, overlap_policy=0, substantive=0).rate(0) == 0.0


@pytest.mark.unit
def test_a_coastline_counts_as_a_land_zone_border() -> None:
    # a coastline is stored twice, in the land polygon and in the ocean polygon
    # around it, so one of the rings at the point is a land one
    ocean_ring = np.array([False, True])
    candidate = Candidate(lng=0.0, lat=0.0, distance_m=10.0, rings_at_distance=(0, 1))
    assert borders_a_land_zone(candidate, ocean_ring)


@pytest.mark.unit
def test_a_meridian_between_two_ocean_zones_does_not() -> None:
    # no simplification can move a line of longitude, so these borders would
    # only dilute a curve that is about geometry
    ocean_ring = np.array([True, True])
    candidate = Candidate(lng=0.0, lat=0.0, distance_m=10.0, rings_at_distance=(0, 1))
    assert not borders_a_land_zone(candidate, ocean_ring)


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
@pytest.mark.parametrize(
    ("distance_m", "expected"),
    [(1.0, "1 m"), (30.0, "30 m"), (1000.0, "1 km"), (10000.0, "10 km")],
)
def test_a_distance_reads_as_metres_or_kilometres(
    distance_m: float, expected: str
) -> None:
    assert format_distance(distance_m) == expected


@pytest.mark.unit
def test_nothing_observed_is_an_upper_bound_and_never_a_zero() -> None:
    # the whole reason the chart is on a log axis. A group with no disagreement
    # in it has not shown that the two packages agree out there, only that the
    # rate is under about 3/n - and plotting the zero is what would let a reader
    # conclude the curve reaches the axis
    assert AgreementCounts(total=20_000, overlap_policy=0, substantive=0).rate(0) == 0.0
    assert chart_point(
        AgreementCounts(total=20_000, overlap_policy=0, substantive=0)
    ) == ChartPoint(percent=0.015, is_upper_bound=True)
    assert chart_point(
        AgreementCounts(total=20_000, overlap_policy=0, substantive=3)
    ) == ChartPoint(percent=0.015, is_upper_bound=False)


@pytest.mark.unit
def test_an_upper_bound_says_so_in_its_label() -> None:
    assert ChartPoint(0.015, is_upper_bound=True).label == "<0.015%"
    assert ChartPoint(26.2, is_upper_bound=False).label == "26.2%"


@pytest.mark.unit
def test_the_chart_states_every_measured_rate() -> None:
    svg = render_chart(_measurement((1.0, 26, 34), (10.0, 17, 22), (1000.0, 0, 0)))
    assert svg.startswith("<svg ") and svg.rstrip().endswith("</svg>")
    for label in ("26%", "34%", "17%", "22%", "1 m", "10 m", "1 km"):
        assert label in svg, f"the chart does not state {label}"
    # the zero group is plotted as a bound, and the "<" has to survive as
    # markup or the whole file is a parse error rather than a chart
    assert "&lt;3%" in svg


@pytest.mark.unit
def test_the_chart_is_valid_xml() -> None:
    # nothing else validates this file: rstcheck accepts an `image::` whose
    # target does not parse, and the docs build copies it without reading it
    svg = render_chart(_measurement((1.0, 26, 34), (10.0, 0, 0)))
    ElementTree.fromstring(svg)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("text", "expected"),
    [("<0.015%", "&lt;0.015%"), ("a & b", "a &amp; b"), ("26.2%", "26.2%")],
)
def test_svg_text_is_escaped(text: str, expected: str) -> None:
    assert escape_svg_text(text) == expected


@pytest.mark.unit
def test_the_chart_is_deterministic_and_pre_commit_clean() -> None:
    # generated files in this repository must come out already formatted, or a
    # regeneration produces a diff nobody asked for - see CLAUDE.md
    measurement = _measurement((1.0, 26, 34), (10.0, 17, 22))
    svg = render_chart(measurement)
    assert svg == render_chart(measurement)
    assert svg.endswith("\n") and not svg.endswith("\n\n")
    assert not any(line != line.rstrip() for line in svg.splitlines())


@pytest.mark.unit
def test_the_committed_chart_is_where_the_docs_page_looks_for_it() -> None:
    # the path is declared once, in the module that writes it; this is the
    # other end of that - the docs page names the file, and nothing else would
    # notice a rename until the page rendered a broken image
    assert CHART_PATH.parent == DOC_ROOT
    assert CHART_PATH.is_file(), f"{CHART_PATH} is missing - run `make tzfpy-agreement`"
    assert CHART_PATH.name in (DOC_ROOT / "alternatives.rst").read_text(
        encoding="utf-8"
    )


@pytest.mark.unit
def test_a_saved_run_round_trips_so_the_chart_can_be_redrawn() -> None:
    # a full sweep takes about twenty minutes, so changing how the chart looks
    # must not require taking one - the same decoupling the benchmark reports
    # have. If this drifts, the redraw silently describes a different run
    measurement = _measurement((1.0, 26, 34), (10.0, 17, 22), (1000.0, 0, 0))
    restored = Measurement.from_json(json.loads(json.dumps(measurement.as_json())))
    assert restored == measurement
    assert render_chart(restored) == render_chart(measurement)


@pytest.mark.unit
def test_a_saved_run_keeps_the_examples_it_named() -> None:
    counts = AgreementCounts(
        total=10,
        overlap_policy=1,
        substantive=1,
        examples=((1.5, 2.5, "Europe/Dublin", ("Europe/London",)),),
    )
    measurement = Measurement("2026c", "1.3.3", (), {"random_points": counts})
    assert Measurement.from_json(measurement.as_json()) == measurement


@pytest.mark.unit
@pytest.mark.parametrize(
    ("value", "upwards", "expected"),
    [
        (47.0, True, 50.0),
        (50.0, True, 50.0),
        (5.1, True, 10.0),
        (0.0265, False, 0.01),
        (0.05, False, 0.05),
        (12.0, False, 10.0),
    ],
)
def test_the_axis_ends_on_a_round_number_just_outside_the_data(
    value: float, upwards: bool, expected: float
) -> None:
    # the axis is tied to what was measured rather than to a fixed decade: a
    # 100 % ceiling over a 47 % maximum spends a third of the plot on nothing
    # and invites the curve to be read against a number no run produced
    assert axis_bound(value, upwards=upwards) == pytest.approx(expected)


@pytest.mark.unit
def test_the_gridlines_step_through_ones_and_fives() -> None:
    assert axis_ticks(0.01, 50.0) == pytest.approx(
        [0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 50.0]
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("distance_m", "expected"),
    [(0.01, True), (0.05, False), (1.0, True), (5.0, False), (1000.0, True)],
)
def test_only_the_decade_distances_carry_a_printed_value(
    distance_m: float, expected: bool
) -> None:
    # eleven distances times two series is twenty-two labels over the curve;
    # the page prints the full table, so the chart names the decades only
    assert is_decade(distance_m) is expected


@pytest.mark.unit
def test_the_hollow_marker_is_explained_only_when_one_is_drawn() -> None:
    # a key for a symbol that is not on the chart is a puzzle, not a key
    with_bound = render_chart(_measurement((1.0, 26, 34), (1000.0, 0, 0)))
    assert "hollow" in with_bound

    without_bound = render_chart(_measurement((1.0, 26, 34), (1000.0, 1, 1)))
    assert "hollow" not in without_bound
