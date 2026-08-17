"""Protect the automated data-release workflow from unrelated pending work."""

import pytest
import yaml

from tests.auxiliaries import PROJECT_ROOT

UPDATE_SCRIPT = PROJECT_ROOT / "update_data.sh"
RELEASE_WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "release_data_update.yml"


def _release_steps() -> list[dict]:
    workflow = yaml.safe_load(RELEASE_WORKFLOW.read_text(encoding="utf-8"))
    return workflow["jobs"]["merge_and_release"]["steps"]


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
def test_update_pr_is_selected_from_the_workflow_run_payload() -> None:
    workflow = yaml.safe_load(RELEASE_WORKFLOW.read_text(encoding="utf-8"))
    steps = [step for job in workflow["jobs"].values() for step in job["steps"]]
    scripts = [str(step.get("run", "")) for step in steps]

    assert not any("gh pr list" in script for script in scripts)
    for step in steps:
        if "gh pr view" in str(step.get("run", "")):
            assert step["env"]["PR_NUMBER"] == (
                "${{ github.event.workflow_run.pull_requests[0].number }}"
            )

    merge = next(step for step in steps if step.get("name") == "Merge the update PR")
    assert "headRepositoryOwner" in merge["run"]
    assert "headRefOid" in merge["run"]
    assert "baseRefName" in merge["run"]


@pytest.mark.unit
def test_notifications_are_deduplicated_by_marker_and_automation_author() -> None:
    workflow = yaml.safe_load(RELEASE_WORKFLOW.read_text(encoding="utf-8"))
    notification_steps = [
        step
        for job in workflow["jobs"].values()
        for step in job["steps"]
        if "gh pr comment" in str(step.get("run", ""))
    ]

    assert notification_steps
    for step in notification_steps:
        script = step["run"]
        assert "<!-- data-update-automation-notice -->" in script
        assert step["env"]["BOT_LOGIN"] == "github-actions[bot]"
        assert step["env"]["HEAD_SHA"] == "${{ github.event.workflow_run.head_sha }}"
        assert "headRepositoryOwner" in script
        assert "baseRefName" in script
        assert ".user.login" in script
