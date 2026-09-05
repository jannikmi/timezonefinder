#!/usr/bin/env python3

"""Carry the stored timing trend history over to lookups/sec, in place.

Why this exists
---------------

The timing chart used to be written by
``benchmark-action/github-action-benchmark``'s ``pytest`` extractor, which
stores ``stats.ops`` as ``iter/sec`` under the raw pytest node id. It is now
written by :mod:`scripts.export_timing_chart_json`, in lookups/sec and under
the human-readable labels the docs use.

The chart joins a metric's history **by name**, so that switch would otherwise
orphan every point recorded so far: the old series would freeze at the last
``pytest``-shaped point and a new, empty one would start beside it. Nothing
about the measurements changed, though - every stored point already measured
one pass over the same fixed batch - so the old points can simply be restated
in the new unit and under the new name:

* ``value`` (batches/sec) x ``BATCH_SIZE`` = lookups/sec
* ``name``: the node id, humanized the same way the exporter humanizes it
* ``range``/``extra``: the pytest extractor's ``stddev: <seconds>`` and
  ``mean: <ms>\\nrounds: <n> on <cpu>`` strings, restated in the exporter's own
  form so a tooltip does not change shape halfway along the chart

The batch size is *not* read from any report here: it is passed in, because
this rewrites points whose own reports are long gone. ``BATCH_SIZE`` has been
2,500 since the commit that recorded the first trend point (it was raised from
1,000 in the same commit that added the workflow), so one constant covers the
whole stored history - and if it had ever changed mid-history, the history
would already have been invalid, since a round would not mean the same thing
across it.

Idempotent: an entry already carrying the new unit is left alone, so a partial
run can be repeated.

Usage - the file lives on the ``gh-pages`` branch, which CI owns and nothing
else may write casually. That branch is an orphan holding the published pages
and nothing else, so check it out *beside* this one rather than over it: this
module does not exist there::

    git fetch origin gh-pages
    git worktree add ../tzf-gh-pages gh-pages
    uv run python -m scripts.migrate_benchmark_chart_history \\
        ../tzf-gh-pages/dev/bench/data.js
    git -C ../tzf-gh-pages commit -am "restate the timing trend history in lookups/sec"
    git -C ../tzf-gh-pages push origin gh-pages
    git worktree remove ../tzf-gh-pages

Run it once, before the first push that stores a lookups/sec point; running it
afterwards is still safe, but until it has run the chart shows the new series
starting from empty.
"""

import argparse
import json
import re
from pathlib import Path
from typing import Any

from scripts.export_timing_chart_json import CHART_UNIT
from scripts.render_benchmark_reports import humanize_benchmark_name

#: what the file assigns to, ahead of the JSON payload this rewrites
ASSIGNMENT_PREFIX = "window.BENCHMARK_DATA = "

#: the suite whose points this restates - the timing one. Its name does not
#: change (the acceleration path and estimator it encodes did not), which is
#: what lets the migrated points and the new ones share a chart.
DEFAULT_SUITE = "timezone lookup (clang, min)"

#: the batch size every stored point was measured with - see the module
#: docstring for why this is a constant rather than a lookup
DEFAULT_BATCH_SIZE = 2_500

_STDDEV = re.compile(r"stddev:\s*(?P<seconds>[0-9.eE+-]+)")
_ROUNDS = re.compile(r"rounds:\s*(?P<rounds>\d+)(?:\s+on\s+(?P<machine>.+))?", re.S)


def load_data_js(text: str) -> dict[str, Any]:
    """Parse the ``window.BENCHMARK_DATA = {...}`` file the action writes."""
    start = text.index("{", text.index(ASSIGNMENT_PREFIX))
    return json.loads(text[start:].strip().rstrip(";"))


def dump_data_js(data: dict[str, Any]) -> str:
    """Render ``data`` byte-for-byte the way the action itself writes the file.

    ``JSON.stringify(data, null, 2)``: two spaces of indentation, no trailing
    newline, and literal UTF-8 rather than ``\\uXXXX`` escapes - hence
    ``ensure_ascii=False``, which Python does not default to. Without it every
    one of the 600-odd ``±`` characters in the stored file (and any non-ASCII
    in a commit message or author name) is re-encoded, so a migration that
    restates nine benchmarks would land as a whole-file diff that the next CI
    push silently reverts. The point of matching exactly is that the migrated
    file differs from the next action-written one *only* in the points it
    restates.
    """
    return f"{ASSIGNMENT_PREFIX}{json.dumps(data, indent=2, ensure_ascii=False)}"


def migrate_bench(
    bench: dict[str, Any], batch_size: int, estimator: str
) -> dict[str, Any]:
    """Restate one stored ``iter/sec`` point as a ``lookups/sec`` one."""
    if bench.get("unit") == CHART_UNIT:
        return bench
    batches_per_second = bench["value"]
    seconds = 1.0 / batches_per_second
    throughput = batches_per_second * batch_size

    migrated = {
        "name": humanize_benchmark_name(bench["name"].split("::")[-1]),
        "unit": CHART_UNIT,
        "value": throughput,
    }

    # the same first-order propagation the exporter applies, from the same
    # `stddev` in seconds the pytest extractor happened to store as prose
    stddev = _STDDEV.search(str(bench.get("range", "")))
    if stddev:
        migrated["range"] = f"± {throughput * float(stddev['seconds']) / seconds:.0f}"

    rounds = _ROUNDS.search(str(bench.get("extra", "")))
    if rounds:
        machine = (rounds["machine"] or "an unrecorded CPU").strip()
        migrated["extra"] = f"{estimator} of {rounds['rounds']} round(s) on {machine}"
    return migrated


def migrate(
    data: dict[str, Any], suite: str, batch_size: int, estimator: str
) -> tuple[dict[str, Any], int]:
    """Restate every point of ``suite``; returns the data and how many moved.

    :raises KeyError: if the suite is absent, which would otherwise report a
        clean no-op run on a typo'd name.
    """
    entries = data["entries"]
    if suite not in entries:
        raise KeyError(
            f"no suite named {suite!r} in this file; it holds {sorted(entries)}"
        )
    migrated_points = 0
    for point in entries[suite]:
        before = point["benches"]
        point["benches"] = [migrate_bench(b, batch_size, estimator) for b in before]
        migrated_points += point["benches"] != before
    return data, migrated_points


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Restate a stored github-action-benchmark timing history in "
            f"{CHART_UNIT} under human-readable names, so the switch to "
            "tool: customBiggerIsBetter continues the history instead of "
            "orphaning it."
        )
    )
    parser.add_argument(
        "data_js",
        type=Path,
        help="path to `dev/bench/data.js` in a gh-pages checkout (rewritten in place)",
    )
    parser.add_argument(
        "--suite",
        default=DEFAULT_SUITE,
        help=f"suite to restate (default: {DEFAULT_SUITE!r})",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=(
            "lookups per round in the stored measurements "
            f"(default: {DEFAULT_BATCH_SIZE})"
        ),
    )
    parser.add_argument(
        "--estimator",
        default="min",
        help="estimator the stored points track, named in the tooltip",
    )
    args = parser.parse_args()

    data, migrated = migrate(
        load_data_js(args.data_js.read_text(encoding="utf-8")),
        args.suite,
        args.batch_size,
        args.estimator,
    )
    args.data_js.write_text(dump_data_js(data), encoding="utf-8")
    total = len(data["entries"][args.suite])
    print(
        f"Restated {migrated} of {total} stored point(s) of {args.suite!r} in "
        f"{CHART_UNIT} ({total - migrated} already migrated or empty)"
    )


if __name__ == "__main__":
    main()
