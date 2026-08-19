"""Invariants of the two release streams this repository publishes.

One branch carries two tag namespaces: a bare version tag releases
``timezonefinder``, and ``data-v*`` releases ``timezonefinder-data``. Neither can be
exercised here - a tag push happens only on GitHub, and no pull request produces one -
so these read the workflow YAML.

That only earns its place for invariants the structure does not enforce and whose
violation is silent. Asserting that a step still contains a particular shell string is
not one of those. What is asserted here is that no job publishing the *code* can be
reached by a data tag, and that the two streams cannot borrow each other's
credentials - both of which fail invisibly: a data tag that reaches build.yml's
release job produces a GitHub Release for the code version with code artefacts
attached to it, and nothing about that looks wrong until someone reads the release
page. Neither stream holds a token any more, so what keeps them apart is the
deployment environment each publishing identity is bound to.
"""

import re

import pytest
import yaml

from tests.auxiliaries import ACTION_DIR, WORKFLOW_DIR

BUILD_WORKFLOW = WORKFLOW_DIR / "build.yml"
PUBLISH_DATA_WORKFLOW = WORKFLOW_DIR / "publish_data.yml"

DATA_TAG_PREFIX = "data-v"
# the actions that make a release public; a job using either must not be reachable
# from the other stream's tag
PYPI_PUBLISH_ACTION = "pypa/gh-action-pypi-publish"
GITHUB_RELEASE_ACTION = "ncipollo/release-action"
# the release job's stand-in for the tox matrix it skips on a tag ref
GREEN_RUN_STEP_ID = "verify_tested_on_master"
# the one implementation of "flatten every uploaded artefact into dist/"
STAGE_ACTION = ACTION_DIR / "stage-artifacts" / "action.yml"
STAGE_ACTION_REF = "./.github/actions/stage-artifacts"
DATA_WHEEL_INPUT = "include-data-wheel"
DATA_WHEEL_PREFIX = "timezonefinder_data-"


def _workflow(path):
    # `on:` is parsed as the boolean True by YAML 1.1, which is what PyYAML implements
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _triggers(workflow: dict) -> dict:
    return workflow[True]


def _uses(step: dict) -> str:
    return str(step.get("uses", ""))


def _jobs_using(workflow: dict, action: str) -> dict[str, dict]:
    return {
        name: job
        for name, job in workflow["jobs"].items()
        if any(_uses(step).startswith(action) for step in job["steps"])
    }


def _needs(job: dict) -> list[str]:
    declared = job.get("needs", [])
    return [declared] if isinstance(declared, str) else list(declared)


def _guarded_against_data_tags(workflow: dict, job_name: str) -> bool:
    """Whether ``job_name`` cannot run on a ``data-v*`` ref, directly or via ``needs``.

    A skipped dependency skips its dependents, so a guard on one job covers everything
    downstream of it - which is why ``publish-pypi`` carries none of its own.
    """
    job = workflow["jobs"][job_name]
    condition = str(job.get("if", ""))
    if DATA_TAG_PREFIX in condition and "!startsWith" in condition:
        return True
    return any(
        _guarded_against_data_tags(workflow, dependency) for dependency in _needs(job)
    )


def _guarded_by_data_check(workflow: dict, job_name: str) -> bool:
    """Whether the data-dependency check has run by the time ``job_name`` publishes.

    Either in the job itself, ahead of its first publishing step and able to fail it,
    or in a job it depends on - a skipped dependency skips its dependents.
    """
    job = workflow["jobs"][job_name]
    steps = job["steps"]
    guard = [
        i
        for i, step in enumerate(steps)
        if "scripts.check_data_dependency" in str(step.get("run", ""))
    ]
    if guard:
        publishing = [
            i
            for i, step in enumerate(steps)
            if _uses(step).startswith(PYPI_PUBLISH_ACTION)
            or _uses(step).startswith(GITHUB_RELEASE_ACTION)
        ]
        if publishing and max(guard) > min(publishing):
            return False
        return all("continue-on-error" not in steps[i] for i in guard)
    return any(
        _guarded_by_data_check(workflow, dependency) for dependency in _needs(job)
    )


