#!/usr/bin/env python3

"""Draw the README banner: one timezone border at street-level zoom, every vertex kept.

The banner shows the border between Europe/Stockholm and Europe/Helsinki where it runs
through the twin towns of Haparanda (Sweden) and Tornio (Finland). Three lookups are
drawn on it: one on each side, and one that lies between the real border and the same
border simplified by :data:`SIMPLIFICATION_METRES` - a point this package answers
correctly and a simplified dataset answers an hour wrong. The border, its vertex count
and every answer come from the packaged data and from ``timezone_at``, so the banner
follows the data rather than a drawing of it.

The map underneath - coastline, lakes and rivers, built-up areas, main roads, railways
and town names - is the one input that is not the package's: an excerpt of
OpenStreetMap, committed beside the banner so a redraw needs no download. It orients
the reader and nothing else; the lookup never reads it. The timezone boundaries are
built from OpenStreetMap too, so the river and the border line up at this zoom, which
the coarser Natural Earth data used for the shortcut index figure does not. To rebuild
the excerpt, pass the JSON that :data:`OVERPASS_QUERY` returns with ``--osm``.

The excerpt's lines are thinned to below a pixel at the banner's scale to keep the
committed file small. That applies to the background map only: the border is drawn from
every vertex the package stores.

The drawing is deterministic, so a redraw only changes the files when the data or the
layout changed. ``make hero-banner`` redraws the SVG the docs embed and the PNG the
README embeds - PyPI and GitHub's raw file host do not serve SVG as an image.
"""

import argparse
import json
import math
from io import BytesIO
from itertools import pairwise
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

import matplotlib

# before pyplot, which otherwise picks an interactive backend that CI has no display for
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.patches import (  # noqa: E402
    Circle,
    Ellipse,
    FancyBboxPatch,
    PathPatch,
    Rectangle,
)
from matplotlib.path import Path as MplPath  # noqa: E402

from scripts.configs import DOC_ROOT  # noqa: E402
from scripts.shortcut_index_figure import Box, Ring, clip_ring  # noqa: E402
from scripts.utils import write_json  # noqa: E402
from timezonefinder import TimezoneFinder  # noqa: E402

FIGURE_PATH = DOC_ROOT / "hero_banner.svg"
PNG_PATH = DOC_ROOT / "hero_banner.png"
MAP_PATH = DOC_ROOT / "hero_banner_map.json"
MAP_SOURCE = "OpenStreetMap, via the Overpass API (© OpenStreetMap contributors, ODbL)"

#: Element ids are otherwise salted from ``uuid4()``, so every render would differ.
SVG_HASH_SALT = "timezonefinder-hero-banner"

#: The query whose response ``--osm`` reads. Its box holds :data:`WINDOW` with a margin,
#: so coastline and rivers enter and leave the window rather than end inside it.
OVERPASS_QUERY = """\
[out:json][timeout:120][bbox:65.75,23.70,65.95,24.40];
(
  way["natural"="coastline"];
  way["natural"="water"]; relation["natural"="water"];
  way["waterway"="riverbank"]; relation["waterway"="riverbank"];
  way["waterway"="river"];
  way["highway"~"^(motorway|trunk|primary|secondary)$"];
  way["railway"="rail"];
  way["landuse"="residential"];
  node["place"~"^(city|town|village|suburb)$"];
);
out geom;
"""

WIDTH_PX, HEIGHT_PX, DPI = 1600, 800, 100

#: Where the map is centred and how far it reaches north to south, in degrees.
CENTRE = (24.105, 65.845)
LAT_SPAN = 0.064

WEST_TO_EAST = ("Europe/Stockholm", "Europe/Helsinki")
COUNTRY = {"Europe/Stockholm": "SWEDEN", "Europe/Helsinki": "FINLAND"}
UTC_OFFSET = {"Europe/Stockholm": "UTC+1", "Europe/Helsinki": "UTC+2"}

#: The tolerance the dashed comparison line is simplified with: the ~110 m maximum
#: displacement the maintainer of a simplifying alternative states for its data (see
#: ``docs/border_accuracy_vs_tzfpy.rst``), not an exaggeration picked to show a gap.
SIMPLIFICATION_METRES = 110.0

#: Vertices of the background map closer together than this, in degrees (Manhattan),
#: are dropped: about a pixel at this zoom.
MAP_TOLERANCE = 0.00012

#: Map polygons smaller than this many square degrees (about 60 square pixels at this
#: zoom) are left out of the excerpt.
MIN_AREA = 1e-6


@dataclass(frozen=True)
class QueryPoint:
    title: str
    lng: float
    lat: float
    #: where the label card's top left corner sits, in pixels from the top left
    card: tuple[float, float]


