"""Protect the automated data-release workflow from unrelated pending work."""

import pytest
import yaml

from tests.auxiliaries import ACTION_DIR, PROJECT_ROOT, WORKFLOW_DIR

UPDATE_SCRIPT = PROJECT_ROOT / "update_data.sh"
RELEASE_WORKFLOW = WORKFLOW_DIR / "release_data_update.yml"
RESOLVE_ACTION = ACTION_DIR / "resolve-update-pr" / "action.yml"
RESOLVE_ACTION_REF = "./.github/actions/resolve-update-pr"
NOTIFY_ACTION = ACTION_DIR / "notify-update-pr" / "action.yml"
NOTIFY_ACTION_REF = "./.github/actions/notify-update-pr"


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
    # a guard failure fails the job; nothing is kept alive with
    # continue-on-error, so nothing can forget to re-fail it afterwards
    assert "continue-on-error" not in guard
    assert "continue-on-error" not in merge
    assert "python -m scripts.changelog check-empty CHANGELOG.rst" in guard["run"]
    assert merge["env"]["HEAD_SHA"] == "${{ github.event.workflow_run.head_sha }}"
    remote_check = 'gh api "repos/$GH_REPO/git/ref/heads/master"'
    assert remote_check in merge["run"]
    assert merge["run"].index(remote_check) < merge["run"].index("gh pr merge")
    assert (
        'gh pr merge "$PR_NUMBER" --squash --match-head-commit "$HEAD_SHA"'
        in merge["run"]
    )


@pytest.mark.unit
def test_the_squash_parent_proves_master_did_not_move() -> None:
    """Comparing master before the merge leaves a window open.

    A push landing between the comparison and ``gh pr merge`` would ship its
    unreleased work under data-only release notes - the exact thing this
    workflow exists to prevent. ``--match-head-commit`` pins the PR head, not
    the base, so the squash commit's first parent is what settles it.
    """
    merge = next(
        step for step in _release_steps() if step.get("name") == "Merge the update PR"
    )
    script = merge["run"]

    assert "parents[0].sha" in script
    assert '"$merge_parent" != "$guarded_master"' in script
    # checked before the commit is published as an output, so a mismatch
    # withholds the tag rather than merely logging
    assert script.index("merge_parent") < script.index('echo "merge_sha=')


@pytest.mark.unit
def test_the_merge_commit_is_waited_for_and_gates_the_release() -> None:
    """GitHub applies a squash merge asynchronously.

    Reading ``.mergeCommit.oid`` straight afterwards returns null often enough
    to matter, which aborted the step under ``set -e`` with the PR already
    merged: data on master, no tag, and no output saying the merge had
    happened. The publish steps key off the resolved commit rather than the
    merge alone, so they cannot run against an empty ref.
    """
    steps = _release_steps()
    merge = next(step for step in steps if step.get("name") == "Merge the update PR")
    script = merge["run"]

    # the merge is recorded before anything that can still fail
    assert script.index('echo "merged=true"') < script.index("mergeCommit")
    assert "// empty" in script, "a null merge commit must not abort the step"
    assert "retrying" in script

    published = [
        step
        for step in steps
        if "uv version --short" in str(step.get("run", ""))
        or str(step.get("uses", "")).startswith("actions/checkout")
        and step.get("name") is None
    ]
    assert published
    for step in published:
        assert step["if"] == "steps.merge.outputs.merge_sha != ''"


@pytest.mark.unit
def test_blocked_auto_release_labels_and_notifies_the_update_pr() -> None:
    """Each notice states the cause it was actually triggered by.

    One step covering both causes had to describe them as a disjunction, and
    told the maintainer to cut a release - useless advice for a merge conflict
    or a tag that never got pushed.
    """
    steps = _release_steps()

    pending = next(step for step in steps if step.get("name") == "Report pending work")
    assert pending["if"].count("outcome == 'failure'") == 1
    assert "steps.changelog-guard.outcome == 'failure'" in pending["if"]
    assert pending["uses"] == NOTIFY_ACTION_REF
    assert "cut its release first" in pending["with"]["body"]

    merge_failed = next(
        step for step in steps if step.get("name") == "Report failed merge"
    )
    assert merge_failed["if"].count("outcome == 'failure'") == 1
    assert "steps.merge.outcome == 'failure'" in merge_failed["if"]
    assert merge_failed["uses"] == NOTIFY_ACTION_REF

    # both link the run whose log holds the reason
    for step in (pending, merge_failed):
        assert "actions/runs/${{ github.run_id }}" in step["with"]["body"]

    # both report only after something has actually failed, so neither can
    # comment on a run that went through
    for step in (pending, merge_failed):
        assert "failure()" in step["if"]

    # the job fails by itself: no step exists whose only purpose is to re-fail
    # it, which is a step that can be forgotten when a cause is added
    assert not [step for step in steps if str(step.get("run", "")).strip() == "exit 1"]


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
def test_an_already_handled_pr_is_a_no_op_rather_than_a_failure() -> None:
    """Re-running build.yml on a merged update PR re-fires ``workflow_run``.

    That used to exit 0 with "nothing to do". Failing instead turns every such
    re-run red and, worse, makes ``Report pending work`` abort before it can
    say anything - a false alarm that buries the real ones.
    """
    script = _resolve_action_script()

    # not open -> found=false, success. Not ours -> error. Different things.
    assert 'if [[ "$pr_state" != "OPEN" ]]; then' in script
    assert "nothing_to_do" in script
    assert "exit 0" in script
    # identity is checked first, so "not ours" cannot be softened into a no-op
    assert script.index('"$head_owner" != "$REPO_OWNER"') < script.index(
        '"$pr_state" != "OPEN"'
    )


