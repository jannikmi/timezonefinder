#!/usr/bin/env python3
"""Measure the headline improvements of this package over its predecessor ``pytzwhere``.

``docs/alternatives.rst`` tells the origin story - ``pytzwhere`` parsed a 76 MB CSV into memory on
every start and used up to 450 MB of RAM - but nothing in the repository re-measures it. This
prototype puts both packages side by side on one set of points and reports the numbers a reader
would quote:

* startup time: import plus constructing the finder, in a fresh process
* memory: peak resident set size of that process, and how much of it the package added
* query latency: median, p99 and throughput, on a uniform global sample and on its on-land subset
* batch throughput: the whole sample answered by ``timezone_names_at()`` in batches of several
  sizes, against a plain loop of single-point calls - ``pytzwhere`` has no batch API, so a loop
  is all a caller of it can write
* coverage: share of points that get an answer at all (``pytzwhere`` has no ocean zones)
* agreement on land where both answer, with the caveat that the datasets are a decade apart
* installed data size on disk
* whether the predecessor still runs on the current Python / NumPy stack

Each package runs in its own subprocess, so neither one's imports or memory leak into the other's
numbers. ``pytzwhere`` is unmaintained and breaks on NumPy >= 1.24 (ragged ``np.array``), so it is
measured in an isolated ``uv`` environment pinned to Python 3.10, ``numpy<1.24`` and ``shapely<2``;
the current-stack attempt is recorded as a result rather than hidden. This package runs in the
interpreter executing this script, once per point-in-polygon path: ``clang`` (the C extension,
which is what a plain ``pip install`` gets and which wins wherever it loaded), ``numba`` (the
fallback where the extension is missing and the ``numba`` extra is installed) and ``python`` (the
fallback where neither is). A path is forced by hiding modules from the import system, so an
import a real install would not make leaves the numbers too. All paths must give identical
answers, and every batch must give the scalar method's answers; the report counts any that do not.

Run with::

    uv run --group numba python prototypes/pytzwhere_headline_comparison.py   # 5,000 points
    uv run --group numba python prototypes/pytzwhere_headline_comparison.py -n 20000 --json out.json

Without ``--group numba`` the numba path is skipped and reported as such. Requires ``uv`` on PATH
for the ``pytzwhere`` environment (downloaded on first run, then cached). Latency is per-call
``perf_counter_ns`` around the public single-point API, after one warm-up query; the cold first
query is reported separately because it includes lazy loading. Throughput times the whole sample
per round with no per-call timer and reports the median of ``--rounds``; the batch sizes default
to 100, 1,000 and 10,000, the last inside the plateau ``docs/benchmark_results_batch_break_even.rst``
measures, and a size above the land subset runs as one call over all of it.

FINDINGS (2026-10-21, Linux x86_64, 4-vCPU Intel Xeon @ 2.10GHz container, 20,000 points, seed
42; timezonefinder-data 4.2026.5 on Python 3.13, tzwhere 3.0.3 on Python 3.10 / NumPy 1.23).
Three consecutive runs; the table is the third. A shared container is noisy: the medians and
startup agreed within ~15 % across runs, the throughput rows within ~25 %, and the p99s of
``tzwhere`` moved 2x (570-900 us global), so quote those as magnitudes. All three paths gave
identical answers, and every batch the scalar method's.

    metric                         unit     tzwhere       tzf numba       tzf clang      tzf python
    startup (import + init)           s        3.44     0.45 (7.7x)    0.17 (20.6x)    0.16 (20.9x)
    first (cold) query               ms       11.41   0.07 (173.8x)   0.02 (549.9x)   0.02 (481.3x)
    peak RSS of the process         MiB         480      180 (2.7x)       63 (7.6x)       61 (7.8x)
    RSS added by import + init      MiB         439      139 (3.1x)      23 (18.9x)      19 (22.8x)
    installed package/data size     MiB        22.9     32.3 (0.7x)     32.3 (0.7x)     32.3 (0.7x)
    median latency (global)          us        13.7     0.9 (14.9x)     1.4 (10.1x)     1.1 (12.9x)
    p99 latency (global)             us       899.9     9.6 (94.2x)    14.4 (62.5x)   1066.2 (0.8x)
    median latency (land)            us        20.4     1.0 (20.8x)     1.5 (13.7x)     1.2 (16.5x)
    p99 latency (land)               us      2668.8    12.1 (220.8x)  18.7 (142.7x)   1798.5 (1.5x)
    answered (global)                 %       28.9%          100.0%          100.0%          100.0%
    answered (land)                   %       84.4%          100.0%          100.0%          100.0%
    queries that raised                          48               0               0               0

    throughput, per point          unit     tzwhere       tzf numba       tzf clang      tzf python
    loop (global)                    us       16.49     1.27 (13.0x)    1.27 (12.9x)   40.07 (0.4x)
    batch of 100 (global)            us       16.49     0.73 (22.6x)    0.80 (20.7x)   39.70 (0.4x)
    batch of 1,000 (global)          us       16.49     0.30 (54.5x)    0.31 (53.3x)   36.65 (0.4x)
    batch of 10,000 (global)         us       16.49     0.23 (73.2x)    0.26 (63.1x)   40.62 (0.4x)
    loop (land)                      us       25.77     1.47 (17.5x)    1.52 (16.9x)   96.99 (0.3x)
    batch of 100 (land)              us       25.77     1.03 (24.9x)    0.92 (27.9x)   96.06 (0.3x)
    batch of 1,000 (land)            us       25.77     0.54 (47.7x)    0.48 (54.2x)   91.05 (0.3x)
    batch of 6,742 (land)            us       25.77     0.49 (52.3x)    0.43 (59.5x)   99.20 (0.3x)

* Batching is where the gap is widest. ``tzwhere`` can only loop, at ~15-25 us a point; a batch of
  10,000 on the default install answers in ~0.2-0.3 us a point, 50-75x more throughput over the
  globe and 50-65x on land across the three runs, against 12-17x for a loop of scalar calls. A
  batch of 100 still gives 20-28x; most of the batch gain is in hand by 1,000 points.
* The pure-Python fallback is the exception, and throughput shows it more plainly than latency
  did: its median is ~1 us like the other paths, but its mean is ~35-45 us a point over the globe
  and ~80-100 us on land, 2-4x *less* throughput than ``tzwhere``, whose ray cast is shapely's C
  code. Batching does not help it, because the polygon tests that dominate it run per point. Its
  p99 was level with ``tzwhere``'s across runs (0.5-1.5x), so it loses the speed headlines and
  keeps memory, startup and coverage.
* numba carries no headline. It is only reached where the C extension is missing; there it
  matches the extension's speed but its import adds ~115 MiB over the default install's ~20 MiB,
  which is ~20x less than ``tzwhere``'s, and it starts 2-3x slower.
* The median single query is ~1 us on every path, 10-20x faster than ``tzwhere``: a unique-zone
  lookup reads no geometry, so the kernel does not show up in it. The C extension's p99 is ~10-20
  us, ~50-200x below ``tzwhere``'s.
* Coverage is the larger practical difference: tzwhere answers 29 % of the globe (no ocean zones),
  misses 16 % of land points, and raises ``KeyError`` for latitudes outside its shortcut table -
  48 of 20,000 points, all polar.
* The one metric that regressed is on-disk size: this package ships more geometry (holes, ocean
  zones, a current dataset) and it is 1.4x the predecessor's.
* The predecessor no longer imports on a current stack (NumPy >= 1.24 rejects its ragged arrays).
* 82 % same-zone agreement on land compares tz_world to a current release, so it measures a decade
  of border and zone-name changes as much as either implementation.
"""

