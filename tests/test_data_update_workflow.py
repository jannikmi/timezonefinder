"""Invariants of the automated data-release workflows.

The workflows cannot be executed here, so these read their YAML. That only earns
its place for invariants the structure does not already enforce and whose
violation is silent - a fork PR reaching the merge step, a notice that hides
another, a local action used without a checkout. Asserting that a step still
contains a particular shell string is not one of those: it fails on any
rewording and passes on any bug that keeps the wording.
"""

from pathlib import Path

import pytest
import yaml

from tests.auxiliaries import ACTION_DIR, WORKFLOW_DIR

RELEASE_WORKFLOW = WORKFLOW_DIR / "release_data_update.yml"
UPDATE_WORKFLOW = WORKFLOW_DIR / "check_data_updates.yml"
APP_TOKEN_ACTION = "actions/create-github-app-token"
APP_SECRET_NAMES = ("DATA_UPDATER_APP_ID", "DATA_UPDATER_PRIVATE_KEY")
RESOLVE_ACTION = ACTION_DIR / "resolve-update-pr" / "action.yml"
RESOLVE_ACTION_REF = "./.github/actions/resolve-update-pr"
NOTIFY_ACTION = ACTION_DIR / "notify-update-pr" / "action.yml"
NOTIFY_ACTION_REF = "./.github/actions/notify-update-pr"


def _workflow() -> dict:
    return yaml.safe_load(RELEASE_WORKFLOW.read_text(encoding="utf-8"))


def _jobs() -> dict:
    return _workflow()["jobs"]


def _all_steps() -> list[dict]:
    return [step for job in _jobs().values() for step in job["steps"]]


def _resolve_script() -> str:
    return yaml.safe_load(RESOLVE_ACTION.read_text(encoding="utf-8"))["runs"]["steps"][
        0
    ]["run"]


@pytest.mark.unit
def test_every_step_acting_on_the_pr_goes_through_the_shared_action() -> None:
    """The identity check is what stops a fork PR from being auto-merged.

    ``data-update-*`` is a branch name, and the job's own condition matches it
    on any head repository. A step that merges, labels or comments using a PR
    number taken from anywhere but the resolver is a step that skipped the
    check - which is why there is one implementation of it and no step is
    allowed to grow a second inline.
    """
    steps = _all_steps()
    assert [step for step in steps if step.get("uses") == RESOLVE_ACTION_REF]

    for step in steps:
        pr_number = step.get("env", {}).get("PR_NUMBER")
        if pr_number is not None:
            assert pr_number.startswith("${{ steps.resolve-"), step.get("name")
            assert pr_number.endswith(".outputs.pr-number }}"), step.get("name")
        # the identity check itself lives in the action, nowhere else
        assert "headRepositoryOwner" not in str(step.get("run", "")), step.get("name")


@pytest.mark.unit
def test_nothing_acts_on_a_pr_that_was_not_resolved() -> None:
    """A run with no update PR must stay green and touch nothing.

    ``workflow_run`` re-fires whenever build.yml is re-run, including on an
    update PR that was merged long ago. Every step that acts is conditioned on a
    PR having been found.
    """
    acting = [
        step
        for step in _all_steps()
        if "gh pr merge" in str(step.get("run", ""))
        or step.get("uses") == NOTIFY_ACTION_REF
    ]
    assert acting

    for step in acting:
        assert "outputs.found == 'true'" in step["if"], step.get("name")


@pytest.mark.unit
def test_publishing_keys_off_the_resolved_merge_commit() -> None:
    """The tag names the merge that happened, or nothing is tagged at all.

    Every publishing step is conditioned on the merge having reported a commit, so
    none of them can run against an empty ref when the merge failed or never
    happened - which would tag whatever master happened to be, publishing data the
    run never validated. The merge step in turn compares its checkout against the
    remote, so the checkout has to precede it.
    """
    steps = _jobs()["merge_and_release"]["steps"]
    names = [step.get("name", "") for step in steps]

    assert names.index("Check out current master") < names.index("Merge the update PR")

    publishing = [
        step
        for step in steps
        if "uv version --short" in str(step.get("run", ""))
        or (
            str(step.get("uses", "")).startswith("actions/checkout")
            and step.get("name") is None
        )
    ]
    assert publishing
    for step in publishing:
        assert step["if"] == "steps.merge.outputs.merge_sha != ''"


