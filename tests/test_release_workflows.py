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
page.
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
def test_the_data_stream_publishes_without_a_shared_credential() -> None:
    """What scopes the data stream to its own project, now that it holds no token.

    It publishes by Trusted Publishing: PyPI trusts this workflow file, gated on a
    deployment environment, and the job exchanges an OIDC identity for a short-lived
    upload token. Two things therefore have to hold, and neither is self-announcing if
    it stops holding. The job must request ``id-token: write`` - without it the
    exchange has nothing to present, and the upload fails only at release time, on a
    tag that cannot be pushed twice. And it must not reach for the code stream's
    token, which would let a data release upload ``timezonefinder``.
    """
    workflow = _workflow(PUBLISH_DATA_WORKFLOW)
    publishing = _jobs_using(workflow, PYPI_PUBLISH_ACTION)
    assert publishing, f"{PUBLISH_DATA_WORKFLOW.name} publishes nothing"

    for name, job in publishing.items():
        assert job.get("permissions", {}).get("id-token") == "write", (
            f"{name} publishes by OIDC but does not request id-token: write"
        )
        assert job.get("environment"), (
            f"{name} is not gated on a deployment environment, which is what the "
            "trusted publisher on PyPI is bound to"
        )

    code_secrets = {
        step["with"]["password"]
        for job in _jobs_using(_workflow(BUILD_WORKFLOW), PYPI_PUBLISH_ACTION).values()
        for step in job["steps"]
        if _uses(step).startswith(PYPI_PUBLISH_ACTION)
    }
    assert code_secrets, (
        f"no publishing credential found in {BUILD_WORKFLOW.name} - this check is "
        "vacuous, so the code stream's mechanism has changed too"
    )
    data_workflow_text = PUBLISH_DATA_WORKFLOW.read_text(encoding="utf-8")
    borrowed = sorted(
        secret for secret in code_secrets if secret.strip() in data_workflow_text
    )
    assert not borrowed, (
        f"{PUBLISH_DATA_WORKFLOW.name} references the code stream's credential "
        f"{borrowed}; that token can upload `timezonefinder`"
    )
