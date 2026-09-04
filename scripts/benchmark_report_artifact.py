#!/usr/bin/env python3

"""Stage and install commit-bound benchmark report artifacts."""

import argparse
import re
import shutil
from collections.abc import Sequence
from pathlib import Path

from scripts.configs import (
    ACCELERATION_REPORT_FILE,
    COMPARISON_REPORT_FILE,
    DATA_REPORT_FILE,
    INITIALIZATION_REPORT_FILE,
    MEMORY_REPORT_FILE,
    PERFORMANCE_REPORT_FILE,
    POLYGON_REPORT_FILE,
)

COMMIT_STAMP = "BENCHMARK_REPORT_COMMIT"
REPORT_FILES = (
    PERFORMANCE_REPORT_FILE,
    POLYGON_REPORT_FILE,
    INITIALIZATION_REPORT_FILE,
    COMPARISON_REPORT_FILE,
    ACCELERATION_REPORT_FILE,
    MEMORY_REPORT_FILE,
    DATA_REPORT_FILE,
)
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40,64}$")


def _validate_commit(commit: str) -> str:
    commit = commit.strip()
    if not COMMIT_PATTERN.fullmatch(commit):
        raise ValueError(f"invalid git commit in benchmark report artifact: {commit!r}")
    return commit


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
    (output_dir / COMMIT_STAMP).write_text(f"{commit}\n", encoding="ascii")


def install_artifact(
    artifact_dir: Path,
    expected_commit: str,
    report_files: Sequence[Path] = REPORT_FILES,
) -> None:
    """Install reports only when the artifact was measured for ``expected_commit``."""
    expected_commit = _validate_commit(expected_commit)
    stamp = artifact_dir / COMMIT_STAMP
    actual_commit = _validate_commit(stamp.read_text(encoding="ascii"))
    if actual_commit != expected_commit:
        raise ValueError(
            "benchmark report artifact commit mismatch: "
            f"expected {expected_commit}, got {actual_commit}"
        )

    sources = [artifact_dir / report.name for report in report_files]
    missing = [path for path in sources if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"benchmark report artifact is incomplete: {missing}")
    for source, destination in zip(sources, report_files, strict=True):
        shutil.copyfile(source, destination)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    stage = subparsers.add_parser("stage", help="stage generated reports for upload")
    stage.add_argument("--output-dir", type=Path, required=True)
    stage.add_argument("--commit", required=True)

    install = subparsers.add_parser(
        "install", help="install a downloaded report artifact"
    )
    install.add_argument("--artifact-dir", type=Path, required=True)
    install.add_argument("--expected-commit", required=True)

    args = parser.parse_args()
    if args.command == "stage":
        stage_artifact(args.output_dir, args.commit)
    else:
        install_artifact(args.artifact_dir, args.expected_commit)


if __name__ == "__main__":
    main()