@pytest.mark.unit
def test_the_code_pipeline_does_not_run_on_a_data_tag() -> None:
    """The push path: one tag filter, in one place, impossible to half-apply.

    Per-job ``if:`` guards were the alternative and are the worse one - the ``release``
    job is the one an implementer overlooks, and it is the job that publishes.
    """
    tags = _triggers(_workflow(BUILD_WORKFLOW))["push"]["tags"]
    assert f"!{DATA_TAG_PREFIX}*" in tags, (
        f"{BUILD_WORKFLOW.name} still runs on every tag: a {DATA_TAG_PREFIX}* push "
        "would build and release the code version under the data's tag"
    )


@pytest.mark.unit
def test_nothing_publishing_the_code_is_reachable_from_a_data_tag() -> None:
    """The trigger filter is not the whole story, which is the easy thing to miss.

    ``release: types: [published]`` sets ``github.ref`` to the tag and consults no tag
    filter, so a GitHub Release published by hand against a data tag reaches build.yml
    regardless. Every job that uploads to PyPI or creates a Release therefore has to be
    guarded on the ref as well - directly, or through a dependency that is.
    """
    workflow = _workflow(BUILD_WORKFLOW)
    publishing = {
        **_jobs_using(workflow, PYPI_PUBLISH_ACTION),
        **_jobs_using(workflow, GITHUB_RELEASE_ACTION),
    }
    assert publishing, (
        f"no publishing job found in {BUILD_WORKFLOW.name} - this check is vacuous, "
        "so the action names above have gone stale"
    )

    unguarded = sorted(
        name for name in publishing if not _guarded_against_data_tags(workflow, name)
    )
    assert not unguarded, (
        f"jobs in {BUILD_WORKFLOW.name} that publish {list(publishing)} but can run on "
        f"a {DATA_TAG_PREFIX}* ref: {unguarded}. The trigger's tag filter does not "
        "cover the `release: types: [published]` path."
    )


@pytest.mark.unit
def test_nothing_irreversible_runs_before_the_data_dependency_is_checked() -> None:
    """Ordering is the whole invariant: a check after the fact checks nothing.

    On a data format change the data distribution must be published first, and
    releasing the code first puts a wheel on PyPI that nobody can install - which
    cannot be undone, because the version number is spent. The upload is not the first
    step that cannot be taken back, though: the `release` job publishes a GitHub
    Release with the wheels attached and creates the tag, before `publish-pypi` runs at
    all. So the guard is asserted against *both* kinds of publishing step, and a job
    may satisfy it through a dependency - a skipped `needs` skips its dependents, which
    is why the upload job carries no copy of its own.
    """
    workflow = _workflow(BUILD_WORKFLOW)
    publishing = {
        **_jobs_using(workflow, PYPI_PUBLISH_ACTION),
        **_jobs_using(workflow, GITHUB_RELEASE_ACTION),
    }
    assert publishing, (
        f"no publishing job found in {BUILD_WORKFLOW.name} - this check is vacuous, "
        "so the action names above have gone stale"
    )

    unguarded = sorted(
        name for name in publishing if not _guarded_by_data_check(workflow, name)
    )
    assert not unguarded, (
        f"jobs in {BUILD_WORKFLOW.name} that publish without the data-dependency check "
        f"having already run: {unguarded}. Put it in the job ahead of its first "
        "publishing step, or in a job it needs."
    )


@pytest.mark.unit
def test_the_data_stream_publishes_only_from_its_own_tag() -> None:
    triggers = _triggers(_workflow(PUBLISH_DATA_WORKFLOW))
    assert set(triggers) == {"push"}, (
        f"{PUBLISH_DATA_WORKFLOW.name} publishes, so it must be reachable only by a "
        f"{DATA_TAG_PREFIX}* tag push; found triggers {sorted(triggers)}"
    )
    assert triggers["push"]["tags"] == [f"{DATA_TAG_PREFIX}*"], (
        f"{PUBLISH_DATA_WORKFLOW.name} must trigger on {DATA_TAG_PREFIX}* alone"
    )


@pytest.mark.unit
def test_the_data_stream_creates_no_github_release() -> None:
    """This is what closes build.yml's third way in, so it is not merely a choice.

    build.yml also triggers on ``release: types: [published]``, where no tag filter
    applies. As long as nothing creates a Release for a data tag, that path cannot fire
    for one - the ref guard on build.yml's release job is the second line of defence,
    not the first.
    """
    workflow = _workflow(PUBLISH_DATA_WORKFLOW)
    releasing = _jobs_using(workflow, GITHUB_RELEASE_ACTION)
    assert not releasing, (
        f"{PUBLISH_DATA_WORKFLOW.name} creates a GitHub Release in {sorted(releasing)}, "
        f"which makes build.yml's `release: types: [published]` trigger fire on a "
        f"{DATA_TAG_PREFIX}* ref. Either drop it, or accept that build.yml's ref guard "
        "is then the only thing standing between a data tag and a code release."
    )


