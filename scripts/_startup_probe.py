#!/usr/bin/env python3

"""Measure what one environment costs before it can answer, in its own process.

Run as a subprocess by :mod:`scripts.measure_acceleration_paths`, once per
repetition, and imported by nothing else. It prints a single JSON object to
stdout and nothing else.

Why this is not part of the paired comparison
---------------------------------------------

The comparisons on the acceleration-path page are two candidates inside one
process, which is what makes them paired. Import cost cannot be measured that
way at all: a process imports ``timezonefinder`` once, the backend is bound at
that import (``timezonefinder/utils.py``), and Numba's own import is already
paid for by the time either candidate runs. What installing Numba costs
*before any query* is therefore a property of the environment, and the only
place it is visible is a process that has just started.

Why a separate process rather than ``scripts/_memory_probe.py``
---------------------------------------------------------------

That probe measures one finder configuration's *data* footprint against a
post-import baseline, deliberately excluding the import so that the boundary
data is what is left. This one measures the opposite quantity - the import
itself, the construction and the first answer, as an absolute resident set -
because the reader deciding whether to install the Numba extra is choosing
between two whole processes, not between two accessors.

Where the JIT compilation lands
-------------------------------

Not in the first query: ``timezonefinder/utils_numba.py`` declares eager
signatures, so the kernels are compiled when that module is first imported -
which a default ``TimezoneFinder()`` triggers, not ``import timezonefinder``.
The construction step therefore carries the compilation, and the first query
carries none of it. Every step is timed separately rather than summed here so
that stays visible.

The compilation is also cached on disk (``cache=True``), beside the installed
package, so only the first process in a fresh environment pays it and later
ones pay a cache load. The parent's median over repetitions is what discards
that first process; see :func:`scripts.measure_acceleration_paths.measure_startup`.

The parent still hands in a point whose H3 cell holds more than one zone, so
the timed query is a real geometry lookup rather than one the shortcut index
answers outright.
"""

import argparse
import gc
import importlib.util
import json
import sys
import time

from scripts._memory_probe import read_rss


def measure(lng: float, lat: float) -> dict:
    """Import, construct and answer once, reporting bytes and seconds per step."""
    rss_at_start = read_rss()

    import_started = time.perf_counter()
    import timezonefinder  # noqa: PLC0415 - measured, so it cannot be top-level

    import_seconds = time.perf_counter() - import_started
    rss_after_import = read_rss()

    init_started = time.perf_counter()
    # The default access mode, which is what a plain `TimezoneFinder()` gives and
    # what the memory-constrained deployments this package is built for run.
    finder = timezonefinder.TimezoneFinder()
    init_seconds = time.perf_counter() - init_started
    rss_after_init = read_rss()

    query_started = time.perf_counter()
    finder.timezone_at(lng=lng, lat=lat)
    first_query_seconds = time.perf_counter() - query_started

    gc.collect()
    rss_ready = read_rss()

    result = {
        "import_rss": _delta(rss_after_import, rss_at_start),
        "init_rss": _delta(rss_after_init, rss_after_import),
        "first_query_rss": _delta(rss_ready, rss_after_init),
        "ready_rss": rss_ready,
        "import_seconds": import_seconds,
        "init_seconds": init_seconds,
        "first_query_seconds": first_query_seconds,
        # Which environment this is, and `find_spec` rather than an import on purpose:
        # importing `utils_numba` to ask would pull Numba into the very process whose
        # resident set is the measurement, adding ~100 MiB to the number. That is also
        # what makes this the right question here - the page's columns are "does this
        # environment have Numba", not "did anything compile". A Numba that is found
        # but cannot import would mislabel the column; the parent cross-checks the
        # label against the run's own path for exactly that reason.
        "numba_installed": importlib.util.find_spec("numba") is not None,
        # and what the dispatch did with it: false wherever the C extension won, which
        # since the import became conditional is also "nothing here is JIT-compiled"
        "using_numba": timezonefinder.TimezoneFinder.using_numba(),
        "using_clang_pip": timezonefinder.TimezoneFinder.using_clang_pip(),
    }
    finder.cleanup()
    return result


def _delta(after: int | None, before: int | None) -> int | None:
    if after is None or before is None:
        return None
    return after - before


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lng", type=float, required=True)
    parser.add_argument("--lat", type=float, required=True)
    args = parser.parse_args()

    json.dump(measure(args.lng, args.lat), sys.stdout)


if __name__ == "__main__":
    main()
