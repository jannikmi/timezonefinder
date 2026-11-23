"""The shortcut index figure in ``docs/architecture.rst`` and the script that draws it.

The figure makes claims about the packaged data - which cases its three points show,
that only two zones meet in its window - so those claims are asserted here against the
data, and the committed SVG is held to a fresh render. A data update that moves either
fails here rather than leaving the docs describing an index that no longer exists.
"""

import json
import xml.etree.ElementTree as ElementTree

import pytest

pytest.importorskip("matplotlib", reason="the `benchmark` dependency group")

from timezonefinder import TimezoneFinder  # noqa: E402

from scripts.configs import DOC_ROOT  # noqa: E402
from scripts.shortcut_index_figure import (  # noqa: E402
    FIGURE_PATH,
    LAND_ZONES,
    QUERIES,
    RIVERS_PATH,
    WINDOW,
    check_aligned,
    describe,
    extract_rivers,
    leaf_cells,
    render,
    replay,
)


@pytest.fixture(scope="module")
def tf() -> TimezoneFinder:
    return TimezoneFinder()


@pytest.mark.unit
def test_each_point_still_shows_the_case_it_is_drawn_for(tf) -> None:
    # the caption and the docs prose name these three cases; if the data moves a point
    # into another one, the figure would explain something it does not show
    colmar, lorraine, kehl = (replay(tf, point) for point in QUERIES)

    assert colmar.candidates == () and colmar.answer == "Europe/Paris"

    assert len(lorraine.tested) == 1
    assert tf.zone_name_from_boundary_id(lorraine.tested[0]) == lorraine.answer

    assert len(kehl.tested) == 1
    assert tf.zone_name_from_boundary_id(kehl.tested[0]) != kehl.answer
    assert kehl.answer == "Europe/Berlin"


@pytest.mark.unit
def test_a_replayed_lookup_answers_what_timezone_at_answers(tf) -> None:
    for point in QUERIES:
        assert replay(tf, point).answer == tf.timezone_at(lng=point.lng, lat=point.lat)


@pytest.mark.unit
def test_the_window_holds_two_land_zones_and_unsplit_cells_of_both(tf) -> None:
    zones = set()
    unsplit = set()
    for cell in leaf_cells(tf, WINDOW):
        lng = (cell.bounds[0] + cell.bounds[2]) / 2
        lat = (cell.bounds[1] + cell.bounds[3]) / 2
        entry = tf.shortcuts.entry_at(lng, lat)
        if entry >= 0:
            zone = tf.zone_name_from_id(entry)
            zones.add(zone)
            if cell.is_root:
                unsplit.add(zone)
        else:
            zones.update(
                tf.zone_name_from_boundary_id(int(c))
                for c in tf.shortcuts.candidates_of(entry)
            )
    assert zones == set(LAND_ZONES)
    assert unsplit == set(LAND_ZONES)


@pytest.mark.unit
def test_a_window_off_the_root_grid_is_refused() -> None:
    check_aligned(WINDOW)
    # 47.75 degrees is not a multiple of 0.75 from the south pole: drawing from it put
    # the root grid lines where the index has no cell edge
    with pytest.raises(ValueError, match="root-cell edge"):
        check_aligned((6.75, 47.75, 9.75, 49.25))


@pytest.mark.unit
def test_the_explanation_names_the_untested_last_zone(tf) -> None:
    text = describe(tf, replay(tf, QUERIES[2]))
    assert "does not contain it" in text
    assert "Europe/Berlin is the only zone left" in text


@pytest.mark.unit
def test_the_figure_is_deterministic_and_pre_commit_clean(tf) -> None:
    import matplotlib

    svg = render(tf)
    with matplotlib.rc_context({"axes.grid": True, "lines.solid_capstyle": "butt"}):
        # another renderer's global style must not leak into a committed artifact
        assert svg == render(tf)
    ElementTree.fromstring(svg)
    assert "font-family: 'DejaVu Sans'" in svg
    assert "dc:date" not in svg
    assert svg.endswith("\n") and not svg.endswith("\n\n")
    assert not any(line != line.rstrip() for line in svg.splitlines())


@pytest.mark.unit
def test_the_committed_figure_is_a_render_of_the_packaged_data(tf) -> None:
    assert FIGURE_PATH.read_text(encoding="utf-8") == render(tf), (
        f"{FIGURE_PATH} is stale - run `make shortcut-index-figure`"
    )


@pytest.mark.unit
def test_the_committed_figure_is_where_the_docs_page_looks_for_it() -> None:
    assert FIGURE_PATH.parent == DOC_ROOT
    assert FIGURE_PATH.name in (DOC_ROOT / "architecture.rst").read_text(
        encoding="utf-8"
    )


@pytest.mark.unit
def test_the_river_excerpt_keeps_only_the_runs_near_the_window(tmp_path) -> None:
    west, south, east, north = WINDOW
    inside = [[west + 0.5, south + 0.5], [west + 0.6, south + 0.6]]
    outside = [[east + 5, north + 5], [east + 6, north + 6]]
    source = tmp_path / "rivers.geojson"
    source.write_text(
        json.dumps(
            {
                "features": [
                    {
                        "geometry": {
                            "coordinates": inside + outside,
                            "type": "LineString",
                        },
                        "properties": {"name": "Near"},
                    },
                    {
                        "geometry": {"coordinates": outside, "type": "LineString"},
                        "properties": {"name": "Far"},
                    },
                    {"geometry": None, "properties": {"name": "Empty"}},
                ]
            }
        ),
        encoding="utf-8",
    )
    excerpt = extract_rivers(source, WINDOW)
    assert [river["name"] for river in excerpt["rivers"]] == ["Near"]
    assert excerpt["rivers"][0]["lines"] == [inside]


@pytest.mark.unit
def test_the_committed_river_excerpt_names_its_source() -> None:
    excerpt = json.loads(RIVERS_PATH.read_text(encoding="utf-8"))
    assert "Natural Earth" in excerpt["source"]
    assert {"Rhin", "Rhine"} <= {river["name"] for river in excerpt["rivers"]}
