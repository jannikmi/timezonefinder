#!/usr/bin/env python3

"""Draw the shortcut index figure that ``docs/architecture.rst`` embeds.

The figure shows a few root cells of the real index where France and Germany meet on
the Rhine, and three lookups through them: one answered by the table alone, one whose
first candidate polygon contains the point, and one where that test rules the first zone
out and the last zone is answered without one. The cells, the zone outlines and every
number in the text come from the packaged data and from replaying the real lookup, so
the figure follows the index rather than a drawing of it.

The rivers are the one input that is not the package's: an excerpt of Natural Earth's
public-domain 1:10m river centre lines, committed beside the figure so a redraw needs
no download. They orient the reader and nothing else; the lookup never reads them. To
rebuild the excerpt, pass a downloaded ``ne_10m_rivers_lake_centerlines.geojson`` with
``--natural-earth``.

The drawing is deterministic, so a redraw only changes the file when the data or the
layout changed. It depends on the packaged data: after a data update, the vertex counts
it states and possibly its cells change, which ``make shortcut-index-figure`` redraws.
"""

import argparse
import json
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

import matplotlib

# before pyplot, which otherwise picks an interactive backend that CI has no display for
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Polygon, Rectangle  # noqa: E402

from scripts.configs import DOC_ROOT  # noqa: E402
from scripts.utils import write_json  # noqa: E402
from timezonefinder import TimezoneFinder, utils  # noqa: E402
from timezonefinder.configs import COORD2INT_FACTOR  # noqa: E402
from timezonefinder.shortcut_index import (  # noqa: E402
    ABSENT,
    cell_bounds,
    child_cells_of,
    root_cell_of,
    shifted,
)

FIGURE_PATH = DOC_ROOT / "shortcut_index_rhine.svg"
RIVERS_PATH = DOC_ROOT / "shortcut_index_rivers.json"
RIVERS_SOURCE = "Natural Earth 1:10m rivers_lake_centerlines, v5.1.2 (public domain)"

#: Element ids are otherwise salted from ``uuid4()``, so every render would differ.
SVG_HASH_SALT = "timezonefinder-shortcut-index"

#: Width of a root cell in degrees. Whole root cells are what the figure shows, so the
#: window has to start and end on their edges - see :func:`check_aligned`.
ROOT_DEGREES = 0.75

#: ``(west, south, east, north)``: 4 x 2 root cells around Strasbourg. Chosen so that
#: only Europe/Paris and Europe/Berlin appear, with unsplit root cells on both sides;
#: one root row further south, Switzerland reaches into the window.
WINDOW = (6.75, 48.0, 9.75, 49.5)

LAND_ZONES = {"Europe/Paris": "FRANCE", "Europe/Berlin": "GERMANY"}


@dataclass(frozen=True)
class QueryPoint:
    label: str
    title: str
    lng: float
    lat: float


#: One point per case the figure explains; ``tests/test_shortcut_index_figure.py``
#: asserts that each still lands in the case it is drawn for.
QUERIES = (
    QueryPoint("1", "Colmar", 7.36, 48.08),
    QueryPoint("2", "Lorraine, 20 km from the border", 7.20, 48.94),
    QueryPoint("3", "Kehl, opposite Strasbourg", 7.81, 48.57),
)

# name: (lng, lat, label dx, label dy, horizontal alignment)
CITIES = {
    "Strasbourg": (7.75, 48.58, -0.07, -0.005, "right"),
    "Karlsruhe": (8.40, 49.01, 0.07, -0.005, "left"),
    "Stuttgart": (9.18, 48.78, 0.07, -0.005, "left"),
    "Saarbrücken": (6.99, 49.23, 0.0, 0.07, "center"),
}

#: Natural Earth spells the river by the country it flows through.
MAIN_RIVER = frozenset({"Rhine", "Rhin"})

FILL = {"Europe/Paris": "#dedaf3", "Europe/Berlin": "#f3e9d0"}
COUNTRY_INK = {"Europe/Paris": "#a79fdb", "Europe/Berlin": "#cfb77b"}
INK = "#262a2e"
MUTED = "#626a72"
GRID = "#a3abb3"
BORDER = "#7b5a2e"
HATCH = "#d07a1f"
RIVER = "#3a7cc0"

