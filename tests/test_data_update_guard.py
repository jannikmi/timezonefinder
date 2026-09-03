"""What the data-update guard promises, and what would otherwise break silently.

The guard's value is entirely in its baselines staying comparable across releases:
a sample that drifts, a baseline that is not the sample's, or a rewritten file the
update pipeline forgets to commit all produce a green run that reviewed nothing.
Those are the properties asserted here, plus the gate's own arithmetic.
"""

import json

import numpy as np
import pytest
import yaml

from scripts.configs import PROJECT_ROOT
from scripts.data_update_guard import (
    ANSWERS_PATH,
    CHANGED_ANSWER_GATE,
    FROZEN_SAMPLE_PATH,
    GUARD_FIXTURES_DIR,
    N_SAMPLE_POINTS,
    NO_ZONE,
    RELEASED_VARIANT,
    PAYLOAD_PATH,
    answer_sample,
    changed_indices,
    check,
    load_frozen_sample,
    parse_answers,
    payload_metrics,
    render_answers,
)
from tests.auxiliaries import BENCHMARK_FIXTURES_DIR, WORKFLOW_DIR

UPDATE_WORKFLOW = WORKFLOW_DIR / "check_data_updates.yml"


def _committed_answers() -> tuple[list[str], list[str]]:
    return parse_answers(ANSWERS_PATH.read_text(encoding="utf-8"))


@pytest.mark.unit
def test_the_frozen_sample_is_not_a_benchmark_fixture() -> None:
    """``update_data.sh`` regenerates the benchmark fixtures on every release.

    A baseline drawn from a directory that moves with the data compares answers for
    two different point sets, which reads exactly like a release that changed
    nothing. The separation is the guarantee, so it is asserted rather than assumed.
    """
    assert GUARD_FIXTURES_DIR != BENCHMARK_FIXTURES_DIR
    assert BENCHMARK_FIXTURES_DIR not in FROZEN_SAMPLE_PATH.parents
    assert len(load_frozen_sample()) == N_SAMPLE_POINTS


@pytest.mark.unit
def test_the_committed_baseline_describes_the_frozen_sample() -> None:
    """Point for point, or no changed-answer rate means anything."""
    coordinates, answers = _committed_answers()
    expected, _ = parse_answers(
        render_answers(load_frozen_sample(), [NO_ZONE] * N_SAMPLE_POINTS)
    )
    assert coordinates == expected
    assert len(answers) == N_SAMPLE_POINTS


@pytest.mark.unit
def test_the_committed_baseline_is_what_the_packaged_data_answers() -> None:
    """The baseline is only a baseline while it describes the data beside it.

    ``update_data.sh`` rewrites it on every release, so a mismatch here means the
    packaged data was regenerated without running the guard - the same failure mode
    the benchmark fixtures' ``DATA_VERSION`` pinning covers, and equally silent.
    """
    _, committed = _committed_answers()
    assert committed == answer_sample(load_frozen_sample())


@pytest.mark.unit
def test_the_committed_payload_record_describes_the_packaged_data() -> None:
    recorded = json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))
    assert recorded == payload_metrics()


