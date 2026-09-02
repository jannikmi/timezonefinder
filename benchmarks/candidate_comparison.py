"""Paired A/B harness for two candidate implementations of one stage.

The rest of ``benchmarks/`` compares *one* implementation across commits or
machines. Deciding between two *candidates* in a single working tree is a
different measurement, and ``docs/benchmarking_methodology.rst`` records three
designs for it that produced wrong answers in this repository - each of them
flattering the newer candidate, each of them hand-rolled again the next time
the question came up. This module is that harness, kept where it can be reused
instead of re-derived.

The four properties it exists to hold, all of which have been got wrong here:

* **The order alternates round by round.** Running A then B lets A warm
  everything the two share - coordinate validation, the H3 call, the zone-name
  lookup, the branch predictors - and hands B the benefit for free. One
  shortcut comparison read as 13.3 % faster in a fixed order and 0.3 % once the
  order alternated.
* **The whole public call is measured**, not the stage. Two candidates rarely
  divide the work at the same place, so a boundary drawn around "the lookup"
  charges one of them for something the other pays a moment later. This module
  cannot enforce that - it times whatever callable it is given - so
  :func:`compare_candidates` requires the callables to take one *input* and
  perform the whole call on it.
* **Inputs are sampled at random.** Iterating a container in its own order
  hands it a cache-friendly access pattern no real query stream has; worth
  77 ns against 108 ns on the same lookup, a third of the quantity compared.
* **Two estimators, believed only when they agree.** The ratio of the two best
  rounds is the least noise-sensitive estimator; the count of rounds the
  candidate won assumes nothing about the noise distribution. Where a
  difference is real they move together. Where they disagree - one saying
  +0.5 %, the other 26 of 61 rounds - the honest answer is ``unresolved``,
  which no single estimator can give.

Reporting only, like every other measurement here: nothing in this module
fails a build. See ``docs/benchmarking_methodology.rst``.
"""

import random
import time
from dataclasses import dataclass
from typing import Callable, Final, Literal, Sequence, TypeVar

T = TypeVar("T")

#: One candidate: a display name and a callable performing the whole public
#: call for one input.
Candidate = tuple[str, Callable[[T], object]]

#: How :class:`CandidateComparison` reads. ``faster``/``slower`` are from the
#: challenger's point of view; ``no difference`` means both estimators say the
#: effect is inside the threshold, and ``unresolved`` means they disagree.
Verdict = Literal["faster", "slower", "no difference", "unresolved"]

#: Odd, so the round-level sign count cannot tie, and large enough that the
#: two best rounds are drawn from a decent sample. 61 is the count the recorded
#: comparisons in ``docs/benchmarking_methodology.rst`` were run at.
DEFAULT_ROUNDS: Final[int] = 61
#: Inputs per round. One round has to be well above timer resolution while
#: staying short enough that the machine's state is unlikely to change inside
#: it; the batch suite's ``BATCH_SIZE`` is 2,500 for the first reason.
DEFAULT_BATCH_SIZE: Final[int] = 2_500
#: Below this a difference is reported as absent rather than as small: a single
#: machine's own jitter on this workload is 3-9 %, so an effect under it cannot
#: be demonstrated by any number of rounds.
DEFAULT_THRESHOLD: Final[float] = 0.03
#: How far the round-level win share must sit from an even split before the
#: sign count claims a direction. At :data:`DEFAULT_ROUNDS` this is 37 of 61.
DEFAULT_WIN_MARGIN: Final[float] = 0.10


