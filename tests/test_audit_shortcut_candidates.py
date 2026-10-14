"""The audit must detect a missing candidate even when lookup hides the omission."""

import json
from types import SimpleNamespace

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
from timezonefinder.shortcut_index import ABSENT, cell_bounds
from timezonefinder.utils import coord2int

pytestmark = pytest.mark.unit


def test_missing_shortcut_is_found_without_using_the_shortcut_as_oracle():
    finder = TimezoneFinder(in_memory=True)
    try:
        assert omission_at(finder, 13.4, 52.5) is None
        finder.shortcuts = SimpleNamespace(
            entry_at=lambda *_: ABSENT,
            # the witness records which cell the omission is in; the oracle is still
            # the polygons alone
            cell_at=finder.shortcuts.cell_at,
        )
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
        finder.shortcuts = SimpleNamespace(
            entry_at=lambda *_: ABSENT,
            # the witness records which cell the omission is in; the oracle is still
            # the polygons alone
            cell_at=finder.shortcuts.cell_at,
        )
        assert omission_at(finder, 13.4, 52.5) is None
    finally:
        finder.cleanup()


def test_limits_count_omissions_beyond_the_retained_witnesses():
    finder = TimezoneFinder(in_memory=True)
    try:
        finder.shortcuts = SimpleNamespace(
            entry_at=lambda *_: ABSENT,
            # the witness records which cell the omission is in; the oracle is still
            # the polygons alone
            cell_at=finder.shortcuts.cell_at,
        )
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


def test_cell_probes_cover_every_stored_cell_corner_and_edge_midpoint():
    """Every grid line is probed from both sides, which is what the edge rule needs.

    A cell owns its north and east edges and not its south or west, so the point that
    tests the rule on one side of a line is the neighbour's own corner on the other.
    Enumerating corners therefore covers both sides without inventing a point - and
    every probe has to land on the intended integer, which is what
    ``query_coordinate`` is for.
    """
    finder = TimezoneFinder(in_memory=True)
    try:
        index = finder.shortcuts
        probes = []
        for cell_id, _ in index.items():
            probes.append(cell_id)
            if len(probes) == 40:
                break
        subset = {cell: None for cell in probes}

        class OnlySome:
            def items(self):
                return ((cell, None) for cell in subset)

        points = list(cell_edge_points(OnlySome()))
        assert len(points) == 8 * len(subset)
        for cell_id in subset:
            x0, y0, x1, y1 = cell_bounds(cell_id)
            corners = {(coord2int(lng), coord2int(lat)) for lng, lat in points}
            assert (x0, y0) in corners
            assert (x1, y1) in corners
        # The grid line between two adjacent cells is probed from both sides, because
        # the eastern cell's x0 is the western cell's x1 plus one and both are corners.
        xs = {coord2int(lng) for lng, _ in points}
        shared_lines = sum(1 for x in xs if x + 1 in xs)
        assert shared_lines >= len(subset) - 1, (
            "adjacent cells' corners must land either side of the line they share"
        )
    finally:
        finder.cleanup()


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
    assert report["grid"]["root_columns"]
    assert report["acceleration_path"] in {"clang", "numba", "python"}
