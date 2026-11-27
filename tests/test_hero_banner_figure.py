"""The README banner and the script that draws it.

The banner makes claims about the packaged data - which zone each of its points is in,
and that one of them lies between the real border and the simplified one - so those
claims are asserted here against the data, and the committed SVG is held to a fresh
render. A data update that moves either fails here rather than leaving the README
showing a lookup the package no longer makes.
"""

import json
import xml.etree.ElementTree as ElementTree

import pytest

pytest.importorskip("matplotlib", reason="the `benchmark` dependency group")

from timezonefinder import TimezoneFinder  # noqa: E402

from scripts.configs import DOC_ROOT  # noqa: E402
from scripts.hero_banner_figure import (  # noqa: E402
    EAST_POINT,
    FIGURE_PATH,
    GAP_POINT,
    MAP_PATH,
    PNG_PATH,
    SIMPLIFICATION_METRES,
    WEST_POINT,
    WEST_TO_EAST,
    border,
    clip_line,
    decode,
    encode,
    land,
    render,
    simplified_answer,
    simplify,
    window,
)


@pytest.fixture(scope="module")
def tf() -> TimezoneFinder:
    return TimezoneFinder()


@pytest.mark.unit
def test_each_point_still_shows_the_case_it_is_drawn_for(tf) -> None:
    shape = border(tf)
    west, east = WEST_TO_EAST
    for point, zone in ((WEST_POINT, west), (EAST_POINT, east)):
        assert tf.timezone_at(lng=point.lng, lat=point.lat) == zone
        assert simplified_answer(shape, point) == zone
    # the banner's point: right with every vertex, an hour wrong once simplified
    assert tf.timezone_at(lng=GAP_POINT.lng, lat=GAP_POINT.lat) == west
    assert simplified_answer(shape, GAP_POINT) == east


@pytest.mark.unit
def test_only_the_two_zones_meet_in_the_window(tf) -> None:
    west, south, east, north = window()
    zones = {
        tf.timezone_at(
            lng=west + (east - west) * i / 20, lat=south + (north - south) * j / 10
        )
        for i in range(21)
        for j in range(11)
    }
    assert zones == set(WEST_TO_EAST)


@pytest.mark.unit
def test_the_comparison_line_keeps_the_stated_tolerance(tf) -> None:
    shape = border(tf)
    assert shape.simplified_in_view < shape.vertices_in_view
    for run in shape.runs:
        simple = simplify(run, SIMPLIFICATION_METRES)
        assert simple[0] == run[0] and simple[-1] == run[-1]
        assert set(simple) <= set(run)


@pytest.mark.unit
def test_land_is_closed_counter_clockwise_along_the_box() -> None:
    box = (0.0, 0.0, 10.0, 10.0)
    # a coast crossing west to east, land on its left - the north half
    coast = [[(-1.0, 5.0), (11.0, 5.0)]]
    (ring,) = land(coast, box)
    assert ring == [(0.0, 5.0), (10.0, 5.0), (10.0, 10.0), (0.0, 10.0)]
    # an island inside the box is land of its own
    island = [(2.0, 2.0), (3.0, 2.0), (3.0, 3.0), (2.0, 2.0)]
    assert island[:-1] in land(coast + [island], box)


@pytest.mark.unit
def test_a_line_is_cut_to_the_runs_inside_the_box() -> None:
    box = (0.0, 0.0, 10.0, 10.0)
    line = [(-5.0, 5.0), (5.0, 5.0), (5.0, 15.0), (6.0, 15.0), (6.0, 5.0)]
    assert clip_line(line, box) == [
        [(0.0, 5.0), (5.0, 5.0), (5.0, 10.0)],
        [(6.0, 10.0), (6.0, 5.0)],
    ]


@pytest.mark.unit
def test_the_excerpt_encoding_round_trips_to_a_metre() -> None:
    line = [(24.123456, 65.8), (24.2, 65.812345)]
    assert decode(encode(line)) == [(24.12346, 65.8), (24.2, 65.81234)]


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
    assert "OpenStreetMap contributors" in svg
    assert svg.endswith("\n") and not svg.endswith("\n\n")
    assert not any(line != line.rstrip() for line in svg.splitlines())


@pytest.mark.unit
def test_the_committed_figure_is_a_render_of_the_packaged_data(tf) -> None:
    assert FIGURE_PATH.read_text(encoding="utf-8") == render(tf), (
        f"{FIGURE_PATH} is stale - run `make hero-banner`"
    )


@pytest.mark.unit
def test_the_banner_is_where_the_readme_and_the_docs_look_for_it() -> None:
    assert FIGURE_PATH.parent == PNG_PATH.parent == DOC_ROOT
    assert PNG_PATH.exists()
    readme = (DOC_ROOT.parent / "README.md").read_text(encoding="utf-8")
    assert f"/master/docs/{PNG_PATH.name}" in readme
    assert FIGURE_PATH.name in (DOC_ROOT / "index.rst").read_text(encoding="utf-8")


@pytest.mark.unit
def test_the_committed_map_excerpt_names_its_source_and_both_towns() -> None:
    excerpt = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    assert "OpenStreetMap" in excerpt["source"] and "ODbL" in excerpt["source"]
    names = {place["name"] for place in excerpt["layers"]["places"]}
    assert names == {"Haparanda", "Tornio"}
