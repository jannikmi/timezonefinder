"""The paired A/B harness must hold the properties it exists to hold.

``benchmarks/candidate_comparison.py`` is a measurement instrument, so its own
correctness cannot be read off a run: a harness that fails to alternate the
order still prints a plausible number, which is exactly how the designs
``docs/benchmarking_methodology.rst`` records produced wrong answers. Every
property is therefore asserted here against an injected clock, so no assertion
depends on how fast the machine running the suite is.
"""

import pytest

from benchmarks.candidate_comparison import (
    DEFAULT_ROUNDS,
    CandidateComparison,
    compare_candidates,
)

INPUTS = list(range(500))


class FakeClock:
    """A timer whose every reading is scripted, so timings are exact.

    ``compare_candidates`` calls the timer twice per timed batch, so the
    duration of a batch is the gap between two consecutive readings. Recording
    the durations to hand out rather than the absolute readings keeps the tests
    readable.
    """

    def __init__(self, durations):
        self._readings = self._expand(durations)

    @staticmethod
    def _expand(durations):
        now = 0.0
        readings = []
        for duration in durations:
            readings.append(now)
            now += duration
            readings.append(now)
            # a gap between batches, so a missed reading shows up as a wrong
            # duration rather than as a plausible one
            now += 1.0
        return iter(readings)

    def __call__(self):
        return next(self._readings)


def _durations(per_round, rounds=DEFAULT_ROUNDS):
    """Warm-up pair, then ``per_round(index) -> (first, second)`` per round."""
    yield 0.0  # baseline warm-up
    yield 0.0  # challenger warm-up
    for round_index in range(rounds):
        first, second = per_round(round_index)
        yield first
        yield second


def _constant(baseline_seconds, challenger_seconds):
    """Durations in *call order*, which alternates round by round."""

    def per_round(round_index):
        if round_index % 2 == 0:
            return baseline_seconds, challenger_seconds
        return challenger_seconds, baseline_seconds

    return per_round


def _record_calls():
    calls = []
    return calls, (
        ("baseline", lambda item: calls.append(("baseline", item))),
        ("challenger", lambda item: calls.append(("challenger", item))),
    )


def _batches(calls, batch_size):
    """Split a recorded call log into the batches that produced it.

    Chunked by count rather than grouped by name on purpose: the order
    alternates, so two consecutive batches run by the same candidate straddle a
    round boundary and a name-grouped reading would silently merge them - which
    is the very property under test.
    """
    return [
        (calls[start][0], [item for _, item in calls[start : start + batch_size]])
        for start in range(0, len(calls), batch_size)
    ]


def test_the_order_alternates_round_by_round():
    """Neither candidate may systematically run second on a warmed cache."""
    calls, (baseline, challenger) = _record_calls()
    compare_candidates(baseline, challenger, INPUTS, rounds=6, batch_size=3)

    order = [name for name, _ in _batches(calls, 3)]
    assert order[:2] == ["baseline", "challenger"]  # the untimed warm-up pair
    assert order[2:] == ["baseline", "challenger", "challenger", "baseline"] * 3
    # every candidate goes first in exactly half the rounds
    assert order[2::2].count("baseline") == order[2::2].count("challenger") == 3


def test_both_candidates_see_the_same_inputs_within_a_round():
    """A round compares one draw, or it compares two workloads."""
    calls, (baseline, challenger) = _record_calls()
    compare_candidates(baseline, challenger, INPUTS, rounds=4, batch_size=5)

    rounds = _batches(calls, 5)[2:]  # drop the two warm-up batches
    assert len(rounds) == 8
    for (first_name, first), (second_name, second) in zip(rounds[::2], rounds[1::2]):
        assert first == second
        assert first_name != second_name


def test_inputs_are_sampled_at_random_rather_than_walked_in_order():
    """Container order hands a candidate a cache pattern no query stream has."""
    calls, (baseline, challenger) = _record_calls()
    compare_candidates(baseline, challenger, INPUTS, rounds=4, batch_size=50)

    drawn = [item for name, item in calls if name == "baseline"]
    assert drawn != sorted(drawn)
    # and a draw is not merely a rotation of the pool either
    assert len(set(drawn)) < len(drawn)


def test_the_same_seed_draws_the_same_workload():
    def drawn(seed):
        calls, (baseline, challenger) = _record_calls()
        compare_candidates(
            baseline, challenger, INPUTS, rounds=4, batch_size=20, seed=seed
        )
        return [item for name, item in calls if name == "baseline"]

    assert drawn(7) == drawn(7)
    assert drawn(7) != drawn(8)


