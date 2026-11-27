#!/usr/bin/env python3

"""Draw the README banner and the border-town figure of the no-simplification page.

Both show the border between Brazil (America/Campo_Grande, UTC-4) and Paraguay
(America/Asuncion, UTC-3) where it runs along Avenida Internacional, between the twin
towns of Ponta Porã and Pedro Juan Caballero: one street, two countries, two clocks.

**The banner** draws the border at street-level zoom with every vertex the package
stores, and magnifies one stretch of the avenue with a lookup on each side of it. The
border, its vertex count, both answers and both clock times come from the packaged data
and from ``timezone_at``, so the banner follows the data rather than a drawing of it.

**The border-town figure** draws the same border beside the one ``tzfpy`` ships, which is
simplified, and marks the buildings near the border that ``tzfpy`` places in the other
zone. Those answers are a measurement of another package, so they are not recomputed on
every redraw: ``--measure`` records them in :data:`MEASUREMENT_PATH` with both packages'
versions, and the figure is drawn from that record. It needs the ``compare`` dependency
group; drawing does not.

The map underneath - built-up areas, water, streets, building outlines and town names -
is the one input that is neither the package's nor a measurement: an excerpt of
OpenStreetMap, committed as :data:`MAP_PATH` so a redraw needs no download. It orients
the reader and gives the measurement its buildings; the lookup never reads it. The
timezone boundaries are built from OpenStreetMap too, so the avenue and the border line
up at this zoom. To rebuild the excerpt, pass the JSON that :data:`OVERPASS_QUERY`
returns with ``--osm``. Only buildings within :data:`BAND_METRES` of the border are
kept: that band is where a simplified border can be wrong, and the whole town would not
fit the repository's file size limit. The excerpt's lines are thinned to about a pixel;
the border is drawn from every vertex the package stores.

The drawing is deterministic, so a redraw only changes the files when the data, the
record or the layout changed. ``make hero-banner`` redraws both SVGs and the PNG the
README embeds - PyPI and GitHub's raw file host do not serve SVG as an image.
"""

import argparse
import json
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO, StringIO
from itertools import pairwise
from pathlib import Path
from zoneinfo import ZoneInfo

import matplotlib

# before pyplot, which otherwise picks an interactive backend that CI has no display for
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import patheffects  # noqa: E402
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
COMPARISON_PATH = DOC_ROOT / "border_town_simplified.svg"
MEASUREMENT_PATH = DOC_ROOT / "border_town_simplified.json"
MAP_SOURCE = "OpenStreetMap, via the Overpass API (© OpenStreetMap contributors, ODbL)"

#: Element ids are otherwise salted from ``uuid4()``, so every render would differ.
SVG_HASH_SALT = "timezonefinder-hero-banner"

#: The query whose response ``--osm`` reads. Building outlines are asked for in a smaller
#: box than the rest: they are only kept near the border, and the whole town is large.
OVERPASS_QUERY = """\
[out:json][timeout:180][bbox:-22.62,-55.80,-22.48,-55.62];
(
  way["natural"="water"]; relation["natural"="water"];
  way["waterway"~"^(river|stream)$"];
  way["highway"~"^(motorway|trunk|primary|secondary|tertiary|residential)$"];
  way["landuse"~"^(residential|commercial|retail|industrial)$"];
  node["place"~"^(city|town|suburb|neighbourhood)$"];
  way["building"](-22.585,-55.745,-22.525,-55.675);
);
out geom;
"""

#: The box the building outlines were fetched in: the measurement's claims hold inside it.
BUILDING_BOX: Box = (-55.745, -22.585, -55.675, -22.525)

BRAZIL, PARAGUAY = "America/Campo_Grande", "America/Asuncion"
ZONES = (BRAZIL, PARAGUAY)
COUNTRY = {BRAZIL: "Brazil", PARAGUAY: "Paraguay"}
TOWN = {BRAZIL: "Ponta Porã", PARAGUAY: "Pedro Juan Caballero"}
TOWNS = frozenset(TOWN.values())

#: The instant whose local times the banner shows: noon on the Brazilian side.
SHOWN_INSTANT = datetime(2026, 1, 15, 16, 0, tzinfo=UTC)

#: Buildings further than this from the border are left out of the excerpt.
BAND_METRES = 150.0

WIDTH_PX, HEIGHT_PX, DPI = 1600, 800, 100