#: Vertices closer together than this (in degrees, Manhattan) are dropped from the
#: *drawn* outlines: well below a pixel at this scale, and it keeps the file small.
DRAWING_TOLERANCE = 0.006


# --- what the figure states ---------------------------------------------------------


@dataclass(frozen=True)
class Lookup:
    """One ``timezone_at`` call replayed: the cell's candidates and the tests it ran."""

    answer: str
    candidates: tuple[int, ...]
    tested: tuple[int, ...]


def replay(tf: TimezoneFinder, point: QueryPoint) -> Lookup:
    """What ``timezone_at`` does at a point, step by step, as the figure tells it."""
    answer = tf.timezone_at(lng=point.lng, lat=point.lat)
    if answer is None:
        raise ValueError(f"no zone at {point}: the packaged data covers every point")
    entry = tf.shortcuts.entry_at(point.lng, point.lat)
    if entry >= 0:
        return Lookup(answer, (), ())
    candidates = tuple(int(c) for c in tf.shortcuts.candidates_of(entry))
    stop = tf.shortcuts.stop_index_of(entry)
    x, y = utils.query2int(point.lng, point.lat)
    tested = []
    for boundary_id in candidates[:stop]:
        tested.append(boundary_id)
        if tf.inside_of_polygon(boundary_id, x, y):
            break
    return Lookup(answer, candidates, tuple(tested))


def describe(tf: TimezoneFinder, lookup: Lookup) -> str:
    """The explanation of one query point, worded from what the lookup did."""
    if not lookup.candidates:
        return (
            "one zone in the cell: the table stores\n"
            f"{lookup.answer} itself. No polygon is tested."
        )
    lines = [f"{len(lookup.candidates)} candidate polygons in the cell."]
    for boundary_id in lookup.tested:
        zone = tf.zone_name_from_boundary_id(boundary_id)
        vertices = len(tf.coords_of(boundary_id)[0])
        verdict = (
            "contains the point" if zone == lookup.answer else "does not contain it"
        )
        lines.append(f"Test {zone} ({vertices:,} vertices):\n{verdict}.")
    if tf.zone_name_from_boundary_id(lookup.tested[-1]) != lookup.answer:
        lines.append(f"{lookup.answer} is the only zone left,\nso it needs no test.")
    lines.append(f"{len(lookup.tested)} of {tf.nr_of_polygons:,} polygons tested.")
    return "\n".join(lines)


# --- geometry -------------------------------------------------------------------------


Box = tuple[float, float, float, float]
Ring = list[tuple[float, float]]


def check_aligned(box: Box) -> None:
    """Refuse a window that does not start and end on root-cell edges.

    The root grid is drawn from the window, so an unaligned one draws lines where the
    index has no cell edge.
    """
    for value, origin in (
        (box[0], -180.0),
        (box[2], -180.0),
        (box[1], -90.0),
        (box[3], -90.0),
    ):
        steps = (value - origin) / ROOT_DEGREES
        if abs(steps - round(steps)) > 1e-9:
            raise ValueError(
                f"{value} is not on a root-cell edge of the shortcut index"
            )


def clip_ring(xs: Sequence[float], ys: Sequence[float], box: Box) -> Ring:
    """Sutherland-Hodgman clip of one ring to an axis-aligned box."""
    x0, y0, x1, y1 = box

    def at_x(a, b, x):
        return x, a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0])

    def at_y(a, b, y):
        return a[0] + (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]), y

    points: Ring = list(zip(xs, ys, strict=True))
    for inside, cut in (
        (lambda p: p[0] >= x0, lambda a, b: at_x(a, b, x0)),
        (lambda p: p[0] <= x1, lambda a, b: at_x(a, b, x1)),
        (lambda p: p[1] >= y0, lambda a, b: at_y(a, b, y0)),
        (lambda p: p[1] <= y1, lambda a, b: at_y(a, b, y1)),
    ):
        clipped: Ring = []
        for i in range(len(points)):
            a, b = points[i - 1], points[i]
            if inside(b):
                if not inside(a):
                    clipped.append(cut(a, b))
                clipped.append(b)
            elif inside(a):
                clipped.append(cut(a, b))
        points = clipped
        if not points:
            break
    return points