#: One point per story the banner tells; ``tests/test_hero_banner_figure.py`` asserts
#: that each still lands in the zone and on the side of the simplified border it is
#: drawn for.
WEST_POINT = QueryPoint("Haparanda", 24.1180, 65.8335, (470, 600))
EAST_POINT = QueryPoint("Tornio", 24.1600, 65.8570, (1180, 120))
GAP_POINT = QueryPoint("between the lines", 24.1375, 65.8455, (1150, 600))

#: The magnifier: the map around :data:`GAP_POINT`, ``LOUPE_ZOOM`` times closer, in a
#: circle of ``LOUPE_RADIUS_PX`` centred at ``LOUPE_CENTRE_PX`` (pixels from top left).
LOUPE_ZOOM = 5.0
LOUPE_RADIUS_PX = 150
LOUPE_CENTRE_PX = (1300, 400)
QUERIES = (WEST_POINT, EAST_POINT, GAP_POINT)

TOWNS = {"Haparanda", "Tornio"}

#: How far each town's name is moved from its OpenStreetMap node, in degrees, to keep it
#: clear of the border and the magnifier's marker.
LABEL_OFFSET = {"Haparanda": (0.0, 0.0), "Tornio": (0.012, 0.0045)}

PAPER = "#f8fafc"
ZONE_FILL = {"Europe/Stockholm": "#dbe7fb", "Europe/Helsinki": "#e9e3fb"}
ZONE_INK = {"Europe/Stockholm": "#1d4ed8", "Europe/Helsinki": "#6d28d9"}
SEA = "#a9cdee"
WATER_LINE = "#7fb2e3"
BUILT_UP = "#cfd3da"
ROAD = "#ffffff"
ROAD_CASING = "#b8bec8"
RAIL = "#8a919c"
INK = "#0f172a"
MUTED = "#475569"
WRONG = "#dc2626"


# --- geometry -------------------------------------------------------------------------


def window() -> Box:
    """``(west, south, east, north)`` of the map, at the banner's aspect ratio."""
    lng, lat = CENTRE
    lng_span = LAT_SPAN * WIDTH_PX / HEIGHT_PX / math.cos(math.radians(lat))
    return (
        lng - lng_span / 2,
        lat - LAT_SPAN / 2,
        lng + lng_span / 2,
        lat + LAT_SPAN / 2,
    )


def metres_xy(lng: float, lat: float) -> tuple[float, float]:
    """A local equirectangular projection around :data:`CENTRE`, in metres."""
    radius = 6_371_008.8
    x = math.radians(lng - CENTRE[0]) * radius * math.cos(math.radians(CENTRE[1]))
    return x, math.radians(lat - CENTRE[1]) * radius


def simplify(line: Ring, tolerance_m: float) -> Ring:
    """Douglas-Peucker in metres, keeping both ends - the comparison line only."""
    if len(line) < 3:
        return list(line)
    xy = [metres_xy(*p) for p in line]
    (x1, y1), (x2, y2) = xy[0], xy[-1]
    length = math.hypot(x2 - x1, y2 - y1)

    def offset(i: int) -> float:
        x, y = xy[i]
        if length == 0:
            return math.hypot(x - x1, y - y1)
        return abs((y2 - y1) * (x - x1) - (x2 - x1) * (y - y1)) / length

    far = max(range(1, len(line) - 1), key=offset)
    if offset(far) <= tolerance_m:
        return [line[0], line[-1]]
    return simplify(line[: far + 1], tolerance_m)[:-1] + simplify(
        line[far:], tolerance_m
    )


def on_edge(point: tuple[float, float], box: Box) -> bool:
    return point[0] in (box[0], box[2]) or point[1] in (box[1], box[3])


def split_ring(ring: Ring, box: Box) -> list[tuple[bool, Ring]]:
    """A clipped ring as consecutive ``(is_border, run)`` pieces, in ring order.

    The pieces that are not border run along the clipping box. Consecutive pieces share
    their end points, and the last one ends where the first one starts.
    """
    start = next((i for i, p in enumerate(ring) if on_edge(p, box)), None)
    if start is None:
        return [(True, ring + ring[:1])]
    rotated = ring[start:] + ring[:start] + [ring[start]]
    pieces: list[tuple[bool, Ring]] = []
    for a, b in pairwise(rotated):
        # an edge between two box points runs along the box
        is_border = not (
            on_edge(a, box) and on_edge(b, box) and (a[0] == b[0] or a[1] == b[1])
        )
        if pieces and pieces[-1][0] == is_border:
            pieces[-1][1].append(b)
        else:
            pieces.append((is_border, [a, b]))
    return pieces


def zone_rings(tf: TimezoneFinder, zone: str, box: Box) -> list[Ring]:
    """The outer rings of a zone's polygons clipped to ``box``, every vertex kept."""
    rings = []
    for polygon in tf.get_geometry(tz_name=zone):
        lngs, lats = polygon[0]
        if max(lngs) < box[0] or min(lngs) > box[2]:
            continue
        if max(lats) < box[1] or min(lats) > box[3]:
            continue
        ring = clip_ring(lngs, lats, box)
        if len(ring) >= 3:
            rings.append(ring)
    return rings


