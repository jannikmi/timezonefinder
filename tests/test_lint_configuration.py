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

# One rule out of each default rule group that `select` actually governs, with a
# snippet that breaks it. Checked by linting the snippet, so the test covers whether
# the rule still fires rather than whether its name still appears in the config; see
# the module docstring.
#
# E9 is deliberately absent: ruff reports a syntax error as `invalid-syntax` whatever
# is selected, so there is nothing for a `select` to switch off and nothing to probe.
DEFAULT_RULE_PROBES = {
    "E402": "import os\nx = 1\nimport sys\n",  # E4, module import not at top of file
    "E711": "x = 1\nif x == None:\n    pass\n",  # E7, comparison to None
    "F821": "undefined_name_probe()\n",  # F, undefined name
}

# A file under the exempted directory that ruff has something to say about, so the
# control below can establish that the exemption is what silences it.
EXEMPT_SAMPLE = "prototypes/query_stage_profile.py"


def _lint_config() -> dict:
    with open(PYPROJECT_PATH, "rb") as f:
        return tomllib.load(f)["tool"]["ruff"]["lint"]


def _ruff(*args: str, input: str | None = None) -> subprocess.CompletedProcess:
    """Run ruff, and fail with ruff's own message rather than an empty result.

    ruff is in the `dev` dependency group and pytest is in `test`, so an environment
    holding only `test` runs these tests without ruff. Without this check that shows up
    as empty output, which every assertion below would misread as "no findings".
    """
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--no-cache", "--quiet", *args],
        cwd=PROJECT_ROOT,
        input=input,
        capture_output=True,
        text=True,
    )
    # ruff exits 1 when it reports findings, which is the normal case here; anything
    # above that, or a failure with nothing on stdout, is the tool and not the tree.
    if result.returncode > 1 or (result.returncode == 1 and not result.stdout.strip()):
        raise AssertionError(
            f"`ruff check {' '.join(args)}` failed (exit {result.returncode}) rather "
            f"than reporting on the tree:\n{result.stderr or result.stdout}"
        )
    return result


@pytest.mark.unit
def test_the_default_rules_survive_the_explicit_select():
    """Naming a `select` replaces ruff's defaults, so they have to be named again.

    Asserted by linting code that breaks each default rule rather than by reading
    `select` out of the TOML: the coverage can be switched off by `ignore`, by a
    `per-file-ignores` entry or by a shadowing selector, none of which a config read
    would notice. What must hold is that the rule still fires, not that a string is
    still present.
    """
    for rule, offending_source in DEFAULT_RULE_PROBES.items():
        reported = _ruff("--stdin-filename", "probe.py", "-", input=offending_source)
        assert rule in reported.stdout, (
            f"{rule} is not reported on code that breaks it, so that check is off. "
            "`select` replaces ruff's default rule set rather than adding to it, and "
            "`ignore` / `per-file-ignores` can switch a selected rule off again - none "
            f"of which fails anything else.\nruff said: {reported.stdout!r}"
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
    assert "--no-force-exclude" not in ruff_hook, (
        "The ruff hook passes `--no-force-exclude`, which makes it lint the paths "
        "pre-commit hands it regardless of [tool.ruff.lint] exclude. `make hook` would "
        "then lint `prototypes/` while a bare `uv run ruff check` does not, and every "
        "other assertion in this file would stay green."
    )
