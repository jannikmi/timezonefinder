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

import pytest
import yaml

from tests.auxiliaries import WORKFLOW_DIR

BUILD_WORKFLOW = WORKFLOW_DIR / "build.yml"
PUBLISH_DATA_WORKFLOW = WORKFLOW_DIR / "publish_data.yml"

DATA_TAG_PREFIX = "data-v"
# the actions that make a release public; a job using either must not be reachable
# from the other stream's tag
PYPI_PUBLISH_ACTION = "pypa/gh-action-pypi-publish"
GITHUB_RELEASE_ACTION = "ncipollo/release-action"


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
