#!/usr/bin/env python3

"""Compare two benchmark measurements taken on the *same* machine.

Why this exists
---------------

The obvious way to judge a pull request is to compare its measurement against
the stored ``master`` baseline, which is what
``benchmark-action/github-action-benchmark`` does. On GitHub-hosted runners
that comparison is worthless: ``runs-on: ubuntu-latest`` pins the runner
*image*, not the hardware. Measured on this project's tracked core set,
repeated runs of **identical code** landed on AMD EPYC 9V74, AMD EPYC 7763 and
Intel Xeon Platinum 8573C parts at 2.30-3.69 GHz and spread up to ~1.58x -
larger than almost any change worth reviewing. A real 1.5x improvement once
showed up as a 21% *regression* purely because the two runs drew different
CPUs.

So the benchmark workflow measures the merge base and the pull request head in
the same job, on the same runner, minutes apart, and this script compares those
two directly. The machine term cancels because it is literally the same
machine - and rather than assuming that, the script *checks* it and says so in
the report.

``github-action-benchmark`` has no "compare these two files" mode, hence a
script rather than a configuration flag.

Usage::

    uv run python -m scripts.compare_benchmark_runs \\
        --base base-report/pass-1.json base-report/pass-2.json \\
        --head benchmark-report/benchmark-report.json \\
        --markdown-out "$GITHUB_STEP_SUMMARY"

Several reports may be given per side; they are reduced elementwise by
``min``, for the same reason the tracked estimator within a run is the min
(see :mod:`scripts.normalize_benchmark_json`). The workflow uses this to
sandwich the head measurement between two base passes, so a machine that
drifts over the job's lifetime does not masquerade as a code change.
"""

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from scripts.benchmark_noise import collect_estimator_values
from scripts.benchmark_utils import (
    BENCHMARK_ESTIMATORS,
    COMPARABILITY_KEYS,
    DEFAULT_BENCHMARK_ESTIMATOR,
    DEFAULT_METRIC_KEY,
    METRIC_SPECS,
    BenchmarkEstimator,
    MetricSpec,
    comparability_info,
    cpu_model,
    load_benchmark_json,
    machine_label,
)
from scripts.normalize_benchmark_json import ESTIMATOR_KEY

# How far head may drift from base before a row is called out. Same-runner
# measurement removes the machine term but not the runner's own moment-to-
# moment jitter, and that residual has never been measured on CI in isolation.
# 110% comes from the closest thing there is: a five-run study that spread only
# 106.8%, against a pool that spreads up to 158% across machines - so those
# five must have drawn near-identical hardware, which makes their spread a
# reasonable stand-in for single-machine jitter (and an upper bound on it
# regardless, since a cross-machine sample can only be wider than a
# within-machine one). Tighten it once a run of `make benchmark-noise` on a
# single CI runner says what the floor really is.
REGRESSION_THRESHOLD_PCT = 110.0

# Benchmark names reach this script from the pull request's own code and are
# rendered into a comment on the base repository, so they are quoted, stripped
# of markdown-significant characters and bounded in length.
MAX_RENDERED_NAME_LEN = 120


@dataclass(frozen=True)
class BenchmarkComparison:
    """One benchmark's tracked duration on either side of a change."""

    name: str
    base: float
    head: float

    @property
    def ratio_pct(self) -> float:
        """``head / base`` as a percentage - >100% means head is slower.

        Directly comparable to ``github-action-benchmark``'s
        ``alert-threshold``, which uses the same convention.
        """
        return self.head / self.base * 100.0

    @property
    def change_pct(self) -> float:
        """Signed change in duration; negative means head got faster."""
        return self.ratio_pct - 100.0

    @property
    def factor(self) -> float:
        """``base / head``: >1 means head is that many times faster."""
        return self.base / self.head


def tracked_estimator(
    runs: Sequence[dict[str, Any]], fallback: BenchmarkEstimator
) -> BenchmarkEstimator:
    """Return the estimator ``runs`` were normalised to track.

    ``scripts.normalize_benchmark_json`` stamps every report it writes, so the
    reader does not have to be told out of band which statistic the numbers
    represent.

    :raises ValueError: if the reports disagree, which would mean comparing a
        min against a mean.
    """
    recorded = {run[ESTIMATOR_KEY] for run in runs if ESTIMATOR_KEY in run}
    if len(recorded) > 1:
        raise ValueError(
            f"the given reports were normalized to track different estimators "
            f"({sorted(recorded)}), so their numbers are not comparable"
        )
    return recorded.pop() if recorded else fallback