def test_a_real_difference_is_reported_when_both_estimators_agree():
    """The challenger is faster in every round and by well over the threshold."""
    clock = FakeClock(_durations(_constant(1.0, 0.5)))
    result = compare_candidates(
        ("baseline", lambda item: None),
        ("challenger", lambda item: None),
        INPUTS,
        batch_size=1,
        timer=clock,
    )

    assert result.best_round_verdict == "faster"
    assert result.win_count_verdict == "faster"
    assert result.verdict == "faster"
    assert result.best_round_change == pytest.approx(-0.5)
    assert result.challenger_wins == DEFAULT_ROUNDS


def test_a_regression_is_reported_in_the_other_direction():
    clock = FakeClock(_durations(_constant(0.5, 1.0)))
    result = compare_candidates(
        ("baseline", lambda item: None),
        ("challenger", lambda item: None),
        INPUTS,
        batch_size=1,
        timer=clock,
    )

    assert result.verdict == "slower"
    assert result.best_round_change == pytest.approx(1.0)
    assert result.challenger_wins == 0


def test_identical_candidates_report_no_difference():
    clock = FakeClock(_durations(_constant(1.0, 1.0)))
    result = compare_candidates(
        ("baseline", lambda item: None),
        ("challenger", lambda item: None),
        INPUTS,
        batch_size=1,
        timer=clock,
    )

    # a tie is not a win, so the sign count sits at zero rather than at half
    assert result.challenger_wins == 0
    assert result.best_round_change == pytest.approx(0.0)
    assert result.best_round_verdict == "no difference"
    assert result.verdict == "unresolved"


def test_estimators_that_disagree_report_unresolved_rather_than_the_flattering_one():
    """The recorded failure: +0.5 % on the best round, 26 of 61 rounds won.

    A harness reporting either number alone ships one of two wrong answers.
    """
    result = CandidateComparison(
        baseline_name="baseline",
        challenger_name="challenger",
        rounds=61,
        batch_size=2_500,
        threshold=0.03,
        win_margin=0.10,
        best_baseline=1.0,
        best_challenger=0.90,
        challenger_wins=26,
    )

    assert result.best_round_verdict == "faster"
    assert result.win_count_verdict == "no difference"
    assert result.verdict == "unresolved"
    assert "no demonstrable difference" in result.render()


def test_a_difference_inside_the_threshold_is_reported_as_absent():
    """A single machine's own jitter is 3-9 %; 1 % cannot be demonstrated."""
    clock = FakeClock(_durations(_constant(1.0, 0.99)))
    result = compare_candidates(
        ("baseline", lambda item: None),
        ("challenger", lambda item: None),
        INPUTS,
        batch_size=1,
        timer=clock,
    )

    assert result.best_round_verdict == "no difference"
    # the sign count still sees the challenger win every round, so the honest
    # reading is that the two estimators do not agree
    assert result.win_count_verdict == "faster"
    assert result.verdict == "unresolved"


def test_the_rendered_block_names_both_estimators():
    clock = FakeClock(_durations(_constant(1.0, 0.5)))
    rendered = compare_candidates(
        ("shipped dict", lambda item: None),
        ("flat array", lambda item: None),
        INPUTS,
        batch_size=1,
        timer=clock,
    ).render()

    assert "flat array vs shipped dict" in rendered
    assert "order alternated" in rendered
    assert "best round" in rendered
    assert "rounds won" in rendered
    assert f"of {DEFAULT_ROUNDS}" in rendered


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"rounds": 1}, "rounds must be at least 2"),
        ({"batch_size": 0}, "batch_size must be at least 1"),
    ],
)
def test_a_degenerate_configuration_is_refused(kwargs, message):
    with pytest.raises(ValueError, match=message):
        compare_candidates(
            ("baseline", lambda item: None),
            ("challenger", lambda item: None),
            INPUTS,
            **kwargs,
        )


def test_an_empty_input_pool_is_refused():
    with pytest.raises(ValueError, match="no inputs"):
        compare_candidates(
            ("baseline", lambda item: None),
            ("challenger", lambda item: None),
            [],
        )


def test_two_candidates_may_not_share_a_name():
    """A report naming one implementation twice cannot be read afterwards."""
    with pytest.raises(ValueError, match="both candidates are named"):
        compare_candidates(
            ("same", lambda item: None),
            ("same", lambda item: None),
            INPUTS,
        )
