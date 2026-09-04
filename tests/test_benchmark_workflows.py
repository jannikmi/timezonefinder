"""Assert the two benchmark workflows still fit together.

GitHub Actions workflows cannot import constants from each other, so
`.github/workflows/benchmark.yml` (measure + record) and
`.github/workflows/benchmark-comment.yml` (compare + comment) repeat the
same literals, held together only by a "must match ..." comment.

A one-sided edit fails silently in the worst possible way: the comparison
job would download a filename or an artifact that no longer corresponds to
what the measuring job produced, so the PR comment compares against nothing
(or the job never runs) - with no error anywhere. These tests are the missing
enforcement of those comments.

They also pin the shape of the comparison itself: the measuring job uploads
both a head and a merge-base measurement, the comment job consumes both, and
only the trend chart goes through `benchmark-action/github-action-benchmark`.
That last one is a design decision, not a detail - comparing a pull request
against the stored gh-pages baseline measures the runner pool rather than the
change (see the `measure` job's comment in benchmark.yml).

Timing and memory are measured in the same job and travel in the same two
artifacts, so the counts pinned below cover both.
"""

from pathlib import Path
import re
from types import SimpleNamespace
from typing import Any

import pytest
import yaml

from tests.auxiliaries import PROJECT_ROOT, WORKFLOW_DIR

BENCHMARK_WORKFLOW = WORKFLOW_DIR / "benchmark.yml"
BENCHMARK_COMMENT_WORKFLOW = WORKFLOW_DIR / "benchmark-comment.yml"
MAKEFILE = PROJECT_ROOT / "Makefile"
RELEASE_WORKFLOW = (
    PROJECT_ROOT / "contributing/workflows/prepare-and-publish-code-release.md"
)

# workflow-level `env:` entries that both files declare and that must be
# identical - see the "must match" comments in benchmark-comment.yml.
# `BENCHMARK_SUITE_NAME` and `ALERT_THRESHOLD` used to be here too; they now
# live only in benchmark.yml, because only the trend chart still uses the
# benchmark action (see test_only_the_trend_chart_uses_the_benchmark_action).
SHARED_ENV_KEYS = (
    # the filename the head measurement is staged under inside its artifact
    "REPORT_FILENAME",
    # and the memory measurement, which rides in the same artifact
    "MEMORY_REPORT_FILENAME",
)


def _load(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text())


def _push_branches(workflow: dict[Any, Any]) -> list[str]:
    """The branches a push starts the workflow on.

    YAML 1.1 reads a bare ``on:`` key as the boolean ``True``, which is why this
    is a lookup rather than ``workflow["on"]``: the key is not a string.
    """
    branches: list[str] = workflow[True]["push"]["branches"]
    return branches


@pytest.fixture(scope="module")
def benchmark_workflow() -> dict[str, Any]:
    return _load(BENCHMARK_WORKFLOW)


@pytest.fixture(scope="module")
def comment_workflow() -> dict[str, Any]:
    return _load(BENCHMARK_COMMENT_WORKFLOW)


@pytest.mark.unit
@pytest.mark.parametrize("key", SHARED_ENV_KEYS)
def test_shared_env_constants_match(
    key: str, benchmark_workflow: dict[str, Any], comment_workflow: dict[str, Any]
) -> None:
    measured = benchmark_workflow["env"]
    compared = comment_workflow["env"]
    assert key in measured, f"{BENCHMARK_WORKFLOW.name} no longer defines env.{key}"
    assert key in compared, (
        f"{BENCHMARK_COMMENT_WORKFLOW.name} no longer defines env.{key}"
    )
    assert measured[key] == compared[key], (
        f"env.{key} differs between {BENCHMARK_WORKFLOW.name} "
        f"({measured[key]!r}) and {BENCHMARK_COMMENT_WORKFLOW.name} "
        f"({compared[key]!r}). GitHub workflows cannot share constants, so "
        "both copies have to be edited together - a mismatch makes the PR "
        "comparison silently compare against nothing."
    )


BENCHMARK_ACTION = "benchmark-action/github-action-benchmark"
UPLOAD_ACTION = "actions/upload-artifact"
DOWNLOAD_ACTION = "actions/download-artifact"


def _steps_using(
    workflow: dict[str, Any], job: str, action: str
) -> list[dict[str, Any]]:
    return [
        step
        for step in workflow["jobs"][job]["steps"]
        if str(step.get("uses", "")).startswith(action)
    ]


