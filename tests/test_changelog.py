"""Regression tests for changelog handling in automated data releases."""

from datetime import date

import pytest

from scripts.changelog import (
    has_pending_unreleased_changes,
    insert_data_release,
    main,
    validate_changelog_order,
)
from tests.auxiliaries import PROJECT_ROOT


@pytest.mark.unit
def test_data_release_is_inserted_below_nonempty_unreleased_section() -> None:
    changelog = """Changelog
=========

X.X.X (unreleased)
------------------

* user-facing change

Internal:

* build change

8.2.5 (2026-07-22)
------------------

* previous release
"""

    updated = insert_data_release(
        changelog,
        version="8.2.6",
        release_date=date(2026, 8, 17),
        data_tag="2026a",
        data_repo_url="https://example.test/data",
    )

    assert (
        updated
        == """Changelog
=========

X.X.X (unreleased)
------------------

* user-facing change

Internal:

* build change

8.2.6 (2026-08-17)
------------------

* updated the data to `2026a <https://example.test/data/releases/tag/2026a>`__

8.2.5 (2026-07-22)
------------------

* previous release
"""
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
    changelog = f"""Changelog
=========

X.X.X (unreleased)
------------------
{unreleased_body}
8.2.5 (2026-07-22)
------------------

* previous release
"""

    assert has_pending_unreleased_changes(changelog) is expected


@pytest.mark.unit
def test_check_empty_cli_blocks_pending_unreleased_changes(tmp_path) -> None:
    changelog_path = tmp_path / "CHANGELOG.rst"
    changelog_path.write_text(
        """Changelog
=========

X.X.X (unreleased)
------------------

* pending change

8.2.5 (2026-07-22)
------------------
"""
    )

    assert main(["check-empty", str(changelog_path)]) == 1


@pytest.mark.unit
@pytest.mark.parametrize("version", ["8.2.6rc1", "8.2", "v8.2.6", "8.2.6.post1"])
def test_insertion_rejects_a_version_no_check_could_find(version: str) -> None:
    """A heading that _RELEASE_TITLE cannot match is invisible to every check.

    ``validate_changelog_order`` would pass over such an entry rather than
    reject it, and the next data update would insert above it instead of
    below - so the ordering guarantee would silently cover only the
    well-formed entries.
    """
    changelog = """Changelog
=========

X.X.X (unreleased)
------------------

8.2.5 (2026-07-22)
------------------
"""

    with pytest.raises(ValueError, match="not a release version"):
        insert_data_release(
            changelog,
            version=version,
            release_date=date(2026, 8, 17),
            data_tag="2026a",
            data_repo_url="https://example.test/data",
        )


@pytest.mark.unit
def test_check_empty_cli_allows_an_empty_unreleased_section(tmp_path) -> None:
    """The exit code that actually releases data was never asserted.

    ``check-empty`` returning 1 for every input would still pass a suite that
    only tests the blocking case, and would silently stop data updates from
    ever being released - a workflow that never merges looks like upstream
    having published nothing.
    """
    changelog_path = tmp_path / "CHANGELOG.rst"
    changelog_path.write_text(
        """Changelog
=========

X.X.X (unreleased)
------------------

Internal:

8.2.5 (2026-07-22)
------------------

* previous release
"""
    )

    assert main(["check-empty", str(changelog_path)]) == 0


@pytest.mark.unit
def test_check_empty_cli_blocks_an_unparsable_changelog(tmp_path) -> None:
    """A changelog the guard cannot parse must block, not release."""
    changelog_path = tmp_path / "CHANGELOG.rst"
    changelog_path.write_text("Changelog\n=========\n\nunstructured prose\n")

    assert main(["check-empty", str(changelog_path)]) == 1


@pytest.mark.unit
def test_check_empty_cli_blocks_a_missing_changelog(tmp_path) -> None:
    """A path that does not exist must block rather than crash the step."""
    assert main(["check-empty", str(tmp_path / "absent.rst")]) == 1


@pytest.mark.unit
def test_committed_changelog_sections_are_in_release_order() -> None:
    validate_changelog_order(
        (PROJECT_ROOT / "CHANGELOG.rst").read_text(encoding="utf-8")
    )


@pytest.mark.unit
def test_changelog_order_rejects_older_release_above_newer_release() -> None:
    changelog = """Changelog
=========

X.X.X (unreleased)
------------------

8.2.4 (2026-07-01)
------------------

8.2.5 (2026-07-22)
------------------
"""

    with pytest.raises(ValueError, match="descending"):
        validate_changelog_order(changelog)


@pytest.mark.unit
def test_insertion_rejects_a_release_date_older_than_the_latest_release() -> None:
    changelog = """Changelog
=========

X.X.X (unreleased)
------------------

8.2.5 (2026-07-22)
------------------
"""

    with pytest.raises(ValueError, match="descending"):
        insert_data_release(
            changelog,
            version="8.2.6",
            release_date=date(2026, 7, 1),
            data_tag="2026a",
            data_repo_url="https://example.test/data",
        )
