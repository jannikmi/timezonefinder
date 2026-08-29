"""Keep contributor memory small, directly linked, and fully reachable."""

import re
from collections import deque
from pathlib import Path

import pytest

from tests.auxiliaries import PROJECT_ROOT

ENTRYPOINT = PROJECT_ROOT / "CONTRIBUTING.md"
MEMORY_ROOT = PROJECT_ROOT / "contributing"
CORE = MEMORY_ROOT / "core-contributor-contract.md"
COMPATIBILITY_FILES = (
    PROJECT_ROOT / "AGENTS.md",
    PROJECT_ROOT / "CLAUDE.md",
    PROJECT_ROOT / ".cursor" / "rules" / "repo-instructions.mdc",
)
ADAPTER_ROOTS = (
    PROJECT_ROOT / ".agents" / "skills",
    PROJECT_ROOT / ".claude" / "skills",
)
LINK = re.compile(r"(?<!!)\[[^]]+\]\(([^)]+)\)")
GENERIC_FILENAMES = {"README.md", "notes.md", "decisions.md"}
CANONICAL_LIMIT = 2_000
FENCE = re.compile(r"^\s*(```|~~~)")
LIST_ITEM = re.compile(r"^\s*(?:[-+*]|\d+\.)\s+")


def words(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").split())


def canonical_files() -> set[Path]:
    return {path.resolve() for path in MEMORY_ROOT.rglob("*.md")}


def checked_files() -> list[Path]:
    adapters = [path for root in ADAPTER_ROOTS for path in root.glob("*/SKILL.md")]
    return [ENTRYPOINT, *MEMORY_ROOT.rglob("*.md"), *COMPATIBILITY_FILES, *adapters]


def local_targets(path: Path) -> set[Path]:
    targets: set[Path] = set()
    for raw in LINK.findall(path.read_text(encoding="utf-8")):
        if raw.startswith(("http://", "https://", "mailto:")):
            continue
        target = raw.split("#", 1)[0]
        if target:
            targets.add((path.parent / target).resolve())
    return targets


def arbitrary_prose_linebreaks(path: Path) -> list[int]:
    violations: list[int] = []
    previous_prose_can_continue = False
    in_fence = False
    in_frontmatter = False

    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if line_number == 1 and line == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if line == "---":
                in_frontmatter = False
            continue
        if FENCE.match(line):
            in_fence = not in_fence
            previous_prose_can_continue = False
            continue
        if in_fence:
            continue

        stripped = line.lstrip()
        if not stripped:
            previous_prose_can_continue = False
            continue
        if LIST_ITEM.match(line):
            previous_prose_can_continue = True
            continue
        if stripped.startswith(
            ("#", "|", ">", "<!--", "<details", "</details", "<summary", "</summary")
        ) or stripped in {
            "---",
            "***",
            "___",
        }:
            previous_prose_can_continue = False
            continue
        if previous_prose_can_continue:
            violations.append(line_number)
        previous_prose_can_continue = True

    return violations


@pytest.mark.unit
def test_local_markdown_links_resolve() -> None:
    for path in checked_files():
        for target in local_targets(path):
            assert target.is_file(), f"{path}: broken local link to {target}"


@pytest.mark.unit
def test_contributor_memory_uses_semantic_linebreaks() -> None:
    for path in checked_files():
        violations = arbitrary_prose_linebreaks(path)
        assert not violations, f"{path}: arbitrary prose wraps at lines {violations}"


@pytest.mark.unit
def test_every_canonical_file_is_reachable_from_entrypoint() -> None:
    canonical = canonical_files()
    seen: set[Path] = set()
    queue: deque[Path] = deque([ENTRYPOINT.resolve()])
    while queue:
        path = queue.popleft()
        if path in seen:
            continue
        seen.add(path)
        for target in local_targets(path):
            if target in canonical and target not in seen:
                queue.append(target)
    assert canonical <= seen, f"orphaned contributor memory: {sorted(canonical - seen)}"


@pytest.mark.unit
def test_memory_names_depth_and_size_budgets() -> None:
    assert words(ENTRYPOINT) <= 800
    assert words(CORE) <= 800
    for path in MEMORY_ROOT.rglob("*.md"):
        assert path.name not in GENERIC_FILENAMES
        assert len(path.relative_to(MEMORY_ROOT).parent.parts) <= 4
        assert words(path) <= CANONICAL_LIMIT, f"{path}: {words(path)} words"
    for path in COMPATIBILITY_FILES:
        assert words(path) <= 100
    for root in ADAPTER_ROOTS:
        for path in root.glob("*/SKILL.md"):
            assert words(path) <= 180


@pytest.mark.unit
def test_routing_rows_require_at_most_three_files() -> None:
    rows = [
        line
        for line in ENTRYPOINT.read_text(encoding="utf-8").splitlines()
        if line.startswith("| ") and not line.startswith(("| Task trigger", "|---"))
    ]
    assert rows
    for row in rows:
        required = row.split("|")[2]
        assert 1 <= len(LINK.findall(required)) <= 3, row


@pytest.mark.unit
def test_canonical_memory_does_not_route_through_compatibility_stubs() -> None:
    forbidden = {path.resolve() for path in COMPATIBILITY_FILES}
    for path in MEMORY_ROOT.rglob("*.md"):
        assert not (local_targets(path) & forbidden), path