def thin(ring: Ring) -> Ring:
    """Drop vertices closer than :data:`DRAWING_TOLERANCE` to the last one kept."""
    kept = [ring[0]]
    for point in ring[1:]:
        if (
            abs(point[0] - kept[-1][0]) + abs(point[1] - kept[-1][1])
            >= DRAWING_TOLERANCE
        ):
            kept.append(point)
    return kept


def zone_outlines(tf: TimezoneFinder, zone: str, box: Box) -> Iterator[Ring]:
    """The outer rings of a zone's polygons, clipped to just beyond ``box``."""
    margin = 0.02
    wide = (box[0] - margin, box[1] - margin, box[2] + margin, box[3] + margin)
    for polygon in tf.get_geometry(tz_name=zone):
        lngs, lats = np.asarray(polygon[0][0]), np.asarray(polygon[0][1])
        if (
            lngs.max() < wide[0]
            or lngs.min() > wide[2]
            or lats.max() < wide[1]
            or lats.min() > wide[3]
        ):
            continue
        ring = clip_ring(lngs, lats, wide)
        if len(ring) >= 3:
            yield thin(ring)


def cell_degrees(cell_id: int) -> Box:
    """A cell's edges in degrees: what it owns, widened by the one unit it does not."""
    x0, y0, x1, y1 = cell_bounds(cell_id)
    return (
        (x0 - 1) / COORD2INT_FACTOR,
        (y0 - 1) / COORD2INT_FACTOR,
        x1 / COORD2INT_FACTOR,
        y1 / COORD2INT_FACTOR,
    )


@dataclass(frozen=True)
class Cell:
    bounds: Box
    candidates: int  # 0 for a cell that stores a single zone
    is_root: bool


def leaf_cells(tf: TimezoneFinder, box: Box) -> list[Cell]:
    """The cells the index answers from inside ``box``, in grid order."""
    index = tf.shortcuts
    cells = []
    for lat in np.arange(box[1] + ROOT_DEGREES / 2, box[3], ROOT_DEGREES):
        for lng in np.arange(box[0] + ROOT_DEGREES / 2, box[2], ROOT_DEGREES):
            root = root_cell_of(*shifted(float(lng), float(lat)))
            if int(index.table[root]) >= ABSENT:
                cells.append(Cell(cell_degrees(root), 0, True))
                continue
            for child in child_cells_of(root).tolist():
                entry = index.entry_of(child)
                count = 0 if entry >= 0 else len(index.candidates_of(entry))
                cells.append(Cell(cell_degrees(child), count, False))
    return cells


# --- the river excerpt --------------------------------------------------------------


def extract_rivers(natural_earth: Path, box: Box) -> dict:
    """The river lines of a Natural Earth file near ``box``, as the committed excerpt.

    Each line is cut to the runs of vertices inside a margin around the window, and the
    coordinates are rounded to 1e-4 degrees, about ten metres.
    """
    margin = 0.1
    x0, y0, x1, y1 = box[0] - margin, box[1] - margin, box[2] + margin, box[3] + margin
    rivers = []
    for feature in json.loads(natural_earth.read_text(encoding="utf-8"))["features"]:
        geometry = feature["geometry"]
        if geometry is None:
            continue
        lines = (
            geometry["coordinates"]
            if geometry["type"] == "MultiLineString"
            else [geometry["coordinates"]]
        )
        runs = []
        for line in lines:
            run: list[list[float]] = []
            for lng, lat in line:
                if x0 <= lng <= x1 and y0 <= lat <= y1:
                    run.append([round(lng, 4), round(lat, 4)])
                    continue
                if len(run) > 1:
                    runs.append(run)
                run = []
            if len(run) > 1:
                runs.append(run)
        if runs:
            rivers.append({"lines": runs, "name": feature["properties"]["name"]})
    rivers.sort(key=lambda river: (river["name"], river["lines"]))
    return {"rivers": rivers, "source": RIVERS_SOURCE}


def read_rivers() -> list[dict]:
    return json.loads(RIVERS_PATH.read_text(encoding="utf-8"))["rivers"]


# --- drawing --------------------------------------------------------------------------