def margin_box(box: Box, margin: float) -> Box:
    return (box[0] - margin, box[1] - margin, box[2] + margin, box[3] + margin)


@dataclass(frozen=True)
class Border:
    """The border in the window: drawn as the package stores it, and simplified."""

    runs: list[Ring]
    simplified_ring: Ring  # the eastern zone, with its border runs simplified
    vertices_in_view: int
    simplified_in_view: int


def border(tf: TimezoneFinder) -> Border:
    view = window()
    # clipped just beyond the view, so the clipping box itself is never on screen
    box = margin_box(view, 0.01)
    (ring,) = zone_rings(tf, WEST_TO_EAST[1], box)
    pieces = split_ring(ring, box)
    runs = [run for is_border, run in pieces if is_border]
    simplified_runs = [simplify(run, SIMPLIFICATION_METRES) for run in runs]

    def in_view(p):
        return view[0] <= p[0] <= view[2] and view[1] <= p[1] <= view[3]

    # the same ring with each border run replaced by its simplified version
    simplified_ring: Ring = []
    simple = iter(simplified_runs)
    for is_border, run in pieces:
        simplified_ring.extend((next(simple) if is_border else run)[:-1])
    return Border(
        runs=runs,
        simplified_ring=simplified_ring,
        vertices_in_view=sum(in_view(p) for run in runs for p in run[:-1]),
        simplified_in_view=sum(in_view(p) for run in simplified_runs for p in run[:-1]),
    )


def inside(point: tuple[float, float], ring: Ring) -> bool:
    """Even-odd point in polygon, for the simplified ring the package never stores."""
    x, y = point
    result = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1], strict=True):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            result = not result
    return result


def simplified_answer(shape: Border, point: QueryPoint) -> str:
    """The zone a lookup on the simplified border would return."""
    east = inside((point.lng, point.lat), shape.simplified_ring)
    return WEST_TO_EAST[1] if east else WEST_TO_EAST[0]


# --- the map excerpt ------------------------------------------------------------------


def thin(line: Ring) -> Ring:
    """Drop vertices closer than :data:`MAP_TOLERANCE` to the last one kept."""
    kept = [line[0]]
    for point in line[1:-1]:
        if abs(point[0] - kept[-1][0]) + abs(point[1] - kept[-1][1]) >= MAP_TOLERANCE:
            kept.append(point)
    kept.append(line[-1])
    return kept


def encode(line: Iterable[tuple[float, float]]) -> str:
    """A line as ``"lng,lat lng,lat ..."`` to 1e-5 degrees, about a metre.

    One string per line rather than nested arrays, which the repository's JSON
    formatter would spread over one line per number - several times the file size.
    """
    return " ".join(f"{x:.5f},{y:.5f}" for x, y in line)


def decode(line: str) -> Ring:
    points = []
    for pair in line.split():
        lng, lat = pair.split(",")
        points.append((float(lng), float(lat)))
    return points


def area(ring: Ring) -> float:
    return abs(
        sum(
            x1 * y2 - x2 * y1
            for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1], strict=True)
        )
        / 2
    )


def join(lines: Iterable[Ring]) -> list[Ring]:
    """Join lines that share end points into the longest chains, keeping direction.

    Coastline ways are directed (land on the left), and a multipolygon's member ways
    are listed in no particular order, so both arrive in pieces.
    """
    chains = [list(line) for line in lines if len(line) > 1]
    joined = True
    while joined:
        joined = False
        for i, a in enumerate(chains):
            for j, b in enumerate(chains):
                if i == j:
                    continue
                if a[-1] == b[0]:
                    chains[i] = a + b[1:]
                elif a[-1] == b[-1] and not a[0] == a[-1]:
                    chains[i] = a + b[::-1][1:]
                else:
                    continue
                del chains[j]
                joined = True
                break
            if joined:
                break
    return chains


def clip_line(line: Ring, box: Box) -> list[Ring]:
    """The runs of a line inside ``box``, ending exactly on its edges."""
    x0, y0, x1, y1 = box
    runs: list[Ring] = []
    run: Ring = []
    for a, b in pairwise(line):
        # Liang-Barsky
        dx, dy = b[0] - a[0], b[1] - a[1]
        t0, t1 = 0.0, 1.0
        for p, q in (
            (-dx, a[0] - x0),
            (dx, x1 - a[0]),
            (-dy, a[1] - y0),
            (dy, y1 - a[1]),
        ):
            if p == 0:
                if q < 0:
                    t0, t1 = 1.0, 0.0
                continue
            t = q / p
            if p < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
        if t0 > t1:
            if len(run) > 1:
                runs.append(run)
            run = []
            continue
        start = (a[0] + t0 * dx, a[1] + t0 * dy) if t0 > 0 else a
        end = (a[0] + t1 * dx, a[1] + t1 * dy) if t1 < 1 else b
        if run and run[-1] != start:
            runs.append(run)
            run = []
        if not run:
            run = [start]
        run.append(end)
        if t1 < 1:
            if len(run) > 1:
                runs.append(run)
            run = []
    if len(run) > 1:
        runs.append(run)
    return runs


