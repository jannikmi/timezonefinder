"""Changelog operations used by release automation."""

from argparse import ArgumentParser
from datetime import date
from pathlib import Path
import re
import sys

_UNRELEASED_HEADING = "X.X.X (unreleased)\n------------------"
_RELEASE_TITLE = re.compile(r"(?m)^\d+\.\d+\.\d+ \((\d{4}-\d{2}-\d{2})\)\n-+$")


def validate_changelog_order(changelog: str) -> None:
    """Require the unreleased section first and dated releases newest-first."""
    release_matches = list(_RELEASE_TITLE.finditer(changelog))
    if not release_matches:
        raise ValueError("changelog has no dated releases")
    if changelog.count(_UNRELEASED_HEADING) != 1:
        raise ValueError("changelog must contain exactly one unreleased section")
    if changelog.index(_UNRELEASED_HEADING) > release_matches[0].start():
        raise ValueError("the unreleased section must be above every dated release")

    release_dates = [date.fromisoformat(match.group(1)) for match in release_matches]
    if release_dates != sorted(release_dates, reverse=True):
        raise ValueError("dated releases must be in descending date order")


def _unreleased_section_end(changelog: str) -> int:
    validate_changelog_order(changelog)
    section_start = changelog.index(_UNRELEASED_HEADING)
    release = _RELEASE_TITLE.search(changelog, section_start + len(_UNRELEASED_HEADING))
    if release is None:
        raise ValueError("changelog has no dated release below the unreleased section")
    return release.start()


def has_pending_unreleased_changes(changelog: str) -> bool:
    """Return whether the unreleased section contains substantive content."""
    section_start = changelog.index(_UNRELEASED_HEADING) + len(_UNRELEASED_HEADING)
    section = changelog[section_start : _unreleased_section_end(changelog)]
    substantive_lines = {
        line.strip()
        for line in section.splitlines()
        if line.strip() and line.strip() != "Internal:"
    }
    return bool(substantive_lines)


def insert_data_release(
    changelog: str,
    *,
    version: str,
    release_date: date,
    data_tag: str,
    data_repo_url: str,
) -> str:
    """Insert a data-release entry after the unreleased section."""
    insertion_point = _unreleased_section_end(changelog)

    title = f"{version} ({release_date.isoformat()})"
    # Everything below recognises a release by _RELEASE_TITLE, so a version
    # this pattern does not match would be inserted as text no check can see:
    # validate_changelog_order() would pass over it, the next data update would
    # insert above it rather than below, and the ordering guarantee would hold
    # only over the entries that happen to be well-formed.
    if not _RELEASE_TITLE.fullmatch(f"{title}\n{'-' * len(title)}"):
        raise ValueError(
            f"{version!r} is not a release version: a changelog heading must "
            "read <major>.<minor>.<patch>, or nothing downstream can find it"
        )
    entry = (
        f"{title}\n{'-' * len(title)}\n\n"
        f"* updated the data to `{data_tag} "
        f"<{data_repo_url}/releases/tag/{data_tag}>`__\n\n"
    )
    updated = changelog[:insertion_point] + entry + changelog[insertion_point:]
    validate_changelog_order(updated)
    return updated


def main(argv: list[str] | None = None) -> int:
    """Run changelog checks and edits for the release scripts."""
    parser = ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_parser = subparsers.add_parser("check-empty")
    check_parser.add_argument("changelog", type=Path)

    insert_parser = subparsers.add_parser("insert-data-release")
    insert_parser.add_argument("changelog", type=Path)
    insert_parser.add_argument("--version", required=True)
    insert_parser.add_argument("--date", type=date.fromisoformat, required=True)
    insert_parser.add_argument("--data-tag", required=True)
    insert_parser.add_argument("--data-repo-url", required=True)

    args = parser.parse_args(argv)
    try:
        changelog = args.changelog.read_text(encoding="utf-8")
        if args.command == "check-empty":
            if has_pending_unreleased_changes(changelog):
                print(
                    "pending work exists under X.X.X (unreleased); "
                    "cut a release before auto-releasing data",
                    file=sys.stderr,
                )
                return 1
            return 0

        updated = insert_data_release(
            changelog,
            version=args.version,
            release_date=args.date,
            data_tag=args.data_tag,
            data_repo_url=args.data_repo_url,
        )
        args.changelog.write_text(updated, encoding="utf-8")
        return 0
    except (OSError, ValueError) as error:
        print(f"cannot process {args.changelog}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