#: Where the banner's map is centred and how far it reaches north to south, in degrees.
CENTRE = (-55.7322, -22.5523)
LAT_SPAN = 0.030

#: The stretch of Avenida Internacional the magnifier shows, and the two lookups in it:
#: this far from the border on either side, perpendicular to it.
AVENUE = (-55.7276, -22.5452)
PIN_METRES = 45.0

#: The magnifier: ``LOUPE_ZOOM`` times closer, in a circle of ``LOUPE_RADIUS_PX`` centred
#: at ``LOUPE_CENTRE_PX`` (pixels from the top left).
LOUPE_ZOOM = 5.0
LOUPE_RADIUS_PX = 150
LOUPE_CENTRE_PX = (1290, 345)

#: Where each lookup's card sits: its top left corner, in pixels from the top left.
CARD_AT = {BRAZIL: (1165, 40), PARAGUAY: (940, 560)}
CARD_WIDTH = 400

#: Where each town's name is written on the banner, in pixels from the top left; the
#: test asserts that each lies in its own town's zone.
TOWN_LABEL_PX = {BRAZIL: (1520, 570), PARAGUAY: (1010, 700)}

#: The border-town figure's map: the stretch of the avenue where ``tzfpy`` answers the
#: most buildings in the other zone, ``COMPARISON_HALF`` degrees of latitude each way.
COMPARISON_CENTRE = (-55.7128, -22.5568)
COMPARISON_HALF = 0.0028

#: Vertices of the background map closer together than this, in degrees (Manhattan),
#: are dropped: about a pixel in the magnifier.
MAP_TOLERANCE = 0.00004

#: Map polygons smaller than this many square degrees are left out of the excerpt,
#: except buildings, which are small by nature.
MIN_AREA = 1e-7

PAPER = "#f8fafc"
ZONE_FILL = {BRAZIL: "#dcfce7", PARAGUAY: "#e0e7ff"}
ZONE_INK = {BRAZIL: "#15803d", PARAGUAY: "#4338ca"}
BUILT_UP = "#e5e7eb"
BUILDING = "#c4c9d1"
WATER = "#a9cdee"
STREET = "#ffffff"
MAJOR = "#fef3c7"
MAJOR_CASING = "#e2c27a"
INK = "#0f172a"
MUTED = "#475569"
WRONG = "#dc2626"


# --- geometry -------------------------------------------------------------------------


def banner_view() -> Box:
    """``(west, south, east, north)`` of the banner's map, at its aspect ratio."""
    lng, lat = CENTRE
    lng_span = LAT_SPAN * WIDTH_PX / HEIGHT_PX / math.cos(math.radians(lat))
    return (
        lng - lng_span / 2,
        lat - LAT_SPAN / 2,
        lng + lng_span / 2,
        lat + LAT_SPAN / 2,
    )


def comparison_view() -> Box:
    lng, lat = COMPARISON_CENTRE
    half_lng = COMPARISON_HALF / math.cos(math.radians(lat))
    return (
        lng - half_lng,
        lat - COMPARISON_HALF,
        lng + half_lng,
        lat + COMPARISON_HALF,
    )


def pixel_to_lnglat(x: float, y: float) -> tuple[float, float]:
    """A banner pixel (from the top left) to where it is on the banner's map."""
    west, south, east, north = banner_view()
    return west + (east - west) * x / WIDTH_PX, north - (north - south) * y / HEIGHT_PX


def margin_box(box: Box, margin: float) -> Box:
    return (box[0] - margin, box[1] - margin, box[2] + margin, box[3] + margin)


#: Everything drawn or measured lies in here; the zones are clipped to it.
WORLD: Box = margin_box(BUILDING_BOX, 0.03)


def metres_xy(lng: float, lat: float) -> tuple[float, float]:
    """A local equirectangular projection around :data:`CENTRE`, in metres."""
    radius = 6_371_008.8
    x = math.radians(lng - CENTRE[0]) * radius * math.cos(math.radians(CENTRE[1]))
    return x, math.radians(lat - CENTRE[1]) * radius


def from_metres(x: float, y: float) -> tuple[float, float]:
    radius = 6_371_008.8
    lat = CENTRE[1] + math.degrees(y / radius)
    return CENTRE[0] + math.degrees(
        x / (radius * math.cos(math.radians(CENTRE[1])))
    ), lat


def on_edge(point: tuple[float, float], box: Box) -> bool:
    return point[0] in (box[0], box[2]) or point[1] in (box[1], box[3])


