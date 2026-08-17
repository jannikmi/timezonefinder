"""Protect the automated data-release workflow from unrelated pending work."""

import pytest
import yaml

from tests.auxiliaries import PROJECT_ROOT

UPDATE_SCRIPT = PROJECT_ROOT / "update_data.sh"
RELEASE_WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "release_data_update.yml"
RESOLVE_ACTION = (
    PROJECT_ROOT / ".github" / "actions" / "resolve-update-pr" / "action.yml"
)
RESOLVE_ACTION_REF = "./.github/actions/resolve-update-pr"


def _workflow() -> dict:
    return yaml.safe_load(RELEASE_WORKFLOW.read_text(encoding="utf-8"))


def _release_steps() -> list[dict]:
    return _workflow()["jobs"]["merge_and_release"]["steps"]


def _all_steps() -> list[dict]:
    return [step for job in _workflow()["jobs"].values() for step in job["steps"]]


def _resolve_action_script() -> str:
    action = yaml.safe_load(RESOLVE_ACTION.read_text(encoding="utf-8"))
    return action["runs"]["steps"][0]["run"]


@pytest.mark.unit
def test_update_script_inserts_data_entry_with_changelog_helper() -> None:
    script = UPDATE_SCRIPT.read_text(encoding="utf-8")

    assert "python -m scripts.changelog insert-data-release" in script
    assert 'head -n 3 "$CHANGELOG_PATH"' not in script


@pytest.mark.unit
def test_current_master_is_checked_before_an_update_pr_can_merge() -> None:
    steps = _release_steps()
    names = [step.get("name", "") for step in steps]
    checkout_index = names.index("Check out current master")
    guard_index = names.index("Check unreleased section")
    merge_index = names.index("Merge the update PR")
    checkout = steps[checkout_index]
    guard = steps[guard_index]
    merge = steps[merge_index]

    assert checkout_index < guard_index < merge_index
    assert checkout["with"]["persist-credentials"] is False
    assert guard["continue-on-error"] is True
    assert "python -m scripts.changelog check-empty CHANGELOG.rst" in guard["run"]
    assert "steps.changelog-guard.outcome == 'success'" in merge["if"]
    assert merge["continue-on-error"] is True
    assert merge["env"]["HEAD_SHA"] == "${{ github.event.workflow_run.head_sha }}"
    remote_check = 'gh api "repos/$GH_REPO/git/ref/heads/master"'
    assert remote_check in merge["run"]
    assert merge["run"].index(remote_check) < merge["run"].index("gh pr merge")
    assert (
        'gh pr merge "$PR_NUMBER" --squash --match-head-commit "$HEAD_SHA"'
        in merge["run"]
    )


@pytest.mark.unit
def test_blocked_auto_release_labels_and_notifies_the_update_pr() -> None:
    steps = _release_steps()
    alert = next(step for step in steps if step.get("name") == "Report pending work")

    assert "steps.changelog-guard.outcome == 'failure'" in alert["if"]
    assert "steps.merge.outcome == 'failure'" in alert["if"]
    assert "automation-failed" in alert["run"]
    assert "gh pr comment" in alert["run"]
    assert "cut a release" in alert["run"]

    stop = next(step for step in steps if step.get("name") == "Stop blocked release")
    assert "steps.changelog-guard.outcome == 'failure'" in stop["if"]
    assert "steps.merge.outcome == 'failure'" in stop["if"]
    assert stop["run"] == "exit 1"


@pytest.mark.unit
def test_annotated_release_tag_has_a_tagger_identity() -> None:
    """`git tag -a` records a tagger and fails without a configured identity.

    A GitHub runner has none, and git refuses to guess one from
    `runner@<host>.(none)`. Without this the PR merges and the tag that starts
    the release pipeline never gets pushed.
    """
    tag_step = next(
        step for step in _release_steps() if step.get("name") == "Tag the release"
    )
    script = tag_step["run"]

    assert "git config user.name" in script
    assert "git config user.email" in script
    assert script.index("git config user.email") < script.index("git tag -a")


@pytest.mark.unit
def test_every_pr_touching_step_resolves_through_the_shared_action() -> None:
    """One identity check, not one copy per step.

    The check is what stops a fork branch named ``data-update-*`` from being
    auto-merged, so a second inline copy is a second thing to keep correct.
    Every step that acts on the PR takes its number from the shared action.
    """
    steps = _all_steps()
    resolvers = [step for step in steps if step.get("uses") == RESOLVE_ACTION_REF]
    assert len(resolvers) == 2, "both jobs resolve the PR through the action"

    for resolver in resolvers:
        assert resolver["with"]["pr-number"] == (
            "${{ github.event.workflow_run.pull_requests[0].number }}"
        )
        assert resolver["with"]["head-sha"] == (
            "${{ github.event.workflow_run.head_sha }}"
        )
        assert resolver["with"]["repo-owner"] == "${{ github.repository_owner }}"

    # no step re-implements the lookup or the identity check inline
    for step in steps:
        script = str(step.get("run", ""))
        assert "gh pr view" not in script or "mergeCommit" in script
        assert "headRepositoryOwner" not in script

    # and every consumer takes the number from a resolver output
    for step in steps:
        pr_number = step.get("env", {}).get("PR_NUMBER")
        if pr_number is not None:
            assert pr_number.startswith("${{ steps.resolve-")
            assert pr_number.endswith(".outputs.pr-number }}")


@pytest.mark.unit
def test_the_shared_action_rejects_a_pr_that_is_not_the_update_pr() -> None:
    script = _resolve_action_script()

    assert "headRepositoryOwner" in script
    assert "headRefOid" in script
    assert "baseRefName" in script
    # a head repository outside this owner is what the check exists for
    assert '"$head_owner" != "$REPO_OWNER"' in script
    assert "exit 1" in script


@pytest.mark.unit
def test_a_job_running_the_local_action_checks_out_master_first() -> None:
    """A local ``uses:`` needs the repo in the workspace, and it must be master.

    Both jobs run while a pull request is in flight; checking out its head
    would run the PR's own code with the automation's permissions.
    """
    for job in _workflow()["jobs"].values():
        steps = job["steps"]
        uses = [step.get("uses") for step in steps]
        if RESOLVE_ACTION_REF not in uses:
            continue
        checkout_index = next(
            i
            for i, step in enumerate(steps)
            if str(step.get("uses", "")).startswith("actions/checkout")
        )
        assert checkout_index < uses.index(RESOLVE_ACTION_REF)
        checkout = steps[checkout_index]
        assert checkout["with"]["ref"] == "master"
        assert checkout["with"]["persist-credentials"] is False


@pytest.mark.unit
def test_notifications_are_deduplicated_by_marker_and_automation_author() -> None:
    notification_steps = [
        step for step in _all_steps() if "gh pr comment" in str(step.get("run", ""))
    ]

    assert notification_steps
    for step in notification_steps:
        script = step["run"]
        assert "<!-- data-update-automation-notice -->" in script
        assert step["env"]["BOT_LOGIN"] == "github-actions[bot]"
        assert ".user.login" in script