def draw_map(ax: Axes, tf: TimezoneFinder) -> None:
    west, south, east, north = WINDOW
    ax.set_xlim(west, east)
    ax.set_ylim(south, north)
    ax.set_aspect(1 / np.cos(np.radians((south + north) / 2)))

    for zone, colour in FILL.items():
        for ring in zone_outlines(tf, zone, WINDOW):
            ax.add_patch(
                Polygon(ring, closed=True, facecolor=colour, edgecolor="none", zorder=1)
            )
    for (zone, country), x in zip(LAND_ZONES.items(), (7.12, 9.0), strict=True):
        ax.text(
            x,
            48.45,
            country,
            fontsize=13,
            color=COUNTRY_INK[zone],
            fontweight="bold",
            ha="center",
            va="center",
            zorder=1.2,
        )
        ax.text(
            x, 48.35, zone, fontsize=9, color=INK, ha="center", va="center", zorder=1.2
        )

    for cell in leaf_cells(tf, WINDOW):
        if cell.is_root:
            continue
        x0, y0, x1, y1 = cell.bounds
        if cell.candidates:
            ax.add_patch(
                Rectangle(
                    (x0, y0),
                    x1 - x0,
                    y1 - y0,
                    facecolor="none",
                    hatch="////",
                    edgecolor=HATCH,
                    linewidth=0,
                    alpha=0.75,
                    zorder=2,
                )
            )
        ax.add_patch(
            Rectangle(
                (x0, y0),
                x1 - x0,
                y1 - y0,
                fill=False,
                edgecolor=GRID,
                linewidth=0.45,
                zorder=3,
            )
        )
    for lng in np.arange(west, east + 1e-9, ROOT_DEGREES):
        ax.plot([lng, lng], [south, north], color=INK, linewidth=1.2, zorder=4)
    for lat in np.arange(south, north + 1e-9, ROOT_DEGREES):
        ax.plot([west, east], [lat, lat], color=INK, linewidth=1.2, zorder=4)

    for river in read_rivers():
        main = river["name"] in MAIN_RIVER
        for line in river["lines"]:
            xy = np.asarray(line)
            ax.plot(
                xy[:, 0],
                xy[:, 1],
                color=RIVER,
                linewidth=2.0 if main else 0.9,
                alpha=1.0 if main else 0.6,
                zorder=1.6,
                solid_capstyle="round",
            )
    ax.text(
        7.80,
        48.30,
        "Rhine",
        fontsize=9,
        color=RIVER,
        style="italic",
        rotation=62,
        ha="center",
        va="center",
        zorder=6,
    )

    # on top of the cells, so the border reads as one line
    for ring in zone_outlines(tf, "Europe/Paris", WINDOW):
        ax.add_patch(
            Polygon(
                ring, closed=True, fill=False, edgecolor=BORDER, linewidth=1.5, zorder=5
            )
        )

    for name, (lng, lat, dx, dy, ha) in CITIES.items():
        ax.plot(
            lng,
            lat,
            "o",
            markersize=3.5,
            markerfacecolor=INK,
            markeredgecolor="white",
            markeredgewidth=0.8,
            zorder=7,
        )
        ax.text(
            lng + dx,
            lat + dy,
            name,
            fontsize=8,
            color=INK,
            ha=ha,
            va="center",
            zorder=7,
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.75),
        )

    for point in QUERIES:
        ax.plot(
            point.lng,
            point.lat,
            "o",
            markersize=15,
            markerfacecolor=INK,
            markeredgecolor="white",
            markeredgewidth=1.6,
            zorder=8,
        )
        ax.text(
            point.lng,
            point.lat,
            point.label,
            color="white",
            fontsize=9,
            ha="center",
            va="center",
            fontweight="bold",
            zorder=9,
        )

    lng_ticks = np.arange(west, east + 1e-9, ROOT_DEGREES)
    lat_ticks = np.arange(south, north + 1e-9, ROOT_DEGREES)
    ax.set_xticks(lng_ticks, [f"{v:g}° E" for v in lng_ticks])
    ax.set_yticks(lat_ticks, [f"{v:g}° N" for v in lat_ticks])
    ax.tick_params(labelsize=7.5, length=0, pad=4, colors=MUTED)
    for spine in ax.spines.values():
        spine.set_visible(False)


