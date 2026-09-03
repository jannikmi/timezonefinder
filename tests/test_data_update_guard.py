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
    GATE_TRIPPED_EXIT,
    GUARD_FIXTURES_DIR,
    N_SAMPLE_POINTS,
    NO_ZONE,
    RELEASED_VARIANT,
    PAYLOAD_PATH,
    answer_sample,
    changed_indices,
    check,
    load_frozen_sample,
    main,
    parse_answers,
    payload_metrics,
    render_answers,
)
from tests.auxiliaries import BENCHMARK_FIXTURES_DIR, WORKFLOW_DIR

UPDATE_WORKFLOW = WORKFLOW_DIR / "check_data_updates.yml"
RELEASE_WORKFLOW = WORKFLOW_DIR / "release_data_update.yml"


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
    """Above the threshold the dataset is refused - and still fully prepared.

    The refusal has its own exit code because it is not a broken run: the release is
    finished and opened as a draft, so the answers that moved are read as a pull
    request diff. Only the publication is withheld.
    """
    _, committed = _committed_answers()
    changed = int(len(committed) * CHANGED_ANSWER_GATE) + 1
    mangled = ["Etc/GMT+0"] * changed + committed[changed:]
    answers_path = _isolated_baselines(monkeypatch, tmp_path, mangled)

    assert check() == GATE_TRIPPED_EXIT
    # what a reviewer diffs before deciding, in the pull request the update opens
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
def test_the_command_line_takes_a_variant_that_starts_with_a_hyphen() -> None:
    """Every real variant does: ``-with-oceans``, ``-now``, ``-with-oceans-now``.

    Quoting does not help - argparse reads the value as an option unless it is glued
    on with ``=`` - and the failure is a usage error at the one moment the pipeline
    needs an answer. Driven through ``main`` because that is the half a call from the
    shell exercises and a call to ``check`` does not.
    """
    assert main(["check", f"--variant={RELEASED_VARIANT}-now"]) == 0


@pytest.mark.unit
def test_the_update_script_hands_the_guard_its_dataset_variant() -> None:
    """The skip above only ever fires if the variant actually reaches the guard.

    ``update_data.sh`` composes it and is the only caller, so a run that stopped
    passing it would silently measure a reduced dataset against the full one's
    baseline again - the behaviour this pairing exists to prevent.
    """
    script = (PROJECT_ROOT / "update_data.sh").read_text(encoding="utf-8")
    assert 'scripts.data_update_guard check --variant="$VARIANT"' in script
    assert RELEASED_VARIANT in script


@pytest.mark.unit
def test_the_script_and_the_guard_agree_on_what_a_refusal_exits() -> None:
    """The one number that has to mean the same thing in two languages.

    ``update_data.sh`` tells a refusal apart from a failure by this code alone. If the
    two drift, a refused dataset becomes a failed run again: no release is prepared,
    no draft is opened, and the answers nobody can see are exactly the ones somebody
    had to look at.
    """
    script = (PROJECT_ROOT / "update_data.sh").read_text(encoding="utf-8")
    assert f"GUARD_REFUSED_EXIT={GATE_TRIPPED_EXIT}" in script


@pytest.mark.unit
def test_a_refused_update_is_opened_as_a_draft() -> None:
    """Preparing the release is how the answer diff reaches a reviewer at all.

    The pull request has to be opened, and it has to be opened in a state nothing
    publishes. Both halves are asserted because either alone is a silent failure: no
    draft flag auto-releases a dataset the guard refused, and no refusal plumbing
    means the flag is never set.
    """
    steps = yaml.safe_load(UPDATE_WORKFLOW.read_text(encoding="utf-8"))["jobs"][
        "open_update_pr"
    ]["steps"]
    create = next(step for step in steps if "gh pr create" in str(step.get("run", "")))
    assert "--draft" in create["run"]
    assert "GUARD_REFUSED" in str(create.get("env", {}))


@pytest.mark.unit
def test_a_draft_update_is_never_merged() -> None:
    """Where the refusal actually withholds the release.

    The merge job is triggered by a *green* pipeline, and green says the data is valid
    - never that it is the data anybody meant to publish. Without this condition an
    update the guard refused is merged and tagged on the strength of passing CI.
    """
    jobs = yaml.safe_load(RELEASE_WORKFLOW.read_text(encoding="utf-8"))["jobs"]
    merge = next(
        step
        for step in jobs["merge_and_release"]["steps"]
        if "gh pr merge" in str(step.get("run", ""))
    )
    assert "draft != 'true'" in merge["if"]


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
