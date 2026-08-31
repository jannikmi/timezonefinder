"""Keep the split discovery-coverage map complete and merge-friendly."""

import re

import pytest

from tests.auxiliaries import PROJECT_ROOT

COVERAGE_INDEX = (
    PROJECT_ROOT
    / "contributing"
    / "improvements"
    / "improvement-discovery-coverage-map.md"
)
COVERAGE_DIR = COVERAGE_INDEX.parent / "discovery-coverage"
SURFACES_DIR = COVERAGE_DIR / "surfaces"
MARKDOWN_LINK = re.compile(r"\[[^]]+\]\((discovery-coverage/[^)]+\.md)\)")
REQUIRED_SURFACE_HEADINGS = (
    "## Baseline",
    "## Covered subjects",
    "## Next useful gap",
)


@pytest.mark.unit
def test_coverage_index_links_every_record_once() -> None:
    targets = MARKDOWN_LINK.findall(COVERAGE_INDEX.read_text(encoding="utf-8"))
    records = {
        path.relative_to(COVERAGE_INDEX.parent).as_posix()
        for path in COVERAGE_DIR.rglob("*.md")
    }

    assert len(targets) == len(set(targets)), "coverage index links a record twice"
    assert set(targets) == records
    for target in targets:
        assert (COVERAGE_INDEX.parent / target).is_file(), target


@pytest.mark.unit
def test_surface_records_keep_independent_merge_units() -> None:
    surfaces = sorted(SURFACES_DIR.glob("*.md"))
    assert surfaces, f"no discovery surfaces found under {SURFACES_DIR}"

    for path in surfaces:
        text = path.read_text(encoding="utf-8")
        for heading in REQUIRED_SURFACE_HEADINGS:
            assert text.count(heading) == 1, f"{path}: expected one {heading!r}"
        assert not any(line.startswith("|") for line in text.splitlines()), (
            f"{path}: tables turn a whole surface into one merge unit"
        )
