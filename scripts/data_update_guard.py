"""What a data update changed, stated as answers rather than as bytes.

The weekly pipeline downloads a ~62 MB upstream drop, converts it, merges its own
pull request and pushes the tag that publishes it. ``scripts/upstream_release.py``
established that the bytes are the ones upstream published; nothing established what
those bytes *mean*, and a release is only reviewable if something says which lookups
it moves.

Comparing two packaged datasets cannot say that. The binary format changed three
times in August 2026, so a report loading "the previously packaged data" breaks on
exactly the releases where review matters most - the older directory is in a layout
the current reader refuses. So the baseline is **text**: a frozen sample of points
and the answer each one got, committed, re-answered by every update and rewritten in
the same pull request. Text against text survives every format change, and the diff
is the review artifact - on a refinement-only release it is empty, and the 2026c
release moved 38 of 10,000 lines.

The sample is frozen and is deliberately **not** one of the benchmark fixtures.
``generate_on_land_points`` is a rejection loop against the installed data, so which
points survive is itself data-dependent, and ``update_data.sh`` regenerates every
benchmark fixture in the same pull request as the data - a baseline needs the
opposite property, or the diff compares answers for two different point sets.

Two signals come out of one run:

* **the changed-answer rate, which gates.** Above :data:`CHANGED_ANSWER_GATE` the
  update stops before it can open a pull request that would auto-merge. The threshold
  is calibrated rather than guessed: over 2025c -> 2026a -> 2026b -> 2026c the
  largest legitimate move was 0.380 %, so 5 % is 13x a real release and far below
  what a truncated or mangled dataset produces. Ordinary refinement changes no
  answers at all - added vertices do not move a border past a sampled point.
* **the payload sizes, which only report.** A symmetric band on them is wanted, and
  the four calibrated releases give no symmetric number: they moved +0.29 %, +0.65 %
  and +1.47 %, so any band they support fires on ordinary refinement. Until the band
  is measured this signal is printed and recorded, never enforced - a blocking gate
  on a guessed band is worse than no gate, because it is switched off after the
  second time it cries wolf.

The gate compares against what is committed, so a legitimately large change is
accepted by committing the rewritten baseline this run leaves behind and running the
update again - there is no override flag, because "re-run once a human has looked at
the diff" is the review this exists to force.
"""

import argparse
import json
import random
import sys
from pathlib import Path

import numpy as np

from scripts.configs import PROJECT_ROOT, SOURCE_DATA_DIR, read_data_version
from timezonefinder import TimezoneFinder
from timezonefinder.flatbuf.io.polygons import get_coordinate_path
from timezonefinder.polygon_array import HoleArray, PolygonArray
from timezonefinder.utils import get_boundaries_dir, get_holes_dir

# Beside the benchmark fixtures rather than among them: same kind of artefact, and
# `update_data.sh` must not confuse the two directories for one another.
GUARD_FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures" / "data_update"
# Written once and never again - see the module docstring on why this cannot be
# `tests/fixtures/benchmarks/on_land_points.npy`.
FROZEN_SAMPLE_PATH = GUARD_FIXTURES_DIR / "on_land_sample.npy"
# The two files an update rewrites.
ANSWERS_PATH = GUARD_FIXTURES_DIR / "answers.txt"
PAYLOAD_PATH = GUARD_FIXTURES_DIR / "payload.json"

N_SAMPLE_POINTS = 10_000
# Its own seed, so the sample is not the benchmark fixtures' points drawn again.
SAMPLE_SEED = 501

# 13x the largest change a legitimate release produced; see the module docstring.
CHANGED_ANSWER_GATE = 0.05

# The scale the packaged coordinates are stored at (int32 at 1e-7 degrees), so a
# coordinate printed here converts to the same integer the sample was answered with:
# a point copied out of the diff reproduces the answer beside it.
COORD_DECIMALS = 7
FIELD_SEPARATOR = "\t"
# No timezone name is a bare hyphen, so this cannot collide with an answer. Reached
# only by a dataset compiled without ocean zones, where the sample's points can fall
# outside every polygon.
NO_ZONE = "-"

