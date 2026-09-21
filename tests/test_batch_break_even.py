"""Unit tests for the batch break-even sweep: its derivation rules, and its chart.

The derivation tests build synthetic rungs rather than measuring, because what they
check is the *reading* of a ladder - which crossing counts, which does not - and a real
measurement cannot be asked for an ambiguous one on demand.
"""

import random
import xml.etree.ElementTree as ElementTree
from dataclasses import asdict
from pathlib import Path

import pytest

from benchmarks.candidate_comparison import (
    DEFAULT_THRESHOLD,
    DEFAULT_WIN_MARGIN,
    CandidateComparison,
)
from scripts.measure_batch_break_even import (
    CONTROL_MIN_BATCH_SIZE,
    DEFAULT_LADDER,
    MIN_CALLS_PER_ROUND,
    MIN_POOL_BATCHES,
    PreparedBatch,
    _scalar_caller,
    break_even,
    comparison_of,
    control_spread,
    ladder_for,
    load_points_csv,
    measure_rung,
    per_point_seconds,
    prepare_pool,
    saturation,
    speedup,
)
from timezonefinder.zone_names import NAMES_GATHER_MIN_BATCH

pytestmark = pytest.mark.unit


def test_scalar_caller_matches_the_selected_result_representation():
    """An id batch must not be credited with skipping work its scalar peer performs."""

    class Finder:
        @staticmethod
        def timezone_at(*, lng, lat):
            return f"name:{lng},{lat}"

        @staticmethod
        def timezone_id_at(*, lng, lat):
            return int(lng + lat)

    batch = PreparedBatch([(1.0, 2.0)], None, None)  # type: ignore[arg-type]
    finder = Finder()
    assert _scalar_caller(finder, "names")(batch) == ["name:1.0,2.0"]  # type: ignore[arg-type]
    assert _scalar_caller(finder, "ids")(batch) == [3]  # type: ignore[arg-type]