def perimeter_position(point: tuple[float, float], box: Box) -> float:
    """Where a point on the box edge lies, counter-clockwise from the south-west corner."""
    x0, y0, x1, y1 = box
    x, y = point
    if y == y0:
        return (x - x0) / (x1 - x0)
    if x == x1:
        return 1 + (y - y0) / (y1 - y0)
    if y == y1:
        return 2 + (x1 - x) / (x1 - x0)
    return 3 + (y1 - y) / (y1 - y0)


def land(coastline: list[Ring], box: Box) -> list[Ring]:
    """Land polygons inside ``box`` from directed coastline (land on the left).

    Each run that crosses the box is closed by walking the box edge counter-clockwise
    from where it leaves to where the next run enters; closed rings are islands.
    """
    corners = [(box[0], box[1]), (box[2], box[1]), (box[2], box[3]), (box[0], box[3])]
    islands, runs = [], []
    for chain in coastline:
        if chain[0] == chain[-1]:
            ring = chain[:-1]
            if all(box[0] < x < box[2] and box[1] < y < box[3] for x, y in ring):
                islands.append(ring)
                continue
        runs.extend(clip_line(chain, box))
    runs = [run for run in runs if on_edge(run[0], box) and on_edge(run[-1], box)]
    polygons = []
    unused = list(range(len(runs)))
    while unused:
        first = unused.pop(0)
        ring = list(runs[first])
        while True:
            exit_at = perimeter_position(ring[-1], box)

            def ahead(i, exit_at=exit_at):
                return (perimeter_position(runs[i][0], box) - exit_at) % 4

            candidates = unused + [first]
            nxt = min(candidates, key=ahead)
            # the box corners between leaving and entering again
            distance = ahead(nxt)
            for k in range(1, 5):
                corner = math.floor(exit_at) + k
                if corner - exit_at >= distance:
                    break
                ring.append(corners[corner % 4])
            if nxt == first:
                break
            unused.remove(nxt)
            ring.extend(runs[nxt])
        polygons.append(ring)
    return polygons + islands


def element_lines(element: dict) -> list[tuple[str, Ring]]:
    """``(role, line)`` for every way of an Overpass element with ``out geom``."""
    if element["type"] == "way":
        members = [("outer", element.get("geometry", []))]
    else:
        members = [
            (m.get("role", ""), m.get("geometry", [])) for m in element["members"]
        ]
    return [
        (role, [(p["lon"], p["lat"]) for p in geometry if p])
        for role, geometry in members
        if len(geometry) > 1
    ]


def polygons_of(element: dict) -> list[tuple[str, Ring]]:
    lines = element_lines(element)
    rings = []
    for role in ("outer", "inner"):
        for chain in join(line for r, line in lines if r == role):
            if chain[0] == chain[-1] and len(chain) > 3:
                rings.append((role, chain[:-1]))
    return rings


def extract_osm(overpass_json: Path) -> dict:
    """The background map of an Overpass response near the window, as the committed excerpt."""
    box = margin_box(window(), 0.005)
    elements = json.loads(overpass_json.read_text(encoding="utf-8"))["elements"]
    tags_of = [(e, e.get("tags", {})) for e in elements]
    layers: dict[str, list] = {
        "built_up": [],
        "land": [],
        "places": [],
        "railways": [],
        "roads": [],
        "streams": [],
        "water": [],
    }

    def add_polygons(layer: str, element: dict) -> None:
        for role, ring in polygons_of(element):
            clipped = clip_ring([p[0] for p in ring], [p[1] for p in ring], box)
            if len(clipped) >= 3 and area(clipped) >= MIN_AREA:
                layers[layer].append(
                    {"hole": role == "inner", "ring": encode(thin(clipped))}
                )

    def add_lines(layer: str, element: dict) -> None:
        for _, line in element_lines(element):
            for run in clip_line(line, box):
                layers[layer].append(encode(thin(run)))

    coastline: list[Ring] = []
    for element, tags in tags_of:
        if element["type"] == "node":
            if tags.get("name") in TOWNS and tags.get("place") == "town":
                layers["places"].append(
                    {"lat": element["lat"], "lng": element["lon"], "name": tags["name"]}
                )
        elif tags.get("natural") == "coastline":
            coastline.extend(line for _, line in element_lines(element))
        elif tags.get("natural") == "water" or tags.get("waterway") == "riverbank":
            add_polygons("water", element)
        elif tags.get("landuse") == "residential":
            add_polygons("built_up", element)
        elif tags.get("waterway") == "river":
            add_lines("streams", element)
        elif "highway" in tags:
            add_lines("roads", element)
        elif tags.get("railway") == "rail":
            add_lines("railways", element)
    layers["land"] = [
        encode(thin(ring))
        for ring in land(join(coastline), box)
        if area(ring) >= MIN_AREA
    ]
    for layer in layers.values():
        layer.sort(key=json.dumps)
    return {"box": list(box), "layers": layers, "source": MAP_SOURCE}


