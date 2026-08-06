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
"""

from pathlib import Path
import re
from typing import Any

import pytest
import yaml

from tests.auxiliaries import PROJECT_ROOT

WORKFLOW_DIR = PROJECT_ROOT / ".github" / "workflows"
BENCHMARK_WORKFLOW = WORKFLOW_DIR / "benchmark.yml"
BENCHMARK_COMMENT_WORKFLOW = WORKFLOW_DIR / "benchmark-comment.yml"

# workflow-level `env:` entries that both files declare and that must be
# identical - see the "must match" comments in benchmark-comment.yml.
# `BENCHMARK_SUITE_NAME` and `ALERT_THRESHOLD` used to be here too; they now
# live only in benchmark.yml, because only the trend chart still uses the
# benchmark action (see test_only_the_trend_chart_uses_the_benchmark_action).
SHARED_ENV_KEYS = (
    # the filename the head measurement is staged under inside its artifact
    "REPORT_FILENAME",
)


def _load(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text())


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
    """
    assert len(_steps_using(benchmark_workflow, "track", BENCHMARK_ACTION)) == 1, (
        f"expected exactly one github-action-benchmark step in "
        f"{BENCHMARK_WORKFLOW.name}'s 'track' job, which owns the trend chart"
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
