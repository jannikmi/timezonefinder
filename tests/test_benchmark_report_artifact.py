"""Tests for the commit-bound handoff of generated benchmark pages."""

from pathlib import Path

import pytest

from scripts.benchmark_report_artifact import (
    COMMIT_STAMP,
    install_artifact,
    stage_artifact,
)

pytestmark = pytest.mark.unit

COMMIT = "a" * 40


def _reports(directory: Path) -> tuple[Path, ...]:
    directory.mkdir(parents=True)
    reports = (directory / "one.rst", directory / "two.rst")
    for index, report in enumerate(reports):
        report.write_text(f"report {index}\n", encoding="utf-8")
    return reports


def test_stage_and_install_preserve_reports_and_commit(tmp_path: Path) -> None:
    sources = _reports(tmp_path / "source")
    artifact = tmp_path / "artifact"
    destinations = (tmp_path / "dest" / "one.rst", tmp_path / "dest" / "two.rst")
    for destination in destinations:
        destination.parent.mkdir(parents=True, exist_ok=True)

    stage_artifact(artifact, COMMIT, sources)
    install_artifact(artifact, COMMIT, destinations)

    assert (artifact / COMMIT_STAMP).read_text(encoding="ascii") == f"{COMMIT}\n"
    assert [path.read_bytes() for path in destinations] == [
        path.read_bytes() for path in sources
    ]


def test_install_refuses_an_artifact_for_another_commit_before_copying(
    tmp_path: Path,
) -> None:
    sources = _reports(tmp_path / "source")
    artifact = tmp_path / "artifact"
    destinations = (tmp_path / "one.rst", tmp_path / "two.rst")
    for destination in destinations:
        destination.write_text("keep\n", encoding="utf-8")
    stage_artifact(artifact, COMMIT, sources)

    with pytest.raises(ValueError, match="commit mismatch"):
        install_artifact(artifact, "b" * 40, destinations)

    assert [path.read_text(encoding="utf-8") for path in destinations] == [
        "keep\n",
        "keep\n",
    ]


def test_install_refuses_an_incomplete_artifact_before_copying(tmp_path: Path) -> None:
    sources = _reports(tmp_path / "source")
    artifact = tmp_path / "artifact"
    destinations = (tmp_path / "one.rst", tmp_path / "two.rst")
    for destination in destinations:
        destination.write_text("keep\n", encoding="utf-8")
    stage_artifact(artifact, COMMIT, sources)
    (artifact / "two.rst").unlink()

    with pytest.raises(FileNotFoundError, match="incomplete"):
        install_artifact(artifact, COMMIT, destinations)

    assert [path.read_text(encoding="utf-8") for path in destinations] == [
        "keep\n",
        "keep\n",
    ]