def _make_recipe(target: str) -> str:
    text = MAKEFILE.read_text(encoding="utf-8")
    match = re.search(
        rf"(?m)^{re.escape(target)}:[^\n]*\n(?P<recipe>(?:\t[^\n]*\n)+)", text
    )
    assert match is not None, f"the Makefile no longer defines {target!r}"
    return match["recipe"]


# Every target that produces a published or CI-tracked measurement, timing and
# footprint alike. The footprint ones belong here for the same reason as the
# timings: importing numba costs resident memory, so a `memory-ci` run in a
# development environment - which has numba, because `make install` syncs
# --all-groups - records a footprint the plain install never has.
MEASUREMENT_TARGETS = ("benchmarks", "benchmarks-ci", "latency", "memory", "memory-ci")


@pytest.mark.unit
@pytest.mark.parametrize("target", MEASUREMENT_TARGETS)
def test_every_measurement_target_asserts_its_acceleration_path(target: str) -> None:
    assert "scripts.assert_acceleration_path" in _make_recipe(target), (
        f"make {target} can measure whichever backend the caller's environment "
        "happens to bind instead of refusing a report for the wrong implementation"
    )


@pytest.mark.unit
def test_the_published_suite_uses_one_fixed_round_count() -> None:
    recipe = _make_recipe("benchmarks")
    assert "--benchmark-min-rounds=$(BENCHMARK_REPORT_ROUNDS)" in recipe
    assert "--benchmark-max-time=0" in recipe


@pytest.mark.unit
def test_the_report_job_uploads_read_only_commit_bound_pages(
    benchmark_workflow: dict[str, Any],
) -> None:
    report_job = benchmark_workflow["jobs"]["render-reports"]
    assert report_job["permissions"] == {"contents": "read", "actions": "read"}
    scripts = "\n".join(str(step.get("run", "")) for step in report_job["steps"])
    assert "make reports" in scripts
    assert "scripts.benchmark_report_artifact stage" in scripts
    assert '--commit "$GITHUB_SHA"' in scripts
    uploads = _steps_using(benchmark_workflow, "render-reports", UPLOAD_ACTION)
    assert [step["with"]["name"] for step in uploads] == ["benchmark-pages"]


@pytest.mark.unit
def test_the_release_installs_only_reports_for_its_exact_commit() -> None:
    instructions = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    push = instructions.index('git push -u origin "$release_branch"')
    listing = instructions.index("gh run list --workflow benchmark.yml", push)
    download = instructions.index("gh run download", listing)
    validation = instructions.index('--expected-commit "$release_sha"', download)
    assert push < listing < download < validation
    # The run the release consumes is the one its own push started, so the
    # listing must select `push` runs; `--event workflow_dispatch` would find
    # nothing and send the reader back to pressing a button.
    assert "--event push" in instructions[listing:download]


# Every event `benchmark.yml` can receive, and the jobs that must run on it.
# Written as an evaluated table rather than as assertions about the text of an
# `if:`, because what this workflow gets wrong is *polarity*: dropping one `!`
# from the release-branch guard inverts the measurement half so that it runs
# only on release branches - the master trend chart silently stops gaining
# points and every pull request's base/head artifacts stop being produced, with
# nothing red anywhere. A substring assertion passes on that edit. Evaluating
# the expression does not.
#
# `inputs` is null on every event but `workflow_dispatch`, which is why the
# dispatch-only jobs can guard on `inputs.render_reports` alone.
TRIGGER_TABLE: tuple[tuple[str, dict[str, Any], set[str]], ...] = (
    (
        "push to master",
        {"event_name": "push", "ref": "refs/heads/master", "inputs": None},
        {"plan", "measure", "track"},
    ),
    (
        "push to a release branch",
        {"event_name": "push", "ref": "refs/heads/release/8.4.0", "inputs": None},
        {"render-reports"},
    ),
    (
        "pull request",
        {"event_name": "pull_request", "ref": "refs/pull/7/merge", "inputs": None},
        {"plan", "measure"},
    ),
    (
        "noise dispatch",
        {
            "event_name": "workflow_dispatch",
            "ref": "refs/heads/master",
            "inputs": {"render_reports": False},
        },
        {"plan", "measure", "noise"},
    ),
    (
        "noise dispatch from a release branch",
        {
            "event_name": "workflow_dispatch",
            "ref": "refs/heads/release/8.4.0",
            "inputs": {"render_reports": False},
        },
        {"plan", "measure", "noise"},
    ),
    (
        "report dispatch",
        {
            "event_name": "workflow_dispatch",
            "ref": "refs/heads/master",
            "inputs": {"render_reports": True},
        },
        {"render-reports"},
    ),
)

