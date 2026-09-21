#!/usr/bin/env python3

"""Draw the batch break-even sweep that ``docs/benchmark_results_batch_break_even.rst``
embeds.

Drawn by the *renderer* from a stored run, never by the measurement script, so a
committed run can be redrawn without re-measuring - the decoupling
``scripts/render_benchmark_reports.py`` and
``contributing/development/generated-file-regeneration-rules.md`` both require.

Two panels on a shared logarithmic x axis, because the repository's verdict rule is that
a difference is believed only where **both** estimators show it
(``benchmarks/candidate_comparison.py``). Drawing one and labelling the other states the
rule; drawing both shows it, and where the panels disagree the reader is looking
directly at what ``unresolved`` means.

* top - the best-round speed-up, the estimator least sensitive to noise
* bottom - the round-level win share, which assumes nothing about the noise distribution

Deliberately **not** a box plot over rounds. That would show the spread of per-round
timings, which ``docs/benchmarking_methodology.rst`` defines as measurement noise rather
than a difference in what was measured - it is why the tracked estimator is ``min`` -
so putting the machine's interference in the most prominent position on the page invites
exactly the misreading the three recorded A/B failures were about. The interval this
measurement genuinely has lives on the *x* axis, where the shaded break-even band puts
it: it is the resolution limit of a discrete ladder, not a spread in any measured
quantity.

seaborn rather than direct matplotlib: fourteen rungs, two panels, two estimators and
four annotated rules benefit from its long-form data and semantic grouping APIs. The
smaller ``tzfpy`` agreement chart uses matplotlib directly, under the same deterministic
SVG constraints.
"""

from pathlib import Path
from typing import Any, Sequence

import matplotlib

# before pyplot, which otherwise picks an interactive backend that CI has no display for
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.ticker import FixedLocator, FuncFormatter, NullFormatter  # noqa: E402

from benchmarks.candidate_comparison import DEFAULT_WIN_MARGIN  # noqa: E402
from scripts.benchmark_utils import machine_label  # noqa: E402
from scripts.measure_batch_break_even import (  # noqa: E402
    break_even,
    comparison_of,
    per_point_seconds,
    point_class_label,
    speedup,
)

#: Salt for the element ids matplotlib derives by hashing. Its default is ``None``, which
#: means a fresh ``uuid4`` per process - so without this line the committed SVG differs
#: on every single render and the file churns forever, hiding the numbers that moved.
SVG_HASH_SALT = "timezonefinder-batch-break-even"

#: Verdicts the harness could not resolve. Their markers are drawn hollow, the convention
#: ``docs/tzfpy_agreement_by_distance.svg`` already uses for "nothing was demonstrated
#: here" - a rung where the two estimators disagree must not read as a measured value.
UNRESOLVED_VERDICTS = frozenset({"no difference", "unresolved"})

FIGURE_SIZE = (11.0, 8.0)
PALETTE = "colorblind"


def _configure_matplotlib() -> None:
    """Make the SVG a file that only changes when a number changes.

    matplotlib's SVG writer is not deterministic out of the box, and each of these
    settings suppresses one source of churn in a *committed* generated file:

    * ``svg.hashsalt`` - element ids are otherwise salted from ``uuid4()``
    * ``svg.fonttype='none'`` - glyphs are otherwise emitted as path outlines taken from
      whatever font file the machine has, which makes the output machine-dependent and
      unreadable in a diff; ``none`` emits real ``<text>`` nodes instead
    * the ``Date`` metadata, suppressed at ``savefig`` time, is otherwise an RDF stamp of
      the moment of rendering

    What remains is the matplotlib version itself, which rewrites the markup wholesale on
    an upgrade. That is why ``pyproject.toml``'s ``benchmark`` group carries a ceiling and
    not only a floor.
    """
    matplotlib.rcParams["svg.hashsalt"] = SVG_HASH_SALT
    matplotlib.rcParams["svg.fonttype"] = "none"


def sweep_frame(run: dict[str, Any]) -> pd.DataFrame:
    """The stored rungs as one long-form frame, which is seaborn's input shape."""
    rows = []
    for sweep in run["sweeps"]:
        for rung in sweep["rungs"]:
            comparison = comparison_of(rung)
            rows.append(
                {
                    "point_class": point_class_label(sweep["point_class"]),
                    "batch_size": rung["batch_size"],
                    "speedup": speedup(rung),
                    "win_share": comparison.win_share,
                    "verdict": comparison.verdict,
                    "per_point_seconds": per_point_seconds(rung, "best_challenger"),
                }
            )
    return pd.DataFrame(rows)


