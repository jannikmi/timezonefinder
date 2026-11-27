"""The README banner, the border-town figure, and the script that draws them.

Both figures make claims about the packaged data - which zone each point and building is
in, and which local time each side shows - so those claims are asserted here against the
data, and the committed SVGs are held to fresh renders. The border-town figure also
states a measurement of ``tzfpy``; the record it is drawn from is checked against the
data and against the prose that quotes it. A data update that moves any of them fails
here rather than leaving the README showing a lookup the package no longer makes.
"""

import json
import xml.etree.ElementTree as ElementTree

import pytest

pytest.importorskip("matplotlib", reason="the `benchmark` dependency group")

from timezonefinder import TimezoneFinder  # noqa: E402

from scripts.configs import DOC_ROOT  # noqa: E402
from scripts.hero_banner_figure import (  # noqa: E402
    BAND_METRES,
    BRAZIL,
    COMPARISON_PATH,
    FIGURE_PATH,
    MAP_PATH,
    MEASUREMENT_PATH,
    PARAGUAY,
    PNG_PATH,
    TOWN_LABEL_PX,
    ZONES,
    avenue_lookups,
    banner_view,
    border,
    centre_of,
    clip_line,
    comparison_counts,
    decode,
    distance_m,
    encode,
    local_time,
    pixel_to_lnglat,
    read_map,
    read_measurement,
    render,
    render_comparison,
    utc_offset,
)


@pytest.fixture(scope="module")
def tf() -> TimezoneFinder:
    return TimezoneFinder()


@pytest.mark.unit
def test_the_avenue_has_one_lookup_on_each_side_an_hour_apart(tf) -> None:
    lookups = avenue_lookups(tf, border(tf))
    assert [lookup.zone for lookup in lookups] == list(ZONES)
    for lookup in lookups:
        assert tf.timezone_at(lng=lookup.lng, lat=lookup.lat) == lookup.zone
    assert (local_time(BRAZIL), local_time(PARAGUAY)) == ("12:00", "13:00")
    assert (utc_offset(BRAZIL), utc_offset(PARAGUAY)) == ("UTC−4", "UTC−3")


@pytest.mark.unit
def test_each_town_name_is_written_in_its_own_zone(tf) -> None:
    for zone, (x, y) in TOWN_LABEL_PX.items():
        lng, lat = pixel_to_lnglat(x, y)
        assert tf.timezone_at(lng=lng, lat=lat) == zone


@pytest.mark.unit
def test_only_the_two_zones_meet_in_the_banner(tf) -> None:
    west, south, east, north = banner_view()
    zones = {
        tf.timezone_at(
            lng=west + (east - west) * i / 20, lat=south + (north - south) * j / 10
        )
        for i in range(21)
        for j in range(11)
    }
    assert zones == set(ZONES)


@pytest.mark.unit
def test_the_record_still_describes_the_packaged_data(tf) -> None:
    # tzfpy's answers are a measurement and are not repeated; ours are the data's, so a
    # data update that moves one of these buildings fails here and asks for --measure
    record = read_measurement()
    assert record["timezonefinder_data"] == tf.data_version, (
        f"{MEASUREMENT_PATH} was measured with other data - run it with --measure"
    )
    buildings = {b["id"]: b["ring"] for b in read_map()["buildings"]}
    assert record["buildings"] == len(buildings)
    for wrong in record["wrong"]:
        lng, lat = centre_of(buildings[wrong["id"]])
        assert tf.timezone_at(lng=lng, lat=lat) == wrong["timezonefinder"]
        assert {wrong["timezonefinder"], wrong["theirs"]} == set(ZONES)


@pytest.mark.unit
def test_the_excerpt_keeps_only_the_buildings_near_the_border(tf) -> None:
    runs = border(tf)
    for building in read_map()["buildings"][::50]:
        assert distance_m(centre_of(building["ring"]), runs) <= BAND_METRES


@pytest.mark.unit
def test_the_prose_quotes_the_record() -> None:
    record = read_measurement()
    total = len(record["wrong"])
    page = (DOC_ROOT / "why_no_simplification.rst").read_text(encoding="utf-8")
    readme = (DOC_ROOT.parent / "README.md").read_text(encoding="utf-8")
    paper = (DOC_ROOT.parent / "paper" / "paper.md").read_text(encoding="utf-8")
    for text in (page, readme, paper):
        assert f"{total} of the {record['buildings']:,} buildings" in text
    assert f"``tzfpy`` {record['tzfpy']}" in page
    for pair, n in comparison_counts(record).items():
        assert f"{n} in {pair}" in page


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
    line = [(-55.123456, -22.5), (-55.12, -22.512345)]
    assert encode(line) == "-5512346,-2250000 346,-1234"
    assert decode(encode(line)) == [(-55.12346, -22.5), (-55.12, -22.51234)]


@pytest.mark.unit
@pytest.mark.parametrize("draw", [render, render_comparison])
def test_the_figures_are_deterministic_and_pre_commit_clean(tf, draw) -> None:
    import matplotlib

    svg = draw(tf)
    with matplotlib.rc_context({"axes.grid": True, "lines.solid_capstyle": "butt"}):
        # another renderer's global style must not leak into a committed artifact
        assert svg == draw(tf)
    ElementTree.fromstring(svg)
    assert "font-family: 'DejaVu Sans'" in svg
    assert "dc:date" not in svg
    assert "OpenStreetMap contributors" in svg
    assert svg.endswith("\n") and not svg.endswith("\n\n")
    assert not any(line != line.rstrip() for line in svg.splitlines())


@pytest.mark.unit
@pytest.mark.parametrize(
    ("path", "draw"), [(FIGURE_PATH, render), (COMPARISON_PATH, render_comparison)]
)
def test_the_committed_figures_are_renders_of_the_packaged_data(tf, path, draw) -> None:
    assert path.read_text(encoding="utf-8") == draw(tf), (
        f"{path} is stale - run `make hero-banner`"
    )


@pytest.mark.unit
def test_the_figures_are_where_the_readme_and_the_docs_look_for_them() -> None:
    assert FIGURE_PATH.parent == PNG_PATH.parent == COMPARISON_PATH.parent == DOC_ROOT
    assert PNG_PATH.exists()
    readme = (DOC_ROOT.parent / "README.md").read_text(encoding="utf-8")
    assert f"/master/docs/{PNG_PATH.name}" in readme
    assert FIGURE_PATH.name in (DOC_ROOT / "index.rst").read_text(encoding="utf-8")
    page = (DOC_ROOT / "why_no_simplification.rst").read_text(encoding="utf-8")
    assert COMPARISON_PATH.name in page


@pytest.mark.unit
def test_the_committed_files_name_their_sources() -> None:
    excerpt = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    assert "OpenStreetMap" in excerpt["source"] and "ODbL" in excerpt["source"]
    names = {place["name"] for place in excerpt["layers"]["places"]}
    assert names == {"Ponta Porã", "Pedro Juan Caballero"}
    record = read_measurement()
    assert record["tzfpy"] and record["tzfpy_data"]
