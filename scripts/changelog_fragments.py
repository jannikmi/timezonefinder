#!/usr/bin/env python3

"""Assemble ``CHANGELOG.rst``'s unreleased section from per-change fragments.

Every non-exempt change used to edit one file at one place, and internal
changes all appended at the same ``Internal:`` boundary. That made the
unreleased section the repository's last routine cross-change merge hotspot:
independently authored work contends on a release artifact whose curation is
needed once, at release time, and not before.

A change now drops one file into ``changelog.d/user/`` or
``changelog.d/internal/`` instead. The directory carries the placement, so no
fragment has to say where it goes and no two fragments touch the same lines.
``--assemble`` folds them into the unreleased section and deletes them; the
release then performs the end-state rewrite the changelog policy has always
required, on a section that already holds every bullet.

``CHANGELOG.rst`` stays the published artifact - it is what ``README.rst``
includes and what ships - so nothing downstream learns about fragments.
"""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Iterable, Sequence

REPO_ROOT: Final[Path] = Path(__file__).resolve().parent.parent
FRAGMENT_ROOT: Final[Path] = REPO_ROOT / "changelog.d"
CHANGELOG_PATH: Final[Path] = REPO_ROOT / "CHANGELOG.rst"

#: Directory name -> where the bullet lands. Ordered, and the order is the
#: rendered order: the changelog policy puts user-visible changes in the main
#: list and development-only ones under ``Internal:``.
CATEGORIES: Final[tuple[str, ...]] = ("user", "internal")
FRAGMENT_SUFFIX: Final[str] = ".rst"
#: Files allowed to sit at the fragment root without being fragments.
ROOT_ALLOWLIST: Final[frozenset[str]] = frozenset({"README.md"})
#: Kept in each category directory so an empty one survives a clone.
KEEP_FILE: Final[str] = ".gitkeep"

UNRELEASED_HEADING: Final[str] = "X.X.X (unreleased)"
INTERNAL_MARKER: Final[str] = "Internal:"


def _display(path: Path) -> str:
    """A path relative to the repository when it is inside one.

    The tests point the loader at a temporary directory, and a message is not
    worth an exception: the point of every one of them is to name the file.
    """
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


class FragmentError(Exception):
    """A fragment that cannot be rendered, named with the reason."""


@dataclass(frozen=True)
class Fragment:
    """One changelog bullet, waiting for the next release to consume it."""

    category: str
    path: Path
    text: str

    @property
    def identity(self) -> str:
        """What makes two fragments the same change.

        The stem rather than the whole path, so the same slug filed under both
        categories is a conflict rather than two bullets describing one change
        in two places.
        """
        return self.path.stem


def load_fragments(root: Path = FRAGMENT_ROOT) -> list[Fragment]:
    """Every fragment under ``root``, validated and deterministically ordered.

    Raises :class:`FragmentError` rather than skipping anything: a fragment
    silently dropped is a change that reaches a release with no changelog
    entry, which is the failure the policy exists to prevent.
    """
    if not root.is_dir():
        return []

    _reject_unclassified(root)

    fragments: list[Fragment] = []
    for category in CATEGORIES:
        directory = root / category
        if not directory.is_dir():
            continue
        for path in sorted(directory.iterdir(), key=lambda p: p.name):
            if path.name == KEEP_FILE:
                continue
            fragments.append(Fragment(category, path, _read_fragment(path)))

    _reject_duplicates(fragments)
    return fragments


def _reject_unclassified(root: Path) -> None:
    """Nothing may sit outside a category directory or in an unknown one."""
    for entry in sorted(root.iterdir(), key=lambda p: p.name):
        if entry.is_dir():
            if entry.name not in CATEGORIES:
                raise FragmentError(
                    f"{_display(entry)}: unknown category directory; "
                    f"expected one of {', '.join(CATEGORIES)}"
                )
        elif entry.name not in ROOT_ALLOWLIST:
            raise FragmentError(
                f"{_display(entry)}: unclassified fragment; "
                f"file it under {'/ or '.join(CATEGORIES)}/ instead"
            )


def _read_fragment(path: Path) -> str:
    if path.suffix != FRAGMENT_SUFFIX:
        raise FragmentError(
            f"{_display(path)}: fragments are plain RST and must "
            f"end in {FRAGMENT_SUFFIX}"
        )

    lines = [line.rstrip() for line in path.read_text(encoding="utf-8").splitlines()]
    body = [line for line in lines if line]
    if not body:
        raise FragmentError(f"{_display(path)}: empty fragment")
    if len(body) > 1:
        # One bullet per fragment, one line per bullet: the changelog is not
        # hard-wrapped, so a wrapped fragment would reflow the whole bullet on
        # the next small edit - and a fragment holding two paragraphs is two
        # changes filed as one.
        raise FragmentError(
            f"{_display(path)}: a fragment is exactly one bullet on "
            f"one line, got {len(body)} lines"
        )

    text = body[0].strip()
    if text.startswith("* "):
        raise FragmentError(
            f"{_display(path)}: write the bullet text only; the "
            f"'* ' marker is added when the fragment is assembled"
        )
    return text


