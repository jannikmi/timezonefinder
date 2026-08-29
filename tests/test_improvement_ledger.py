"""Keep the linked improvement ranking and one-file-per-item memory in sync."""

import re
from pathlib import Path

import pytest

from tests.auxiliaries import PROJECT_ROOT

IMPROVEMENTS_DIR = PROJECT_ROOT / "contributing" / "improvements"
RANKING_FILE = IMPROVEMENTS_DIR / "improvement-priority-ranking.md"
ITEMS_DIR = IMPROVEMENTS_DIR / "items"

ITEM_HEADING = re.compile(r"^# ([A-Z0-9-]+) [—-] (.+)$")
ITEM_FILENAME = re.compile(r"^(data-binaries|[a-z]+-[0-9]+)-(.+)\.md$")
RANKING_ROW = re.compile(r"^\| \[([A-Z][A-Z0-9-]+)\]\((items/[^)]+\.md)\) \|")
ENTRY_STATUS = re.compile(r"^- \*\*Status:\*\* +(\S+)")
DECISION_BULLET = "- **Decision needed:**"
NEEDS_A_DECISION = "needs"
CLOSED_HEADING = "### Closed"
CLOSED_OPENINGS = frozenset({"rejected", "withdrawn", "out"})
STATUS_OPENINGS = frozenset(
    {
        "open",
        "needs",
        "blocked",
        "conditional",
        "parked",
        "rejected",
        "out",
        "withdrawn",
    }
)


@pytest.fixture(scope="module")
def ranking_text() -> str:
    return RANKING_FILE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def item_files() -> list[Path]:
    files = sorted(ITEMS_DIR.rglob("*.md"))
    assert files, f"no improvement items found under {ITEMS_DIR}"
    return files


def heading_of(path: Path) -> tuple[str, str]:
    first = path.read_text(encoding="utf-8").splitlines()[0]
    match = ITEM_HEADING.fullmatch(first)
    assert match, f"{path} must start with '# <ID> — <descriptive title>'"
    return match.group(1), match.group(2)


def status_of(path: Path) -> str:
    statuses = [
        match.group(1)
        for line in path.read_text(encoding="utf-8").splitlines()
        if (match := ENTRY_STATUS.match(line))
    ]
    assert len(statuses) == 1, f"{path} must declare exactly one Status bullet"
    return statuses[0].rstrip(".,:").lower()


def ranking_tables(text: str) -> tuple[str, str]:
    live, separator, closed = text.partition(CLOSED_HEADING)
    assert separator, f"{RANKING_FILE} must contain a {CLOSED_HEADING!r} table"
    return live, closed


def ranked(text: str) -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in text.splitlines():
        if match := RANKING_ROW.match(line):
            id_, target = match.groups()
            assert id_ not in rows, f"{id_} occurs more than once in {RANKING_FILE}"
            rows[id_] = target
    return rows


@pytest.mark.unit
def test_item_filenames_are_stable_and_descriptive(item_files: list[Path]) -> None:
    for path in item_files:
        match = ITEM_FILENAME.fullmatch(path.name)
        assert match, f"{path.name} must be '<lowercase-id>-<descriptive-slug>.md'"
        id_, title = heading_of(path)
        assert match.group(1).upper() == id_
        assert len(match.group(2)) >= 3
        assert path.parent != ITEMS_DIR, (
            f"{path} must live in a stable subject directory"
        )


@pytest.mark.unit
def test_ranking_and_items_name_the_same_ids(
    ranking_text: str, item_files: list[Path]
) -> None:
    rows = ranked(ranking_text)
    items = {heading_of(path)[0]: path for path in item_files}
    assert rows, "the ranking must not be empty"
    assert rows.keys() == items.keys()
    for id_, target in rows.items():
        assert (IMPROVEMENTS_DIR / target).resolve() == items[id_].resolve()


@pytest.mark.unit
def test_ranking_links_resolve_once(ranking_text: str) -> None:
    targets = list(ranked(ranking_text).values())
    assert len(targets) == len(set(targets))
    for target in targets:
        assert (IMPROVEMENTS_DIR / target).is_file(), target


@pytest.mark.unit
def test_status_vocabulary_and_closed_placement(
    ranking_text: str, item_files: list[Path]
) -> None:
    live_table, closed_table = ranking_tables(ranking_text)
    live = set(ranked(live_table))
    closed = set(ranked(closed_table))
    for path in item_files:
        id_, _ = heading_of(path)
        status = status_of(path)
        assert status in STATUS_OPENINGS, f"{path}: unknown status {status!r}"
        if status in CLOSED_OPENINGS:
            assert id_ in closed and id_ not in live
        else:
            assert id_ in live and id_ not in closed


@pytest.mark.unit
def test_waiting_items_say_what_they_need(item_files: list[Path]) -> None:
    for path in item_files:
        text = path.read_text(encoding="utf-8")
        count = text.count(DECISION_BULLET)
        assert count <= 1, f"{path} carries {count} decision-needed bullets"
        assert (status_of(path) == NEEDS_A_DECISION) == bool(count)
