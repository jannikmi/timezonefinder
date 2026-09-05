"""Keep ruff's configured rule set and its one exemption from silently doing nothing.

Two things here fail open rather than loudly, which is why they are asserted rather
than left to review:

`[tool.ruff.lint] select` *replaces* ruff's default rule set instead of extending it,
so dropping `F` from the list disables every undefined-name and unused-import check
without failing anything - `make hook` goes green faster and nobody sees why.

`[tool.ruff.lint] exclude` needs a glob: a bare `"prototypes"` is accepted, matches no
file, and leaves the directory linted, where the top-level `exclude` does honour a bare
directory name. The failure is the other direction of the same problem - the exemption
looks configured and is not - and it is invisible until someone wonders why exploratory
code is being held to the rules.
"""

import subprocess
import sys
import tomllib

import pytest

from tests.auxiliaries import PROJECT_ROOT

PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"
PRE_COMMIT_CONFIG_PATH = PROJECT_ROOT / ".pre-commit-config.yaml"

# ruff lints these unless a `select` replaces them; see the module docstring.
RUFF_DEFAULT_SELECT = ("E4", "E7", "E9", "F")

# A file under the exempted directory that ruff has something to say about, so the
# control below can establish that the exemption is what silences it.
EXEMPT_SAMPLE = "prototypes/query_stage_profile.py"


def _lint_config() -> dict:
    with open(PYPROJECT_PATH, "rb") as f:
        return tomllib.load(f)["tool"]["ruff"]["lint"]


def _ruff(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--no-cache", "--quiet", *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )


@pytest.mark.unit
def test_the_default_rules_survive_the_explicit_select():
    """Naming a `select` replaces ruff's defaults, so they have to be named again."""
    selected = _lint_config()["select"]
    missing = [rule for rule in RUFF_DEFAULT_SELECT if rule not in selected]
    assert not missing, (
        f"{missing} dropped from [tool.ruff.lint] select. `select` replaces ruff's "
        "default rule set rather than adding to it, so removing one of these turns "
        "the check off everywhere and fails nothing."
    )


@pytest.mark.unit
def test_the_exploratory_code_exemption_actually_exempts():
    """A pattern that matches nothing is accepted and reads exactly like one that works.

    The control run is the half that matters: without it this test also passes when
    `prototypes/` simply has no findings, which would make it stop covering the
    exemption on the day the sample file is cleaned up.
    """
    exempted = _ruff("--force-exclude", EXEMPT_SAMPLE)
    control = _ruff("--force-exclude", "--config", "lint.exclude=[]", EXEMPT_SAMPLE)

    assert control.stdout.strip(), (
        f"{EXEMPT_SAMPLE} no longer produces any finding, so this test can no longer "
        "tell a working exemption from a pattern that matches nothing. Point "
        "EXEMPT_SAMPLE at a file under the exempted directory that ruff still reports."
    )
    assert not exempted.stdout.strip(), (
        "[tool.ruff.lint] exclude is not excluding "
        f"{EXEMPT_SAMPLE}:\n{exempted.stdout}\n"
        "A bare directory name is accepted here and matches nothing - the pattern "
        "needs the glob, as `prototypes/*`."
    )


@pytest.mark.unit
def test_the_hook_does_not_carry_a_second_exclusion():
    """One statement of what is linted, so a bare run and the hook cannot disagree.

    The ruff pre-commit hook passes `--force-exclude`, which is what makes it honour
    `[tool.ruff.lint] exclude`; an `exclude:` on the hook would be a second, silently
    diverging copy of the same list.
    """
    config = PRE_COMMIT_CONFIG_PATH.read_text()
    ruff_hook = config.split("- id: ruff\n", 1)[1].split("- id:", 1)[0]
    assert "exclude:" not in ruff_hook, (
        "The ruff hook carries its own `exclude:`. What is linted is stated in "
        "[tool.ruff.lint] in pyproject.toml so that `uv run ruff check` and the hook "
        "cannot drift; a hook-local copy reintroduces exactly that drift."
    )
