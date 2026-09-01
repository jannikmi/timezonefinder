#!/usr/bin/env python3

"""Measure one finder configuration's memory footprint, in its own process.

Run as a subprocess by :mod:`scripts.measure_memory`, once per configuration
per repetition, and never imported by anything else. It prints a single JSON
object of byte counts to stdout and nothing else.

Why a separate process
----------------------

``import timezonefinder`` pulls in numpy and h3 for ~100 MB of resident memory
before any timezone data is touched at all, which dwarfs everything this is
trying to measure. Only a *delta* against a post-import baseline says anything
about the library's own data, and taking that delta requires a process whose
baseline was not already polluted by a previously constructed finder - one
mode's page cache and freed-but-unreturned arenas would otherwise leak into
the next mode's numbers.

Why this module is deliberately tiny
------------------------------------

It must not import ``tests.auxiliaries``: that module builds a module-level
``PolygonArray(..., in_memory=True)`` at import time (``tests/auxiliaries.py``),
i.e. 64 MB of boundary coordinates, which would land in the baseline of every
configuration and make the file-based mode look identical to the in-memory
one. The query points are therefore handed in as an already-resolved ``.npy``
path by the parent, which owns the fixture constants.
"""

import argparse
import gc
import json
import resource
import sys
import tracemalloc
from pathlib import Path

# The Linux-only file that reports *current* resident set size. `resource`'s
# `ru_maxrss` is a high-water mark that never comes back down, so it cannot
# show a footprint shrinking - and the whole point of the file-based mode is
# that its resident set stays small. CI is Linux, so the tracked numbers always
# come from here; the fallback below only serves local runs on macOS/BSD.
PROC_STATUS_PATH = Path("/proc/self/status")
PROC_RSS_FIELD = "VmRSS:"


def read_rss() -> int | None:
    """Current resident set size in bytes, or ``None`` if unobtainable.

    Callers must tolerate ``None``: neither source exists on Windows, and the
    report renders an unavailable RSS as such rather than as a zero.
    """
    try:
        for line in PROC_STATUS_PATH.read_text().splitlines():
            if line.startswith(PROC_RSS_FIELD):
                # "VmRSS:\t   123456 kB"
                return int(line.split()[1]) * 1024
    except OSError:
        pass
    try:
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except (AttributeError, OSError):
        return None
    # ru_maxrss is bytes on macOS and kibibytes on Linux/BSD. Only the
    # non-Linux branch reaches here, and of those only macOS is realistically
    # in use, so treat a Linux-shaped value as kibibytes and everything else
    # as bytes.
    return peak if sys.platform == "darwin" else peak * 1024


def measure(
    finder_cls_name: str, in_memory: bool, points_path: Path, workload_size: int
) -> dict:
    """Construct one finder, exercise it, and report the byte deltas.

    Three checkpoints, in order: the cost of importing the package, the cost
    of construction, and the cost of a steady-state workload. The last one is
    not redundant - with ``in_memory=False`` the coordinate data is memory
    mapped, so it is not resident until a lookup actually faults its pages in.
    A construction-only measurement would report that mode as almost free.
    """
    import_rss_before = read_rss()
    import timezonefinder  # noqa: PLC0415 - measured, so it cannot be top-level

    import_rss_after = read_rss()

    import numpy as np  # noqa: PLC0415 - already paid for by timezonefinder

    # Loaded before the baseline so the points themselves are excluded from
    # every delta below.
    points = np.load(points_path)
    if len(points) < workload_size:
        raise ValueError(
            f"point fixture {points_path} has only {len(points)} points, but the "
            f"memory workload needs {workload_size}. Regenerate the fixtures with "
            "a larger count via `make benchmark-fixtures`."
        )
    points = points[:workload_size]
    finder_cls = getattr(timezonefinder, finder_cls_name)

    gc.collect()
    baseline_rss = read_rss()
    tracemalloc.start()

    # ``TimezoneFinderL`` takes no ``in_memory``: it loads no polygon data, so there
    # is no access mode to select. Its one config passes False, which is simply the
    # absence of the argument there.
    finder = finder_cls(in_memory=in_memory) if in_memory else finder_cls()

    gc.collect()
    init_heap = tracemalloc.get_traced_memory()[0]
    init_rss = read_rss()

    for lng, lat in points:
        finder.timezone_at(lng=float(lng), lat=float(lat))

    gc.collect()
    steady_heap = tracemalloc.get_traced_memory()[0]
    steady_rss = read_rss()
    tracemalloc.stop()

    # keep the instance alive until every measurement is taken
    del finder

    return {
        "import_rss": _delta(import_rss_after, import_rss_before),
        "init_heap": init_heap,
        "init_rss": _delta(init_rss, baseline_rss),
        "steady_heap": steady_heap,
        "steady_rss": _delta(steady_rss, baseline_rss),
        "workload_size": len(points),
    }


def _delta(after: int | None, before: int | None) -> int | None:
    if after is None or before is None:
        return None
    return after - before


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--finder-class", required=True)
    parser.add_argument("--in-memory", action="store_true")
    parser.add_argument("--points", type=Path, required=True)
    parser.add_argument("--workload-size", type=int, required=True)
    args = parser.parse_args()

    result = measure(args.finder_class, args.in_memory, args.points, args.workload_size)
    json.dump(result, sys.stdout)


if __name__ == "__main__":
    main()