GATED_JOBS = ("plan", "measure", "track", "noise", "render-reports")

_EXPRESSION_TOKENS = (("&&", " and "), ("||", " or "), ("!", " not "))


def _evaluate(expression: str, context: dict[str, Any]) -> bool:
    """Evaluate one GitHub Actions `if:` against a synthetic event context.

    Only the operators these five conditions use are supported; anything else
    raises rather than quietly evaluating to something. `!=` is deliberately
    absent from the rewrite table - none of them use it, and rewriting `!`
    before `=` would corrupt it.
    """
    assert "!=" not in expression, f"unsupported operator in {expression!r}"
    body = expression.strip()
    if body.startswith("${{"):
        body = body.removeprefix("${{").removesuffix("}}")
    for token, python in _EXPRESSION_TOKENS:
        body = body.replace(token, python)
    namespace = {
        "github": SimpleNamespace(event_name=context["event_name"], ref=context["ref"]),
        "inputs": SimpleNamespace(**(context["inputs"] or {}))
        if context["inputs"]
        else SimpleNamespace(render_reports=None),
        "startsWith": lambda value, prefix: str(value).startswith(prefix),
    }
    return bool(eval(body, {"__builtins__": {}}, namespace))  # noqa: S307


@pytest.mark.unit
@pytest.mark.parametrize(
    ("event", "context", "expected"),
    TRIGGER_TABLE,
    ids=[row[0] for row in TRIGGER_TABLE],
)
def test_each_event_runs_exactly_the_jobs_it_should(
    benchmark_workflow: dict[Any, Any],
    event: str,
    context: dict[str, Any],
    expected: set[str],
) -> None:
    """The whole gated job graph, per event.

    Three properties this pins that no single job's condition states. A release
    branch renders the report pages, so a release never depends on somebody
    having remembered a manual dispatch - the previous arrangement failed late,
    at `benchmark_report_artifact install`, on a stamp check with no run to
    install from. A release branch contributes no point to the `gh-pages` trend
    series, whose alert threshold was derived from `ubuntu-latest` hardware
    spread and would be meaningless with a second confound in it. And a
    *noise* dispatch aimed at a release branch still measures: guarding the
    measurement half on `github.ref` alone would have disabled it there.
    """
    if event == "push to a release branch":
        assert "release/**" in _push_branches(benchmark_workflow), (
            "a release branch push no longer starts the workflow at all"
        )
    jobs = benchmark_workflow["jobs"]
    running = {name for name in GATED_JOBS if _evaluate(str(jobs[name]["if"]), context)}
    # `track` needs `measure`, so a skipped measurement half skips it anyway;
    # the table states the end result rather than the condition in isolation.
    if "measure" not in running:
        running.discard("track")
    assert running == expected, f"wrong job set on {event}"


@pytest.mark.unit
def test_the_manual_report_dispatch_survives(
    benchmark_workflow: dict[Any, Any],
) -> None:
    """It is the only way to re-render for a commit that has stopped moving.

    A push trigger renders the head it was given. When that artifact expires
    against an unchanged release commit, or a pull request outside a release
    moves a measured path, there is no push left to make - so the dispatch
    input stays.
    """
    condition = str(benchmark_workflow["jobs"]["render-reports"]["if"])
    assert "inputs.render_reports" in condition
    assert "render_reports" in benchmark_workflow[True]["workflow_dispatch"]["inputs"]