@pytest.mark.unit
def test_the_data_tag_is_derived_from_the_data_package_alone() -> None:
    """A bare version tag would publish `timezonefinder`, not the data.

    The two streams share a branch and differ only in the tag namespace,
    so reading the *root* version here - which is what this step used to do, when a
    data update was a patch release of the code - would push a code release tag for a
    commit that changed no code. build.yml would then build and publish
    `timezonefinder` from it.
    """
    steps = _jobs()["merge_and_release"]["steps"]
    tagging = next(step for step in steps if step.get("name") == "Tag the release")
    script = str(tagging["run"])

    assert "uv version --short --package timezonefinder-data" in script, (
        "the tag must name the data distribution's version; a bare `uv version "
        "--short` reads the root's and tags a code release"
    )
    assert "data-v" in script, "the pushed tag must live in the data namespace"


@pytest.mark.unit
def test_nothing_can_fail_after_the_last_notice() -> None:
    """The merge is irreversible, so a failure past it must still be reported.

    ``Report failed merge`` covers the merge step alone. A tag push that is
    rejected happens after it and leaves master carrying the data update with
    no release built - and since a ``workflow_run`` failure appears on no pull
    request, nothing marks it anywhere the maintainer looks. The notice for
    that is the job's last step by construction: a step appended below it
    would fail unreported again, which is the hole this closes.
    """
    steps = _jobs()["merge_and_release"]["steps"]
    post_merge = [
        i
        for i, step in enumerate(steps)
        if step.get("uses") == NOTIFY_ACTION_REF
        and "steps.merge.outcome == 'success'" in step["if"]
    ]

    assert post_merge == [len(steps) - 1]


@pytest.mark.unit
def test_each_notice_cause_deduplicates_on_its_own_marker() -> None:
    """One shared marker meant the first notice silenced every later one.

    Fix a failing CI run, re-run it, and the merge then fails on a conflict - a
    notice the earlier CI-failure comment would suppress, leaving a red workflow as
    the only signal. Dedup also depends on ``bot-login`` naming whoever
    ``token`` authenticates as; ``secrets.GITHUB_TOKEN`` posts as
    github-actions[bot] and the app token this workflow also holds does not.
    """
    notifiers = [step for step in _all_steps() if step.get("uses") == NOTIFY_ACTION_REF]
    assert len(notifiers) > 1

    markers = [step["with"]["marker"] for step in notifiers]
    assert len(set(markers)) == len(markers), f"causes share a marker: {markers}"

    action = yaml.safe_load(NOTIFY_ACTION.read_text(encoding="utf-8"))
    default_login = action["inputs"]["bot-login"]["default"]
    for step in notifiers:
        assert step["with"]["token"] == "${{ secrets.GITHUB_TOKEN }}", (
            f"{step.get('name')!r} posts as something other than {default_login}; "
            "set bot-login to match or dedup silently stops working"
        )
        assert step["with"].get("bot-login", default_login) == default_login


@pytest.mark.unit
def test_an_unmatched_pr_errors_while_an_absent_one_does_not() -> None:
    """Two outcomes that must not collapse into each other.

    "Not ours" has to fail: that is the fork check. "Already merged, or no PR
    at all" has to succeed: that is an ordinary re-run. Checking identity
    before state is what keeps a mismatched PR from taking the no-op path.
    """
    script = _resolve_script()

    assert script.index('"$head_owner" != "$REPO_OWNER"') < script.index(
        '"$pr_state" != "OPEN"'
    )


@pytest.mark.unit
def test_a_run_the_pr_has_moved_past_is_a_no_op_rather_than_an_error() -> None:
    """Superseded and "not ours" are different, and only one of them is fatal.

    build.yml declares no concurrency group, so a run for an older head does
    finish after a push rather than being cancelled. Comparing the head SHA
    inside the fork check made that ordinary case fail the job - and in the
    alert job, failing before the notice means a genuinely failed CI run is
    reported nowhere at all.
    """
    script = _resolve_script()

    fork_check = script[: script.index("exit 1")]
    assert "$HEAD_SHA" not in fork_check, "a stale head must not fail the fork check"

    superseded = script[script.index('"$head_sha" != "$HEAD_SHA"') :]
    assert "nothing_to_do" in superseded[: superseded.index("fi")]


