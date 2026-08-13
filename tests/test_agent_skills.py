"""Assert the agent skills under ``.claude/skills/`` keep usable frontmatter.

A skill is discovered by its ``description``: the loader matches a request
against that text, so a description that arrives truncated or empty makes the
skill reachable only by name. Nothing surfaces that - the file still parses,
the skill still loads, and the only symptom is that it stops being suggested.

The truncation is easy to write by accident, because these descriptions name
issues. In a plain (unquoted) YAML scalar a ``#`` preceded by a space starts a
comment, so ``description: ... roadmap issue #506 by one pass ...`` stores the
five words before ``#506`` and silently discards the rest.
"""

from pathlib import Path

import pytest
import yaml

from tests.auxiliaries import PROJECT_ROOT

SKILLS_DIR = PROJECT_ROOT / ".claude" / "skills"
FRONTMATTER_DELIMITER = "---"

SKILL_FILES = sorted(SKILLS_DIR.glob("*/SKILL.md"))


def split_frontmatter(text: str) -> str:
    """Return the YAML frontmatter block of a skill file, without its delimiters."""
    lines = text.splitlines()
    assert lines and lines[0].strip() == FRONTMATTER_DELIMITER, (
        "a skill file must open with a YAML frontmatter delimiter"
    )
    end = next(
        i
        for i, line in enumerate(lines[1:], start=1)
        if line.strip() == FRONTMATTER_DELIMITER
    )
    return "\n".join(lines[1:end])


def raw_field(frontmatter: str, key: str) -> str:
    """Return the literal characters a frontmatter key spans, quoting and all.

    Continuation lines of a folded scalar are included; the block ends at the
    next top-level key. This is what the parsed value is compared against, so
    that dropped text shows up as a mismatch rather than as valid YAML.
    """
    lines = frontmatter.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(f"{key}:"))
    block = [lines[start][len(key) + 1 :]]
    for line in lines[start + 1 :]:
        if line and not line[0].isspace():
            break
        block.append(line)
    return " ".join(part.strip() for part in block).strip()


@pytest.fixture(scope="module")
def skill_files() -> list[Path]:
    assert SKILL_FILES, f"no skill files found under {SKILLS_DIR}"
    return SKILL_FILES


@pytest.mark.unit
def test_skills_exist(skill_files: list[Path]) -> None:
    # guards the parametrisation below: an empty glob would make every case vacuous
    assert len(skill_files) >= 1


@pytest.mark.unit
@pytest.mark.parametrize("skill_file", SKILL_FILES, ids=lambda p: p.parent.name)
def test_frontmatter_declares_name_and_description(skill_file: Path) -> None:
    metadata = yaml.safe_load(split_frontmatter(skill_file.read_text(encoding="utf-8")))
    assert isinstance(metadata, dict), "frontmatter must parse to a mapping"
    assert metadata.get("name") == skill_file.parent.name, (
        "the declared name must match the directory the skill is invoked by"
    )
    assert metadata.get("description", "").strip(), (
        "a skill without a description is undiscoverable"
    )


@pytest.mark.unit
@pytest.mark.parametrize("skill_file", SKILL_FILES, ids=lambda p: p.parent.name)
def test_description_is_not_silently_truncated(skill_file: Path) -> None:
    """The parsed description must end where the file does, not at a stray ``#``."""
    text = skill_file.read_text(encoding="utf-8")
    frontmatter = split_frontmatter(text)
    parsed = yaml.safe_load(frontmatter)["description"]
    written = raw_field(frontmatter, "description").strip("\"'")
    assert parsed.split()[-1] == written.split()[-1], (
        f"{skill_file.parent.name}: the description stored by a YAML parser ends at "
        f"{parsed.split()[-1]!r} but the file writes {written.split()[-1]!r} - "
        "an unquoted ' #' starts a YAML comment; quote the scalar"
    )