@pytest.mark.unit
def test_only_the_trend_chart_uses_the_benchmark_action(
    benchmark_workflow: dict[str, Any], comment_workflow: dict[str, Any]
) -> None:
    """The pull request comparison must not go through the stored baseline.

    `benchmark-action/github-action-benchmark` compares against the value
    recorded on gh-pages, which was measured on whatever CPU that run drew.
    `ubuntu-latest` does not pin the CPU, so that comparison is dominated by
    the runner pool - it once reported a 21% regression for a change that was
    a 1.5x improvement. Pull requests therefore compare head against their own
    merge base, measured on the same runner
    (`scripts/compare_benchmark_runs.py`). Re-introducing the action into the
    comment workflow would quietly restore the confound.

    Two steps, not one: the timing suite and the memory suite are separate
    charts sharing one `dev/bench` data file. They must stay in this single
    job and therefore sequential - both push to `gh-pages`, so splitting them
    across parallel jobs would race for the branch.
    """
    assert len(_steps_using(benchmark_workflow, "track", BENCHMARK_ACTION)) == 2, (
        f"expected exactly two github-action-benchmark steps in "
        f"{BENCHMARK_WORKFLOW.name}'s 'track' job, which owns both trend charts"
    )
    for job in comment_workflow["jobs"]:
        assert not _steps_using(comment_workflow, job, BENCHMARK_ACTION), (
            f"{BENCHMARK_COMMENT_WORKFLOW.name} job {job!r} uses "
            f"{BENCHMARK_ACTION}, which compares against the cross-machine "
            "gh-pages baseline. Pull requests compare against their own merge "
            "base on the same runner instead - see scripts/compare_benchmark_runs.py."
        )


def _repetition_pattern(upload_name: str) -> re.Pattern[str]:
    """The upload name with its templated repetition index made a wildcard."""
    return re.compile(
        "".join(
            r"\d+" if part.endswith("}}") else re.escape(part)
            for part in re.split(r"(\$\{\{.*?\}\})", upload_name)
        )
    )


@pytest.mark.unit
def test_every_downloaded_artifact_is_uploaded_by_measure(
    benchmark_workflow: dict[str, Any], comment_workflow: dict[str, Any]
) -> None:
    """Every consumer downloads an artifact the measure job actually uploads.

    The upload names are templated per repetition (`benchmark-core-<n>`,
    `benchmark-base-<n>`); the consumers hardcode the first repetition. A
    rename of an upload alone would make the download fail after the whole
    measurement already ran.
    """
    uploads = [
        str(step["with"]["name"])
        for step in _steps_using(benchmark_workflow, "measure", UPLOAD_ACTION)
    ]
    patterns = [_repetition_pattern(name) for name in uploads]

    for workflow, path, job in (
        (benchmark_workflow, BENCHMARK_WORKFLOW, "track"),
        (comment_workflow, BENCHMARK_COMMENT_WORKFLOW, "comment"),
    ):
        for download in _steps_using(workflow, job, DOWNLOAD_ACTION):
            downloaded = str(download["with"]["name"])
            assert any(p.fullmatch(downloaded) for p in patterns), (
                f"{path.name} job {job!r} downloads artifact {downloaded!r}, "
                f"which none of benchmark.yml's uploads produce ({uploads})."
            )


@pytest.mark.unit
def test_the_comment_job_compares_head_against_the_merge_base(
    benchmark_workflow: dict[str, Any], comment_workflow: dict[str, Any]
) -> None:
    """The comment job consumes *both* measurements, not just the head one.

    A same-runner comparison needs the merge base measured alongside the head;
    downloading only the head would leave nothing to compare it against but
    the cross-machine baseline this design exists to avoid.
    """
    uploaded = {
        str(step["with"]["name"])
        for step in _steps_using(benchmark_workflow, "measure", UPLOAD_ACTION)
    }
    assert len(uploaded) == 2, (
        "the measure job should upload two artifacts on a pull request - the "
        f"head measurement and the merge base's passes - but uploads {uploaded}"
    )
    downloaded = {
        str(step["with"]["name"])
        for step in _steps_using(comment_workflow, "comment", DOWNLOAD_ACTION)
    }
    assert len(downloaded) == 2, (
        f"{BENCHMARK_COMMENT_WORKFLOW.name} downloads {downloaded}; it needs "
        "both the head and the merge base measurement to compare them."
    )


# `POST /repos/{owner}/{repo}/issues/{number}/comments` - a pull request's
# conversation is an issue timeline, so its comments live under `issues`
PR_COMMENT_ENDPOINT = re.compile(r"issues/[^/\s]+/comments")
# `POST /repos/{owner}/{repo}/commits/{sha}/comments` - a different thing
# entirely. The `commits/{sha}/pulls` lookup in the same script is not matched.
COMMIT_COMMENT_ENDPOINT = re.compile(r"commits/[^/\s]+/comments")