def border_runs(ring: Ring, box: Box) -> list[Ring]:
    """The parts of a ring clipped to ``box`` that are border rather than the box."""
    start = next((i for i, p in enumerate(ring) if on_edge(p, box)), None)
    if start is None:
        return [ring + ring[:1]]
    rotated = ring[start:] + ring[:start] + [ring[start]]
    runs: list[Ring] = []
    for a, b in pairwise(rotated):
        # an edge between two box points runs along the box
        if on_edge(a, box) and on_edge(b, box) and (a[0] == b[0] or a[1] == b[1]):
            continue
        if runs and runs[-1][-1] == a:
            runs[-1].append(b)
        else:
            runs.append([a, b])
    return runs


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


def border(tf: TimezoneFinder) -> list[Ring]:
    """The border between the two zones in :data:`WORLD`, as the package stores it."""
    return [
        run
        for ring in zone_rings(tf, PARAGUAY, WORLD)
        for run in border_runs(ring, WORLD)
    ]


def in_box(point: tuple[float, float], box: Box) -> bool:
    return box[0] <= point[0] <= box[2] and box[1] <= point[1] <= box[3]


def vertices_in(runs: Sequence[Ring], box: Box) -> int:
    return len({p for run in runs for p in run if in_box(p, box)})


def distance_m(point: tuple[float, float], runs: Sequence[Ring]) -> float:
    """The distance from a point to the nearest border segment, in metres."""
    x, y = metres_xy(*point)
    best = math.inf
    for run in runs:
        xy = [metres_xy(*p) for p in run]
        for (x1, y1), (x2, y2) in pairwise(xy):
            dx, dy = x2 - x1, y2 - y1
            length2 = dx * dx + dy * dy
            t = (
                0.0
                if length2 == 0
                else max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / length2))
            )
            best = min(best, math.hypot(x - x1 - t * dx, y - y1 - t * dy))
    return best


@dataclass(frozen=True)
class Lookup:
    zone: str
    lng: float
    lat: float


def avenue_lookups(tf: TimezoneFinder, runs: Sequence[Ring]) -> list[Lookup]:
    """A point :data:`PIN_METRES` from the border on each side of it at :data:`AVENUE`."""
    x, y = metres_xy(*AVENUE)
    best = None
    for run in runs:
        for a, b in pairwise(metres_xy(*p) for p in run):
            dx, dy = b[0] - a[0], b[1] - a[1]
            length = math.hypot(dx, dy)
            if length == 0:
                continue
            t = max(0.0, min(1.0, ((x - a[0]) * dx + (y - a[1]) * dy) / length**2))
            foot = (a[0] + t * dx, a[1] + t * dy)
            d = math.hypot(x - foot[0], y - foot[1])
            if best is None or d < best[0]:
                best = (d, foot, (-dy / length, dx / length))
    assert best is not None
    _, (fx, fy), (nx, ny) = best
    lookups = []
    for side in (1, -1):
        lng, lat = from_metres(fx + side * PIN_METRES * nx, fy + side * PIN_METRES * ny)
        zone = tf.timezone_at(lng=lng, lat=lat)
        if zone not in ZONES:
            raise ValueError(
                f"{zone} at {lng}, {lat}: the avenue is not where the figure expects"
            )
        lookups.append(Lookup(zone, round(lng, 5), round(lat, 5)))
    return sorted(lookups, key=lambda lookup: ZONES.index(lookup.zone))


def local_time(zone: str) -> str:
    return SHOWN_INSTANT.astimezone(ZoneInfo(zone)).strftime("%H:%M")


def utc_offset(zone: str) -> str:
    offset = SHOWN_INSTANT.astimezone(ZoneInfo(zone)).utcoffset()
    assert offset is not None
    hours = offset.total_seconds() / 3600
    return f"UTC{'+' if hours >= 0 else '−'}{abs(hours):g}"


# --- the map excerpt ------------------------------------------------------------------


def encode(line: Iterable[tuple[float, float]]) -> str:
    """A line as ``"lng,lat dlng,dlat ..."`` in steps of 1e-5 degrees, about a metre.

    The first point is absolute and each later one an offset from the one before, as
    integers. One string per line rather than nested arrays, which the repository's JSON
    formatter would spread over one line per number - several times the file size.
    """
    steps = [(round(x * 1e5), round(y * 1e5)) for x, y in line]
    first = [f"{steps[0][0]},{steps[0][1]}"]
    return " ".join(
        first + [f"{x - px},{y - py}" for (px, py), (x, y) in pairwise(steps)]
    )