# Fixed text, carrying no version and no count: a header that moved with the data
# would put a line in every diff, and "this file diffs by zero lines" is what makes a
# refinement release reviewable at a glance.
ANSWERS_HEADER = (
    "# The frozen on-land sample and the timezone each point resolves to.\n"
    "# Rewritten by `uv run python -m scripts.data_update_guard check`; not by hand.\n"
    "# Columns: longitude, latitude (7 decimals), tab, timezone name.\n"
)


def load_frozen_sample(path: Path = FROZEN_SAMPLE_PATH) -> np.ndarray:
    """The committed sample, as an ``(n, 2)`` array of longitude/latitude pairs."""
    if not path.is_file():
        raise FileNotFoundError(
            f"the frozen data-update sample is missing at {path}. It is committed and "
            f"is drawn exactly once; regenerate it only deliberately, with "
            f"`python -m scripts.data_update_guard freeze --force`."
        )
    return np.load(path)


def answer_sample(points: np.ndarray, data_dir: Path = SOURCE_DATA_DIR) -> list[str]:
    """One answer per sampled point, from the data currently in ``data_dir``."""
    finder = TimezoneFinder(bin_file_location=data_dir, in_memory=True)
    names = finder.timezone_names_at(lngs=points[:, 0], lats=points[:, 1])
    return [NO_ZONE if name is None else name for name in names]


def format_coordinate(value: float) -> str:
    return f"{value:.{COORD_DECIMALS}f}"


def render_answers(points: np.ndarray, answers: list[str]) -> str:
    """The committed baseline's exact text for this sample and these answers."""
    lines = [
        f"{format_coordinate(lng)},{format_coordinate(lat)}{FIELD_SEPARATOR}{answer}"
        for (lng, lat), answer in zip(points.tolist(), answers)
    ]
    return ANSWERS_HEADER + "\n".join(lines) + "\n"


def parse_answers(text: str) -> tuple[list[str], list[str]]:
    """Split a baseline into its coordinate labels and its answers.

    The labels are compared as text rather than as floats: they are re-rendered from
    the frozen sample on every run, so a difference means the sample moved, and a
    float comparison would only make that harder to state.
    """
    coordinates: list[str] = []
    answers: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if line.startswith("#") or not line.strip():
            continue
        coordinate, separator, answer = line.partition(FIELD_SEPARATOR)
        if not separator:
            raise ValueError(
                f"line {number} of the answer baseline holds no tab separator: {line!r}"
            )
        coordinates.append(coordinate)
        answers.append(answer)
    return coordinates, answers


def changed_indices(baseline: list[str], current: list[str]) -> list[int]:
    return [i for i, (was, now) in enumerate(zip(baseline, current)) if was != now]


def payload_metrics(data_dir: Path = SOURCE_DATA_DIR) -> dict[str, int | str]:
    """The size signal's raw numbers, taken from the compiled directory itself.

    Byte sizes rather than coordinate counts: what the release ships is the file, and
    a layout change that alters bytes per coordinate is exactly the event the size
    signal should not silently absorb.
    """
    boundaries = PolygonArray(data_location=get_boundaries_dir(data_dir))
    holes = HoleArray(
        data_location=get_holes_dir(data_dir),
        boundaries=boundaries,
    )
    return {
        "data_version": read_data_version(),
        "boundary_polygons": len(boundaries),
        "hole_polygons": len(holes),
        "boundary_payload_bytes": get_coordinate_path(get_boundaries_dir(data_dir))
        .stat()
        .st_size,
        "hole_payload_bytes": get_coordinate_path(get_holes_dir(data_dir))
        .stat()
        .st_size,
    }


def render_payload(metrics: dict[str, int | str]) -> str:
    return json.dumps(metrics, indent=2, sort_keys=True) + "\n"


def _relative_move(before: object, after: object) -> str:
    """``+1.47 %`` for two numbers, and a plain arrow for anything else."""
    if not isinstance(before, int) or not isinstance(after, int) or before == 0:
        return f"{before} -> {after}"
    return f"{before:,} -> {after:,} ({(after - before) / before:+.2%})"


def report_payload(previous: dict[str, object], current: dict[str, int | str]) -> None:
    """Print the size signal. It never gates - see the module docstring."""
    print("payload signal (report-only, no threshold is calibrated yet):")
    for key in sorted(current):
        print(f"  {key}: {_relative_move(previous.get(key), current[key])}")