def _subtitle(run: dict[str, Any]) -> str:
    """Two lines: what was compared, then where. Two because one does not fit.

    The acceleration path belongs here and is load-bearing: this page describes the one
    backend its environment bound, and a reader must not carry the number to a different
    install.
    """
    info = run["machine_info"]["timezonefinder"]
    what = " | ".join(
        [
            f"{info['batch_api']}() against a {info['scalar_api']}() loop",
            f"{info['acceleration_path']} path",
            "in memory" if info.get("in_memory") else "memory mapped",
        ]
    )
    where = [
        f"{info['rounds']} rounds x ~{info['points_per_round_target']:,} points per rung"
    ]
    machine = machine_label(run)
    if machine:
        where.append(machine)
    if info.get("data_version"):
        where.append(f"data {info['data_version']}")
    return f"{what}\n{' | '.join(where)}"


#: Where the speed-up axis gets a labelled tick. A 1-2-5 ladder per decade, which is what
#: a log axis is readable at, filtered to the range the data actually occupies.
SPEEDUP_TICKS = (0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0)


def _label_speedup_axis(ax, values: Sequence[float]) -> None:
    """Ticks reading ``0.5x`` / ``1x`` / ``2x`` rather than ``10^0``.

    matplotlib's default log formatter labels the decades only, which on a curve
    spanning 0.1x to 2x leaves exactly one labelled tick and makes the distance from
    parity - the quantity the whole panel exists to show - impossible to read off.
    """
    # A margin around the data rather than snapping out to the bracketing ticks. Snapping
    # would floor a curve bottoming at 0.098x down to the 0.05x tick and spend a third of
    # the panel on empty space; snapping *in* would clip that marker off the axis. A
    # margin does neither, and is wide enough that the ticks just outside the data - the
    # ones naming the floor and the ceiling of the curve - still land on the page, which
    # matplotlib's own limits would have cut.
    low, high = min(values) / 1.15, max(values) * 1.15
    ticks = [t for t in SPEEDUP_TICKS if low <= t <= high]
    ax.yaxis.set_major_locator(FixedLocator(ticks))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:g}x"))
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.set_ylim(low, high)


def _annotate_rungs(ax, frame: pd.DataFrame, run: dict[str, Any]) -> None:
    """The three vertical rules every panel carries."""
    names_gather = run["machine_info"]["timezonefinder"].get("names_gather_min_batch")
    if names_gather and names_gather <= frame["batch_size"].max():
        # Without this rule the step at the gather threshold reads as a measurement
        # failure rather than as the documented regime switch it is.
        ax.axvline(names_gather, color="0.55", linestyle=":", linewidth=1.0, zorder=1)

    for sweep in run["sweeps"]:
        bracket = break_even(sweep["rungs"]).bracket
        if bracket is not None:
            ax.axvspan(*bracket, color="0.85", alpha=0.45, zorder=0)


def _draw_unresolved(
    ax, frame: pd.DataFrame, column: str, classes: Sequence[str]
) -> None:
    """Redraw the markers the harness could not resolve as hollow ones."""
    palette = dict(zip(classes, sns.color_palette(PALETTE, len(classes)), strict=True))
    unresolved = frame[frame["verdict"].isin(UNRESOLVED_VERDICTS)]
    for point_class, group in unresolved.groupby("point_class", sort=False):
        ax.plot(
            group["batch_size"],
            group[column],
            linestyle="none",
            marker="o",
            markersize=7,
            markerfacecolor="white",
            markeredgecolor=palette[point_class],
            markeredgewidth=1.6,
            zorder=5,
        )


