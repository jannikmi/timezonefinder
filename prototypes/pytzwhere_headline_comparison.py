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
interpreter executing this script.

Run with::

    uv run python prototypes/pytzwhere_headline_comparison.py            # 5,000 points
    uv run python prototypes/pytzwhere_headline_comparison.py -n 20000 --json out.json

Requires ``uv`` on PATH for the ``pytzwhere`` environment (downloaded on first run, then cached).
Timings are per-call ``perf_counter_ns`` around the public single-point API, after one warm-up
query; the cold first query is reported separately because it includes lazy loading (and JIT
compilation when numba is installed).

FINDINGS (2026-09-21, macOS arm64, 20,000 points, seed 42; timezonefinder-data 3.2026.4 on Python
3.14 via the numba path, tzwhere 3.0.3 on Python 3.10 / NumPy 1.23). One run, so read ratios as
orders of magnitude, and the p99 rows least of all: the same run on the 3.2026.3 data put this
package's land p99 at 154.7 us and a 5,000-point run at 10.5 us, so the tail needs repeated, paired
rounds before it is quoted. Every other row moved by under 20 % between the two data releases.

    metric                         unit     tzwhere  timezonefinder  improvement
    startup (import + init)           s        1.71            0.23         7.4x
    first (cold) query               ms        8.24            0.02       373.3x
    peak RSS of the process         MiB         693             135         5.1x
    RSS added by import + init      MiB         596              91         6.6x
    installed package/data size     MiB        22.9            32.1         0.7x
    median latency (global)          us         7.2             0.9         8.2x
    p99 latency (global)             us       262.8             6.1        43.2x
    median latency (land)            us        10.8             0.9        11.8x
    p99 latency (land)               us       784.4             8.1        97.0x
    answered (global)                 %       28.9%          100.0%
    answered (land)                   %       84.2%          100.0%
    queries that raised                          48               0

* Memory is the headline the docs already claim, and it holds: ~600 MiB added versus ~90 MiB, most
  of the latter NumPy/numba imports rather than data (the polygon coordinates stay memory-mapped).
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


def _acceleration_path(package: str) -> str:
    if package != "timezonefinder":
        return "-"
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.assert_acceleration_path import active_acceleration_path

    return active_acceleration_path()