def reduce_side(
    runs: Iterable[dict[str, Any]], estimator: BenchmarkEstimator
) -> dict[str, float]:
    """Collapse repeated passes of one side into one value per benchmark.

    ``collect_estimator_values`` already rejects passes that do not contain
    the same benchmarks, so a partial pass cannot quietly halve the sample.
    """
    return {
        name: min(values)
        for name, values in collect_estimator_values(runs, estimator).items()
    }


def compare_runs(
    base_runs: Sequence[dict[str, Any]],
    head_runs: Sequence[dict[str, Any]],
    estimator: BenchmarkEstimator,
) -> list[BenchmarkComparison]:
    """Compare two sides benchmark by benchmark, worst regression first.

    :raises ValueError: if the two sides do not contain the same benchmarks -
        which happens when the pull request renames or adds one, and means
        there is nothing to compare that entry against.
    """
    base = reduce_side(base_runs, estimator)
    head = reduce_side(head_runs, estimator)
    if set(base) != set(head):
        raise ValueError(
            "base and head do not contain the same benchmarks, so they cannot "
            f"be compared. Only in base: {sorted(set(base) - set(head))}; "
            f"only in head: {sorted(set(head) - set(base))}. Renaming a "
            "benchmark also resets its trend history - see "
            "tests/test_benchmark_names.py."
        )
    for name, value in (*base.items(), *head.items()):
        if value <= 0:
            raise ValueError(
                f"benchmark {name!r} reports a non-positive '{estimator}' of "
                f"{value!r}s, so a ratio cannot be derived from it"
            )
    comparisons = [
        BenchmarkComparison(name=name, base=base[name], head=head[name])
        for name in base
    ]
    return sorted(comparisons, key=lambda c: c.ratio_pct, reverse=True)


def comparability_warnings(
    base_runs: Sequence[dict[str, Any]], head_runs: Sequence[dict[str, Any]]
) -> list[str]:
    """List the reasons the two sides may not actually be comparable.

    The point of the whole exercise is that both sides ran on one machine, so
    that is verified rather than assumed; the rest are workload changes that
    make the durations describe different amounts of work.
    """
    warnings: list[str] = []

    models = {cpu_model(run) or "unknown" for run in (*base_runs, *head_runs)}
    if len(models) > 1:
        warnings.append(
            "the two sides were **not measured on the same machine** "
            f"({', '.join(sorted(models))}), which is exactly the confound "
            "this comparison exists to remove. Treat the numbers below as "
            "meaningless and re-run the workflow."
        )

    base_info = [comparability_info(run) for run in base_runs]
    head_info = [comparability_info(run) for run in head_runs]
    for key in COMPARABILITY_KEYS:
        values = {info[key] for info in (*base_info, *head_info)}
        if len(values) > 1:
            base_values = sorted({str(info[key]) for info in base_info})
            head_values = sorted({str(info[key]) for info in head_info})
            warnings.append(
                f"`{key}` differs between the two sides "
                f"(base: {', '.join(base_values)}; head: {', '.join(head_values)}), "
                "so the two measurements do not describe the same workload."
            )
    return warnings


def _render_name(name: str) -> str:
    """Quote a benchmark name for a markdown table cell.

    The name originates in the pull request's own code and is rendered into a
    comment on the base repository, so backticks (which would break out of the
    code span), pipes (which would forge table columns) and newlines are
    replaced rather than escaped.
    """
    collapsed = re.sub(r"\s+", " ", name).strip()
    cleaned = collapsed.replace("`", "'").replace("|", "/")
    if len(cleaned) > MAX_RENDERED_NAME_LEN:
        cleaned = cleaned[: MAX_RENDERED_NAME_LEN - 1] + "…"
    return f"`{cleaned}`"


def _verdict(
    comparison: BenchmarkComparison, threshold_pct: float, metric: MetricSpec
) -> str:
    if comparison.ratio_pct >= threshold_pct:
        return f"🔴 {metric.worse}"
    if comparison.factor * 100.0 >= threshold_pct:
        return f"🟢 {metric.better}"
    return "⚪ unchanged"


def regressions(
    comparisons: Iterable[BenchmarkComparison], threshold_pct: float
) -> list[BenchmarkComparison]:
    """The comparisons whose head is at least ``threshold_pct`` of base."""
    return [c for c in comparisons if c.ratio_pct >= threshold_pct]