@pytest.mark.unit
def test_both_streams_publish_without_a_shared_credential() -> None:
    """What scopes each stream to its own project, now that neither holds a token.

    Both publish by Trusted Publishing: PyPI trusts one workflow file per project,
    gated on a deployment environment, and the job exchanges an OIDC identity for a
    short-lived upload token. Three things therefore have to hold, and none is
    self-announcing if it stops holding. A publishing job must request
    ``id-token: write`` - without it the exchange has nothing to present, and the
    upload fails only at release time, on a tag that cannot be pushed twice. It must
    be gated on a deployment environment, which is what the publisher on PyPI is bound
    to. And the two streams must not name the *same* environment, which is what keeps
    a data release from presenting an identity PyPI accepts for ``timezonefinder``.
    """
    publishing = {
        (path.name, name): job
        for path in (BUILD_WORKFLOW, PUBLISH_DATA_WORKFLOW)
        for name, job in _jobs_using(_workflow(path), PYPI_PUBLISH_ACTION).items()
    }
    assert len(publishing) == 2, (
        f"expected one PyPI upload job per stream, found {sorted(publishing)} - this "
        "check no longer covers what it names"
    )

    for (workflow_name, name), job in publishing.items():
        assert job.get("permissions", {}).get("id-token") == "write", (
            f"{workflow_name}: {name} publishes by OIDC but does not request "
            "id-token: write"
        )
        assert job.get("environment"), (
            f"{workflow_name}: {name} is not gated on a deployment environment, which "
            "is what the trusted publisher on PyPI is bound to"
        )
        with_a_password = [
            step
            for step in job["steps"]
            if _uses(step).startswith(PYPI_PUBLISH_ACTION)
            and "password" in (step.get("with") or {})
        ]
        assert not with_a_password, (
            f"{workflow_name}: {name} passes a `password` to {PYPI_PUBLISH_ACTION}, "
            "so it uploads with a long-lived token rather than by OIDC"
        )

    environments = {job["environment"] for job in publishing.values()}
    assert len(environments) == len(publishing), (
        f"both streams publish from the same deployment environment {environments}; "
        "a data release could then present an identity PyPI accepts for the code"
    )


# --- what a ref actually reaches -------------------------------------------------
#
# The code stream now splits by ref: a master push runs the tox matrix and publishes
# nothing, a version tag publishes and skips the matrix. That split is expressed
# entirely in `if:` conditions over `needs` results, where the failure mode is silent
# and only surfaces during a real release - a skipped `needs` job skips its dependents,
# and naming any status check function drops the implicit `success()` over the rest. So
# these evaluate the conditions rather than read them.

_STATUS_FUNCTIONS = ("success()", "always()", "cancelled()", "failure()")
_PUBLISHING_ACTIONS = (PYPI_PUBLISH_ACTION, GITHUB_RELEASE_ACTION)


def _as_python(condition: str) -> str:
    """Translate the subset of GitHub expression syntax these conditions use."""
    expression = condition.replace("!=", "\0NE\0")
    expression = re.sub(r"needs\['([^']+)'\]\.result", r"needs['\1']", expression)
    expression = re.sub(r"needs\.([A-Za-z0-9_-]+)\.result", r"needs['\1']", expression)
    expression = expression.replace("cancelled()", "cancelled")
    expression = expression.replace("github.ref", "ref")
    expression = re.sub(
        r"startsWith\(\s*([^,]+?)\s*,\s*('[^']*')\s*\)",
        r"\1.startswith(\2)",
        expression,
    )
    expression = expression.replace("&&", " and ").replace("||", " or ")
    expression = expression.replace("!", " not ")
    return expression.replace("\0NE\0", "!=")