@pytest.mark.unit
def test_no_step_acts_on_the_pr_unless_one_was_found() -> None:
    acting = [
        step
        for step in _all_steps()
        if "gh pr merge" in str(step.get("run", ""))
        or step.get("uses") == NOTIFY_ACTION_REF
    ]
    assert acting

    for step in acting:
        assert "outputs.found == 'true'" in step["if"], step.get("name")

    # the changelog guard fails the job by itself, so it too must stay out of
    # the way when there is no update PR: master having pending work is not a
    # failure of a run that had nothing to release
    guard = next(
        step
        for step in _release_steps()
        if step.get("name") == "Check unreleased section"
    )
    assert "outputs.found == 'true'" in guard["if"]


@pytest.mark.unit
def test_the_shared_action_falls_back_to_a_branch_lookup() -> None:
    """``workflow_run.pull_requests`` is not always populated.

    Trusting it alone made an empty array resolve to ``gh pr view ""``, failing
    the whole job - including ``alert_failure``, whose entire purpose is to
    still reach the maintainer when something has gone wrong.
    """
    action = yaml.safe_load(RESOLVE_ACTION.read_text(encoding="utf-8"))
    assert action["inputs"]["pr-number"]["required"] is False

    script = action["runs"]["steps"][0]["run"]
    assert 'gh pr list --state open --base master --head "$BRANCH"' in script
    # the fallback is narrowed the same way, and still identity-checked after
    assert script.index("gh pr list") < script.index("gh pr view")


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
def test_notice_dedup_matches_the_login_the_token_posts_as() -> None:
    """The author filter and the posting token are set independently.

    Dedup only works while ``bot-login`` names whoever ``token``
    authenticates as. ``secrets.GITHUB_TOKEN`` posts as github-actions[bot];
    the GitHub App token this workflow also holds does not. Switching a
    notifier to the app token without changing the login would match no
    comment ever, so every re-run of build.yml would add another mention -
    a silent failure, since commenting still succeeds.
    """
    default_login = yaml.safe_load(NOTIFY_ACTION.read_text(encoding="utf-8"))["inputs"][
        "bot-login"
    ]["default"]
    assert default_login == "github-actions[bot]"

    for step in [
        step for step in _all_steps() if step.get("uses") == NOTIFY_ACTION_REF
    ]:
        given = step["with"]
        assert given["token"] == "${{ secrets.GITHUB_TOKEN }}", (
            f"{step['name']!r} posts with a token that is not github-actions[bot]; "
            "set bot-login to match or dedup silently stops working"
        )
        assert given.get("bot-login", default_login) == default_login


@pytest.mark.unit
def test_each_notice_cause_deduplicates_on_its_own_marker() -> None:
    """One marker for both notices meant the first one silenced the second.

    A CI failure and a blocked release are different things to tell the
    maintainer, and either can follow the other: fix the CI, re-run, and the
    guard then reports pending work - which the earlier notice would have
    swallowed, leaving a red workflow as the only signal.
    """
    notifiers = [step for step in _all_steps() if step.get("uses") == NOTIFY_ACTION_REF]
    assert len(notifiers) == 3

    markers = [step["with"]["marker"] for step in notifiers]
    assert len(set(markers)) == len(markers), f"causes share a marker: {markers}"

    script = yaml.safe_load(NOTIFY_ACTION.read_text(encoding="utf-8"))["runs"]["steps"][
        0
    ]["run"]
    # the marker is part of the string both written and searched for
    assert "data-update-automation-notice:$MARKER" in script
    assert '.user.login == \\"$BOT_LOGIN\\"' in script
    assert "contains(" in script