def run_worker(package: str, points_file: Path, out_file: Path) -> None:
    points = json.loads(points_file.read_text())
    rss_baseline = _maxrss_bytes()
    t0 = time.perf_counter()
    query, data_dir = {
        "tzwhere": _setup_tzwhere,
        "timezonefinder": _setup_timezonefinder,
    }[package]()
    startup_s = time.perf_counter() - t0
    rss_after_init = _maxrss_bytes()

    t0 = time.perf_counter_ns()
    query(*points[0])
    first_query_ns = time.perf_counter_ns() - t0

    answers, times_ns = [], []
    for lng, lat in points:
        t0 = time.perf_counter_ns()
        try:
            answer = query(lng, lat)
        except (
            Exception
        ) as exc:  # tzwhere raises KeyError where its shortcut table has no row
            answer = {"crash": type(exc).__name__}
        times_ns.append(time.perf_counter_ns() - t0)
        answers.append(answer)

    out_file.write_text(
        json.dumps(
            {
                "python": sys.version.split()[0],
                "acceleration": _acceleration_path(package),
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


def spawn(prefix: list[str], package: str, points_file: Path, tmp: Path) -> dict:
    out = tmp / f"{package}.json"
    out.unlink(missing_ok=True)
    cmd = [*prefix, __file__, "--worker", package, str(points_file), str(out)]
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


def summarise(legacy: dict, tzf: dict) -> dict:
    n = len(tzf["answers"])
    # on land = this package names a real zone; its ocean zones are all Etc/GMT*
    land = [i for i, a in enumerate(tzf["answers"]) if a and not a.startswith("Etc/")]
    both = [i for i in land if isinstance(legacy["answers"][i], str)]
    agree = sum(legacy["answers"][i] == tzf["answers"][i] for i in both)
    answered = lambda a: isinstance(a, str)  # noqa: E731 - None is no zone, a dict is a crash
    summary = {
        "points": n,
        "land_points": len(land),
        "agreement": {"compared": len(both), "same_zone": agree},
    }
    for name, r in (("tzwhere", legacy), ("timezonefinder", tzf)):
        summary[name] = {
            "python": r["python"],
            "acceleration": r["acceleration"],
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


def ratio(old: float, new: float) -> str:
    return f"{old / new:,.1f}x" if new else "-"


def print_report(s: dict, current_stack: dict | None) -> None:
    old, new = s["tzwhere"], s["timezonefinder"]
    rows = [
        ("startup (import + init)", "s", old["startup_s"], new["startup_s"], "{:.2f}"),
        (
            "first (cold) query",
            "ms",
            old["first_query_ms"],
            new["first_query_ms"],
            "{:.2f}",
        ),
        (
            "peak RSS of the process",
            "MiB",
            old["rss_peak_mib"],
            new["rss_peak_mib"],
            "{:.0f}",
        ),
        (
            "RSS added by import + init",
            "MiB",
            old["rss_added_by_init_mib"],
            new["rss_added_by_init_mib"],
            "{:.0f}",
        ),
        (
            "installed package/data size",
            "MiB",
            old["data_size_mib"],
            new["data_size_mib"],
            "{:.1f}",
        ),
    ]
    for scope in ("global", "land"):
        o, n = old[f"latency_{scope}"], new[f"latency_{scope}"]
        rows += [
            (
                f"median latency ({scope})",
                "us",
                o["median_us"],
                n["median_us"],
                "{:.1f}",
            ),
            (f"p99 latency ({scope})", "us", o["p99_us"], n["p99_us"], "{:.1f}"),
        ]
    print(
        f"\n{s['points']:,} points uniform on the sphere, {s['land_points']:,} of them on land\n"
    )
    print(
        f"{'metric':<30}{'unit':>5}{'tzwhere':>12}{'timezonefinder':>16}{'improvement':>13}"
    )
    for label, unit, o, n, fmt in rows:
        print(
            f"{label:<30}{unit:>5}{fmt.format(o):>12}{fmt.format(n):>16}{ratio(o, n):>13}"
        )
    for scope in ("global", "land"):
        o, n = old[f"coverage_{scope}"], new[f"coverage_{scope}"]
        print(f"{f'answered ({scope})':<30}{'%':>5}{o:>12.1%}{n:>16.1%}")
    print(
        f"{'queries that raised':<30}{'':>5}{old['crashes']:>12,}{new['crashes']:>16,}"
    )
    a = s["agreement"]
    print(
        f"\nsame zone on land where both answer: {a['same_zone']:,} / {a['compared']:,}"
        f" ({a['same_zone'] / max(1, a['compared']):.1%}) - tz_world vs a current"
        " timezone-boundary-builder release, so differences include real border and zone changes"
    )
    print(
        f"interpreters: tzwhere on Python {old['python']},"
        f" timezonefinder on Python {new['python']} ({new['acceleration']} acceleration path)"
    )
    if current_stack is not None:
        verdict = current_stack.get("error", "runs")
        print(f"tzwhere on the current Python/NumPy stack: {verdict}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("-n", "--points", type=int, default=5_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--json", type=Path, help="also write the summary here")
    parser.add_argument(
        "--skip-current-stack",
        action="store_true",
        help="skip the unpinned tzwhere attempt",
    )
    parser.add_argument(
        "--worker",
        nargs=3,
        metavar=("PACKAGE", "POINTS", "OUT"),
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args()
    if args.worker:
        run_worker(args.worker[0], Path(args.worker[1]), Path(args.worker[2]))
        return
    if shutil.which("uv") is None:
        sys.exit("uv is required to build the isolated pytzwhere environment")

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
        legacy = spawn(LEGACY_ENV, "tzwhere", points_file, tmp)
        tzf = spawn([sys.executable], "timezonefinder", points_file, tmp)
    for name, result in (("tzwhere", legacy), ("timezonefinder", tzf)):
        if "error" in result:
            sys.exit(f"{name} worker failed: {result['error']}")

    summary = summarise(legacy, tzf)
    summary["tzwhere_current_stack"] = current_stack and current_stack.get(
        "error", "runs"
    )
    summary["platform"] = f"{sys.platform} {os.uname().machine}"
    print_report(summary, current_stack)
    if args.json:
        args.json.write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
