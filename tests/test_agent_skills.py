"""Validate the paired provider adapters that discover canonical workflows."""

from pathlib import Path

import pytest
import yaml

from tests.auxiliaries import PROJECT_ROOT

PROVIDER_DIRS = (
    PROJECT_ROOT / ".agents" / "skills",
    PROJECT_ROOT / ".claude" / "skills",
)
FRONTMATTER_DELIMITER = "---"


def skill_files(root: Path) -> dict[str, Path]:
    return {path.parent.name: path for path in sorted(root.glob("*/SKILL.md"))}


def split_frontmatter(text: str) -> str:
    lines = text.splitlines()
    assert lines and lines[0].strip() == FRONTMATTER_DELIMITER
    end = next(
        i
        for i, line in enumerate(lines[1:], start=1)
        if line.strip() == FRONTMATTER_DELIMITER
    )
    return "\n".join(lines[1:end])


@pytest.mark.unit
def test_provider_skill_sets_are_paired() -> None:
    left, right = (skill_files(root) for root in PROVIDER_DIRS)
    assert left and left.keys() == right.keys()
    for name in left:
        assert left[name].read_bytes() == right[name].read_bytes(), name


@pytest.mark.unit
@pytest.mark.parametrize("provider_dir", PROVIDER_DIRS, ids=lambda p: p.parent.name)
def test_adapters_have_valid_frontmatter_and_canonical_target(
    provider_dir: Path,
) -> None:
    files = skill_files(provider_dir)
    assert files
    for name, path in files.items():
        text = path.read_text(encoding="utf-8")
        metadata = yaml.safe_load(split_frontmatter(text))
        assert metadata["name"] == name
        assert metadata["description"].strip()
        assert text.count("contributing/workflows/") == 1
        target_text = text.split("](", 2)[-1].split(")", 1)[0]
        assert (path.parent / target_text).resolve().is_file()
