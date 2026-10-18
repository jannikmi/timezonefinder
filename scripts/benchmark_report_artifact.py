#!/usr/bin/env python3

"""Stage and install commit-bound benchmark report artifacts."""

import argparse
import re
import shutil
from collections.abc import Sequence
from pathlib import Path

from scripts.configs import (
    ACCELERATION_REPORT_FILE,
    BATCH_BREAK_EVEN_CHART_FILE,
    BATCH_BREAK_EVEN_REPORT_FILE,
    COMPARISON_REPORT_FILE,
    DATA_REPORT_FILE,
    INITIALIZATION_REPORT_FILE,
    MEMORY_REPORT_FILE,
    PERFORMANCE_REPORT_FILE,
    POLYGON_REPORT_FILE,
)

COMMIT_STAMP = "BENCHMARK_REPORT_COMMIT"
#: Which pages an artifact carries. Written by :func:`stage_artifact` so that a render
#: of a few report groups installs exactly those pages and leaves the rest alone.
MANIFEST = "BENCHMARK_REPORT_FILES"

#: The report groups a render can be limited to (``make reports REPORTS=...``), and
#: the pages each one writes. A group is the unit one measurement feeds, so it is never
#: split: the full pytest suite's JSON feeds four pages, and the timezone-finding page
#: embeds the latency distribution. The Makefile's ``REPORT_GROUPS`` names the same
#: groups; ``tests/test_benchmark_report_artifact.py`` holds the two together.
REPORT_GROUPS: dict[str, tuple[Path, ...]] = {
    "suite": (
        PERFORMANCE_REPORT_FILE,
        POLYGON_REPORT_FILE,
        INITIALIZATION_REPORT_FILE,
        COMPARISON_REPORT_FILE,
    ),
    "memory": (MEMORY_REPORT_FILE,),
    "acceleration": (ACCELERATION_REPORT_FILE,),
    # the chart is generated beside its page and belongs to the same run: an artifact
    # carrying the page without it installs a report whose figure is the previous one
    "break-even": (BATCH_BREAK_EVEN_REPORT_FILE, BATCH_BREAK_EVEN_CHART_FILE),
    "data": (DATA_REPORT_FILE,),
}
ALL_REPORTS = "all"
REPORT_FILES = tuple(path for paths in REPORT_GROUPS.values() for path in paths)
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40,64}$")


def _validate_commit(commit: str) -> str:
    commit = commit.strip()
    if not COMMIT_PATTERN.fullmatch(commit):
        raise ValueError(f"invalid git commit in benchmark report artifact: {commit!r}")
    return commit


def report_files_for(groups: str) -> tuple[Path, ...]:
    """The pages a comma-separated group selection writes; ``all`` for every page."""
    names = [name.strip() for name in groups.split(",") if name.strip()]
    if not names or names == [ALL_REPORTS]:
        return REPORT_FILES
    unknown = [name for name in names if name not in REPORT_GROUPS]
    if unknown:
        raise ValueError(
            f"unknown report group(s) {', '.join(unknown)}; choose from "
            f"{', '.join(REPORT_GROUPS)} or {ALL_REPORTS}"
        )
    return tuple(
        path for name in REPORT_GROUPS if name in names for path in REPORT_GROUPS[name]
    )


def stage_artifact(
    output_dir: Path,
    commit: str,
    report_files: Sequence[Path] = REPORT_FILES,
) -> None:
    """Copy generated reports into ``output_dir`` and bind them to ``commit``."""
    commit = _validate_commit(commit)
    missing = [path for path in report_files if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"benchmark report files are missing: {missing}")

    output_dir.mkdir(parents=True, exist_ok=True)
    for report in report_files:
        shutil.copyfile(report, output_dir / report.name)
    (output_dir / MANIFEST).write_text(
        "".join(f"{report.name}\n" for report in report_files), encoding="ascii"
    )
    (output_dir / COMMIT_STAMP).write_text(f"{commit}\n", encoding="ascii")


def install_artifact(
    artifact_dir: Path,
    expected_commit: str,
    report_files: Sequence[Path] = REPORT_FILES,
) -> list[Path]:
    """Install the reports an artifact carries, only when it was measured for
    ``expected_commit``, and return the pages written.

    The manifest says which pages the artifact carries; every one it names must be a
    known page and be present, and pages it does not name are left untouched. An
    artifact without a manifest predates it and carries every page. Nothing is copied
    until all of that holds.
    """
    expected_commit = _validate_commit(expected_commit)
    stamp = artifact_dir / COMMIT_STAMP
    actual_commit = _validate_commit(stamp.read_text(encoding="ascii"))
    if actual_commit != expected_commit:
        raise ValueError(
            "benchmark report artifact commit mismatch: "
            f"expected {expected_commit}, got {actual_commit}"
        )

    by_name = {report.name: report for report in report_files}
    manifest = artifact_dir / MANIFEST
    # an artifact staged before the manifest existed always carried every page
    names = (
        manifest.read_text(encoding="ascii").split()
        if manifest.is_file()
        else [report.name for report in report_files]
    )
    unknown = [name for name in names if name not in by_name]
    if not names or unknown:
        raise ValueError(
            f"benchmark report artifact names no known page or unknown pages: {unknown}"
        )
    destinations = [by_name[name] for name in names]
    sources = [artifact_dir / name for name in names]
    missing = [path for path in sources if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"benchmark report artifact is incomplete: {missing}")
    for source, destination in zip(sources, destinations, strict=True):
        shutil.copyfile(source, destination)
    return destinations


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    stage = subparsers.add_parser("stage", help="stage generated reports for upload")
    stage.add_argument("--output-dir", type=Path, required=True)
    stage.add_argument("--commit", required=True)
    stage.add_argument(
        "--reports",
        default=ALL_REPORTS,
        help=(
            "comma-separated report groups the render wrote "
            f"({', '.join(REPORT_GROUPS)}), or {ALL_REPORTS} (default)"
        ),
    )

    install = subparsers.add_parser(
        "install", help="install a downloaded report artifact"
    )
    install.add_argument("--artifact-dir", type=Path, required=True)
    install.add_argument("--expected-commit", required=True)

    args = parser.parse_args()
    if args.command == "stage":
        stage_artifact(args.output_dir, args.commit, report_files_for(args.reports))
    else:
        written = install_artifact(args.artifact_dir, args.expected_commit)
        print("Installed " + ", ".join(str(path) for path in written))


if __name__ == "__main__":
    main()