def overlaps(line: Ring, view: Box) -> bool:
    return not (
        max(p[0] for p in line) < view[0]
        or min(p[0] for p in line) > view[2]
        or max(p[1] for p in line) < view[1]
        or min(p[1] for p in line) > view[3]
    )


def read_map(view: Box | None = None) -> dict:
    """The committed excerpt with its lines decoded; polygons as ``{"hole", "ring"}``.

    With ``view``, only what reaches into it: the magnifier would otherwise write the
    whole map into the SVG a second time, clipped away but still there.
    """
    layers = json.loads(MAP_PATH.read_text(encoding="utf-8"))["layers"]
    decoded = {
        name: [
            {"hole": item["hole"], "ring": decode(item["ring"])}
            if isinstance(item, dict) and "ring" in item
            else decode(item)
            if isinstance(item, str)
            else item
            for item in items
        ]
        for name, items in layers.items()
    }
    if view is None:
        return decoded
    return {
        name: [
            item
            for item in items
            if "name" in item
            or overlaps(item["ring"] if isinstance(item, dict) else item, view)
        ]
        for name, items in decoded.items()
    }


# --- drawing --------------------------------------------------------------------------


def to_pixels(ax: Axes, lng: float, lat: float) -> tuple[float, float]:
    """Data coordinates to pixels from the figure's top left, as the cards are placed."""
    x, y = ax.transData.transform((lng, lat))
    return x, HEIGHT_PX - y


def fill_rings(ax: Axes, rings: Sequence[dict], colour: str, zorder: float) -> None:
    """One compound path per layer, so holes cut through the fill (even-odd)."""
    vertices, codes = [], []
    for item in rings:
        ring = item["ring"] if isinstance(item, dict) else item
        vertices.extend(ring + ring[:1])
        codes.extend(
            [MplPath.MOVETO] + [MplPath.LINETO] * (len(ring) - 1) + [MplPath.CLOSEPOLY]
        )
    if vertices:
        ax.add_patch(
            PathPatch(
                MplPath(vertices, codes),
                facecolor=colour,
                edgecolor="none",
                zorder=zorder,
            )
        )


def draw_lines(
    ax: Axes,
    lines: Sequence[Ring],
    color: str,
    linewidth: float,
    zorder: float,
    linestyle="solid",
) -> None:
    """A layer of lines as one compound path: one SVG element, not one per line."""
    vertices, codes = [], []
    for line in lines:
        vertices.extend(line)
        codes.extend([MplPath.MOVETO] + [MplPath.LINETO] * (len(line) - 1))
    if vertices:
        ax.add_patch(
            PathPatch(
                MplPath(vertices, codes),
                fill=False,
                edgecolor=color,
                linewidth=linewidth,
                linestyle=linestyle,
                capstyle="round",
                joinstyle="round",
                zorder=zorder,
            )
        )


def set_view(ax: Axes, view: Box) -> None:
    ax.set_xlim(view[0], view[2])
    ax.set_ylim(view[1], view[3])
    ax.set_aspect(1 / math.cos(math.radians(CENTRE[1])))
    ax.set_axis_off()