def decode(line: str) -> Ring:
    points: Ring = []
    x = y = 0
    for pair in line.split():
        dx, dy = pair.split(",")
        x, y = x + int(dx), y + int(dy)
        points.append((x / 1e5, y / 1e5))
    return points


def thin(line: Ring) -> Ring:
    """Drop vertices closer than :data:`MAP_TOLERANCE` to the last one kept."""
    kept = [line[0]]
    for point in line[1:-1]:
        if abs(point[0] - kept[-1][0]) + abs(point[1] - kept[-1][1]) >= MAP_TOLERANCE:
            kept.append(point)
    kept.append(line[-1])
    return kept


def area(ring: Ring) -> float:
    return abs(
        sum(
            x1 * y2 - x2 * y1
            for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1], strict=True)
        )
        / 2
    )


def centre_of(ring: Ring) -> tuple[float, float]:
    """The mean of a ring's vertices: where a building is looked up."""
    return sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring)


def join(lines: Iterable[Ring]) -> list[Ring]:
    """Join lines that share end points: a multipolygon's member ways arrive in pieces."""
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
                elif a[-1] == b[-1] and a[0] != a[-1]:
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


def extract_osm(overpass_json: Path, tf: TimezoneFinder) -> dict:
    """The background map of an Overpass response, as the committed excerpt.

    Clipped to the banner's view, which holds the border-town figure's: the response
    reaches further, so that streets run off the edge rather than end inside it.
    """
    box = margin_box(banner_view(), 0.002)
    runs = border(tf)
    elements = json.loads(overpass_json.read_text(encoding="utf-8"))["elements"]
    layers: dict[str, list] = {
        "buildings": [],
        "built_up": [],
        "major_roads": [],
        "places": [],
        "streams": [],
        "streets": [],
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

    for element in elements:
        tags = element.get("tags", {})
        if element["type"] == "node":
            if tags.get("name") in TOWNS and tags.get("place") in ("city", "town"):
                layers["places"].append(
                    {"lat": element["lat"], "lng": element["lon"], "name": tags["name"]}
                )
        elif "building" in tags:
            ring = [(p["lon"], p["lat"]) for p in element.get("geometry", []) if p][:-1]
            if len(ring) >= 3 and distance_m(centre_of(ring), runs) <= BAND_METRES:
                layers["buildings"].append({"id": element["id"], "ring": encode(ring)})
        elif tags.get("natural") == "water":
            add_polygons("water", element)
        elif "landuse" in tags:
            add_polygons("built_up", element)
        elif "waterway" in tags:
            add_lines("streams", element)
        elif tags.get("highway") in ("motorway", "trunk", "primary", "secondary"):
            add_lines("major_roads", element)
        elif "highway" in tags:
            add_lines("streets", element)
    for layer in layers.values():
        layer.sort(key=json.dumps)
    return {
        "box": list(box),
        "layers": layers,
        "query": OVERPASS_QUERY,
        "source": MAP_SOURCE,
    }


def read_map(view: Box | None = None) -> dict:
    """The committed excerpt, decoded; with ``view``, only what reaches into it."""
    layers = json.loads(MAP_PATH.read_text(encoding="utf-8"))["layers"]

    def decoded(item):
        if isinstance(item, str):
            return decode(item)
        if "ring" in item:
            return {**item, "ring": decode(item["ring"])}
        return item

    def reaches(item) -> bool:
        if view is None or "name" in item:
            return True
        line = item["ring"] if isinstance(item, dict) else item
        return not (
            max(p[0] for p in line) < view[0]
            or min(p[0] for p in line) > view[2]
            or max(p[1] for p in line) < view[1]
            or min(p[1] for p in line) > view[3]
        )

    return {
        name: [item for item in map(decoded, items) if reaches(item)]
        for name, items in layers.items()
    }


# --- the measurement ------------------------------------------------------------------


def measure(tf: TimezoneFinder) -> dict:
    """Look every building in the excerpt up with both packages, and keep tzfpy's border."""
    import importlib.metadata

    import tzfpy

    buildings = read_map()["buildings"]
    wrong = []
    for building in buildings:
        lng, lat = centre_of(building["ring"])
        ours = tf.timezone_at(lng=lng, lat=lat)
        theirs = tzfpy.get_tz(lng, lat)
        if ours != theirs:
            wrong.append(
                {"id": building["id"], "theirs": theirs, "timezonefinder": ours}
            )
    simplified: list[str] = []
    geometry = json.loads(tzfpy.get_tz_polygon_geojson(PARAGUAY))["features"][0][
        "geometry"
    ]
    for polygon in geometry["coordinates"]:
        ring = [(p[0], p[1]) for p in polygon[0]]
        clipped = clip_ring([p[0] for p in ring], [p[1] for p in ring], WORLD)
        if len(clipped) >= 3:
            simplified.extend(encode(run) for run in border_runs(clipped, WORLD))
    return {
        "band_metres": BAND_METRES,
        "building_box": list(BUILDING_BOX),
        "buildings": len(buildings),
        "simplified_border": sorted(simplified),
        "timezonefinder_data": tf.data_version,
        "tzfpy": importlib.metadata.version("tzfpy"),
        "tzfpy_data": tzfpy.data_version(),
        "wrong": sorted(wrong, key=lambda w: w["id"]),
    }


def read_measurement() -> dict:
    return json.loads(MEASUREMENT_PATH.read_text(encoding="utf-8"))


# --- drawing --------------------------------------------------------------------------


def px(x: float, y: float) -> tuple[float, float]:
    """Pixels from the top left to figure fractions."""
    return x / WIDTH_PX, 1 - y / HEIGHT_PX


def to_pixels(ax: Axes, lng: float, lat: float) -> tuple[float, float]:
    x, y = ax.transData.transform((lng, lat))
    return x, HEIGHT_PX - y


def halo(width: float = 3.5) -> list:
    return [patheffects.withStroke(linewidth=width, foreground="white", alpha=0.9)]


def compound(lines: Iterable[Ring], closed: bool) -> MplPath:
    """Many lines or rings as one path: one SVG element, not one per line."""
    vertices: list[tuple[float, float]] = []
    codes: list[int] = []
    for line in lines:
        points = list(line) + ([line[0]] if closed else [])
        vertices.extend(points)
        codes.extend([MplPath.MOVETO] + [MplPath.LINETO] * (len(points) - 1))
    return MplPath(vertices or [(0.0, 0.0)], codes or [MplPath.MOVETO])


def fill(ax: Axes, rings: Iterable[Ring], colour: str, zorder: float, **style) -> None:
    ax.add_patch(
        PathPatch(
            compound(rings, True),
            facecolor=colour,
            edgecolor="none",
            zorder=zorder,
            **style,
        )
    )


def stroke(
    ax: Axes, lines: Iterable[Ring], colour: str, width: float, zorder: float, **style
) -> None:
    style.setdefault("capstyle", "round")
    style.setdefault("joinstyle", "round")
    ax.add_patch(
        PathPatch(
            compound(lines, False),
            fill=False,
            edgecolor=colour,
            linewidth=width,
            zorder=zorder,
            **style,
        )
    )


def set_view(ax: Axes, view: Box) -> None:
    ax.set_xlim(view[0], view[2])
    ax.set_ylim(view[1], view[3])
    ax.set_aspect(1 / math.cos(math.radians(CENTRE[1])))
    ax.set_axis_off()


def draw_map(
    ax: Axes,
    tf: TimezoneFinder,
    runs: Sequence[Ring],
    view: Box,
    scale: float = 1.0,
    buildings: bool = True,
    wrong: frozenset[int] = frozenset(),
) -> None:
    """The map layers and the border in ``view``; ``scale`` widens lines when zoomed in."""
    set_view(ax, view)
    layers = read_map(margin_box(view, 0.002))
    ax.add_patch(
        Rectangle(
            view[:2], view[2] - view[0], view[3] - view[1], facecolor=PAPER, zorder=0
        )
    )
    for zone in ZONES:
        fill(ax, zone_rings(tf, zone, WORLD), ZONE_FILL[zone], 0.1)
    fill(
        ax,
        [i["ring"] for i in layers["built_up"] if not i["hole"]],
        BUILT_UP,
        0.2,
        alpha=0.6,
    )
    fill(ax, [i["ring"] for i in layers["water"] if not i["hole"]], WATER, 0.3)
    stroke(ax, layers["streams"], WATER, 1.0 * scale, 0.4)
    stroke(ax, layers["streets"], STREET, 1.0 * scale, 0.5)
    stroke(ax, layers["major_roads"], MAJOR_CASING, 2.6 * scale, 0.6)
    stroke(ax, layers["major_roads"], MAJOR, 1.8 * scale, 0.61)
    if buildings:
        fill(
            ax,
            [b["ring"] for b in layers["buildings"] if b["id"] not in wrong],
            BUILDING,
            0.7,
        )
        fill(
            ax,
            [b["ring"] for b in layers["buildings"] if b["id"] in wrong],
            WRONG,
            0.71,
        )
    mark = 1.0 if scale == 1 else 1.5
    stroke(ax, runs, INK, 2.4 * mark, 3)
    near = [p for run in runs for p in run[:-1] if in_box(p, margin_box(view, 0.001))]
    ax.plot(
        *zip(*near, strict=True),
        "o",
        color=INK,
        markersize=2.6 * mark,
        zorder=3.1,
        linestyle="none",
    )


def draw_towns(fig: Figure) -> None:
    for zone, (x, y) in TOWN_LABEL_PX.items():
        fig.text(
            *px(x, y),
            f"{TOWN[zone]}\n{COUNTRY[zone].upper()}",
            fontsize=13,
            color=ZONE_INK[zone],
            fontweight="bold",
            ha="center",
            va="center",
            linespacing=1.3,
            zorder=12,
            path_effects=halo(),
        )


def fade(fig: Figure) -> None:
    """A white wash behind the title that clears before the border."""
    solid, clear = 0.30, 0.50  # fractions of the width
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


def loupe(fig: Figure, main: Axes, tf: TimezoneFinder, runs: Sequence[Ring]) -> Axes:
    """The avenue magnified in a circle, tied to where it is on the map."""
    cx, cy = LOUPE_CENTRE_PX
    r = LOUPE_RADIUS_PX
    ax = fig.add_axes(
        (*px(cx - r, cy + r), 2 * r / WIDTH_PX, 2 * r / HEIGHT_PX), zorder=15
    )
    lat_half = r / HEIGHT_PX * LAT_SPAN / LOUPE_ZOOM
    lng_half = lat_half / math.cos(math.radians(CENTRE[1]))
    view = (
        AVENUE[0] - lng_half,
        AVENUE[1] - lat_half,
        AVENUE[0] + lng_half,
        AVENUE[1] + lat_half,
    )
    draw_map(ax, tf, runs, view, scale=2.0)
    disc = Circle((0.5, 0.5), 0.5, transform=ax.transAxes)
    for artist in ax.get_children():
        artist.set_clip_path(disc)
    ax.text(
        0.5,
        0.86,
        f"Avenida Internacional  × {LOUPE_ZOOM:g}",
        transform=ax.transAxes,
        fontsize=9.5,
        color=MUTED,
        ha="center",
        va="center",
        zorder=5,
        path_effects=halo(),
    )

    sx, sy = to_pixels(main, *AVENUE)
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


def card(fig: Figure, ax: Axes, lookup: Lookup) -> None:
    x, y = CARD_AT[lookup.zone]
    width, height = CARD_WIDTH, 104
    accent = ZONE_INK[lookup.zone]
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
        *px(x + 20, y + 24),
        f"{TOWN[lookup.zone]}, {COUNTRY[lookup.zone]}",
        fontsize=12,
        fontweight="bold",
        color=INK,
        va="center",
        zorder=22,
    )
    fig.text(
        *px(x + 20, y + 50),
        f"{lookup.lat:.5f}, {lookup.lng:.5f}",
        fontsize=10,
        color=MUTED,
        family="DejaVu Sans Mono",
        va="center",
        zorder=22,
    )
    fig.text(
        *px(x + 20, y + 80),
        lookup.zone,
        fontsize=14,
        fontweight="bold",
        color=accent,
        family="DejaVu Sans Mono",
        va="center",
        zorder=22,
    )
    fig.text(
        *px(x + width - 18, y + 70),
        local_time(lookup.zone),
        fontsize=26,
        fontweight="bold",
        color=accent,
        ha="right",
        va="center",
        zorder=22,
    )
    fig.text(
        *px(x + width - 18, y + 92),
        utc_offset(lookup.zone),
        fontsize=9,
        color=MUTED,
        ha="right",
        va="center",
        zorder=22,
    )
    pin = to_pixels(ax, lookup.lng, lookup.lat)
    target = (
        min(max(pin[0], x + 30), x + width - 30),
        y + height if pin[1] > y + height else y,
    )
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


