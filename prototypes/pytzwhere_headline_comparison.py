#!/usr/bin/env python3
"""Measure the headline improvements of this package over its predecessor ``pytzwhere``.

``docs/alternatives.rst`` tells the origin story - ``pytzwhere`` parsed a 76 MB CSV into memory on
every start and used up to 450 MB of RAM - but nothing in the repository re-measures it. This
prototype puts both packages side by side on one set of points and reports the numbers a reader
would quote:

* startup time: import plus constructing the finder, in a fresh process
* memory: peak resident set size of that process, and how much of it the package added
* query latency: median, p99 and throughput, on a uniform global sample and on its on-land subset
* coverage: share of points that get an answer at all (``pytzwhere`` has no ocean zones)
* agreement on land where both answer, with the caveat that the datasets are a decade apart
* installed data size on disk
* whether the predecessor still runs on the current Python / NumPy stack

Each package runs in its own subprocess, so neither one's imports or memory leak into the other's
numbers. ``pytzwhere`` is unmaintained and breaks on NumPy >= 1.24 (ragged ``np.array``), so it is
measured in an isolated ``uv`` environment pinned to Python 3.10, ``numpy<1.24`` and ``shapely<2``;
the current-stack attempt is recorded as a result rather than hidden. This package runs in the
interpreter executing this script, once per point-in-polygon path: ``numba`` when it is installed,
``clang`` (the C extension, which is what a plain ``pip install`` gets) and ``python`` (the fallback
where no extension is built). A path is forced by hiding ``numba`` and the extension from the
import system, so its import cost leaves the numbers as it would from a real install. All paths
must give identical answers, and the report counts any that do not.

Run with::

    uv run python prototypes/pytzwhere_headline_comparison.py            # 5,000 points
    uv run python prototypes/pytzwhere_headline_comparison.py -n 20000 --json out.json

Requires ``uv`` on PATH for the ``pytzwhere`` environment (downloaded on first run, then cached).
Timings are per-call ``perf_counter_ns`` around the public single-point API, after one warm-up
query; the cold first query is reported separately because it includes lazy loading (and JIT
compilation when numba is installed).

FINDINGS (2026-09-22, macOS arm64, 20,000 points, seed 42; timezonefinder-data 3.2026.4 on Python
3.14, tzwhere 3.0.3 on Python 3.10 / NumPy 1.23). Three consecutive runs; the table is the third,
and every row but the p99s agreed within ~10 % across them. The p99 rows of the ``python`` and
``clang`` paths were stable too, but the ``numba`` path put 111 us and 165 us p99s into the first
run and 6-10 us into the other two (earlier single runs gave 10.5 us and 154.7 us on land), so its
tail wants paired rounds before it is quoted. All three paths gave identical answers.

    metric                         unit     tzwhere       tzf numba       tzf clang      tzf python
    startup (import + init)           s        1.50     0.25 (6.1x)    0.07 (21.8x)    0.06 (23.6x)
    first (cold) query               ms        5.42   0.02 (222.7x)   0.02 (239.5x)   0.02 (267.6x)
    peak RSS of the process         MiB         694      137 (5.1x)      62 (11.2x)      60 (11.5x)
    RSS added by import + init      MiB         597       92 (6.5x)      18 (32.6x)      17 (35.2x)
    installed package/data size     MiB        22.9     32.1 (0.7x)     32.1 (0.7x)     32.1 (0.7x)
    median latency (global)          us         7.5      1.0 (7.8x)      0.9 (8.2x)      1.0 (7.5x)
    p99 latency (global)             us       272.8      7.9 (34.5x)     5.2 (52.4x)  1033.0 (0.3x)
    median latency (land)            us        11.0     1.0 (11.5x)     0.9 (12.0x)     1.0 (10.6x)
    p99 latency (land)               us       793.8      9.7 (81.8x)     6.7 (119.1x) 1474.3 (0.5x)
    answered (global)                 %       28.9%          100.0%          100.0%          100.0%
    answered (land)                   %       84.2%          100.0%          100.0%          100.0%
    queries that raised                          48               0               0               0

* numba is not needed for any headline, and costs memory. Its import is ~75 MiB of the ~90 MiB
  the numba path adds; a default install (the C extension) adds under 20 MiB, ~30x less than
  tzwhere, and starts ~20x faster, because it imports neither numba nor tzwhere's full geometry.
* The median query is ~1 us on every path, 8-12x faster than tzwhere: a unique-zone lookup reads
  no geometry, so the kernel does not show up in it.
* The tail is where the kernel shows. The C extension's p99 is 5-7 us; the pure-Python fallback's
  is 1-1.5 ms, *slower than tzwhere's* (whose ray cast is shapely's C code), so a platform without
  a built extension loses the latency headline and keeps only memory, startup and coverage.
* Coverage is the larger practical difference: tzwhere answers 29 % of the globe (no ocean zones),
  misses 16 % of land points, and raises ``KeyError`` for latitudes outside its shortcut table -
  48 of 20,000 points, all polar.
* The one metric that regressed is on-disk size: this package ships more geometry (holes, ocean
  zones, a current dataset) and it is still 1.4x the predecessor's.
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
# the modules to hide from the import system so that it picks the one asked for; hiding ``numba``
# is exactly an install without the ``numba`` extra, so its import cost leaves the numbers too
TZF_PATHS = {
    "numba": (),
    "clang": ("numba",),
    "python": ("numba", "timezonefinder.inside_polygon_ext"),
}


def _setup_tzwhere():
    from tzwhere import tzwhere

    finder = tzwhere.tzwhere()
    data_dir = Path(tzwhere.__file__).parent
    return lambda lng, lat: finder.tzNameAt(lat, lng), data_dir


def _setup_timezonefinder():
    import timezonefinder_data
    from timezonefinder import TimezoneFinder

    finder = TimezoneFinder()
    return lambda lng, lat: finder.timezone_at(lng=lng, lat=lat), Path(
        timezonefinder_data.DATA_DIR
    )


def _acceleration_path() -> str:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.assert_acceleration_path import active_acceleration_path

    return active_acceleration_path()


def run_worker(variant: str, points_file: Path, out_file: Path) -> None:
    """``variant`` is ``tzwhere`` or ``timezonefinder:<path>`` with a path from TZF_PATHS."""
    package, _, path = variant.partition(":")
    for module in TZF_PATHS.get(path, ()):
        sys.modules[module] = None  # makes ``import module`` raise ImportError
    points = json.loads(points_file.read_text())
    rss_baseline = _maxrss_bytes()
    t0 = time.perf_counter()
    query, data_dir = {
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


def spawn(prefix: list[str], variant: str, points_file: Path, tmp: Path) -> dict:
    out = tmp / f"{variant.replace(':', '-')}.json"
    out.unlink(missing_ok=True)
    cmd = [*prefix, __file__, "--worker", variant, str(points_file), str(out)]
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
        "--skip-current-stack",
        action="store_true",
        help="skip the unpinned tzwhere attempt",
    )
    parser.add_argument(
        "--worker",
        nargs=3,
        metavar=("VARIANT", "POINTS", "OUT"),
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args()
    if args.worker:
        run_worker(args.worker[0], Path(args.worker[1]), Path(args.worker[2]))
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
            json.dumps(uniform_sphere_points(args.points, args.seed))
        )
        # build (or reuse) the cached legacy env outside the measured run
        subprocess.run([*LEGACY_ENV, "-c", "import tzwhere"], check=True)
        current_stack = None
        if not args.skip_current_stack:
            current_stack = spawn(CURRENT_STACK_ENV, "tzwhere", points_file, tmp)
            current_stack.pop("answers", None), current_stack.pop("times_ns", None)
        results["tzwhere"] = spawn(LEGACY_ENV, "tzwhere", points_file, tmp)
        if "error" in results["tzwhere"]:
            sys.exit(f"tzwhere worker failed: {results['tzwhere']['error']}")
        for path in paths:
            variant = f"timezonefinder:{path}"
            result = spawn([sys.executable], variant, points_file, tmp)
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
    if args.json:
        args.json.write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