import argparse
import json
import math
import os
import random
import resource
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

LEGACY_ENV = [
    "uv",
    "run",
    "--no-project",
    "--isolated",
    "--quiet",
    "--python",
    "3.10",
    "--with",
    "tzwhere",
    "--with",
    "numpy<1.24",
    "--with",
    "shapely<2",
    "python",
]
# the stack a user installing ``tzwhere`` today would get
CURRENT_STACK_ENV = [
    "uv",
    "run",
    "--no-project",
    "--isolated",
    "--quiet",
    "--with",
    "tzwhere",
    "python",
]


# ---------------------------------------------------------------------------
# worker side: runs inside the measured process, stdlib + the measured package only


def _maxrss_bytes() -> int:
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss if sys.platform == "darwin" else rss * 1024  # Linux reports KiB


def _dir_size(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


# the three point-in-polygon paths ``timezonefinder/utils.py`` picks between at import time, and
# the modules to hide from the import system so that it picks the one asked for. The C extension
# wins wherever it loaded, so ``numba`` is reached only by hiding it; hiding ``numba`` is exactly
# an install without the ``numba`` extra, so its import cost leaves the other numbers too
TZF_PATHS = {
    "numba": ("timezonefinder.inside_polygon_ext",),
    "clang": ("numba",),
    "python": ("numba", "timezonefinder.inside_polygon_ext"),
}


def _setup_tzwhere():
    from tzwhere import tzwhere

    finder = tzwhere.tzwhere()
    data_dir = Path(tzwhere.__file__).parent
    return lambda lng, lat: finder.tzNameAt(lat, lng), None, data_dir


def _setup_timezonefinder():
    import timezonefinder_data
    from timezonefinder import TimezoneFinder

    finder = TimezoneFinder()
    return (
        lambda lng, lat: finder.timezone_at(lng=lng, lat=lat),
        lambda lngs, lats: finder.timezone_names_at(lngs=lngs, lats=lats),
        Path(timezonefinder_data.DATA_DIR),
    )


def _acceleration_path() -> str:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.assert_acceleration_path import active_acceleration_path

    return active_acceleration_path()


def _loop(query, points) -> list:
    """One answer per point, the way a caller without a batch API has to get them."""
    answers = []
    for lng, lat in points:
        try:
            answers.append(query(lng, lat))
        except Exception as exc:
            answers.append({"crash": type(exc).__name__})
    return answers


def _time_batches(query, batch_query, points, batch_sizes, rounds) -> dict:
    """Median per-point time of answering all ``points``, by a loop and in batches of each size.

    The loop has no per-call timer around it, unlike the latency measurement above, so it is the
    fair baseline for a batch: a timer read per call is ~5-10 % of a ~1 us query. A batch size
    larger than ``points`` is answered as one call over all of them, and reported at the size it
    actually ran at. The coordinate arrays are built before the clock starts, because a caller
    holding a dataframe column already has them; the answers are names, which is what ``tzwhere``
    returns. ``mismatches`` counts batch answers that differ from the scalar method's.
    """
    n = len(points)
    reference = _loop(query, points)
    loop_ns = []
    for _ in range(rounds):
        t0 = time.perf_counter_ns()
        _loop(query, points)
        loop_ns.append(time.perf_counter_ns() - t0)
    result = {"loop_ns_per_point": statistics.median(loop_ns) / n, "batches": {}}
    if batch_query is None or not n:
        return result
    import numpy as np

    for size in batch_sizes:
        size = min(size, n)
        chunks = [
            (
                np.array([p[0] for p in points[i : i + size]], dtype=np.float64),
                np.array([p[1] for p in points[i : i + size]], dtype=np.float64),
            )
            for i in range(0, n, size)
        ]
        answers = [a for lngs, lats in chunks for a in batch_query(lngs, lats)]
        batch_ns = []
        for _ in range(rounds):
            t0 = time.perf_counter_ns()
            for lngs, lats in chunks:
                batch_query(lngs, lats)
            batch_ns.append(time.perf_counter_ns() - t0)
        result["batches"][str(size)] = {
            "ns_per_point": statistics.median(batch_ns) / n,
            "mismatches": sum(a != b for a, b in zip(answers, reference)),
        }
    return result


def run_worker(
    variant: str,
    points_file: Path,
    out_file: Path,
    batch_sizes: list[int],
    rounds: int,
) -> None:
    """``variant`` is ``tzwhere`` or ``timezonefinder:<path>`` with a path from TZF_PATHS."""
    package, _, path = variant.partition(":")
    for module in TZF_PATHS.get(path, ()):
        sys.modules[module] = None  # makes ``import module`` raise ImportError
    sample = json.loads(points_file.read_text())
    points, land = sample["points"], sample["land"]
    rss_baseline = _maxrss_bytes()
    t0 = time.perf_counter()
    query, batch_query, data_dir = {
        "tzwhere": _setup_tzwhere,
        "timezonefinder": _setup_timezonefinder,
    }[package]()
    startup_s = time.perf_counter() - t0
    rss_after_init = _maxrss_bytes()
    if path and (active := _acceleration_path()) != path:
        sys.exit(f"asked for the {path} path, this environment gives {active}")

    t0 = time.perf_counter_ns()
    query(*points[0])
    first_query_ns = time.perf_counter_ns() - t0

    answers, times_ns = [], []
    for lng, lat in points:
        t0 = time.perf_counter_ns()
        try:
            answer = query(lng, lat)
        # tzwhere raises KeyError where its shortcut table has no row
        except Exception as exc:
            answer = {"crash": type(exc).__name__}
        times_ns.append(time.perf_counter_ns() - t0)
        answers.append(answer)

    land_points = [points[i] for i in land]
    batch = {
        scope: _time_batches(query, batch_query, sample_, batch_sizes, rounds)
        for scope, sample_ in (("global", points), ("land", land_points))
    }

    out_file.write_text(
        json.dumps(
            {
                "python": sys.version.split()[0],
                "startup_s": startup_s,
                "first_query_ns": first_query_ns,
                "rss_baseline": rss_baseline,
                "rss_after_init": rss_after_init,
                "rss_peak": _maxrss_bytes(),
                "data_size": _dir_size(data_dir),
                "answers": answers,
                "times_ns": times_ns,
                "batch": batch,
            }
        )
    )


# ---------------------------------------------------------------------------
# driver side


def uniform_sphere_points(n: int, seed: int) -> list[tuple[float, float]]:
    """Points uniform by area, not by degree - a uniform latitude oversamples the poles."""
    rng = random.Random(seed)
    return [
        (rng.uniform(-180, 180), math.degrees(math.asin(rng.uniform(-1, 1))))
        for _ in range(n)
    ]


def add_land_indices(points_file: Path) -> None:
    """Add the points this package puts in a real zone; its ocean zones are all ``Etc/GMT*``.

    Taken once up front so every worker times the same land subset; ``summarise`` re-derives the
    same set from the measured answers. It runs in its own process because Linux carries the peak
    RSS across ``fork`` and ``exec``: a driver that had loaded this package would raise every
    worker's ``rss_baseline`` above what the package adds, and the added-RSS row would read 0.
    """
    from timezonefinder import TimezoneFinder

    sample = json.loads(points_file.read_text())
    points = sample["points"]
    names = TimezoneFinder().timezone_names_at(
        lngs=[p[0] for p in points], lats=[p[1] for p in points]
    )
    sample["land"] = [i for i, a in enumerate(names) if a and not a.startswith("Etc/")]
    points_file.write_text(json.dumps(sample))


def spawn(prefix: list[str], variant: str, points_file: Path, tmp: Path, args) -> dict:
    out = tmp / f"{variant.replace(':', '-')}.json"
    out.unlink(missing_ok=True)
    cmd = [
        *prefix,
        __file__,
        "--worker",
        variant,
        str(points_file),
        str(out),
        "--batch-sizes",
        args.batch_sizes,
        "--rounds",
        str(args.rounds),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        lines = [ln for ln in proc.stderr.strip().splitlines() if ln.strip()]
        return {"error": lines[-1] if lines else f"exit code {proc.returncode}"}
    return json.loads(out.read_text())


def latency_stats(times_ns: list[int]) -> dict:
    if not times_ns:
        return {}
    us = sorted(t / 1e3 for t in times_ns)
    return {
        "median_us": statistics.median(us),
        "p99_us": us[min(len(us) - 1, int(0.99 * len(us)))],
        "mean_us": statistics.fmean(us),
        "queries_per_s": 1e6 / statistics.fmean(us),
    }


def summarise(results: dict[str, dict]) -> dict:
    """``results`` maps ``tzwhere`` and each measured ``timezonefinder:<path>`` to its run."""
    legacy = results["tzwhere"]
    tzf_names = [name for name in results if name != "tzwhere"]
    reference = results[tzf_names[0]]["answers"]
    n = len(reference)
    # on land = this package names a real zone; its ocean zones are all Etc/GMT*
    land = [i for i, a in enumerate(reference) if a and not a.startswith("Etc/")]
    both = [i for i in land if isinstance(legacy["answers"][i], str)]
    agree = sum(legacy["answers"][i] == reference[i] for i in both)
    answered = lambda a: isinstance(a, str)  # noqa: E731 - None is no zone, a dict is a crash
    summary = {
        "points": n,
        "land_points": len(land),
        "agreement": {"compared": len(both), "same_zone": agree},
        # the paths share one data set and one lookup, so any difference here is a kernel bug
        "path_disagreements": {
            name: sum(a != b for a, b in zip(results[name]["answers"], reference))
            for name in tzf_names[1:]
        },
        "variants": {},
    }
    for name, r in results.items():
        summary["variants"][name] = {
            "python": r["python"],
            "startup_s": r["startup_s"],
            "first_query_ms": r["first_query_ns"] / 1e6,
            "rss_peak_mib": r["rss_peak"] / 2**20,
            "rss_added_by_init_mib": (r["rss_after_init"] - r["rss_baseline"]) / 2**20,
            "data_size_mib": r["data_size"] / 2**20,
            "coverage_global": sum(map(answered, r["answers"])) / n,
            "coverage_land": sum(answered(r["answers"][i]) for i in land)
            / max(1, len(land)),
            "crashes": sum(isinstance(a, dict) for a in r["answers"]),
            "latency_global": latency_stats(r["times_ns"]),
            "latency_land": latency_stats([r["times_ns"][i] for i in land]),
            "batch": r["batch"],
        }
    return summary


# (label, unit, getter, format); lower is better for every timed and sized row
TIMED_ROWS = [
    ("startup (import + init)", "s", lambda v: v["startup_s"], "{:.2f}"),
    ("first (cold) query", "ms", lambda v: v["first_query_ms"], "{:.2f}"),
    ("peak RSS of the process", "MiB", lambda v: v["rss_peak_mib"], "{:.0f}"),
    (
        "RSS added by import + init",
        "MiB",
        lambda v: v["rss_added_by_init_mib"],
        "{:.0f}",
    ),
    ("installed package/data size", "MiB", lambda v: v["data_size_mib"], "{:.1f}"),
] + [
    (
        f"{stat} latency ({scope})",
        "us",
        lambda v, s=scope, k=key: v[f"latency_{s}"][k],
        "{:.1f}",
    )
    for scope in ("global", "land")
    for stat, key in (("median", "median_us"), ("p99", "p99_us"))
]
COUNT_ROWS = [
    ("answered (global)", lambda v: f"{v['coverage_global']:.1%}"),
    ("answered (land)", lambda v: f"{v['coverage_land']:.1%}"),
    ("queries that raised", lambda v: f"{v['crashes']:,}"),
]


def print_batch_report(s: dict) -> None:
    """Per-point time of answering the whole sample, by a loop and in batches.

    ``tzwhere`` has no batch API, so its column repeats its loop in every batch row: a caller
    with many points has nothing faster to reach for.
    """
    variants = s["variants"]
    old = variants["tzwhere"]
    names = list(variants)[1:]
    print(
        "\nthroughput over the whole sample, median of rounds; per-point time"
        " (improvement over tzwhere's loop)\n"
    )
    headers = ["tzwhere"] + [f"tzf {name.partition(':')[2]}" for name in names]
    print(f"{'metric':<30}{'unit':>5}" + "".join(f"{h:>18}" for h in headers))
    mismatches = 0
    for scope in ("global", "land"):
        base_us = old["batch"][scope]["loop_ns_per_point"] / 1e3
        sizes = list(variants[names[0]]["batch"][scope]["batches"])
        rows = [("loop", lambda b: b["loop_ns_per_point"])] + [
            (
                f"batch of {int(size):,}",
                lambda b, k=size: b["batches"][k]["ns_per_point"],
            )
            for size in sizes
        ]
        for label, get in rows:
            cells = [f"{base_us:.2f}"]
            for name in names:
                us = get(variants[name]["batch"][scope]) / 1e3
                cells.append(f"{us:.2f} ({base_us / us:,.1f}x)")
            print(
                f"{f'{label} ({scope})':<30}{'us':>5}"
                + "".join(f"{c:>18}" for c in cells)
            )
        mismatches += sum(
            b["mismatches"]
            for name in names
            for b in variants[name]["batch"][scope]["batches"].values()
        )
    print(f"batch answers differing from the scalar method's: {mismatches:,}")


def print_report(s: dict, current_stack: dict | None) -> None:
    variants = s["variants"]
    old = variants["tzwhere"]
    names = list(variants)
    headers = ["tzwhere"] + [f"tzf {name.partition(':')[2]}" for name in names[1:]]
    print(
        f"\n{s['points']:,} points uniform on the sphere, {s['land_points']:,} of them on land;"
        " tzf columns show value (improvement over tzwhere)\n"
    )
    print(f"{'metric':<30}{'unit':>5}" + "".join(f"{h:>18}" for h in headers))
    for label, unit, get, fmt in TIMED_ROWS:
        cells = [fmt.format(get(old))]
        for name in names[1:]:
            new = get(variants[name])
            gain = f"{get(old) / new:,.1f}x" if new else "-"
            cells.append(f"{fmt.format(new)} ({gain})")
        print(f"{label:<30}{unit:>5}" + "".join(f"{c:>18}" for c in cells))
    for label, get in COUNT_ROWS:
        print(f"{label:<35}" + "".join(f"{get(variants[n]):>18}" for n in names))
    a = s["agreement"]
    print(
        f"\nsame zone on land where both answer: {a['same_zone']:,} / {a['compared']:,}"
        f" ({a['same_zone'] / max(1, a['compared']):.1%}) - tz_world vs a current"
        " timezone-boundary-builder release, so differences include real border and zone changes"
    )
    for name, count in s["path_disagreements"].items():
        print(f"answers differing from {names[1]}: {name} {count:,}")
    print(
        f"interpreters: tzwhere on Python {old['python']},"
        f" timezonefinder on Python {variants[names[1]]['python']}"
    )
    for name, reason in s["skipped"].items():
        print(f"skipped {name}: {reason}")
    if current_stack is not None:
        verdict = current_stack.get("error", "runs")
        print(f"tzwhere on the current Python/NumPy stack: {verdict}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("-n", "--points", type=int, default=5_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--json", type=Path, help="also write the summary here")
    parser.add_argument(
        "--paths",
        default=",".join(TZF_PATHS),
        help="timezonefinder acceleration paths to measure, comma-separated"
        f" (default: all of {', '.join(TZF_PATHS)}; unavailable ones are skipped)",
    )
    parser.add_argument(
        "--batch-sizes",
        default="100,1000,10000",
        help="timezone_names_at() batch sizes, comma-separated (default: %(default)s)",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=5,
        help="rounds of the throughput measurement; the median is reported (default: %(default)s)",
    )
    parser.add_argument(
        "--skip-current-stack",
        action="store_true",
        help="skip the unpinned tzwhere attempt",
    )
    parser.add_argument("--land-indices", type=Path, help=argparse.SUPPRESS)
    parser.add_argument(
        "--worker",
        nargs=3,
        metavar=("VARIANT", "POINTS", "OUT"),
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args()
    if args.land_indices:
        add_land_indices(args.land_indices)
        return
    if args.worker:
        run_worker(
            args.worker[0],
            Path(args.worker[1]),
            Path(args.worker[2]),
            [int(b) for b in args.batch_sizes.split(",") if b],
            args.rounds,
        )
        return
    if shutil.which("uv") is None:
        sys.exit("uv is required to build the isolated pytzwhere environment")
    paths = [p for p in args.paths.split(",") if p]
    if unknown := set(paths) - set(TZF_PATHS):
        sys.exit(f"unknown paths {sorted(unknown)}; choose from {list(TZF_PATHS)}")

    results, skipped = {}, {}
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        points_file = tmp / "points.json"
        points_file.write_text(
            json.dumps({"points": uniform_sphere_points(args.points, args.seed)})
        )
        subprocess.run(
            [sys.executable, __file__, "--land-indices", str(points_file)], check=True
        )
        # build (or reuse) the cached legacy env outside the measured run
        subprocess.run([*LEGACY_ENV, "-c", "import tzwhere"], check=True)
        current_stack = None
        if not args.skip_current_stack:
            current_stack = spawn(CURRENT_STACK_ENV, "tzwhere", points_file, tmp, args)
            for key in ("answers", "times_ns", "batch"):
                current_stack.pop(key, None)
        results["tzwhere"] = spawn(LEGACY_ENV, "tzwhere", points_file, tmp, args)
        if "error" in results["tzwhere"]:
            sys.exit(f"tzwhere worker failed: {results['tzwhere']['error']}")
        for path in paths:
            variant = f"timezonefinder:{path}"
            result = spawn([sys.executable], variant, points_file, tmp, args)
            if "error" in result:
                skipped[variant] = result["error"]
            else:
                results[variant] = result
    if len(results) == 1:
        sys.exit(f"no timezonefinder path could be measured: {skipped}")

    summary = summarise(results)
    summary["skipped"] = skipped
    summary["tzwhere_current_stack"] = current_stack and current_stack.get(
        "error", "runs"
    )
    summary["platform"] = f"{sys.platform} {os.uname().machine}"
    print_report(summary, current_stack)
    print_batch_report(summary)
    if args.json:
        args.json.write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