def _reject_duplicates(fragments: Sequence[Fragment]) -> None:
    seen: dict[str, Fragment] = {}
    for fragment in fragments:
        clash = seen.get(fragment.identity)
        if clash is not None:
            raise FragmentError(
                f"{_display(fragment.path)} and "
                f"{_display(clash.path)} name the same change"
            )
        seen[fragment.identity] = fragment


def render_bullets(fragments: Iterable[Fragment], category: str) -> list[str]:
    """The ``* …`` lines one category contributes, in fragment order."""
    return [f"* {f.text}" for f in fragments if f.category == category]


def assemble(changelog_text: str, fragments: Sequence[Fragment]) -> str:
    """``changelog_text`` with every fragment folded into its unreleased section.

    Additive by construction: existing bullets are never rewritten, reordered
    or re-wrapped, so assembling into a section that already holds curated text
    leaves that text byte-identical and appends beneath it. The release's
    end-state rewrite is a separate, deliberate act.
    """
    lines = changelog_text.splitlines()
    start, end = _unreleased_bounds(lines)
    section = lines[start:end]

    internal_at = next(
        (i for i, line in enumerate(section) if line.strip() == INTERNAL_MARKER),
        None,
    )
    user_bullets = render_bullets(fragments, "user")
    internal_bullets = render_bullets(fragments, "internal")

    if internal_at is None:
        head, tail = section, []
    else:
        head, tail = section[:internal_at], section[internal_at:]

    head = _append_bullets(head, user_bullets)
    if internal_bullets:
        if not tail:
            tail = ["", INTERNAL_MARKER, ""]
        tail = _append_bullets(tail, internal_bullets)

    rebuilt = lines[:start] + _tidy(head + tail) + lines[end:]
    return "\n".join(rebuilt) + "\n"


def _unreleased_bounds(lines: Sequence[str]) -> tuple[int, int]:
    """Index range of the unreleased section's *body*, heading excluded."""
    for index, line in enumerate(lines):
        if line.strip() != UNRELEASED_HEADING:
            continue
        underline = index + 1
        if underline >= len(lines) or not set(lines[underline]) == {"-"}:
            break
        start = underline + 1
        for offset in range(start, len(lines) - 1):
            if set(lines[offset + 1]) == {"-"} and lines[offset].strip():
                return start, offset
        return start, len(lines)
    raise FragmentError(
        f"{CHANGELOG_PATH.name} has no '{UNRELEASED_HEADING}' section to assemble into"
    )


def _append_bullets(block: list[str], bullets: list[str]) -> list[str]:
    if not bullets:
        return block
    trimmed = list(block)
    while trimmed and not trimmed[-1].strip():
        trimmed.pop()
    # a bullet list follows a heading-like line (``Internal:``) after a blank
    # line, and follows another bullet immediately
    if trimmed and not trimmed[-1].startswith("* "):
        trimmed.append("")
    return trimmed + bullets


def _tidy(section: list[str]) -> list[str]:
    """One trailing blank line, whatever the section started or ended with."""
    while section and not section[0].strip():
        section.pop(0)
    while section and not section[-1].strip():
        section.pop()
    return ["", *section, "", ""] if section else ["", ""]


def _preview(fragments: Sequence[Fragment]) -> str:
    """The unreleased section as it would read once assembled."""
    heading = [UNRELEASED_HEADING, "-" * len(UNRELEASED_HEADING)]
    if not fragments:
        return "\n".join([*heading, ""])
    body = assemble(
        "\n".join([*heading, "", ""]),
        fragments,
    ).splitlines()
    return "\n".join(body)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate every fragment and exit; prints nothing when they are sound",
    )
    parser.add_argument(
        "--require-consumed",
        action="store_true",
        help=(
            "additionally fail when any fragment is still present - the release "
            "check, since a fragment left behind is a bullet that never ships"
        ),
    )
    parser.add_argument(
        "--assemble",
        action="store_true",
        help="fold the fragments into CHANGELOG.rst and delete them",
    )
    args = parser.parse_args(argv)

    try:
        fragments = load_fragments()
    except FragmentError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    if args.require_consumed and fragments:
        listed = ", ".join(_display(f.path) for f in fragments)
        print(f"error: unconsumed changelog fragments: {listed}", file=sys.stderr)
        return 1

    if args.check:
        return 0

    if not args.assemble:
        print(_preview(fragments))
        return 0

    if not fragments:
        print("no changelog fragments to assemble")
        return 0

    CHANGELOG_PATH.write_text(
        assemble(CHANGELOG_PATH.read_text(encoding="utf-8"), fragments),
        encoding="utf-8",
    )
    for fragment in fragments:
        fragment.path.unlink()
    print(f"assembled {len(fragments)} fragment(s) into {CHANGELOG_PATH.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