def draw_map(
    ax: Axes, tf: TimezoneFinder, shape: Border, view: Box, zoom: float = 1.0
) -> None:
    """The map layers and the border in ``view``; ``zoom`` scales the border's marks."""
    set_view(ax, view)
    layers = read_map(view)

    # sea under everything, land over it, then the zones tint land and sea alike: the
    # zones reach into territorial waters, and a lookup at sea is answered there too
    ax.add_patch(
        Rectangle(
            (view[0], view[1]),
            view[2] - view[0],
            view[3] - view[1],
            facecolor=SEA,
            zorder=0,
        )
    )
    fill_rings(ax, layers["land"], PAPER, 0.1)
    fill_rings(ax, [i for i in layers["water"] if not i["hole"]], SEA, 0.2)
    fill_rings(ax, [i for i in layers["water"] if i["hole"]], PAPER, 0.25)
    box = margin_box(window(), 0.01)
    for zone in WEST_TO_EAST:
        for ring in zone_rings(tf, zone, box):
            ax.fill(
                [p[0] for p in ring],
                [p[1] for p in ring],
                facecolor=ZONE_FILL[zone],
                edgecolor="none",
                alpha=0.55,
                zorder=0.3,
            )
    fill_rings(ax, [i for i in layers["built_up"] if not i["hole"]], BUILT_UP, 0.5)
    road = 1 + (zoom > 1)
    draw_lines(
        ax,
        layers["streams"],
        color=WATER_LINE,
        linewidth=1.1 * road,
        zorder=0.6,
    )
    draw_lines(
        ax,
        layers["railways"],
        color=RAIL,
        linewidth=0.8 * road,
        zorder=0.7,
        linestyle=(0, (4, 2)),
    )
    draw_lines(
        ax,
        layers["roads"],
        color=ROAD_CASING,
        linewidth=2.6 * road,
        zorder=0.8,
    )
    draw_lines(
        ax,
        layers["roads"],
        color=ROAD,
        linewidth=1.6 * road,
        zorder=0.81,
    )

    mark = 1 + (zoom > 1) * 0.6
    for run in shape.runs:
        simple = simplify(run, SIMPLIFICATION_METRES)
        ax.plot(
            [p[0] for p in simple],
            [p[1] for p in simple],
            color=WRONG,
            linewidth=2.0 * mark,
            linestyle=(0, (5, 4)),
            zorder=2,
        )
        ax.plot(
            [p[0] for p in run],
            [p[1] for p in run],
            color=INK,
            linewidth=2.4 * mark,
            solid_joinstyle="round",
            zorder=3,
        )
        ax.plot(
            [p[0] for p in run[:-1]],
            [p[1] for p in run[:-1]],
            "o",
            markersize=2.6 * mark * 1.4 ** (zoom > 1),
            color=INK,
            zorder=3.1,
        )


def draw_labels(ax: Axes) -> None:
    for place in read_map()["places"]:
        dx, dy = LABEL_OFFSET[place["name"]]
        ax.text(
            place["lng"] + dx,
            place["lat"] + dy,
            place["name"],
            fontsize=13,
            color=INK,
            fontweight="bold",
            ha="center",
            va="center",
            zorder=2.5,
            path_effects=_halo(),
        )
    # the country names sit where the land is, the zone colour says which side is which
    for zone, (lng, lat) in zip(
        WEST_TO_EAST, ((24.112, 65.871), (24.232, 65.8735)), strict=True
    ):
        ax.text(
            lng,
            lat,
            COUNTRY[zone],
            fontsize=30,
            fontweight="bold",
            color=ZONE_INK[zone],
            alpha=0.22,
            ha="center",
            va="center",
            zorder=1.5,
        )


def loupe(fig: Figure, main: Axes, tf: TimezoneFinder, shape: Border) -> Axes:
    """The map around :data:`GAP_POINT` magnified in a circle, tied to where it is."""
    cx, cy = LOUPE_CENTRE_PX
    r = LOUPE_RADIUS_PX
    ax = fig.add_axes(
        (*px(cx - r, cy + r), 2 * r / WIDTH_PX, 2 * r / HEIGHT_PX), zorder=15
    )
    lat_half = r / HEIGHT_PX * LAT_SPAN / LOUPE_ZOOM
    lng_half = lat_half / math.cos(math.radians(CENTRE[1]))
    view = (
        GAP_POINT.lng - lng_half,
        GAP_POINT.lat - lat_half,
        GAP_POINT.lng + lng_half,
        GAP_POINT.lat + lat_half,
    )
    draw_map(ax, tf, shape, view, zoom=LOUPE_ZOOM)
    disc = Circle((0.5, 0.5), 0.5, transform=ax.transAxes)
    for artist in ax.get_children():
        artist.set_clip_path(disc)
    ax.text(
        0.5,
        0.9,
        f"× {LOUPE_ZOOM:g}",
        transform=ax.transAxes,
        fontsize=11,
        color=MUTED,
        ha="center",
        va="center",
        zorder=5,
        path_effects=_halo(),
    )

    # the patch of the main map the loupe shows, and the two lines tying them together
    sx, sy = to_pixels(main, GAP_POINT.lng, GAP_POINT.lat)
    small = r / LOUPE_ZOOM
    fig.patches.append(
        Ellipse(
            px(sx, sy),
            2 * small / WIDTH_PX,
            2 * small / HEIGHT_PX,
            transform=fig.transFigure,
            fill=False,
            edgecolor=INK,
            linewidth=1.4,
            zorder=14,
        )
    )
    for side in (-1, 1):
        fig.lines.append(
            plt.Line2D(
                *zip(px(sx, sy + side * small), px(cx, cy + side * r), strict=True),
                transform=fig.transFigure,
                color=INK,
                linewidth=1.0,
                alpha=0.5,
                zorder=14,
            )
        )
    # the circle is drawn on the figure, whose x and y fractions differ in scale
    fig.patches.append(
        Ellipse(
            px(cx, cy),
            2 * r / WIDTH_PX,
            2 * r / HEIGHT_PX,
            transform=fig.transFigure,
            fill=False,
            edgecolor=INK,
            linewidth=2.2,
            zorder=16,
        )
    )
    return ax