LEGEND = (
    (
        "root",
        "0.75° root cell: stores one zone, or a\nblock of 4 × 4 finer cells where zones meet",
    ),
    ("child", "0.1875° cell inside a refined root cell"),
    ("hatch", "cell several zones can own:\nstores a list of candidate polygons"),
    ("border", "zone border (Europe/Paris | Europe/Berlin)"),
    ("river", "rivers, for orientation only.\nMade with Natural Earth."),
)


def draw_panel(
    fig: Figure,
    tf: TimezoneFinder,
    lookups: Sequence[Lookup],
    top: float,
    bottom: float,
    left: float,
) -> None:
    y = top
    for point, lookup in zip(QUERIES, lookups, strict=True):
        fig.text(
            left,
            y,
            point.label,
            fontsize=9,
            color="white",
            fontweight="bold",
            ha="center",
            va="center",
            bbox=dict(boxstyle="circle,pad=0.32", fc=INK, ec="none"),
        )
        fig.text(
            left + 0.022,
            y,
            point.title,
            fontsize=10,
            color=INK,
            fontweight="bold",
            va="center",
        )
        body = describe(tf, lookup)
        fig.text(
            left + 0.022,
            y - 0.026,
            body,
            fontsize=8.5,
            color=INK,
            va="top",
            linespacing=1.35,
        )
        y -= 0.09 + 0.031 * body.count("\n")

    line = 0.026
    gap = 0.014
    y = (
        bottom
        + sum(1 + text.count("\n") for _, text in LEGEND) * line
        + (len(LEGEND) - 1) * gap
    )
    for kind, text in LEGEND:
        rows = 1 + text.count("\n")
        mid = y - rows * line / 2
        x = left - 0.01
        if kind == "hatch":
            fig.patches.append(
                Rectangle(
                    (x, mid - 0.013),
                    0.022,
                    0.026,
                    transform=fig.transFigure,
                    facecolor="none",
                    hatch="////",
                    edgecolor=HATCH,
                    linewidth=0,
                    alpha=0.75,
                )
            )
        else:
            colour, width = {
                "root": (INK, 1.2),
                "child": (GRID, 0.6),
                "border": (BORDER, 1.5),
                "river": (RIVER, 2.0),
            }[kind]
            fig.lines.append(
                Line2D(
                    [x, x + 0.022],
                    [mid, mid],
                    transform=fig.transFigure,
                    color=colour,
                    linewidth=width,
                )
            )
        fig.text(
            left + 0.022,
            mid,
            text,
            fontsize=8,
            color=MUTED,
            va="center",
            linespacing=1.3,
        )
        y -= rows * line + gap


def render(tf: TimezoneFinder) -> str:
    """The figure as SVG markup: deterministic, and already pre-commit-clean."""
    check_aligned(WINDOW)
    lookups = [replay(tf, point) for point in QUERIES]
    style = {
        "svg.hashsalt": SVG_HASH_SALT,
        # real <text> nodes rather than glyph outlines from whatever fonts are installed
        "svg.fonttype": "none",
        "font.family": "DejaVu Sans",
    }
    with plt.style.context("default"), matplotlib.rc_context(style):
        fig = plt.figure(figsize=(10.0, 5.2))
        try:
            ax = fig.add_axes((0.055, 0.07, 0.56, 0.88))
            draw_map(ax, tf)
            fig.canvas.draw()  # settles the axes' box, which the aspect ratio shrinks
            box = ax.get_position()
            draw_panel(
                fig, tf, lookups, top=box.y1 - 0.01, bottom=box.y0 + 0.01, left=0.665
            )
            buffer = StringIO()
            fig.savefig(buffer, format="svg", metadata={"Date": None})
        finally:
            plt.close(fig)
    svg = buffer.getvalue()
    return "\n".join(line.rstrip() for line in svg.splitlines()) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out",
        type=Path,
        default=FIGURE_PATH,
        help=f"where to write the SVG (default: {FIGURE_PATH})",
    )
    parser.add_argument(
        "--natural-earth",
        type=Path,
        help="rebuild the committed river excerpt from this "
        "ne_10m_rivers_lake_centerlines.geojson before drawing",
    )
    args = parser.parse_args(argv)
    if args.natural_earth is not None:
        write_json(extract_rivers(args.natural_earth, WINDOW), RIVERS_PATH)
    args.out.write_text(render(TimezoneFinder()), encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
