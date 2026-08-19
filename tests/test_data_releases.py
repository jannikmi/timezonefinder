"""Regression tests for the release list of the data distribution."""

from datetime import date

import pytest

from scripts.configs import DATA_RELEASES_FILE
from scripts.data_releases import (
    RELEASES_HEADING,
    insert_data_release,
    main,
    validate_release_order,
)

PREVIOUS_RELEASE = (
    "- `1.2026.3` - timezone-boundary-builder "
    "[2026c](https://example.test/data/releases/tag/2026c), 2026-08-18\n"
)


def _releases(entries: str = PREVIOUS_RELEASE) -> str:
    """Build a README whose release list holds ``entries``."""
    return (
        "# timezonefinder-data\n\nprose about the distribution\n\n"
        f"{RELEASES_HEADING}\n\n{entries}\n## License\n\nODbL\n"
    )


def _insert(
    readme: str, *, version: str = "1.2026.4", release_date: date = date(2026, 9, 1)
) -> str:
    return insert_data_release(
        readme,
        version=version,
        release_date=release_date,
        data_tag="2026d",
        data_repo_url="https://example.test/data",
    )


@pytest.mark.unit
def test_a_data_release_is_prepended_to_the_list() -> None:
    """Newest first: the list is read top-down by someone choosing a dataset to pin."""
    inserted = (
        "- `1.2026.4` - timezone-boundary-builder "
        "[2026d](https://example.test/data/releases/tag/2026d), 2026-09-01\n"
    )

    assert _insert(_releases()) == _releases(inserted + PREVIOUS_RELEASE)


@pytest.mark.unit
@pytest.mark.parametrize("version", ["1.2026.4rc1", "1.2026", "v1.2026.4", "2026d"])
def test_insertion_rejects_a_version_no_later_check_could_find(version: str) -> None:
    """An entry the release pattern cannot match is invisible to every check.

    ``validate_release_order`` would pass over such a line rather than reject it, and
    the next data update would insert above it instead of below - so the ordering
    guarantee would silently cover only the well-formed entries.
    """
    with pytest.raises(ValueError, match="not a data distribution version"):
        _insert(_releases(), version=version)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("version", "data_tag"),
    [("1.2026.3", "2026d"), ("1.2026.4", "2026c"), ("1.2026.3", "2026c")],
    ids=["same-version", "same-tag", "both"],
)
def test_insertion_rejects_a_release_already_listed(
    version: str, data_tag: str
) -> None:
    """A re-run of the data update must not record the release a second time.

    Re-running ``update_data.sh`` over an unchanged upstream release derives the same
    version and the same date, and equal dates pass the descending-order check - so
    nothing else here would notice the duplicate, in the text that is the
    distribution's PyPI page.
    """
    with pytest.raises(ValueError, match="already has an entry"):
        insert_data_release(
            _releases(),
            version=version,
            release_date=date(2026, 9, 1),
            data_tag=data_tag,
            data_repo_url="https://example.test/data",
        )


@pytest.mark.unit
def test_insertion_rejects_a_date_older_than_the_latest_release() -> None:
    with pytest.raises(ValueError, match="descending"):
        _insert(_releases(), release_date=date(2026, 1, 1))


@pytest.mark.unit
@pytest.mark.parametrize(
    "readme",
    [
        "# timezonefinder-data\n\nno release list at all\n",
        f"# timezonefinder-data\n\n{RELEASES_HEADING}\n\nnothing listed yet\n",
        # the heading below its own entries: the insertion point would land outside
        # the section it belongs to
        f"{PREVIOUS_RELEASE}\n{RELEASES_HEADING}\n",
    ],
)
def test_insertion_refuses_a_list_it_cannot_read(readme: str) -> None:
    with pytest.raises(ValueError):
        _insert(readme)


@pytest.mark.unit
def test_the_cli_records_a_release(tmp_path) -> None:
    releases = tmp_path / "README.md"
    releases.write_text(_releases())

    exit_code = main(
        [
            "insert-data-release",
            str(releases),
            "--version",
            "1.2026.4",
            "--date",
            "2026-09-01",
            "--data-tag",
            "2026d",
            "--data-repo-url",
            "https://example.test/data",
        ]
    )

    assert exit_code == 0
    assert "`1.2026.4`" in releases.read_text()


@pytest.mark.unit
@pytest.mark.parametrize("content", [None, "# timezonefinder-data\n\nunstructured\n"])
def test_the_cli_reports_what_it_cannot_read(tmp_path, content) -> None:
    """A release list the tool cannot parse must fail, not write something arbitrary."""
    releases = tmp_path / "README.md"
    if content is not None:
        releases.write_text(content)

    assert (
        main(
            [
                "insert-data-release",
                str(releases),
                "--version",
                "1.2026.4",
                "--date",
                "2026-09-01",
                "--data-tag",
                "2026d",
                "--data-repo-url",
                "https://example.test/data",
            ]
        )
        == 1
    )


@pytest.mark.unit
def test_the_committed_release_list_is_in_release_order() -> None:
    validate_release_order(DATA_RELEASES_FILE.read_text(encoding="utf-8"))