def _simulate(workflow: dict, ref: str, failing: frozenset[str] = frozenset()) -> dict:
    """Every job's result for a run on ``ref``, with ``failing`` jobs failing.

    Models the two rules that make this workflow's conditions non-obvious: a job with no
    ``if`` runs only when every ``needs`` succeeded, and an ``if`` naming a status check
    function replaces that rule entirely instead of narrowing it.
    """
    results: dict[str, str] = {}

    def resolve(name: str) -> str:
        if name in results:
            return results[name]
        job = workflow["jobs"][name]
        needs = {dependency: resolve(dependency) for dependency in _needs(job)}
        condition = job.get("if")
        all_needs_succeeded = all(result == "success" for result in needs.values())
        if condition is None:
            runs = all_needs_succeeded
        else:
            condition = str(condition)
            value = eval(  # noqa: S307 - the input is this repository's own workflow
                _as_python(condition),
                {},
                {"ref": ref, "needs": needs, "cancelled": False},
            )
            names_status_function = any(fn in condition for fn in _STATUS_FUNCTIONS)
            runs = bool(value) and (names_status_function or all_needs_succeeded)
        results[name] = (
            ("failure" if name in failing else "success") if runs else "skipped"
        )
        return results[name]

    for name in workflow["jobs"]:
        resolve(name)
    return results


@pytest.mark.unit
def test_a_push_to_master_tests_and_publishes_nothing() -> None:
    """The tag is the publish. Master's own run must not get there first.

    It used to: the release job accepted `refs/heads/master`, and it hands the release
    action a `tag:`, so master's run created the GitHub Release *and* the tag. The
    maintainer's `git push` of that tag then found it already there, reported
    "Everything up-to-date" and fired no webhook.
    """
    results = _simulate(_workflow(BUILD_WORKFLOW), "refs/heads/master")
    assert results["test"] == "success", (
        "the tox matrix must run on master - it is the only run that tests the tree a "
        "tag will later publish without re-testing"
    )
    for name in ("release", "publish-pypi"):
        assert results[name] == "skipped", (
            f"a push to master reaches `{name}`, which publishes; the tag then races it"
        )


@pytest.mark.unit
def test_a_version_tag_publishes_without_re_running_the_matrix() -> None:
    """The skip-semantics check: `test` is skipped here, and skipping cascades.

    A skipped `needs` job skips its dependents no matter what the dependent's `if` says,
    unless that `if` names a status check function - which in turn discards the implicit
    `success()` over every *other* dependency. Get either half wrong and nothing is
    visible until a release either publishes nothing or publishes off a red matrix.
    """
    results = _simulate(_workflow(BUILD_WORKFLOW), "refs/tags/9.9.9")
    assert results["test"] == "skipped", (
        "the tox matrix runs on the tag ref as well, which is the duplicate run this "
        "split exists to remove"
    )
    for name in ("release", "publish-pypi"):
        assert results[name] == "success", (
            f"`{name}` is skipped on a version tag: a skipped `needs` job skips its "
            "dependents, so the condition has to name a status check function"
        )


@pytest.mark.unit
def test_a_tag_release_still_requires_every_job_that_did_run() -> None:
    """Naming a status function drops the implicit `success()` over *all* of `needs`.

    So each dependency that is not skipped has to be re-checked by hand, and forgetting
    one publishes off a red check.
    """
    workflow = _workflow(BUILD_WORKFLOW)
    dependencies = _needs(workflow["jobs"]["release"])
    assert dependencies, "`release` depends on nothing - this check is vacuous"
    for dependency in dependencies:
        results = _simulate(
            workflow, "refs/tags/9.9.9", failing=frozenset({dependency})
        )
        if results[dependency] == "skipped":
            continue
        assert results["release"] == "skipped", (
            f"`release` publishes even though `{dependency}` failed"
        )


@pytest.mark.unit
def test_the_skipped_matrix_is_replaced_by_a_check_and_not_an_assumption() -> None:
    """Skipping the matrix on a tag is only sound if that SHA passed on master.

    Ancestry is the weaker claim and the one already checked: a commit can sit on master
    with a red run, or with no run at all. So the release job has to assert the green run
    exists, and assert it before the first step that cannot be taken back. The step is
    pinned by `id`, not by its name or its shell - a rewording must not fail this, a
    deletion must.
    """
    workflow = _workflow(BUILD_WORKFLOW)
    if _simulate(workflow, "refs/tags/9.9.9")["test"] != "skipped":
        pytest.skip("the matrix runs on tags again, so it needs no stand-in")

    steps = workflow["jobs"]["release"]["steps"]
    guard = [i for i, step in enumerate(steps) if step.get("id") == GREEN_RUN_STEP_ID]
    assert guard, (
        f"no step with id `{GREEN_RUN_STEP_ID}` in the release job, but the tox matrix "
        "is skipped on tags - nothing establishes that this commit ever passed it"
    )
    publishing = [
        i for i, step in enumerate(steps) if _uses(step).startswith(_PUBLISHING_ACTIONS)
    ]
    assert publishing and max(guard) < min(publishing), (
        "the green-run check runs after the release is already published"
    )
    assert (
        workflow["jobs"]["release"].get("permissions", {}).get("actions") == "read"
    ), (
        "the green-run check reads this commit's other workflow runs, which needs "
        "`actions: read`; declaring any permission zeroes the rest, and the omission "
        "fails only at release time, on a tag that cannot be pushed twice"
    )


