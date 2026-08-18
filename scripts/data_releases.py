"""The release list of the ``timezonefinder-data`` distribution.

A data release is recorded in that package's own README (``## Releases``) and nowhere
else. The root ``CHANGELOG.rst`` describes ``timezonefinder`` and is not touched by a
data update at all - which is the point of the split: the two release
streams must not be able to block each other, and a dated ``timezonefinder`` section
for a release that was never published is worse than no entry.

The README *is* the distribution's PyPI long description, so this list is what a user
comparing dataset versions actually reads.
"""

from argparse import ArgumentParser
from datetime import date
from pathlib import Path
import re
import sys

from scripts.configs import DATA_RELEASES_FILE, data_distribution_version

RELEASES_HEADING = "## Releases"

# One line of the release list, mapping a distribution version to the upstream release
# it was built from. Everything below recognises an entry by this pattern, so an entry
# it cannot match is invisible: the ordering check would pass over it and the next
# update would insert above it rather than below.
_RELEASE_ENTRY = re.compile(
    r"(?m)^- `(?P<version>\d+\.\d+\.\d+)` - timezone-boundary-builder "
    r"\[(?P<tag>[^\]]+)\]\((?P<url>[^)]+)\), (?P<date>\d{4}-\d{2}-\d{2})$"
)


def validate_release_order(readme: str) -> None:
    """Require a release list that exists and runs newest-first.

    Ordered by date rather than by version: within a format generation the two agree,
    but the version's leading component is the *format* generation, so it deliberately
    does not sort by data recency across a format bump.

    :raises ValueError: if the list is missing, empty, or out of order.
    """
    if readme.count(RELEASES_HEADING) != 1:
        raise ValueError(
            f"the release list must have exactly one {RELEASES_HEADING!r} heading"
        )

    entries = list(_RELEASE_ENTRY.finditer(readme))
    if not entries:
        raise ValueError("the release list contains no releases")
    if readme.index(RELEASES_HEADING) > entries[0].start():
        raise ValueError("every release must be listed below the heading")

    dates = [date.fromisoformat(entry.group("date")) for entry in entries]
    if dates != sorted(dates, reverse=True):
        raise ValueError("releases must be in descending date order")


def insert_data_release(
    readme: str,
    *,
    version: str,
    release_date: date,
    data_tag: str,
    data_repo_url: str,
) -> str:
    """Prepend a data release to the list, keeping it newest-first."""
    validate_release_order(readme)

    entry = (
        f"- `{version}` - timezone-boundary-builder "
        f"[{data_tag}]({data_repo_url}/releases/tag/{data_tag}), "
        f"{release_date.isoformat()}\n"
    )
    if not _RELEASE_ENTRY.fullmatch(entry.rstrip("\n")):
        raise ValueError(
            f"{version!r} is not a data distribution version: an entry must read "
            "<format>.<year>.<letter>, or nothing downstream can find it"
        )

    # above the current newest entry, which is where the heading's own text ends up
    # pointing - inserting after the heading instead would have to guess how many
    # blank lines separate the two
    insertion_point = _RELEASE_ENTRY.search(readme).start()  # type: ignore[union-attr]
    updated = readme[:insertion_point] + entry + readme[insertion_point:]
    validate_release_order(updated)
    return updated


def main(argv: list[str] | None = None) -> int:
    """Record a data release for the release automation."""
    parser = ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    # update_data.sh needs the version before it can set or record it, and deriving it
    # in shell would be a second implementation of the base-26 rule
    derive_parser = subparsers.add_parser("derive-version")
    derive_parser.add_argument("--data-tag", required=True)

    insert_parser = subparsers.add_parser("insert-data-release")
    # defaulted, so that no caller restates where the release list lives
    insert_parser.add_argument(
        "releases", type=Path, nargs="?", default=DATA_RELEASES_FILE
    )
    insert_parser.add_argument("--version", required=True)
    insert_parser.add_argument("--date", type=date.fromisoformat, required=True)
    insert_parser.add_argument("--data-tag", required=True)
    insert_parser.add_argument("--data-repo-url", required=True)

    args = parser.parse_args(argv)
    if args.command == "derive-version":
        try:
            print(data_distribution_version(args.data_tag))
            return 0
        except ValueError as error:
            print(error, file=sys.stderr)
            return 1

    try:
        releases = args.releases.read_text(encoding="utf-8")
        updated = insert_data_release(
            releases,
            version=args.version,
            release_date=args.date,
            data_tag=args.data_tag,
            data_repo_url=args.data_repo_url,
        )
        args.releases.write_text(updated, encoding="utf-8")
        return 0
    except (OSError, ValueError) as error:
        print(f"cannot process {args.releases}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