def _halo():
    from matplotlib import patheffects

    return [patheffects.withStroke(linewidth=3.5, foreground="white", alpha=0.85)]


def fade(fig: Figure) -> None:
    """A white wash behind the title that clears before the border."""
    solid, clear = 0.30, 0.52  # fractions of the width
    columns = 256
    alpha = [
        0.94 * (min(1.0, (clear - x) / (clear - solid)) ** 1.4)
        for x in (clear * (i + 0.5) / columns for i in range(columns))
    ]
    wash = fig.add_axes((0, 0, clear, 1), zorder=10)
    wash.set_axis_off()
    wash.imshow(
        [[(1.0, 1.0, 1.0, a) for a in alpha]],
        aspect="auto",
        interpolation="bilinear",
        extent=(0, 1, 0, 1),
    )


def px(x: float, y: float) -> tuple[float, float]:
    """Pixels from the top left to figure fractions."""
    return x / WIDTH_PX, 1 - y / HEIGHT_PX


def card(
    fig: Figure,
    ax: Axes,
    point: QueryPoint,
    lines: Sequence[tuple[str, str, dict]],
    accent: str,
) -> None:
    x, y = point.card
    width, height = 340, 26 + 30 * len(lines)
    fig.patches.append(
        FancyBboxPatch(
            px(x, y + height),
            width / WIDTH_PX,
            height / HEIGHT_PX,
            boxstyle="round,pad=0,rounding_size=0.008",
            transform=fig.transFigure,
            facecolor="white",
            edgecolor="#e2e8f0",
            linewidth=1,
            zorder=20,
        )
    )
    fig.patches.append(
        Rectangle(
            px(x, y + height),
            5 / WIDTH_PX,
            height / HEIGHT_PX,
            transform=fig.transFigure,
            facecolor=accent,
            edgecolor="none",
            zorder=21,
        )
    )
    fig.text(
        *px(x + 20, y + 22),
        f"{point.lat:.4f}, {point.lng:.4f}",
        fontsize=11,
        color=MUTED,
        family="DejaVu Sans Mono",
        va="center",
        zorder=22,
    )
    for i, (text, colour, style) in enumerate(lines):
        fig.text(
            *px(x + 20, y + 52 + 30 * i),
            text,
            color=colour,
            va="center",
            zorder=22,
            family="DejaVu Sans Mono",
            **style,
        )
    # the leader runs from the pin to the nearest side of the card
    pin = to_pixels(ax, point.lng, point.lat)
    if pin[1] < y:
        target = (min(max(pin[0], x + 40), x + width - 40), y)
    else:
        target = (x if pin[0] < x else x + width, y + height / 2)
    fig.lines.append(
        plt.Line2D(
            *zip(px(*pin), px(*target), strict=True),
            transform=fig.transFigure,
            color=accent,
            linewidth=1.5,
            zorder=19,
        )
    )
    fig.lines.append(
        plt.Line2D(
            [px(*pin)[0]],
            [px(*pin)[1]],
            transform=fig.transFigure,
            marker="o",
            markersize=13,
            markerfacecolor=accent,
            markeredgecolor="white",
            markeredgewidth=2.5,
            zorder=23,
        )
    )


def draw_text(fig: Figure, shape: Border) -> None:
    fig.text(
        *px(80, 150),
        "Coordinates",
        fontsize=44,
        fontweight="bold",
        color=INK,
        zorder=30,
    )
    fig.text(
        *px(80, 220),
        "→ IANA timezone",
        fontsize=44,
        fontweight="bold",
        color=ZONE_INK["Europe/Stockholm"],
        zorder=30,
    )
    fig.text(
        *px(82, 290),
        "Every boundary vertex kept. No simplification.\nCorrect right up to the border line.",
        fontsize=16,
        color="#334155",
        linespacing=1.5,
        va="top",
        zorder=30,
    )
    legend_y = 420
    fig.lines.append(
        plt.Line2D(
            *zip(px(82, legend_y), px(124, legend_y), strict=True),
            transform=fig.transFigure,
            color=INK,
            linewidth=2.4,
            zorder=30,
        )
    )
    fig.lines.append(
        plt.Line2D(
            [px(103, legend_y)[0]],
            [px(103, legend_y)[1]],
            transform=fig.transFigure,
            marker="o",
            markersize=4,
            color=INK,
            zorder=30,
        )
    )
    fig.text(
        *px(140, legend_y),
        f"timezonefinder: all {shape.vertices_in_view} border vertices in view",
        fontsize=13,
        color=INK,
        va="center",
        zorder=30,
    )
    fig.lines.append(
        plt.Line2D(
            *zip(px(82, legend_y + 34), px(124, legend_y + 34), strict=True),
            transform=fig.transFigure,
            color=WRONG,
            linewidth=2.0,
            linestyle=(0, (5, 4)),
            zorder=30,
        )
    )
    fig.text(
        *px(140, legend_y + 34),
        f"simplified to within {SIMPLIFICATION_METRES:.0f} m: {shape.simplified_in_view} vertices",
        fontsize=13,
        color=MUTED,
        va="center",
        zorder=30,
    )
    fig.text(
        *px(82, 740),
        "Haparanda (SE) and Tornio (FI), 65.84° N 24.14° E",
        fontsize=11,
        color=MUTED,
        family="DejaVu Sans Mono",
        zorder=30,
    )
    fig.text(
        *px(WIDTH_PX - 12, HEIGHT_PX - 10),
        "Map data © OpenStreetMap contributors",
        fontsize=9,
        color=MUTED,
        ha="right",
        va="bottom",
        zorder=30,
    )