@pytest.mark.unit
def test_the_comparison_is_posted_to_the_pull_request_conversation(
    comment_workflow: dict[str, Any],
) -> None:
    """The comparison must be a pull request comment, not a commit comment.

    It was a commit comment on the head commit first, on the assumption -
    written into the workflow and the former monolithic contributor guide - that they surface in the
    pull request's conversation timeline. They do not: GitHub renders issue
    comments, reviews and review comments there, while a commit comment only
    ever appears on the commit's own page, and a force push orphans it
    besides. The API call succeeded, the job went green, and the table reached
    nobody. That is the failure mode this module exists to catch, so the
    endpoint and the permission it needs are pinned here.
    """
    job = comment_workflow["jobs"]["comment"]
    permissions = job["permissions"]
    assert permissions.get("pull-requests") == "write", (
        "commenting on a pull request's conversation needs "
        f"`pull-requests: write`, but the comment job declares {permissions}. "
        "`contents: write` only buys a commit comment, which is invisible there."
    )
    scripts = "\n".join(str(step.get("run", "")) for step in job["steps"])
    assert PR_COMMENT_ENDPOINT.search(scripts), (
        f"no step in {BENCHMARK_COMMENT_WORKFLOW.name} posts to the pull "
        "request's `issues/{number}/comments` endpoint, so the comparison "
        "reaches no one who reviews the pull request."
    )
    assert not COMMIT_COMMENT_ENDPOINT.search(scripts), (
        f"{BENCHMARK_COMMENT_WORKFLOW.name} posts a commit comment "
        "(`commits/{sha}/comments`). Those do not appear in a pull request's "
        "conversation timeline - use `issues/{number}/comments` instead."
    )


# `gh api --method PATCH .../issues/comments/{id}` edits a comment where it
# stands; `--method DELETE` removes it. `--input` is the only way the job
# sends a request body, so it marks the call that posts the table.
COMMENT_EDIT = re.compile(r"--method\s+PATCH")
COMMENT_DELETE = re.compile(r"--method\s+DELETE")
COMMENT_CREATE = re.compile(r"--input\s+\S+")


@pytest.mark.unit
def test_the_comparison_is_posted_anew_rather_than_edited_in_place(
    comment_workflow: dict[str, Any],
) -> None:
    """One table per pull request, always at the end of the conversation.

    A conversation orders its comments by creation time and an edit does not
    move one, so a comparison edited in place stays where the pull request's
    first push put it - above every commit and review comment made since,
    reading as a measurement of a superseded head, which is indistinguishable
    from the table actually being out of date. Nothing fails when it happens:
    the job goes green and the numbers are current, they just look stale to
    everyone reviewing. So each run posts a fresh comment and deletes the one
    it supersedes.

    The order of those two is part of the invariant, and the reason it is
    pinned here rather than left to the shell: deleting first reads as the
    more obvious way round, and it leaves the pull request with no comparison
    at all whenever the post that should have replaced it fails.
    """
    job = comment_workflow["jobs"]["comment"]
    scripts = "\n".join(str(step.get("run", "")) for step in job["steps"])
    assert not COMMENT_EDIT.search(scripts), (
        f"{BENCHMARK_COMMENT_WORKFLOW.name} edits its comment in place "
        "(`--method PATCH`), which leaves the table wherever the first push "
        "put it - above everything that happened since. Post a new comment "
        "and delete the superseded one instead."
    )
    created = COMMENT_CREATE.search(scripts)
    deleted = COMMENT_DELETE.search(scripts)
    assert created is not None, (
        f"no step in {BENCHMARK_COMMENT_WORKFLOW.name} sends a comment body "
        "(`gh api --input`), so nothing posts the comparison."
    )
    assert deleted is not None, (
        f"{BENCHMARK_COMMENT_WORKFLOW.name} never deletes (`--method DELETE`) "
        "the comment it posted on the previous push, so every push leaves "
        "another full table in the conversation."
    )
    assert created.start() < deleted.start(), (
        f"{BENCHMARK_COMMENT_WORKFLOW.name} deletes the previous comparison "
        "before posting the new one. A failure in between then leaves the "
        "pull request with no comparison at all - post first, delete after."
    )
