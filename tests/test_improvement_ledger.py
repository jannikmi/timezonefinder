"""Assert the improvement register's ranking and its entries stay in step.

``potential-improvements.md`` states its order in one place - the ranking table -
and its detail in another, the entry sections below it. That split is what keeps
the entries groupable by kind while the ranking stays a single walkable list, and
it is also how the two drift: an entry added without a row is invisible to the
pass that walks the ranking, and a row left behind by a shipped entry sends that
pass looking for something that is no longer there. Neither shows up in a diff
review, because both halves read as correct on their own.
"""

import re

import pytest

from tests.auxiliaries import PROJECT_ROOT

LEDGER_FILE = PROJECT_ROOT / "potential-improvements.md"

RANKING_HEADING = "## The ranking"
ENTRY_HEADING = re.compile(r"^### ([A-Z0-9-]+) [-\u2014]")
RANKING_ROW = re.compile(r"^\| *\d+ *\| *([A-Z0-9-]+) *\|")


@pytest.fixture(scope="module")
def ledger_text() -> str:
    assert LEDGER_FILE.is_file(), f"{LEDGER_FILE} is the register every pass reads"
    return LEDGER_FILE.read_text(encoding="utf-8")


def ranking_section(text: str) -> str:
    """Return the ranking table alone.

    Other tables in the file are numbered the same way - the coverage log opens
    with a pass number - so a repository-wide row match would read their first
    column as an entry id.
    """
    _, _, below = text.partition(RANKING_HEADING)
    assert below, f"{LEDGER_FILE} no longer has a {RANKING_HEADING!r} section"
    section, _, _ = below.partition("\n## ")
    return section


def ids_of(pattern: re.Pattern[str], text: str) -> list[str]:
    return [
        match.group(1) for line in text.splitlines() if (match := pattern.match(line))
    ]


@pytest.mark.unit
def test_ranking_and_entries_are_not_empty(ledger_text: str) -> None:
    # guards the comparisons below: two empty sets match each other
    assert ids_of(RANKING_ROW, ranking_section(ledger_text)), (
        "the ranking table has no rows"
    )
    assert ids_of(ENTRY_HEADING, ledger_text), "the register has no entries"


@pytest.mark.unit
def test_every_id_is_declared_once(ledger_text: str) -> None:
    for name, ids in (
        ("ranking", ids_of(RANKING_ROW, ranking_section(ledger_text))),
        ("entries", ids_of(ENTRY_HEADING, ledger_text)),
    ):
        duplicates = {id_ for id_ in ids if ids.count(id_) > 1}
        assert not duplicates, f"the {name} declare {sorted(duplicates)} more than once"


@pytest.mark.unit
def test_ranking_and_entries_name_the_same_items(ledger_text: str) -> None:
    ranked = set(ids_of(RANKING_ROW, ranking_section(ledger_text)))
    described = set(ids_of(ENTRY_HEADING, ledger_text))
    assert described - ranked == set(), (
        f"{sorted(described - ranked)} have an entry but no row in the ranking, so a pass "
        "walking the ranking never reaches them"
    )
    assert ranked - described == set(), (
        f"{sorted(ranked - described)} are ranked but have no entry - a shipped entry must "
        "take its row with it"
    )