@pytest.mark.unit
def test_a_job_using_a_local_action_checks_out_the_repo_first() -> None:
    """``uses: ./...`` resolves from the workspace, not from the remote.

    Without a checkout the step fails with "can't find action.yml" - and in
    the alert job that is the path whose entire purpose is to reach the
    maintainer once something has already gone wrong. master, never the PR
    head: these jobs run the action while a pull request is in flight.
    """
    for job_name, job in _jobs().items():
        steps = job["steps"]
        local_action = next(
            (i for i, s in enumerate(steps) if str(s.get("uses", "")).startswith("./")),
            None,
        )
        if local_action is None:
            continue
        checkout = next(
            i
            for i, s in enumerate(steps)
            if str(s.get("uses", "")).startswith("actions/checkout")
        )
        assert checkout < local_action, job_name
        assert steps[checkout]["with"]["ref"] == "master", job_name
        assert steps[checkout]["with"]["persist-credentials"] is False, job_name


def _steps_of(workflow: Path) -> dict[str, list[dict]]:
    jobs = yaml.safe_load(workflow.read_text(encoding="utf-8"))["jobs"]
    return {name: job["steps"] for name, job in jobs.items()}


def _app_secret_env(step: dict) -> list[str]:
    """The step's environment values that read an App credential."""
    return [
        str(value)
        for value in step.get("env", {}).values()
        if any(name in str(value) for name in APP_SECRET_NAMES)
    ]


@pytest.mark.unit
@pytest.mark.parametrize(
    "workflow", [RELEASE_WORKFLOW, UPDATE_WORKFLOW], ids=lambda path: path.name
)
def test_an_absent_app_credential_is_reported_before_the_token_is_minted(
    workflow: Path,
) -> None:
    """Both halves of the pipeline stop on a credential nobody configured.

    ``create-github-app-token`` reports an empty input as its own error, naming
    neither secret nor the repository that is missing them, and it does so
    before anything else in the job has run. In the weekly job that left the
    fallback issue asking for the data to be compiled by hand; in the release
    job it would leave a ``workflow_run`` failure, which appears on no pull
    request and in no issue at all. Neither job had ever run when this was
    found: the weekly check always exited at ``update_needed=false``, and the
    release job is skipped on every branch but an update branch, so upstream
    ``2026d`` on 2026-09-20 was the first run of either that needed the App.
    """
    for name, steps in _steps_of(workflow).items():
        token_step = next(
            (
                index
                for index, step in enumerate(steps)
                if str(step.get("uses", "")).startswith(APP_TOKEN_ACTION)
            ),
            None,
        )
        if token_step is None:
            continue
        preflight = next(
            (index for index, step in enumerate(steps) if _app_secret_env(step)),
            None,
        )
        assert preflight is not None, f"{name} mints an App token unchecked"
        assert preflight < token_step, f"{name} checks the credentials too late"


@pytest.mark.unit
@pytest.mark.parametrize(
    "workflow", [RELEASE_WORKFLOW, UPDATE_WORKFLOW], ids=lambda path: path.name
)
def test_no_step_takes_an_app_credential_as_its_value(workflow: Path) -> None:
    """The checks read whether the secrets are set, never what they hold.

    A private key placed in the environment to be tested for emptiness is a
    private key that ``set -x``, a crash dump or an error message can echo. The
    expression form yields 'true' or 'false' and carries nothing. Only the
    ``with:`` of the token action itself may receive the values.
    """
    for name, steps in _steps_of(workflow).items():
        for step in steps:
            for value in _app_secret_env(step):
                assert "!= ''" in value, (
                    f"{name}: {step.get('name')!r} puts an App credential in its "
                    f"environment rather than a comparison: {value!r}"
                )


@pytest.mark.unit
def test_the_fallback_issue_distinguishes_its_two_causes() -> None:
    """The issue is the only place a scheduled failure is ever seen.

    "The pipeline broke, compile the data by hand" and "this repository has no
    credentials to open a pull request with" ask for entirely different work,
    and the second one is answered by two secrets and a re-run. An issue that
    cannot tell them apart spends an afternoon on the converter for a missing
    credential - which is what the ``2026d`` issue asked for.
    """
    notifying = [
        step
        for steps in _steps_of(UPDATE_WORKFLOW).values()
        for step in steps
        if "gh issue create" in str(step.get("run", ""))
    ]
    assert notifying

    for step in notifying:
        assert _app_secret_env(step), (
            f"{step.get('name')!r} opens the fallback issue without knowing "
            "whether the App is configured, so it cannot name the cause"
        )