def render_sweep(run: dict[str, Any], output_path: Path) -> str:
    """Write the sweep to ``output_path`` as SVG and return the markup written."""
    _configure_matplotlib()
    sns.set_theme(style="whitegrid", context="paper", palette=PALETTE)

    frame = sweep_frame(run)
    classes = list(dict.fromkeys(frame["point_class"]))
    rungs = sorted(frame["batch_size"].unique())

    figure, (top, bottom) = plt.subplots(
        2,
        1,
        sharex=True,
        figsize=FIGURE_SIZE,
        height_ratios=[3, 1],
        constrained_layout=True,
    )

    # --- top: the best-round speed-up -------------------------------------------
    sns.lineplot(
        data=frame,
        x="batch_size",
        y="speedup",
        hue="point_class",
        marker="o",
        markersize=6,
        ax=top,
    )
    _annotate_rungs(top, frame, run)
    _draw_unresolved(top, frame, "speedup", classes)
    # log y so that 0.5x and 2.0x sit equidistant from parity: on a linear axis the
    # sub-1 half of the curve compresses into a sliver and the crossing - the whole
    # subject of this page - becomes unreadable
    top.set_yscale("log")
    _label_speedup_axis(top, frame["speedup"])
    top.axhline(1.0, color="0.25", linewidth=1.4, zorder=2)
    top.set_ylabel("speed-up (scalar loop / batched)")
    top.annotate(
        "equal - scalar loop and batch",
        xy=(rungs[0], 1.0),
        xytext=(2, 4),
        textcoords="offset points",
        fontsize=8,
        color="0.25",
    )

    for sweep in run["sweeps"]:
        bracket = break_even(sweep["rungs"]).bracket
        if bracket is not None:
            lower, upper = bracket
            # inside the band and near the top, where the legend is not: the band is the
            # statement that the answer is an interval, so its label must sit on it.
            # The geometric mean centres it on a logarithmic axis.
            top.annotate(
                f"break-even\n{lower}-{upper}",
                xy=((lower * upper) ** 0.5, top.get_ylim()[1]),
                xytext=(0, -6),
                textcoords="offset points",
                fontsize=8,
                color="0.3",
                ha="center",
                va="top",
            )

    names_gather = run["machine_info"]["timezonefinder"].get("names_gather_min_batch")
    if names_gather and rungs[0] <= names_gather <= rungs[-1]:
        top.annotate(
            f"names gather ({names_gather})",
            xy=(names_gather, top.get_ylim()[0]),
            xytext=(3, 6),
            textcoords="offset points",
            fontsize=8,
            color="0.45",
            rotation=90,
            va="bottom",
        )

    handles, labels = top.get_legend_handles_labels()
    handles.append(
        Line2D(
            [],
            [],
            linestyle="none",
            marker="o",
            markerfacecolor="white",
            markeredgecolor="0.35",
            markersize=7,
        )
    )
    labels.append("the two estimators do not resolve this rung")
    # upper left: the curve rises left to right, so this is the one corner it never
    # reaches, and the break-even label sits top-centre on the band
    top.legend(handles, labels, loc="upper left", frameon=True, fontsize=8)

    # --- bottom: the round-level win share ---------------------------------------
    sns.lineplot(
        data=frame,
        x="batch_size",
        y="win_share",
        hue="point_class",
        marker="o",
        markersize=6,
        legend=False,
        ax=bottom,
    )
    _annotate_rungs(bottom, frame, run)
    _draw_unresolved(bottom, frame, "win_share", classes)
    bottom.axhline(0.5, color="0.25", linewidth=1.4, zorder=2)
    # the band inside which the sign count is not allowed to claim a direction, taken
    # from the harness rather than restated, so the two cannot drift apart
    bottom.axhspan(
        0.5 - DEFAULT_WIN_MARGIN, 0.5 + DEFAULT_WIN_MARGIN, color="0.9", zorder=0
    )
    bottom.set_ylim(-0.02, 1.02)
    bottom.set_ylabel("rounds won\nby the batch")
    bottom.set_xlabel("batch size (points per batched call)")

    # --- shared x ------------------------------------------------------------------
    bottom.set_xscale("log")
    bottom.xaxis.set_major_locator(FixedLocator(rungs))
    # a tick at every rung, but a label only where one fits: fourteen labels on a log
    # axis overlap (127 and 128 land on top of each other), and the decades plus the
    # ladder's ends are what a reader navigates by
    labelled = {rungs[0], rungs[-1]} | {r for r in rungs if _is_decade(r)}
    bottom.xaxis.set_major_formatter(
        FuncFormatter(lambda value, _: f"{int(value):,}" if value in labelled else "")
    )
    bottom.xaxis.set_minor_formatter(NullFormatter())

    figure.suptitle(
        "Batched lookups against a scalar loop, by batch size",
        fontsize=13,
        fontweight="bold",
    )
    top.set_title(_subtitle(run), fontsize=8, color="0.35", loc="left")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    # metadata={"Date": None}: otherwise every render stamps the current time into the
    # RDF block and the committed file changes when nothing measured did
    figure.savefig(output_path, format="svg", metadata={"Date": None})
    plt.close(figure)

    # the repository's own normalisation for a generated file: no trailing whitespace,
    # exactly one final newline (contributing/development/generated-file-regeneration-rules.md)
    markup = output_path.read_text(encoding="utf-8")
    markup = (
        "\n".join(line.rstrip() for line in markup.splitlines()).rstrip("\n") + "\n"
    )
    output_path.write_text(markup, encoding="utf-8")
    return markup


def _is_decade(value: int) -> bool:
    while value % 10 == 0 and value > 1:
        value //= 10
    return value == 1