def freeze(force: bool, n_points: int = N_SAMPLE_POINTS) -> None:
    """Draw the sample once. Running this again invalidates every baseline."""
    if FROZEN_SAMPLE_PATH.exists() and not force:
        raise FileExistsError(
            f"{FROZEN_SAMPLE_PATH} already holds the frozen sample. Redrawing it "
            f"compares answers for a different set of points, which is what the "
            f"freeze exists to prevent; pass --force if that is really intended."
        )
    # the sampler the benchmark fixtures use, imported rather than copied so that a
    # change to what "on land" means cannot apply to one of them and not the other
    from scripts.generate_benchmark_fixtures import generate_on_land_points

    finder = TimezoneFinder(bin_file_location=SOURCE_DATA_DIR, in_memory=True)
    points = generate_on_land_points(finder, random.Random(SAMPLE_SEED), n_points)
    GUARD_FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    np.save(FROZEN_SAMPLE_PATH, np.array(points, dtype=np.float64))
    print(f"wrote {n_points:,} frozen sample points to {FROZEN_SAMPLE_PATH}")


def check() -> int:
    """Re-answer the frozen sample, rewrite both baselines, and gate on the diff."""
    points = load_frozen_sample()
    answers = answer_sample(points)
    rendered = render_answers(points, answers)

    if ANSWERS_PATH.is_file():
        previous_coordinates, previous_answers = parse_answers(
            ANSWERS_PATH.read_text(encoding="utf-8")
        )
    else:
        # First run in a checkout that has the sample but no baseline. Nothing to
        # compare against, so nothing can be gated; the file this run writes is what
        # the next update is measured against.
        previous_coordinates, previous_answers = [], []

    metrics = payload_metrics()
    previous_metrics: dict[str, object] = {}
    if PAYLOAD_PATH.is_file():
        previous_metrics = json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))

    # Written before the gate is evaluated: a blocked update still has to leave the
    # diff a human reviews, and re-running after committing it is the only override.
    GUARD_FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    ANSWERS_PATH.write_text(rendered, encoding="utf-8")
    PAYLOAD_PATH.write_text(render_payload(metrics), encoding="utf-8")

    report_payload(previous_metrics, metrics)

    if not previous_answers:
        print(
            f"no answer baseline was committed; wrote one from {len(points):,} points"
        )
        return 0

    current_coordinates, _ = parse_answers(rendered)
    if previous_coordinates != current_coordinates:
        print(
            f"the committed baseline in {ANSWERS_PATH} does not describe the frozen "
            f"sample in {FROZEN_SAMPLE_PATH}: {len(previous_coordinates):,} points "
            f"against {len(current_coordinates):,}, or the coordinates themselves "
            f"moved. The two are only comparable point by point, so no changed-answer "
            f"rate is reported.",
            file=sys.stderr,
        )
        return 1

    changed = changed_indices(previous_answers, answers)
    rate = len(changed) / len(answers)
    print(f"changed answers: {len(changed):,} of {len(answers):,} ({rate:.3%})")
    for index in changed[:10]:
        print(
            f"  {current_coordinates[index]}: "
            f"{previous_answers[index]} -> {answers[index]}"
        )
    if len(changed) > 10:
        print(f"  ... and {len(changed) - 10:,} more; see the diff of {ANSWERS_PATH}")

    if rate > CHANGED_ANSWER_GATE:
        print(
            f"{rate:.3%} of the sample changed answer, above the {CHANGED_ANSWER_GATE:.0%} "
            f"gate. A refinement release moves ~0 % and the largest legitimate change "
            f"measured was 0.380 %, so this is a dataset to look at rather than to "
            f"publish. The rewritten baseline is in the working tree: review its diff, "
            f"and re-run the update once committing it is the right answer.",
            file=sys.stderr,
        )
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "check", help="re-answer the frozen sample, rewrite the baselines, gate"
    )
    freeze_parser = subparsers.add_parser(
        "freeze", help="draw the frozen sample (once; it is committed)"
    )
    freeze_parser.add_argument("--force", action="store_true")

    args = parser.parse_args(argv)
    try:
        if args.command == "freeze":
            freeze(force=args.force)
            return 0
        return check()
    except (OSError, ValueError) as error:
        print(f"{parser.prog}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