def render_markdown(
    comparisons: Sequence[BenchmarkComparison],
    *,
    estimator: BenchmarkEstimator,
    machine: str | None,
    warnings: Sequence[str] = (),
    threshold_pct: float = REGRESSION_THRESHOLD_PCT,
    base_label: str = "base",
    head_label: str = "head",
    metric: MetricSpec = METRIC_SPECS[DEFAULT_METRIC_KEY],
) -> str:
    """Render the comparison for a job summary or a pull request comment."""
    lines = [
        f"## {metric.heading}: head vs merge base (same runner)",
        "",
        f"Both sides measured in one job on **{machine or 'an unrecorded CPU'}**, "
        f"{metric.estimator_phrase.format(estimator=estimator)}. Comparing on one "
        "machine is what makes these numbers meaningful: `ubuntu-latest` pins the "
        "runner image, not the CPU, and the pool's spread on unchanged code is "
        "larger than most real changes.",
        "",
    ]
    for warning in warnings:
        lines += ["> [!WARNING]", f"> {warning}", ""]
    lines += [
        f"| {metric.row_noun} | {base_label} | {head_label} | change | |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for c in comparisons:
        lines.append(
            f"| {_render_name(c.name)} | {metric.format_value(c.base)} | "
            f"{metric.format_value(c.head)} | {c.change_pct:+.1f}% ({c.factor:.2f}x) | "
            f"{_verdict(c, threshold_pct, metric)} |"
        )
    lines += [
        "",
        f"{metric.change_help} Rows are flagged at {threshold_pct:.0f}%.",
        "",
        f"> {metric.noise_note}",
    ]
    return "\n".join(lines) + "\n"


def _load_all(paths: Sequence[Path]) -> list[dict[str, Any]]:
    return [load_benchmark_json(path) for path in paths]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Compare two pytest-benchmark measurements taken on the same "
            "machine (a pull request's merge base and its head) and render the "
            "result as markdown."
        )
    )
    parser.add_argument(
        "--base",
        type=Path,
        nargs="+",
        required=True,
        help="one or more reports for the merge base (reduced elementwise by min)",
    )
    parser.add_argument(
        "--head",
        type=Path,
        nargs="+",
        required=True,
        help="one or more reports for the pull request head",
    )
    parser.add_argument(
        "--estimator",
        choices=BENCHMARK_ESTIMATORS,
        default=DEFAULT_BENCHMARK_ESTIMATOR,
        help=(
            "statistic to compare, used only if the reports do not record which "
            f"one they were normalized to (default: {DEFAULT_BENCHMARK_ESTIMATOR})"
        ),
    )
    parser.add_argument(
        "--threshold-pct",
        type=float,
        default=REGRESSION_THRESHOLD_PCT,
        help=(
            "flag a benchmark whose head/base ratio reaches this percentage "
            f"(default: {REGRESSION_THRESHOLD_PCT:.0f})"
        ),
    )
    parser.add_argument(
        "--metric",
        choices=sorted(METRIC_SPECS),
        default=DEFAULT_METRIC_KEY,
        help=(
            "what the compared numbers measure, which selects the units and "
            f"wording of the rendered table (default: {DEFAULT_METRIC_KEY}). The "
            "comparison itself is unit-agnostic - see scripts/measure_memory.py"
        ),
    )
    parser.add_argument(
        "--markdown-out",
        type=Path,
        help="also append the report to this file (e.g. $GITHUB_STEP_SUMMARY)",
    )
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help=(
            "exit non-zero if any benchmark reaches the threshold. Off by "
            "default: the same-runner noise floor has not been measured yet, "
            "and a gate that fires on noise is one everybody learns to ignore"
        ),
    )
    args = parser.parse_args()

    base_runs = _load_all(args.base)
    head_runs = _load_all(args.head)

    try:
        estimator = tracked_estimator([*base_runs, *head_runs], args.estimator)
        comparisons = compare_runs(base_runs, head_runs, estimator)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    warnings = comparability_warnings(base_runs, head_runs)
    report = render_markdown(
        comparisons,
        estimator=estimator,
        machine=machine_label(head_runs[0]),
        warnings=warnings,
        threshold_pct=args.threshold_pct,
        metric=METRIC_SPECS[args.metric],
    )
    print(report)
    if args.markdown_out is not None:
        with open(args.markdown_out, "a") as f:
            f.write(report)

    worse = regressions(comparisons, args.threshold_pct)
    if worse and args.fail_on_regression:
        names = ", ".join(c.name for c in worse)
        print(
            f"ERROR: {METRIC_SPECS[args.metric].row_noun}(s) "
            f"{METRIC_SPECS[args.metric].worse} than the threshold: {names}",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