@pytest.mark.unit
def test_a_printed_coordinate_reproduces_the_answer_beside_it() -> None:
    """The diff is read by a human, who has to be able to re-query a moved line.

    Rendering at the packaged coordinates' own resolution is what makes that true;
    a shorter rendering would round points across a border and answer differently.
    """
    coordinates, answers = _committed_answers()
    sampled = [0, 1, len(coordinates) // 2, len(coordinates) - 1]
    points = np.array(
        [[float(part) for part in coordinates[i].split(",")] for i in sampled]
    )
    assert answer_sample(points) == [answers[i] for i in sampled]


@pytest.mark.unit
def test_the_changed_rate_counts_answers_rather_than_lines() -> None:
    baseline = ["Europe/Berlin", "Europe/Paris", "Asia/Hebron"]
    assert changed_indices(baseline, list(baseline)) == []
    assert changed_indices(
        baseline, ["Europe/Berlin", "Europe/Rome", "Asia/Jerusalem"]
    ) == [1, 2]


def _isolated_baselines(monkeypatch, tmp_path, answers: list[str]):
    """Point the guard at throwaway copies of the two files an update rewrites."""
    for name, path in (("ANSWERS_PATH", ANSWERS_PATH), ("PAYLOAD_PATH", PAYLOAD_PATH)):
        copy = tmp_path / path.name
        copy.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        monkeypatch.setattr(f"scripts.data_update_guard.{name}", copy)
    monkeypatch.setattr("scripts.data_update_guard.GUARD_FIXTURES_DIR", tmp_path)
    monkeypatch.setattr(
        "scripts.data_update_guard.answer_sample", lambda *args, **kwargs: answers
    )
    return tmp_path / ANSWERS_PATH.name


@pytest.mark.unit
def test_the_gate_blocks_a_dataset_that_moved_too_many_answers(
    monkeypatch, tmp_path
) -> None:
    """Above the threshold the run stops, and it still leaves the diff to review."""
    _, committed = _committed_answers()
    changed = int(len(committed) * CHANGED_ANSWER_GATE) + 1
    mangled = ["Etc/GMT+0"] * changed + committed[changed:]
    answers_path = _isolated_baselines(monkeypatch, tmp_path, mangled)

    assert check() == 1
    # the blocked run's own artifact: what a reviewer diffs before deciding
    rewritten, rewritten_answers = parse_answers(
        answers_path.read_text(encoding="utf-8")
    )
    assert rewritten_answers == mangled
    assert rewritten == parse_answers(render_answers(load_frozen_sample(), mangled))[0]


@pytest.mark.unit
def test_a_change_at_the_gate_still_passes(monkeypatch, tmp_path) -> None:
    """The threshold is what is refused *above*, so the boundary itself is allowed."""
    _, committed = _committed_answers()
    changed = int(len(committed) * CHANGED_ANSWER_GATE)
    moved = ["Etc/GMT+0"] * changed + committed[changed:]
    _isolated_baselines(monkeypatch, tmp_path, moved)

    assert check() == 0


@pytest.mark.unit
def test_a_sample_the_baseline_does_not_describe_is_refused(
    monkeypatch, tmp_path
) -> None:
    """A truncated or redrawn baseline reports no rate at all, rather than a wrong one."""
    _, committed = _committed_answers()
    answers_path = _isolated_baselines(monkeypatch, tmp_path, committed)
    lines = answers_path.read_text(encoding="utf-8").splitlines()
    answers_path.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")

    assert check() == 1


@pytest.mark.unit
def test_another_dataset_variant_is_skipped_rather_than_measured(
    monkeypatch, tmp_path
) -> None:
    """``--dataset=same-since-now`` merges ~440 zones into ~90.

    Those points answer differently by construction, so measuring them against this
    baseline reports thousands of changed lines that say nothing about the upstream
    release - and, before this skip, stopped every reduced-dataset run at the gate.
    Nothing is written either: the baseline belongs to one dataset.
    """
    answers_path = _isolated_baselines(monkeypatch, tmp_path, ["Etc/GMT+0"] * 3)
    before = answers_path.read_text(encoding="utf-8")

    assert check(variant="-with-oceans-now") == 0
    assert answers_path.read_text(encoding="utf-8") == before


@pytest.mark.unit
def test_the_update_script_hands_the_guard_its_dataset_variant() -> None:
    """The skip above only ever fires if the variant actually reaches the guard.

    ``update_data.sh`` composes it and is the only caller, so a run that stopped
    passing it would silently measure a reduced dataset against the full one's
    baseline again - the behaviour this pairing exists to prevent.
    """
    script = (PROJECT_ROOT / "update_data.sh").read_text(encoding="utf-8")
    assert "scripts.data_update_guard check --variant" in script
    assert RELEASED_VARIANT in script


@pytest.mark.unit
def test_a_refused_dataset_leaves_its_diff_behind() -> None:
    """A tripped gate ends the regeneration step, so every later step is skipped.

    The rewritten baseline then exists only on the runner, and the log carries just
    the first ten changed answers - in exactly the case a maintainer has to review the
    whole diff. Only a step that runs *on failure* can still carry it off the runner.
    """
    workflow = yaml.safe_load(UPDATE_WORKFLOW.read_text(encoding="utf-8"))
    uploads = [
        step
        for job in workflow["jobs"].values()
        for step in job.get("steps", [])
        if str(step.get("uses", "")).startswith("actions/upload-artifact")
        and str(GUARD_FIXTURES_DIR.relative_to(PROJECT_ROOT))
        in str(step["with"]["path"])
    ]
    assert len(uploads) == 1, "the guard's diff is uploaded by exactly one step"
    assert "failure()" in uploads[0]["if"]


@pytest.mark.unit
def test_the_update_pipeline_commits_what_the_guard_rewrites() -> None:
    """A baseline the update forgets to stage never advances, so every later release
    is measured against the data of the one before it - and the job's own leftover
    check turns that into a failed update rather than a wrong comparison. Naming the
    directory here is what keeps the two lists from drifting apart quietly.
    """
    workflow = yaml.safe_load(UPDATE_WORKFLOW.read_text(encoding="utf-8"))
    staged = "\n".join(
        str(step.get("run", ""))
        for job in workflow["jobs"].values()
        for step in job.get("steps", [])
        if "git add" in str(step.get("run", ""))
    )
    assert staged, "no step in the update workflow stages anything any more"
    assert str(GUARD_FIXTURES_DIR.relative_to(PROJECT_ROOT)) in staged