def _rung(
    batch_size: int,
    baseline_per_point: float,
    challenger_per_point: float,
    *,
    rounds: int = 61,
    challenger_wins: int | None = None,
    points_per_round_target: int = 25_000,
) -> dict:
    """One synthetic rung, in the shape the measurement stores.

    ``challenger_wins`` defaults to whatever agrees with the best-round estimator, so a
    test that does not care about the second estimator gets a resolved verdict; pass it
    explicitly to build the disagreement that reads as ``unresolved``.
    """
    calls_per_round = max(1, points_per_round_target // batch_size)
    points_per_round = calls_per_round * batch_size
    if challenger_wins is None:
        ratio = challenger_per_point / baseline_per_point
        if ratio < 1 - DEFAULT_THRESHOLD:
            challenger_wins = rounds
        elif ratio > 1 + DEFAULT_THRESHOLD:
            challenger_wins = 0
        else:
            challenger_wins = rounds // 2
    comparison = CandidateComparison(
        baseline_name="scalar loop",
        challenger_name="timezone_names_at",
        rounds=rounds,
        batch_size=calls_per_round,
        threshold=DEFAULT_THRESHOLD,
        win_margin=DEFAULT_WIN_MARGIN,
        best_baseline=baseline_per_point * points_per_round,
        best_challenger=challenger_per_point * points_per_round,
        challenger_wins=challenger_wins,
    )
    return {
        "batch_size": batch_size,
        "calls_per_round": calls_per_round,
        "points_per_round": points_per_round,
        "pool_batches": 8,
        "comparison": asdict(comparison),
    }


def _ladder(pairs: list[tuple[int, float, float]]) -> list[dict]:
    return [_rung(size, baseline, challenger) for size, baseline, challenger in pairs]


# --- normalisation ------------------------------------------------------------------


def test_per_point_divides_by_the_work_actually_done_not_the_target():
    """A rung whose size does not divide the target does less work than asked for.

    Dividing by the nominal target instead would put a sawtooth of up to a percent into
    a curve whose saturation is read at a 5 % tolerance.
    """
    rung = _rung(127, 1e-6, 1e-6, points_per_round_target=25_000)
    assert rung["calls_per_round"] == 196
    assert rung["points_per_round"] == 196 * 127 == 24_892
    assert per_point_seconds(rung, "best_baseline") == pytest.approx(1e-6)


def test_speedup_is_the_baseline_over_the_challenger():
    rung = _rung(100, 2e-6, 1e-6)
    assert speedup(rung) == pytest.approx(2.0)


def test_verdict_comes_from_the_harness_rather_than_being_recomputed():
    rung = _rung(100, 1e-6, 1e-6, challenger_wins=61)
    # best rounds say "no difference", the sign count says "faster": the harness's rule
    # is that two estimators which disagree resolve nothing, and the page must inherit
    # that rather than pick the one showing an effect
    assert comparison_of(rung).verdict == "unresolved"


# --- break-even ---------------------------------------------------------------------


def test_break_even_brackets_the_crossing():
    rungs = _ladder(
        [(1, 1e-6, 8e-6), (10, 1e-6, 2e-6), (100, 1e-6, 5e-7), (1000, 1e-6, 4e-7)]
    )
    crossing = break_even(rungs)
    assert crossing.status == "bracketed"
    assert (crossing.lower, crossing.upper) == (10, 100)
    assert crossing.non_monotone == ()


def test_break_even_reports_an_interval_never_a_single_size():
    """A discrete ladder plus a threshold verdict cannot locate a crossing point."""
    crossing = break_even(_ladder([(1, 1e-6, 8e-6), (10, 1e-6, 5e-7)]))
    assert crossing.lower != crossing.upper
    assert "between" in crossing.describe()


def test_break_even_below_the_ladder_when_the_smallest_rung_already_wins():
    crossing = break_even(_ladder([(1, 1e-6, 5e-7), (10, 1e-6, 4e-7)]))
    assert crossing.status == "below_ladder"
    assert crossing.upper == 1
    assert crossing.lower is None


def test_break_even_not_reached_when_no_rung_wins():
    crossing = break_even(_ladder([(1, 1e-6, 8e-6), (10, 1e-6, 2e-6)]))
    assert crossing.status == "not_reached"


def test_break_even_takes_the_terminal_run_not_the_first_crossing():
    """One lucky rung that wins and then loses again must not fix the bracket.

    The reported interval is the point beyond which the batch never loses, and the lone
    early win is reported separately - it is a reason to re-measure, not a finer answer.
    """
    rungs = _ladder(
        [
            (1, 1e-6, 8e-6),
            (10, 1e-6, 5e-7),  # wins here...
            (100, 1e-6, 2e-6),  # ...and loses again
            (1000, 1e-6, 5e-7),
            (2000, 1e-6, 4e-7),
        ]
    )
    crossing = break_even(rungs)
    assert (crossing.lower, crossing.upper) == (100, 1000)
    assert crossing.non_monotone == (10,)


def test_break_even_does_not_call_a_table_of_wins_never_faster():
    """One noisy top rung must not turn seven ``faster`` rungs into "never faster".

    The terminal-run rule is right - a crossing is the size beyond which batching never
    loses again - but an empty terminal run has two causes, and reporting the wrong one
    puts a headline on the page that its own table contradicts.
    """
    rungs = [
        _rung(1, 1e-6, 8e-6),
        *(_rung(n, 1e-6, 5e-7) for n in (5, 10, 20, 50, 100, 200, 500)),
        _rung(1000, 1e-6, 1e-6, challenger_wins=61),  # unresolved at the top
    ]
    crossing = break_even(rungs)
    assert crossing.status == "no_terminal_run"
    assert crossing.non_monotone == (5, 10, 20, 50, 100, 200, 500)
    assert "not established" in crossing.describe()
    assert crossing.bracket is None


def test_break_even_not_reached_is_kept_for_a_ladder_that_never_wins():
    crossing = break_even(_ladder([(1, 1e-6, 8e-6), (10, 1e-6, 2e-6)]))
    assert crossing.status == "not_reached"
    assert crossing.non_monotone == ()


def test_unresolved_rungs_inside_the_bracket_do_not_move_it():
    """Rungs near the crossing read ``unresolved`` by construction, not by failure."""
    rungs = [
        _rung(1, 1e-6, 8e-6),
        _rung(10, 1e-6, 1e-6, challenger_wins=61),  # unresolved
        _rung(100, 1e-6, 5e-7),
        _rung(1000, 1e-6, 4e-7),
    ]
    assert comparison_of(rungs[1]).verdict == "unresolved"
    crossing = break_even(rungs)
    assert (crossing.lower, crossing.upper) == (10, 100)


# --- saturation ---------------------------------------------------------------------


def test_saturation_finds_where_the_curve_flattens():
    # challenger per point = 1us + 20us/N, a fixed per-call cost amortised over N
    rungs = _ladder([(n, 2e-6, 1e-6 + 20e-6 / n) for n in (1, 10, 100, 1000, 5000)])
    settled = saturation(rungs, tolerance=0.05)
    assert settled.status == "saturated"
    # 1000 is within 5 % of the top-three median; 100 (1.2us) is 20 % above it
    assert settled.batch_size == 1000


def test_saturation_requires_every_larger_rung_to_stay_inside_the_tolerance():
    """One lucky dip at a small rung is not saturation."""
    rungs = _ladder(
        [
            (1, 2e-6, 4e-6),
            (10, 2e-6, 1.0e-6),  # a dip, well under the asymptote
            (100, 2e-6, 1.6e-6),  # but the curve is still above it here
            (1000, 2e-6, 1.02e-6),
            (5000, 2e-6, 1.0e-6),
        ]
    )
    assert saturation(rungs, tolerance=0.05).batch_size == 1000


def test_saturation_reference_is_the_top_rungs_not_the_ladder_minimum():
    """A minimum over a dozen noisy rungs is biased low and would delay the answer."""
    rungs = _ladder(
        [
            (n, 2e-6, value)
            for n, value in (
                (1, 4e-6),
                (10, 2e-6),
                (100, 1.00e-6),
                (1000, 1.02e-6),
                (5000, 1.01e-6),
            )
        ]
    )
    settled = saturation(rungs, tolerance=0.05)
    # the ladder minimum is 1.00us at N=100; the median of the top three is 1.01us
    assert settled.reference_seconds == pytest.approx(1.01e-6, rel=1e-9)


def test_saturation_not_reached_while_the_curve_is_still_falling():
    """A pure 1/N curve has not saturated anywhere, and must not be said to have.

    This is the check that makes ``not_reached`` reachable at all: the median of the top
    three rungs of *any* decreasing curve is its second-from-last value, so without a
    separate test for whether the top of the ladder has stopped moving, that rung would
    always qualify and every run would report saturation.
    """
    rungs = _ladder([(n, 2e-6, 100e-6 / n) for n in (1, 10, 100, 1000)])
    assert saturation(rungs, tolerance=0.05).status == "not_reached"


def test_saturation_not_reached_is_decided_by_the_top_of_the_ladder():
    """Same ladder, extended until it flattens: now there is an answer."""
    falling = [(n, 2e-6, 1e-6 + 100e-6 / n) for n in (1, 10, 100)]
    flat = [(n, 2e-6, 1e-6 + 100e-6 / n) for n in (1000, 2000, 5000)]
    assert saturation(_ladder(falling), tolerance=0.05).status == "not_reached"
    assert saturation(_ladder(falling + flat), tolerance=0.05).status == "saturated"


def test_saturation_refuses_a_tolerance_inside_the_instruments_own_floor():
    """Below the harness's threshold nothing is demonstrable, saturation included."""
    rungs = _ladder([(n, 2e-6, 1e-6) for n in (1, 10, 100)])
    with pytest.raises(ValueError, match="threshold"):
        saturation(rungs, tolerance=DEFAULT_THRESHOLD)


def test_saturation_needs_enough_rungs_to_take_a_reference_from():
    with pytest.raises(ValueError, match="at least 3 rungs"):
        saturation(_ladder([(1, 2e-6, 1e-6), (10, 2e-6, 1e-6)]))


# --- the control --------------------------------------------------------------------


def test_control_spread_excludes_the_smallest_rungs():
    """Their baseline carries the harness's per-batch cost divided by a very small N.

    That is a known structural term, not evidence of a contaminated ladder, and a
    control that flagged it every run would train its reader to ignore it.
    """
    rungs = _ladder(
        [
            (1, 4e-6, 1e-6),  # wildly inflated, and excluded
            (10, 1.00e-6, 1e-6),
            (100, 1.02e-6, 1e-6),
            (1000, 1.01e-6, 1e-6),
        ]
    )
    control = control_spread(rungs)
    assert control.min_batch_size == CONTROL_MIN_BATCH_SIZE
    assert control.rungs_used == 3
    assert control.spread == pytest.approx(0.02, abs=1e-9)
    assert control.within_threshold


def test_control_spread_flags_a_ladder_that_did_not_measure_one_thing():
    rungs = _ladder([(10, 1e-6, 1e-6), (100, 1e-6, 1e-6), (1000, 2e-6, 1e-6)])
    control = control_spread(rungs)
    assert control.spread == pytest.approx(1.0)
    assert not control.within_threshold


def test_control_spread_needs_a_rung_above_its_floor():
    with pytest.raises(ValueError, match="no rung at or above"):
        control_spread(_ladder([(1, 1e-6, 1e-6), (2, 1e-6, 1e-6)]))


# --- the ladder ---------------------------------------------------------------------


def test_default_ladder_straddles_the_names_gather_threshold():
    """``ZoneNames.names_of`` changes regime there, so the ladder must sample both sides.

    Imported rather than hard-coded, because the constant is tunable and a ladder that
    wrote 127/128 would silently stop bracketing it.
    """
    assert NAMES_GATHER_MIN_BATCH in DEFAULT_LADDER
    assert NAMES_GATHER_MIN_BATCH - 1 in DEFAULT_LADDER


def test_ladder_is_capped_at_half_the_pool():
    """At N == pool size only one batch exists without replacement, which is no sample."""
    assert ladder_for((1, 10, 100, 1000), pool_size=200) == [1, 10, 100]


def test_ladder_is_sorted_and_deduplicated():
    assert ladder_for((100, 1, 100, 10), pool_size=10_000) == [1, 10, 100]


def test_ladder_refuses_a_pool_too_small_for_any_requested_size():
    with pytest.raises(ValueError, match="without replacement"):
        ladder_for((500, 1000), pool_size=100)


# --- the batch pool -----------------------------------------------------------------


def test_pool_batches_hold_no_duplicate_point():
    """With replacement, points sharing an H3 cell would be answered once for the whole
    batch - the saving would grow with N and fake exactly the curve being measured."""
    points = [(float(i), float(-i)) for i in range(500)]
    for batch in prepare_pool(points, 50, random.Random(0)):
        assert len(set(batch.points)) == 50
        assert batch.lngs.shape == batch.lats.shape == (50,)
        assert batch.lngs.flags["C_CONTIGUOUS"]


def test_pool_always_holds_more_than_one_batch():
    points = [(float(i), float(-i)) for i in range(500)]
    assert len(prepare_pool(points, 250, random.Random(0))) >= MIN_POOL_BATCHES


def test_pool_is_reproducible_under_a_seed():
    points = [(float(i), float(-i)) for i in range(500)]
    first = prepare_pool(points, 10, random.Random(7))
    second = prepare_pool(points, 10, random.Random(7))
    assert [batch.points for batch in first] == [batch.points for batch in second]


def test_a_rung_with_too_few_calls_per_round_is_refused():
    """Below a handful of calls, ``min`` over rounds is the luckiest call, not the
    least perturbed round."""
    points = [(float(i), float(-i)) for i in range(50)]
    with pytest.raises(ValueError, match="--points-per-round"):
        measure_rung(
            finder=None,
            points=points,
            batch_size=10,
            api="names",
            rounds=3,
            points_per_round_target=10 * (MIN_CALLS_PER_ROUND - 1),
            seed=0,
        )


# --- the CSV a downstream user brings ------------------------------------------------


def test_points_csv_reads_two_columns_and_skips_a_header(tmp_path: Path):
    path = tmp_path / "points.csv"
    path.write_text("lng,lat\n13.358,52.5061\n2.3522,48.8566\n", encoding="utf-8")
    assert load_points_csv(path) == [(13.358, 52.5061), (2.3522, 48.8566)]


def test_points_csv_rejects_a_swapped_pair_it_can_detect(tmp_path: Path):
    """Columns are lng first. A swap is a valid coordinate over most of the populated
    world, so an out-of-range latitude is the only swap this can catch - and catching
    it is worth more than accepting the file."""
    path = tmp_path / "points.csv"
    path.write_text("52.5061,213.358\n", encoding="utf-8")
    with pytest.raises(ValueError, match="out of range"):
        load_points_csv(path)


def test_points_csv_rejects_a_non_numeric_row_past_the_header(tmp_path: Path):
    path = tmp_path / "points.csv"
    path.write_text("13.358,52.5061\nnot,numbers\n", encoding="utf-8")
    with pytest.raises(ValueError, match="two numeric columns"):
        load_points_csv(path)


def test_points_csv_rejects_an_empty_file(tmp_path: Path):
    path = tmp_path / "points.csv"
    path.write_text("# only a comment\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no coordinates"):
        load_points_csv(path)


# --- the chart -----------------------------------------------------------------------
#
# seaborn lives in the `benchmark` dependency group, which is deliberately absent from
# the measurement environment (pyproject.toml says why), so these five skip there.
#
# The skip is taken *inside each test*, never at module scope: a module-level
# `importorskip` skips the whole file, which would take the derivation tests above - the
# ones that need no plotting stack at all - down with it wherever seaborn is missing, and
# that is exactly the environment continuous integration runs.


def _require_seaborn() -> None:
    pytest.importorskip("seaborn", reason="the `benchmark` dependency group")


def _fake_run() -> dict:
    return {
        "machine_info": {
            "cpu": {"brand_raw": "Test CPU"},
            "timezonefinder": {
                "python_version": "3.13.0",
                "python_implementation": "CPython",
                "platform_system": "Linux",
                "platform_machine": "x86_64",
                "platform_processor": "x86_64",
                "numpy_version": "2.2.0",
                "using_clang_pip": True,
                "using_numba": False,
                "timezonefinder_version": "9.0.0",
                "acceleration_path": "clang",
                "in_memory": False,
                "scalar_api": "timezone_at",
                "batch_api": "timezone_names_at",
                "points_per_round_target": 25_000,
                "rounds": 61,
                "seed": 0,
                "names_gather_min_batch": NAMES_GATHER_MIN_BATCH,
                "saturation_tolerance": 0.05,
                "control_spread_threshold": 0.15,
                "control_spread_min_batch_size": CONTROL_MIN_BATCH_SIZE,
                "fixture_version": 3,
                "data_version": "2026c",
            },
        },
        "sweeps": [
            {
                "point_class": "random",
                "points_source": "random_points",
                "pool_size": 10_000,
                "ladder_cap": 5_000,
                "rungs": [
                    _rung(1, 1.3e-6, 12e-6),
                    _rung(10, 1.3e-6, 2.2e-6),
                    _rung(20, 1.3e-6, 1.32e-6, challenger_wins=31),  # unresolved
                    _rung(100, 1.3e-6, 1.0e-6),
                    _rung(1000, 1.3e-6, 8.2e-7),
                    _rung(5000, 1.3e-6, 8.1e-7),
                ],
            }
        ],
    }


def test_chart_is_byte_identical_across_renders(tmp_path: Path):
    """The one property a committed generated file must have.

    matplotlib salts its element ids from ``uuid4`` and stamps a date into the SVG
    unless told not to, so without the settings in ``_configure_matplotlib`` this file
    would differ on every single render and churn forever, hiding the numbers that
    actually moved.
    """
    _require_seaborn()
    from scripts.batch_break_even_chart import render_sweep

    run = _fake_run()
    first = render_sweep(run, tmp_path / "a.svg")
    second = render_sweep(run, tmp_path / "b.svg")
    assert first == second


def test_chart_is_pre_commit_clean(tmp_path: Path):
    _require_seaborn()
    from scripts.batch_break_even_chart import render_sweep

    markup = render_sweep(_fake_run(), tmp_path / "chart.svg")
    assert markup.endswith("\n")
    assert not markup.endswith("\n\n")
    assert all(line == line.rstrip() for line in markup.splitlines())


def test_chart_is_well_formed_xml_and_carries_its_annotations(tmp_path: Path):
    _require_seaborn()
    from scripts.batch_break_even_chart import render_sweep

    markup = render_sweep(_fake_run(), tmp_path / "chart.svg")
    ElementTree.fromstring(markup)  # raises if matplotlib emitted anything unparseable
    # svg.fonttype='none' keeps the labels as real text nodes rather than path outlines,
    # which is what makes the file both diffable and machine-independent
    assert "equal - scalar loop and batch" in markup
    assert "break-even" in markup
    assert f"names gather ({NAMES_GATHER_MIN_BATCH})" in markup
    assert "the two estimators do not resolve this rung" in markup


def test_chart_frame_carries_both_estimators(tmp_path: Path):
    """The two panels are the repository's "believe it only where both agree" rule
    drawn rather than asserted, so both quantities must reach the frame."""
    _require_seaborn()
    from scripts.batch_break_even_chart import sweep_frame

    frame = sweep_frame(_fake_run())
    assert list(frame["batch_size"]) == [1, 10, 20, 100, 1000, 5000]
    assert frame["speedup"].iloc[0] < 1.0 < frame["speedup"].iloc[-1]
    assert set(frame.columns) >= {"speedup", "win_share", "verdict", "point_class"}


def test_renderer_writes_the_page_and_the_chart_together(tmp_path: Path):
    _require_seaborn()
    from scripts.render_benchmark_reports import render_batch_break_even

    page, chart = tmp_path / "page.rst", tmp_path / "sweep.svg"
    render_batch_break_even(_fake_run(), page, chart)
    text = page.read_text(encoding="utf-8")

    assert chart.exists()
    assert f".. image:: {chart.name}" in text
    # the derived answers on the page are the helpers' own, not a second implementation
    rungs = _fake_run()["sweeps"][0]["rungs"]
    crossing = break_even(rungs)
    assert f"between {crossing.lower} and {crossing.upper} points per call" in text
    assert f"{saturation(rungs).batch_size:,}" in text
    assert "C extension (clang)" in text
    assert "timezone_ids_at()`` against a ``timezone_id_at()`` loop" in text
    assert text.endswith("\n") and not text.endswith("\n\n")


def test_renderer_refuses_a_ladder_that_is_not_ascending(tmp_path: Path):
    """Both answers are read as runs along the ladder and mean nothing out of order."""
    _require_seaborn()
    from scripts.render_benchmark_reports import render_batch_break_even

    run = _fake_run()
    run["sweeps"][0]["rungs"].reverse()
    with pytest.raises(ValueError, match="ascending"):
        render_batch_break_even(run, tmp_path / "page.rst", tmp_path / "sweep.svg")


def test_renderer_uses_the_thresholds_the_run_was_taken_under(tmp_path: Path):
    """A stored run must render as the answers it made, not as this checkout's constants.

    The measurement stamps its tolerances into the JSON precisely so a re-render cannot
    silently restate them; nothing read them back until this test.
    """
    _require_seaborn()
    from scripts.render_benchmark_reports import batch_break_even_settings

    run = _fake_run()
    run["machine_info"]["timezonefinder"]["saturation_tolerance"] = 0.42
    run["machine_info"]["timezonefinder"]["control_spread_threshold"] = 0.99
    run["machine_info"]["timezonefinder"]["control_spread_min_batch_size"] = 77
    settings = batch_break_even_settings(run["machine_info"]["timezonefinder"])
    assert settings.saturation_tolerance == 0.42
    assert settings.control_spread_threshold == 0.99
    assert settings.control_spread_min_batch_size == 77


def test_settings_fall_back_for_a_run_taken_before_they_were_stamped():
    from scripts.measure_batch_break_even import (
        CONTROL_SPREAD_THRESHOLD,
        DEFAULT_SATURATION_TOLERANCE,
    )
    from scripts.render_benchmark_reports import batch_break_even_settings

    settings = batch_break_even_settings({})
    assert settings.saturation_tolerance == DEFAULT_SATURATION_TOLERANCE
    assert settings.control_spread_threshold == CONTROL_SPREAD_THRESHOLD


def test_saturation_is_withheld_from_the_headline_when_the_control_fails(
    tmp_path: Path,
):
    """Saturation is an absolute quantity read across rungs, so a drifting baseline
    cannot support it - and three repeat runs showed it moving with the control.

    The crossing is a within-rung comparison and stays in the headline either way.
    """
    _require_seaborn()
    from scripts.render_benchmark_reports import render_batch_break_even

    run = _fake_run()
    # make the scalar baseline wander across rungs, which is what the control detects
    for factor, rung in zip(
        (1.0, 1.0, 1.0, 1.0, 1.0, 2.0), run["sweeps"][0]["rungs"], strict=True
    ):
        rung["comparison"]["best_baseline"] *= factor

    page = tmp_path / "page.rst"
    render_batch_break_even(run, page, tmp_path / "sweep.svg")
    text = page.read_text(encoding="utf-8")

    assert "not established on this run" in text
    assert "stops improving beyond" not in text
    # the crossing survives a noisy baseline and must still be stated
    assert "points per call" in text
