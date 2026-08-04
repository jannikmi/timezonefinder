"""Assert the constants shared by the two benchmark workflows agree.

GitHub Actions workflows cannot import constants from each other, so
`.github/workflows/benchmark.yml` (measure + record) and
`.github/workflows/benchmark-comment.yml` (compare + comment) repeat the
same literals, held together only by a "must match ..." comment.

A one-sided edit fails silently in the worst possible way: the comparison
job would look up a suite name, download a filename or apply a threshold
that no longer corresponds to what the measuring job produced, so the PR
comment compares against nothing (or the job never runs) - with no error
anywhere. This test is the missing enforcement of those comments.
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
# identical - see the "must match" comments in benchmark-comment.yml
SHARED_ENV_KEYS = (
    # the key the stored trend data is filed under
    "BENCHMARK_SUITE_NAME",
    # noise-derived, documented in benchmark.yml
    "ALERT_THRESHOLD",
    # the filename the report is staged under inside its artifact
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


def _benchmark_action_step(workflow: dict[str, Any], job: str) -> dict[str, Any]:
    steps = workflow["jobs"][job]["steps"]
    matches = [
        step
        for step in steps
        if str(step.get("uses", "")).startswith(
            "benchmark-action/github-action-benchmark"
        )
    ]
    assert len(matches) == 1, (
        f"expected exactly one github-action-benchmark step in job {job!r}, "
        f"found {len(matches)}"
    )
    return matches[0]


# where the trend data lives: the recording job writes it, the comparing job
# reads it. Different values would again compare against nothing.
STORAGE_INPUTS = ("gh-pages-branch", "benchmark-data-dir-path")


@pytest.mark.unit
@pytest.mark.parametrize("input_name", STORAGE_INPUTS)
def test_trend_storage_location_matches(
    input_name: str,
    benchmark_workflow: dict[str, Any],
    comment_workflow: dict[str, Any],
) -> None:
    recording = _benchmark_action_step(benchmark_workflow, "track")["with"]
    comparing = _benchmark_action_step(comment_workflow, "comment")["with"]
    assert recording[input_name] == comparing[input_name], (
        f"the benchmark action's {input_name!r} differs between "
        f"{BENCHMARK_WORKFLOW.name} ({recording[input_name]!r}) and "
        f"{BENCHMARK_COMMENT_WORKFLOW.name} ({comparing[input_name]!r}): the "
        "comparison would read a different location than the one master writes."
    )


@pytest.mark.unit
def test_downloaded_artifact_name_matches_uploaded_one(
    benchmark_workflow: dict[str, Any], comment_workflow: dict[str, Any]
) -> None:
    """The comment job downloads the artifact the measure job uploaded.

    The upload name is templated per repetition (`benchmark-core-<n>`); the
    consumers hardcode the first repetition. A rename of the upload alone
    would make the download fail after the whole measurement already ran.
    """
    upload = next(
        step
        for step in benchmark_workflow["jobs"]["measure"]["steps"]
        if str(step.get("uses", "")).startswith("actions/upload-artifact")
    )
    upload_name = str(upload["with"]["name"])
    # the only templated part is the repetition index
    expected = re.compile(
        "".join(
            r"\d+" if part.endswith("}}") else re.escape(part)
            for part in re.split(r"(\$\{\{.*?\}\})", upload_name)
        )
    )

    for workflow, path, job in (
        (benchmark_workflow, BENCHMARK_WORKFLOW, "track"),
        (comment_workflow, BENCHMARK_COMMENT_WORKFLOW, "comment"),
    ):
        download = next(
            step
            for step in workflow["jobs"][job]["steps"]
            if str(step.get("uses", "")).startswith("actions/download-artifact")
        )
        downloaded = str(download["with"]["name"])
        assert expected.fullmatch(downloaded), (
            f"{path.name} job {job!r} downloads artifact {downloaded!r}, which "
            f"does not match the name uploaded by benchmark.yml "
            f"({upload_name!r})."
        )