def build(tf: TimezoneFinder) -> Figure:
    shape = border(tf)
    fig = plt.figure(figsize=(WIDTH_PX / DPI, HEIGHT_PX / DPI), dpi=DPI)
    fig.patch.set_facecolor(PAPER)
    ax = fig.add_axes((0, 0, 1, 1))
    draw_map(ax, tf, shape, window())
    draw_labels(ax)
    fade(fig)
    magnified = loupe(fig, ax, tf, shape)
    draw_text(fig, shape)

    def zone_at(point: QueryPoint) -> str:
        zone = tf.timezone_at(lng=point.lng, lat=point.lat)
        if zone is None:
            raise ValueError(
                f"no zone at {point}: the packaged data covers every point"
            )
        return zone

    for point in (WEST_POINT, EAST_POINT):
        zone = zone_at(point)
        style = dict(fontsize=15, fontweight="bold")
        card(
            fig,
            ax,
            point,
            [(f"{zone}  {UTC_OFFSET[zone]}", ZONE_INK[zone], style)],
            ZONE_INK[zone],
        )
    zone = zone_at(GAP_POINT)
    wrong = simplified_answer(shape, GAP_POINT)
    card(
        fig,
        magnified,
        GAP_POINT,
        [
            (
                f"✓ {zone}  {UTC_OFFSET[zone]}",
                ZONE_INK[zone],
                dict(fontsize=15, fontweight="bold"),
            ),
            (f"✗ {wrong}  simplified", WRONG, dict(fontsize=13)),
        ],
        WRONG,
    )
    return fig


STYLE = {
    "svg.hashsalt": SVG_HASH_SALT,
    # real <text> nodes rather than glyph outlines from whatever fonts are installed
    "svg.fonttype": "none",
    "font.family": "DejaVu Sans",
}


def render(tf: TimezoneFinder) -> str:
    """The banner as SVG markup: deterministic, and already pre-commit-clean."""
    with plt.style.context("default"), matplotlib.rc_context(STYLE):
        fig = build(tf)
        try:
            buffer = StringIO()
            fig.savefig(buffer, format="svg", metadata={"Date": None})
        finally:
            plt.close(fig)
    svg = buffer.getvalue()
    return "\n".join(line.rstrip() for line in svg.splitlines()) + "\n"


def render_png(tf: TimezoneFinder, path: Path) -> None:
    """The banner as a PNG at 1.5 times its size, for the README.

    Reduced to a 256-colour palette: the full-colour file is several times larger than
    the repository's limit for an added file, and a flat-coloured map loses nothing
    visible to the palette.
    """
    from PIL import Image

    with plt.style.context("default"), matplotlib.rc_context(STYLE):
        fig = build(tf)
        try:
            buffer = BytesIO()
            fig.savefig(
                buffer, format="png", dpi=DPI * 1.5, metadata={"Software": None}
            )
        finally:
            plt.close(fig)
    image = Image.open(buffer).convert("RGB")
    image.quantize(colors=256, method=Image.Quantize.MEDIANCUT).save(
        path, optimize=True
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out",
        type=Path,
        default=FIGURE_PATH,
        help=f"where to write the SVG (default: {FIGURE_PATH})",
    )
    parser.add_argument(
        "--png",
        type=Path,
        default=PNG_PATH,
        help=f"where to write the PNG (default: {PNG_PATH})",
    )
    parser.add_argument(
        "--osm",
        type=Path,
        help="rebuild the committed map excerpt from this Overpass JSON response to OVERPASS_QUERY before drawing",
    )
    args = parser.parse_args(argv)
    if args.osm is not None:
        write_json(extract_osm(args.osm), MAP_PATH)
    tf = TimezoneFinder()
    args.out.write_text(render(tf), encoding="utf-8")
    render_png(tf, args.png)
    print(f"wrote {args.out} and {args.png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
