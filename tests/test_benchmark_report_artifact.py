"""Tests for the commit-bound handoff of generated benchmark pages."""

from pathlib import Path

import pytest

from scripts.benchmark_report_artifact import (
    COMMIT_STAMP,
    MANIFEST,
    REPORT_GROUPS,
    install_artifact,
    report_files_for,
    stage_artifact,
)
from tests.auxiliaries import PROJECT_ROOT

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


def test_install_replaces_only_the_pages_the_artifact_carries(tmp_path: Path) -> None:
    """A render of some report groups must leave every other committed page alone."""
    sources = _reports(tmp_path / "source")
    artifact = tmp_path / "artifact"
    destinations = (tmp_path / "one.rst", tmp_path / "two.rst")
    for destination in destinations:
        destination.write_text("keep\n", encoding="utf-8")
    stage_artifact(artifact, COMMIT, sources[:1])

    written = install_artifact(artifact, COMMIT, destinations)

    assert written == [destinations[0]]
    assert destinations[0].read_text(encoding="utf-8") == "report 0\n"
    assert destinations[1].read_text(encoding="utf-8") == "keep\n"


def test_install_reads_an_artifact_staged_before_the_manifest_as_complete(
    tmp_path: Path,
) -> None:
    sources = _reports(tmp_path / "source")
    artifact = tmp_path / "artifact"
    destinations = (tmp_path / "one.rst", tmp_path / "two.rst")
    stage_artifact(artifact, COMMIT, sources)
    (artifact / MANIFEST).unlink()

    assert install_artifact(artifact, COMMIT, destinations) == list(destinations)


def test_install_refuses_a_manifest_naming_an_unknown_page(tmp_path: Path) -> None:
    """The artifact decides which pages to write, so it may only name known ones."""
    sources = _reports(tmp_path / "source")
    artifact = tmp_path / "artifact"
    destinations = (tmp_path / "one.rst", tmp_path / "two.rst")
    stage_artifact(artifact, COMMIT, sources)
    (artifact / MANIFEST).write_text("one.rst\n../../setup.py\n", encoding="ascii")

    with pytest.raises(ValueError, match="unknown"):
        install_artifact(artifact, COMMIT, destinations)
    assert not destinations[0].exists()


def test_report_groups_cover_every_page_once() -> None:
    pages = [path for paths in REPORT_GROUPS.values() for path in paths]
    assert len(pages) == len(set(pages))
    assert report_files_for("all") == tuple(pages)
    assert report_files_for("data,break-even") == (
        REPORT_GROUPS["break-even"] + REPORT_GROUPS["data"]
    )


def test_report_groups_refuse_an_unknown_name() -> None:
    with pytest.raises(ValueError, match="unknown report group"):
        report_files_for("suite,charts")


def test_the_makefile_names_the_same_report_groups() -> None:
    """`make reports REPORTS=...` and the artifact's manifest must mean one thing."""
    makefile = (PROJECT_ROOT / "Makefile").read_text(encoding="utf-8")
    line = next(
        line for line in makefile.splitlines() if line.startswith("REPORT_GROUPS :=")
    )
    assert line.split(":=", 1)[1].split() == list(REPORT_GROUPS)