def draw_text(fig: Figure, runs: Sequence[Ring]) -> None:
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
        color="#1d4ed8",
        zorder=30,
    )
    fig.text(
        *px(82, 290),
        "One street, two countries, two clocks.\nEvery boundary vertex kept - no simplification.",
        fontsize=16,
        color="#334155",
        linespacing=1.5,
        va="top",
        zorder=30,
    )
    y = 430
    fig.lines.append(
        plt.Line2D(
            *zip(px(82, y), px(124, y), strict=True),
            transform=fig.transFigure,
            color=INK,
            linewidth=2.4,
            zorder=30,
        )
    )
    fig.lines.append(
        plt.Line2D(
            [px(103, y)[0]],
            [px(103, y)[1]],
            transform=fig.transFigure,
            marker="o",
            markersize=4,
            color=INK,
            zorder=30,
        )
    )
    fig.text(
        *px(140, y),
        f"the border as published: all {vertices_in(runs, banner_view())} vertices in view",
        fontsize=13,
        color=INK,
        va="center",
        zorder=30,
    )
    for i, zone in enumerate(ZONES):
        fig.patches.append(
            Rectangle(
                px(86, y + 44 + 30 * i),
                34 / WIDTH_PX,
                16 / HEIGHT_PX,
                transform=fig.transFigure,
                facecolor=ZONE_FILL[zone],
                edgecolor=ZONE_INK[zone],
                zorder=30,
            )
        )
        fig.text(
            *px(140, y + 36 + 30 * i),
            f"{COUNTRY[zone]}  {zone}  {utc_offset(zone)}",
            fontsize=12,
            color=ZONE_INK[zone],
            family="DejaVu Sans Mono",
            va="center",
            zorder=30,
        )
    fig.text(
        *px(82, 745),
        "Ponta Porã (BR) and Pedro Juan Caballero (PY), 22.55° S 55.73° W",
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


def build_banner(tf: TimezoneFinder) -> Figure:
    runs = border(tf)
    fig = plt.figure(figsize=(WIDTH_PX / DPI, HEIGHT_PX / DPI), dpi=DPI)
    fig.patch.set_facecolor(PAPER)
    ax = fig.add_axes((0, 0, 1, 1))
    draw_map(ax, tf, runs, banner_view(), buildings=False)
    fade(fig)
    draw_towns(fig)
    magnified = loupe(fig, ax, tf, runs)
    draw_text(fig, runs)
    for lookup in avenue_lookups(tf, runs):
        card(fig, magnified, lookup)
    return fig


def comparison_counts(record: dict) -> dict[str, int]:
    """How many buildings each way round tzfpy answers in the other zone."""
    counts = {
        f"{COUNTRY[a]} as {COUNTRY[b]}": 0 for a in ZONES for b in ZONES if a != b
    }
    for w in record["wrong"]:
        counts[f"{COUNTRY[w['timezonefinder']]} as {COUNTRY[w['theirs']]}"] += 1
    return counts


def build_comparison(tf: TimezoneFinder) -> Figure:
    """The border-town figure for ``docs/why_no_simplification.rst``."""
    record = read_measurement()
    runs = border(tf)
    simplified = [decode(line) for line in record["simplified_border"]]
    wrong = frozenset(w["id"] for w in record["wrong"])
    fig = plt.figure(figsize=(10.0, 5.6))
    ax = fig.add_axes((0.01, 0.02, 0.56, 0.96))
    draw_map(ax, tf, runs, comparison_view(), scale=1.6, wrong=wrong)
    stroke(ax, simplified, WRONG, 2.6, 2.9, linestyle=(0, (5, 4)), capstyle="butt")
    for zone, (x, y) in zip(ZONES, ((0.78, 0.92), (0.22, 0.08)), strict=True):
        ax.text(
            x,
            y,
            f"{COUNTRY[zone].upper()}\n{zone}",
            transform=ax.transAxes,
            fontsize=10,
            fontweight="bold",
            color=ZONE_INK[zone],
            ha="center",
            va="center",
            zorder=5,
            path_effects=halo(),
        )
    ax.text(
        0.99,
        0.01,
        "Map data © OpenStreetMap contributors",
        transform=ax.transAxes,
        fontsize=7,
        color=MUTED,
        ha="right",
        va="bottom",
        zorder=5,
        # a box rather than a halo: a path effect turns the text into outlines, and the
        # attribution has to stay text
        bbox=dict(boxstyle="square,pad=0.2", fc="white", ec="none", alpha=0.8),
    )

    left, y = 0.60, 0.93
    counts = comparison_counts(record)
    fig.text(
        left,
        y,
        f"{len(wrong)} of {record['buildings']:,} buildings",
        fontsize=18,
        fontweight="bold",
        color=WRONG,
        va="top",
    )
    body = (
        f"within {record['band_metres']:g} m of the border get a zone one hour\n"
        f"off from tzfpy {record['tzfpy']}, which simplifies its polygons:\n"
        + "\n".join(f"{n} in {pair}" for pair, n in counts.items())
        + ".\n\nBoth packages use timezone-boundary-builder\n"
        f"{record['tzfpy_data']}; timezonefinder answers every\n"
        "building as the published border does."
    )
    fig.text(left, y - 0.09, body, fontsize=10, color=INK, va="top", linespacing=1.45)
    legend = (
        ("line", INK, "the border as published (timezonefinder)"),
        ("dash", WRONG, f"the border tzfpy {record['tzfpy']} ships"),
        ("box", WRONG, "building tzfpy puts in the other zone"),
        (
            "box",
            BUILDING,
            f"other building within {record['band_metres']:g} m of the border",
        ),
    )
    y = 0.36
    for kind, colour, text in legend:
        if kind == "box":
            fig.patches.append(
                Rectangle(
                    (left, y - 0.014),
                    0.024,
                    0.028,
                    transform=fig.transFigure,
                    facecolor=colour,
                    edgecolor="none",
                )
            )
        else:
            fig.lines.append(
                plt.Line2D(
                    [left, left + 0.024],
                    [y, y],
                    transform=fig.transFigure,
                    color=colour,
                    linewidth=2.2,
                    linestyle="-" if kind == "line" else (0, (3, 2)),
                )
            )
        fig.text(left + 0.036, y, text, fontsize=9.5, color=MUTED, va="center")
        y -= 0.06
    return fig


STYLE = {
    "svg.hashsalt": SVG_HASH_SALT,
    # real <text> nodes rather than glyph outlines from whatever fonts are installed
    "svg.fonttype": "none",
    "font.family": "DejaVu Sans",
}


def to_svg(fig: Figure) -> str:
    try:
        buffer = StringIO()
        fig.savefig(buffer, format="svg", metadata={"Date": None})
    finally:
        plt.close(fig)
    return "\n".join(line.rstrip() for line in buffer.getvalue().splitlines()) + "\n"


def render(tf: TimezoneFinder) -> str:
    """The banner as SVG markup: deterministic, and already pre-commit-clean."""
    with plt.style.context("default"), matplotlib.rc_context(STYLE):
        return to_svg(build_banner(tf))


def render_comparison(tf: TimezoneFinder) -> str:
    """The border-town figure as SVG markup, drawn from the committed measurement."""
    with plt.style.context("default"), matplotlib.rc_context(STYLE):
        return to_svg(build_comparison(tf))


def render_png(tf: TimezoneFinder, path: Path) -> None:
    """The banner as a PNG at 1.5 times its size, for the README.

    Reduced to a 256-colour palette: the full-colour file is several times larger than
    the repository's limit for an added file, and a flat-coloured map loses nothing
    visible to the palette.
    """
    from PIL import Image

    with plt.style.context("default"), matplotlib.rc_context(STYLE):
        fig = build_banner(tf)
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
        "--osm",
        type=Path,
        help="rebuild the committed map excerpt from this Overpass JSON response to "
        "OVERPASS_QUERY before drawing",
    )
    parser.add_argument(
        "--measure",
        action="store_true",
        help="look the excerpt's buildings up with tzfpy and timezonefinder again and "
        "record the result before drawing (needs the `compare` dependency group)",
    )
    args = parser.parse_args(argv)
    tf = TimezoneFinder()
    if args.osm is not None:
        write_json(extract_osm(args.osm, tf), MAP_PATH)
    if args.measure:
        write_json(measure(tf), MEASUREMENT_PATH)
    FIGURE_PATH.write_text(render(tf), encoding="utf-8")
    COMPARISON_PATH.write_text(render_comparison(tf), encoding="utf-8")
    render_png(tf, PNG_PATH)
    print(f"wrote {FIGURE_PATH}, {COMPARISON_PATH} and {PNG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