@dataclass(frozen=True)
class CandidateComparison:
    """What one paired comparison measured, and what it is allowed to claim."""

    baseline_name: str
    challenger_name: str
    rounds: int
    batch_size: int
    threshold: float
    win_margin: float
    #: fastest round of each candidate, in seconds per batch
    best_baseline: float
    best_challenger: float
    #: rounds in which the challenger's batch was the faster of the pair
    challenger_wins: int

    @property
    def best_round_change(self) -> float:
        """Challenger's fastest round relative to the baseline's.

        Negative is faster, matching the sign convention of the base/head
        comparison table (``scripts/compare_benchmark_runs.py``).
        """
        return self.best_challenger / self.best_baseline - 1.0

    @property
    def win_share(self) -> float:
        """Fraction of rounds the challenger won."""
        return self.challenger_wins / self.rounds

    @property
    def best_round_verdict(self) -> Verdict:
        """What the two best rounds alone say."""
        if self.best_round_change < -self.threshold:
            return "faster"
        if self.best_round_change > self.threshold:
            return "slower"
        return "no difference"

    @property
    def win_count_verdict(self) -> Verdict:
        """What the round-level sign count alone says."""
        if self.win_share > 0.5 + self.win_margin:
            return "faster"
        if self.win_share < 0.5 - self.win_margin:
            return "slower"
        return "no difference"

    @property
    def verdict(self) -> Verdict:
        """The reportable answer: the estimators' agreement, or ``unresolved``.

        Deliberately not a tie-break. Two estimators that disagree are the
        measurement saying it cannot resolve the difference, and reporting the
        one that happens to show an effect is how a 0.3 % change gets shipped
        as 13.3 %.
        """
        if self.best_round_verdict == self.win_count_verdict:
            return self.best_round_verdict
        return "unresolved"

    def render(self) -> str:
        """A human-readable block, in the form the other reports use."""
        lines = [
            f"{self.challenger_name} vs {self.baseline_name}"
            f"  ({self.rounds} rounds x {self.batch_size} inputs, order alternated)",
            f"  best round : {self.best_baseline * 1e3:.3f} ms -> "
            f"{self.best_challenger * 1e3:.3f} ms "
            f"({self.best_round_change * 100:+.1f} %, {self.best_round_verdict})",
            f"  rounds won : {self.challenger_wins} of {self.rounds} "
            f"({self.win_share * 100:.1f} %, {self.win_count_verdict})",
            f"  verdict    : {self.verdict}",
        ]
        if self.verdict == "unresolved":
            lines.append(
                "  the estimators disagree, so there is no demonstrable difference"
            )
        return "\n".join(lines)


def compare_candidates(
    baseline: Candidate[T],
    challenger: Candidate[T],
    inputs: Sequence[T],
    *,
    rounds: int = DEFAULT_ROUNDS,
    batch_size: int = DEFAULT_BATCH_SIZE,
    threshold: float = DEFAULT_THRESHOLD,
    win_margin: float = DEFAULT_WIN_MARGIN,
    seed: int = 0,
    timer: Callable[[], float] = time.perf_counter,
) -> CandidateComparison:
    """Measure two candidates against each other over one shared input pool.

    Both callables must perform the *whole* public call for one input, so the
    boundary between the stage under test and everything around it falls where
    each candidate puts it rather than where the harness does.

    Each round draws ``batch_size`` inputs at random from ``inputs`` - the same
    draw for both candidates, a fresh draw per round - and times one pass of
    each over it. The order within a round alternates, so neither candidate
    systematically runs second on a warmed cache. ``seed`` makes the draws
    reproducible; ``timer`` exists so the harness itself can be tested.
    """
    if not inputs:
        raise ValueError("no inputs to sample from")
    if rounds < 2:
        raise ValueError(f"rounds must be at least 2, got {rounds}")
    if batch_size < 1:
        raise ValueError(f"batch_size must be at least 1, got {batch_size}")

    baseline_name, run_baseline = baseline
    challenger_name, run_challenger = challenger
    if baseline_name == challenger_name:
        raise ValueError(f"both candidates are named {baseline_name!r}")

    rng = random.Random(seed)
    # One untimed pass each, so neither candidate's first round pays for an
    # import, a JIT compilation or a cold page the other has already faulted in.
    warmup = [rng.choice(inputs) for _ in range(min(batch_size, len(inputs)))]
    _time_batch(run_baseline, warmup, timer)
    _time_batch(run_challenger, warmup, timer)

    best_baseline = float("inf")
    best_challenger = float("inf")
    challenger_wins = 0
    for round_index in range(rounds):
        batch = [rng.choice(inputs) for _ in range(batch_size)]
        if round_index % 2 == 0:
            baseline_seconds = _time_batch(run_baseline, batch, timer)
            challenger_seconds = _time_batch(run_challenger, batch, timer)
        else:
            challenger_seconds = _time_batch(run_challenger, batch, timer)
            baseline_seconds = _time_batch(run_baseline, batch, timer)
        best_baseline = min(best_baseline, baseline_seconds)
        best_challenger = min(best_challenger, challenger_seconds)
        if challenger_seconds < baseline_seconds:
            challenger_wins += 1

    return CandidateComparison(
        baseline_name=baseline_name,
        challenger_name=challenger_name,
        rounds=rounds,
        batch_size=batch_size,
        threshold=threshold,
        win_margin=win_margin,
        best_baseline=best_baseline,
        best_challenger=best_challenger,
        challenger_wins=challenger_wins,
    )


def _time_batch(
    call: Callable[[T], object], batch: Sequence[T], timer: Callable[[], float]
) -> float:
    """Seconds for one pass of ``call`` over ``batch``.

    The loop is deliberately the plainest one available: a comprehension or
    ``map`` would build a list of every answer, which on a batch of thousands
    is allocation the measurement did not ask for.
    """
    started = timer()
    for item in batch:
        call(item)
    return timer() - started
