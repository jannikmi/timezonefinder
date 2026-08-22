"""Assert the improvement register's ranking and its entries stay in step.

``potential-improvements.md`` states its order in one place - the ranking table -
and its detail in another, the entry sections below it. That split is what keeps
the entries groupable by area while the ranking stays a single walkable list, and
it is also how the two drift: an entry added without a row is invisible to the
pass that walks the ranking, and a row left behind by a shipped entry sends that
pass looking for something that is no longer there. Neither shows up in a diff
review, because both halves read as correct on their own.

The status vocabulary is checked for the same reason. Work that landed is deleted
from the file rather than marked, so no status may say it is done - and an agent
reaching for ``shipped`` is exactly how a register turns back into a changelog
nobody reads.

``needs`` is the one status naming work no agent can do by reading harder: a
person has to decide something. It is therefore paired with a ``Decision
needed:`` bullet holding the question, and the pairing is checked in both
directions. A ``needs`` status without the bullet says an entry is waiting
without saying what for, which is unactionable by the pass that records it and by
the maintainer who would answer it; the bullet without the status is a question
that no search over statuses will ever surface.
"""

import re

import pytest

from tests.auxiliaries import PROJECT_ROOT

LEDGER_FILE = PROJECT_ROOT / "potential-improvements.md"

RANKING_HEADING = "## The ranking"
ENTRY_HEADING = re.compile(r"^### ([A-Z0-9-]+) [-\u2014]")
RANKING_ROW = re.compile(r"^\| *([A-Z][A-Z0-9-]+) *\|")
ENTRY_STATUS = re.compile(r"^- \*\*Status:\*\* +(\S+)")
DECISION_BULLET = "- **Decision needed:**"
NEEDS_A_DECISION = "needs"

# the file documents this list; there is deliberately no status meaning "done"
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
def ledger_text() -> str:
    assert LEDGER_FILE.is_file(), f"{LEDGER_FILE} is the register every pass reads"
    return LEDGER_FILE.read_text(encoding="utf-8")


def ranking_section(text: str) -> str:
    """Return the ranking table alone.

    The file holds other tables - the coverage log, and tables inside entries -
    so a repository-wide row match would read their first column as an entry id.
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


@pytest.mark.unit
def test_no_status_claims_the_work_is_done(ledger_text: str) -> None:
    """A shipped entry is deleted, so no status may report one as finished."""
    statuses = ids_of(ENTRY_STATUS, ledger_text)
    assert statuses, "no entry declares a status"
    unknown = {
        word for word in statuses if word.rstrip(".,:").lower() not in STATUS_OPENINGS
    }
    assert not unknown, (
        f"{sorted(unknown)} open a status line, but the register documents "
        f"{sorted(STATUS_OPENINGS)} - and none of them means done, because work that landed "
        "is deleted from the file rather than marked"
    )


def entry_bodies(text: str) -> dict[str, str]:
    """Return each entry id mapped to the lines below its heading.

    Scoped to entries on purpose: the file's own prose describes the convention
    below, and a whole-file search would read that description as an entry.
    """
    bodies: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = None
        if match := ENTRY_HEADING.match(line):
            current = bodies.setdefault(match.group(1), [])
        elif current is not None:
            current.append(line)
    return {id_: "\n".join(lines) for id_, lines in bodies.items()}


@pytest.mark.unit
def test_waiting_entries_say_what_they_are_waiting_for() -> None:
    """``Status: needs ...`` and a ``Decision needed:`` bullet imply each other."""
    bodies = entry_bodies(LEDGER_FILE.read_text(encoding="utf-8"))
    assert bodies, "the register has no entries"
    for id_, body in bodies.items():
        statuses = ids_of(ENTRY_STATUS, body)
        waiting = statuses[:1] == [NEEDS_A_DECISION]
        briefed = body.count(DECISION_BULLET)
        assert briefed <= 1, (
            f"{id_} carries {briefed} {DECISION_BULLET!r} bullets - one entry asks one "
            "question, so that the answer has somewhere unambiguous to be written back"
        )
        assert waiting == bool(briefed), (
            f"{id_} declares {statuses[:1]} and has {briefed} {DECISION_BULLET!r} bullets. "
            f"A {NEEDS_A_DECISION!r} status must name the question it is waiting on, and a "
            "question must be findable from the status - neither half is any use alone"
        )
