"""Regression tests for changelog handling in automated data releases."""

from datetime import date

import pytest

from scripts.changelog import (
    _RELEASE_TITLE,
    has_pending_unreleased_changes,
    insert_data_release,
    main,
    validate_changelog_order,
)
from tests.auxiliaries import PROJECT_ROOT

PREVIOUS_RELEASE = "8.2.5 (2026-07-22)\n------------------\n\n* previous release\n"
# CHANGELOG.rst puts two blank lines above every release title, so the fixture
# does too - one that does not cannot tell correct spacing from wrong spacing
SECTION_GAP = "\n\n"


def _changelog(unreleased: str = "", *, below: str = PREVIOUS_RELEASE) -> str:
    """Build a changelog with ``unreleased`` as the pending section's body."""
    return (
        f"=========\nChangelog\n=========\n{SECTION_GAP}"
        f"X.X.X (unreleased)\n------------------\n{unreleased}{SECTION_GAP}{below}"
    )


def _insert(
    changelog: str, *, version: str = "8.2.6", release_date: date = date(2026, 8, 17)
) -> str:
    return insert_data_release(
        changelog,
        version=version,
        release_date=release_date,
        data_tag="2026a",
        data_repo_url="https://example.test/data",
    )


@pytest.mark.unit
def test_data_release_is_inserted_below_a_nonempty_unreleased_section() -> None:
    """Pending work stays pending: the entry goes below it, not above.

    The previous implementation prepended after the file header, which put the
    data release above work it does not describe.
    """
    pending = "\n* user-facing change\n\nInternal:\n\n* build change\n"

    assert _insert(_changelog(pending)) == _changelog(
        pending,
        below=(
            "8.2.6 (2026-08-17)\n------------------\n\n"
            "* updated the data to `2026a "
            "<https://example.test/data/releases/tag/2026a>`__\n"
            f"{SECTION_GAP}{PREVIOUS_RELEASE}"
        ),
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("unreleased_body", "expected"),
    [
        ("", False),
        ("\nInternal:\n", False),
        ("\n* user-facing change\n", True),
        ("\nInternal:\n\n* build change\n", True),
        ("\npending prose\n", True),
        ("\n- differently formatted change\n", True),
    ],
)
def test_pending_unreleased_changes_are_detected(
    unreleased_body: str, expected: bool
) -> None:
    assert has_pending_unreleased_changes(_changelog(unreleased_body)) is expected


@pytest.mark.unit
@pytest.mark.parametrize(
    ("unreleased_body", "exit_code"),
    [("\n* pending change\n", 1), ("", 0), ("\nInternal:\n", 0)],
)
def test_check_empty_cli_reports_whether_work_is_pending(
    tmp_path, unreleased_body: str, exit_code: int
) -> None:
    """Both exit codes matter.

    A check-empty returning 1 unconditionally passes a suite that only tests
    the blocking case, while ensuring no data update is ever released again -
    and a workflow that merges nothing looks exactly like upstream having
    published nothing.
    """
    changelog = tmp_path / "CHANGELOG.rst"
    changelog.write_text(_changelog(unreleased_body))

    assert main(["check-empty", str(changelog)]) == exit_code


@pytest.mark.unit
@pytest.mark.parametrize("content", [None, "Changelog\n=========\n\nunstructured\n"])
def test_check_empty_cli_blocks_what_it_cannot_read(tmp_path, content) -> None:
    """A changelog the guard cannot parse must block, not crash or release."""
    changelog = tmp_path / "CHANGELOG.rst"
    if content is not None:
        changelog.write_text(content)

    assert main(["check-empty", str(changelog)]) == 1


@pytest.mark.unit
@pytest.mark.parametrize("version", ["8.2.6rc1", "8.2", "v8.2.6"])
def test_insertion_rejects_a_version_no_later_check_could_find(version: str) -> None:
    """A heading the release pattern cannot match is invisible to every check.

    ``validate_changelog_order`` would pass over such an entry rather than
    reject it, and the next data update would insert above it instead of
    below - so the ordering guarantee would silently cover only the
    well-formed entries.
    """
    with pytest.raises(ValueError, match="not a release version"):
        _insert(_changelog(), version=version)


@pytest.mark.unit
def test_insertion_rejects_a_date_older_than_the_latest_release() -> None:
    with pytest.raises(ValueError, match="descending"):
        _insert(_changelog(), release_date=date(2026, 7, 1))


@pytest.mark.unit
def test_committed_changelog_sections_are_in_release_order() -> None:
    validate_changelog_order(
        (PROJECT_ROOT / "CHANGELOG.rst").read_text(encoding="utf-8")
    )


@pytest.mark.unit
def test_the_inserted_entry_is_spaced_like_the_committed_changelog() -> None:
    """The entry lands in a real file, so its own spacing has to match it.

    Nothing else catches a mismatch: ``rstcheck`` accepts either gap and the
    pre-commit hooks only look at trailing whitespace, so wrong spacing ships
    with the data update and is noticed by a reader or not at all. The
    convention is read off the file rather than restated here - the older
    entries at the bottom predate it and do not follow it.
    """
    committed = (PROJECT_ROOT / "CHANGELOG.rst").read_text(encoding="utf-8")
    newest = _RELEASE_TITLE.search(committed)
    assert newest is not None
    separator = committed[: newest.start()][-3:]

    updated = _insert(committed, version="99.0.0", release_date=date(2099, 1, 1))
    inserted, displaced = [m.start() for m in _RELEASE_TITLE.finditer(updated)][:2]
    # both boundaries the insertion created: above the new entry and below it
    assert updated[:inserted].endswith(separator)
    assert updated[:displaced].endswith(separator)