# --- staging dist/ ---------------------------------------------------------------
#
# Three jobs need the same dist/ and one of them needs it to differ. Written out
# three times, that difference was a diff between shell one-liners; through the
# shared action it is a named input, which is what these two checks pin.


@pytest.mark.unit
def test_every_job_stages_dist_through_the_shared_action() -> None:
    """A second inline copy is how the callers drifted apart in the first place.

    The point of the action is not that the shell is written once - it is that the
    data-wheel exclusion below is a parameter rather than something a reader has to
    notice. A job that stages dist/ with its own `run:` opts out of that silently.
    """
    workflow = _workflow(BUILD_WORKFLOW)
    callers = _jobs_using(workflow, STAGE_ACTION_REF)
    assert callers, (
        f"no job in {BUILD_WORKFLOW.name} uses {STAGE_ACTION_REF} - this check is "
        "vacuous, so the action has been moved or renamed"
    )

    inline = sorted(
        name
        for name, job in workflow["jobs"].items()
        for step in job["steps"]
        if "mkdir -p dist/" in str(step.get("run", ""))
    )
    assert not inline, (
        f"jobs in {BUILD_WORKFLOW.name} that stage dist/ inline instead of through "
        f"{STAGE_ACTION_REF}: {inline}"
    )


@pytest.mark.unit
def test_the_pypi_upload_stages_no_data_wheel() -> None:
    """What keeps timezonefinder-data off `timezonefinder`'s trusted publisher.

    The upload action takes no file list: it publishes whatever sits in dist/, with
    the identity this job's environment is bound to. A data wheel staged here is
    therefore released as part of the code project - it cannot be unpublished, and
    it burns a version number the real data release then cannot use.
    """
    workflow = _workflow(BUILD_WORKFLOW)
    for name in _jobs_using(workflow, PYPI_PUBLISH_ACTION):
        staging = [
            step
            for step in workflow["jobs"][name]["steps"]
            if _uses(step) == STAGE_ACTION_REF
        ]
        assert staging, (
            f"{name} uploads to PyPI without staging dist/ through "
            f"{STAGE_ACTION_REF}, so nothing excludes the data wheel"
        )
        for step in staging:
            assert (step.get("with") or {}).get(DATA_WHEEL_INPUT) == "false", (
                f"{name} stages dist/ with the data wheel included and uploads it as "
                "`timezonefinder`"
            )

    action = yaml.safe_load(STAGE_ACTION.read_text(encoding="utf-8"))
    assert action["inputs"][DATA_WHEEL_INPUT]["default"] == "true", (
        f"{DATA_WHEEL_INPUT} defaults to excluding the data wheel, so the end-to-end "
        "test would install a published dataset instead of this branch's"
    )
    assert DATA_WHEEL_PREFIX in str(action["runs"]["steps"]), (
        f"{STAGE_ACTION.name} no longer names {DATA_WHEEL_PREFIX}, so "
        f"{DATA_WHEEL_INPUT} excludes nothing"
    )


@pytest.mark.unit
def test_a_job_using_a_local_action_checks_out_the_repo_first() -> None:
    """``uses: ./...`` resolves from the workspace, not from the remote.

    Without a checkout the step fails with "can't find action.yml". It is the
    non-obvious cost of extracting one: `end-to-end-test` and `publish-pypi` had no
    reason to check out at all before this, and `publish-pypi`'s remaining checkout
    exists for nothing else.
    """
    for name, job in _workflow(BUILD_WORKFLOW)["jobs"].items():
        steps = job["steps"]
        local_action = next(
            (i for i, step in enumerate(steps) if _uses(step).startswith("./")),
            None,
        )
        if local_action is None:
            continue
        checkout = next(
            (
                i
                for i, step in enumerate(steps)
                if _uses(step).startswith("actions/checkout")
            ),
            None,
        )
        assert checkout is not None and checkout < local_action, (
            f"{name} uses a local action without checking out the repository first"
        )
