"""The audit must detect a missing candidate even when lookup hides the omission."""

import json
from types import SimpleNamespace

import h3.api.basic_int as h3
import numpy as np
import pytest

from scripts.audit_shortcut_candidates import (
    audit_points,
    cell_edge_points,
    main,
    omission_at,
    query_coordinate,
    seam_points,
    source_edge_points,
)
from timezonefinder import TimezoneFinder
from timezonefinder.shortcut_index import ABSENT
from timezonefinder.utils import coord2int

pytestmark = pytest.mark.unit


def test_missing_shortcut_is_found_without_using_the_shortcut_as_oracle():
    finder = TimezoneFinder(in_memory=True)
    try:
        assert omission_at(finder, 13.4, 52.5) is None
        finder.shortcuts = SimpleNamespace(entry_of=lambda _: ABSENT)
        finding = omission_at(finder, 13.4, 52.5)
        assert finding is not None
        assert finding["missing_polygon_ids"]
        assert finding["candidate_polygon_ids"] == []
        assert finding["containing_zones"] == ["Europe/Berlin"]
        assert finding["timezone_at"] is None
        assert finding["answer_outside_containing_zones"]
    finally:
        finder.cleanup()


def test_an_omission_can_leave_the_timezone_answer_correct(monkeypatch):
    monkeypatch.setattr(
        TimezoneFinder, "_iter_boundaries_in_shortcut", lambda *a, **k: []
    )
    finder = TimezoneFinder(in_memory=True)
    try:
        finding = omission_at(finder, 13.4, 52.5)
        assert finding is not None
        assert finding["missing_polygon_ids"]
        assert not finding["answer_outside_containing_zones"]
    finally:
        finder.cleanup()


def test_holes_are_checked_before_reporting_a_bbox_candidate(monkeypatch):
    finder = TimezoneFinder(in_memory=True)
    try:
        # A point in an exterior bbox is insufficient: the polygon predicate must run.
        monkeypatch.setattr(TimezoneFinder, "inside_of_polygon", lambda *a: False)
        finder.shortcuts = SimpleNamespace(entry_of=lambda _: ABSENT)
        assert omission_at(finder, 13.4, 52.5) is None
    finally:
        finder.cleanup()


def test_limits_count_omissions_beyond_the_retained_witnesses():
    finder = TimezoneFinder(in_memory=True)
    try:
        finder.shortcuts = SimpleNamespace(entry_of=lambda _: ABSENT)
        report = audit_points(finder, [(13.4, 52.5)] * 4, max_points=3, witness_limit=1)
        assert report["points_checked"] == 3
        assert report["points_with_omissions"] == 3
        assert report["answers_outside_containing_zones_at_omissions"] == 3
        assert len(report["witnesses"]) == 1
        assert report["witnesses_truncated"]
        assert not report["sample_stream_exhausted"]
        assert not report["completeness_proven"]
    finally:
        finder.cleanup()


def test_empty_input_cannot_report_a_successful_audit():
    with pytest.raises(ValueError, match="no points"):
        audit_points(None, [])


@pytest.mark.parametrize(
    "point", [(float("nan"), 0), (0, float("inf")), (181, 0), (0, -91)]
)
def test_invalid_replay_coordinates_fail(point):
    with pytest.raises(ValueError, match="invalid"):
        omission_at(None, *point)


@pytest.mark.parametrize("cell", [0x8400001FFFFFFFF, *h3.get_pentagons(4)])
def test_cell_probes_include_vertices_and_both_sides_of_edges(cell):
    points = list(cell_edge_points([cell]))
    boundary = h3.cell_to_boundary(cell)
    assert len(points) == 3 * len(boundary)
    assert points[: len(boundary)] == [(lng, lat) for lat, lng in boundary]
    memberships = {h3.latlng_to_cell(lat, lng, 4) for lng, lat in points}
    assert cell in memberships
    assert len(memberships) > 1


def test_source_edges_keep_the_planar_antimeridian_frame_and_include_holes():
    ring = np.array([[-1790000000, 1790000000, 1790000000], [0, 0, 10000000]])

    class Rings:
        def __len__(self):
            return 1

        def coords_of(self, _):
            return ring

    finder = SimpleNamespace(boundaries=Rings(), holes=Rings())
    points = list(source_edge_points(finder))
    assert len(points) == 12
    assert points[3] == (0.0, 0.0)
    assert points[:6] == points[6:]


@pytest.mark.parametrize(
    "scaled", [-26224600, 26224600, -1799999999, 1799999999, -123.5, 123.5, 0]
)
def test_source_queries_reach_the_intended_integer_coordinates(scaled):
    assert coord2int(query_coordinate(scaled)) == int(scaled)


def test_seams_include_exact_poles_and_both_antimeridian_representations():
    points = set(seam_points())
    assert {(0.0, -90.0), (0.0, 90.0), (-180.0, 0.0), (180.0, 0.0)} <= points


def test_replay_cli_records_identity_and_returns_failure_on_omissions(
    tmp_path, monkeypatch
):
    points = tmp_path / "points.json"
    points.write_text("[[13.4, 52.5]]", encoding="utf-8")
    output = tmp_path / "audit.json"
    monkeypatch.setattr(
        TimezoneFinder, "_iter_boundaries_in_shortcut", lambda *a, **k: []
    )
    assert main(["--points", str(points), "--output", str(output)]) == 1
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["points_with_omissions"] == 1
    assert report["sample_stream_exhausted"]
    assert report["probe_mode"] == "replay"
    assert report["data_sha256"]
    assert report["replay_sha256"]
    assert report["h3_versions"]
    assert report["acceleration_path"] in {"clang", "numba", "python"}
