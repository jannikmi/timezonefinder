"""The build workflow's aggregate gate is the one check branch protection requires.

Requiring the gate jobs themselves does not survive: ``test``'s check name carries its
matrix values, so renaming an interpreter renames a required check, and GitHub then
waits for a context nothing produces - or, once protection is edited to match, gates on
whatever the new list happens to name. ``ci-ok`` is a fixed name in front of that.

Its weakness is the ``needs`` list: a job added to the workflow and not listed there
produces no signal the required check can miss, which is indistinguishable from passing.
That is what is asserted here - not the shell of any step, which would fail on rewording
and pass on every bug that keeps the wording.
"""

import pytest
import yaml

from tests.auxiliaries import WORKFLOW_DIR

# the expression evaluator for `if:` conditions lives with the release-stream tests;
# re-implementing it here would be a second model of the same GitHub semantics
from tests.test_release_workflows import _simulate, _workflow

BUILD_WORKFLOW = WORKFLOW_DIR / "build.yml"
GATE_JOB = "ci-ok"
# jobs that publish; they run on tag refs only and are downstream of the gate
PUBLISHING_ACTIONS = ("pypa/gh-action-pypi-publish", "ncipollo/release-action")


def _jobs() -> dict[str, dict]:
    return yaml.safe_load(BUILD_WORKFLOW.read_text(encoding="utf-8"))["jobs"]


def _publishes(job: dict) -> bool:
    return any(
        str(step.get("uses", "")).startswith(PUBLISHING_ACTIONS)
        for step in job.get("steps", [])
    )


@pytest.mark.unit
def test_gate_job_aggregates_every_non_publishing_job() -> None:
    jobs = _jobs()
    assert GATE_JOB in jobs
    expected = {
        name for name, job in jobs.items() if name != GATE_JOB and not _publishes(job)
    }
    assert set(jobs[GATE_JOB]["needs"]) == expected


@pytest.mark.unit
def test_gate_job_fails_when_a_dependency_did_not_succeed() -> None:
    gate = _jobs()[GATE_JOB]
    # it has to run even when a dependency failed, or a red matrix leaves the required
    # check skipped rather than failing
    assert gate["if"].startswith("always()")
    conditions = " ".join(str(step.get("if", "")) for step in gate["steps"])
    for result in ("failure", "cancelled", "skipped"):
        assert f"'{result}'" in conditions


@pytest.mark.unit
def test_the_gate_still_runs_when_a_dependency_failed() -> None:
    """Skipped is not neutral: branch protection counts a skipped required check as met.

    A gate that steps aside when a dependency fails would report the one state that lets
    the merge through. It has to run and fail instead - running is what is modelled here,
    failing is the step condition asserted above.
    """
    results = _simulate(
        _workflow(BUILD_WORKFLOW), "refs/heads/master", frozenset({"test"})
    )
    assert results[GATE_JOB] != "skipped"
    assert results["test"] == "failure"
