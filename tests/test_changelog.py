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
