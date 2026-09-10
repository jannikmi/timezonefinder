"""Gate data updates on sampled candidate completeness against the new dataset.

The slow tox environment runs these streams on every PR, including data updates.
Unlike comparing two shortcut-based answers, full-polygon containment can detect a
polygon both answers silently omitted. These samples cover every cell/ring edge,
not every possible coordinate; they are regression guards, not a coverage proof.
"""

import itertools
import json
from collections.abc import Iterable
from types import SimpleNamespace

import h3.api.basic_int as h3
import pytest

from scripts.audit_shortcut_candidates import (
    audit_points,
    cell_edge_points,
    seam_points,
    source_edge_points,
)
from timezonefinder import TimezoneFinder
from timezonefinder.configs import SHORTCUT_H3_RES
from timezonefinder.shortcut_index import ABSENT


def assert_candidate_coverage(
    finder: TimezoneFinder, points: Iterable[tuple[float, float]]
) -> None:
    report = audit_points(finder, points, witness_limit=5)
    assert report["sample_stream_exhausted"], (
        "the release guard must not truncate its stream"
    )
    assert report["points_with_omissions"] == 0, (
        "Packaged shortcuts omit containing polygons. Replay the longitude/latitude "
        "witnesses with scripts.audit_shortcut_candidates before releasing this data:\n"
        + json.dumps(report, indent=2)
    )


@pytest.mark.slow
def test_packaged_shortcuts_cover_curved_cell_edges(timezonefinder_in_memory):
    cells = itertools.chain.from_iterable(
        h3.cell_to_children(root, SHORTCUT_H3_RES) for root in h3.get_res0_cells()
    )
    assert_candidate_coverage(timezonefinder_in_memory, cell_edge_points(cells))


@pytest.mark.slow
def test_packaged_shortcuts_cover_source_edges(timezonefinder_in_memory):
    assert_candidate_coverage(
        timezonefinder_in_memory, source_edge_points(timezonefinder_in_memory)
    )


@pytest.mark.slow
def test_packaged_shortcuts_cover_coordinate_seams(timezonefinder_in_memory):
    assert_candidate_coverage(timezonefinder_in_memory, seam_points())


@pytest.mark.unit
def test_a_missing_shortcut_fails_the_release_guard():
    finder = TimezoneFinder(in_memory=True)
    try:
        finder.shortcuts = SimpleNamespace(entry_of=lambda _: ABSENT)
        cell = h3.latlng_to_cell(52.5, 13.4, SHORTCUT_H3_RES)
        with pytest.raises(AssertionError, match="missing_polygon_ids"):
            assert_candidate_coverage(finder, cell_edge_points([cell]))
    finally:
        finder.cleanup()
