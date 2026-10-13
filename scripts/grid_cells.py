"""Which boundary polygons can own a point of a grid-tree cell.

This is the whole of the shortcut index's candidate rule, and it is **exact** rather than
conservative: a polygon is a candidate in a cell if and only if the point-in-polygon
kernel can put one of the cell's integer points inside it. Nothing is over-included to be
safe, and nothing is left out.

Two facts make that possible, and both are the cells' doing rather than this module's:

* **A cell is an axis-aligned rectangle of integer coordinates**, ``[x0, x1] x [y0, y1]``
  from ``timezonefinder.shortcut_index.cell_bounds``, so "can this polygon own one of
  those points" is a planar question about two rectangles and a ring. The H3 cells this
  replaced were spherical hexagons that could straddle the coordinate plane's cut and
  enclose a pole, so the same question needed a half-turn rotation, polar special cases,
  per-cell vertex caching and three separate overlap tests - and still answered only
  "might" rather than "does".
* **The kernel's edge convention decides the edges**, and it is pinned by
  ``tests/test_point_in_polygon_boundary_convention.py``: a polygon contains a point on
  its north or east boundary and never one on its south or west. So a polygon that only
  *touches* the box ``[x0 - 0.5, x1] x [y0 - 0.5, y1]`` owns none of the cell's points,
  and one whose interior meets that box may own some. Shifting the box half a unit
  south-west is what turns "the polygon reaches the cell" into "the polygon can own an
  integer point of it".

The geometry runs on the **stored integer rings**, read planar exactly as the kernel reads
them, because matching the kernel is the point: a candidate set computed on the sphere
would disagree with the runtime along every ring the coordinate plane's cut tears.
"""

import numpy as np
import shapely
from shapely import STRtree

from scripts.timezone_data import TimezoneData


def planar_polygons(data: TimezoneData) -> np.ndarray:
    """Every boundary polygon as the planar ring the kernel tests, holes cut out.

    In stored integer coordinates and prepared for repeated predicate calls. A hole is
    subtracted rather than carried separately, because the kernel's answer for a point in
    a hole is "not in this polygon" and a candidate rule that ignored holes would list
    zones a lookup can never return.

    **A ring that is not a valid planar polygon falls back to its bounding box**, and the
    ids are printed. The exactness below is a property of valid rings: every predicate it
    uses is undefined on a self-intersecting one, and repairing such a ring can *shrink*
    it, which would drop a candidate the kernel still matches. A bounding box can only
    over-include - a ray cast cannot put a point inside a ring and outside its own box -
    so a lookup in those cells tests a few polygons more and still answers correctly.
    The packaged boundaries have no such ring; custom input may.
    """
    geometries = []
    repaired: list[int] = []
    for boundary_id in range(data.boundaries.nr_of_polygons):
        outer = data.boundaries.coords_of(boundary_id).T.astype(np.float64)
        holes = [
            hole.T.astype(np.float64) for hole in data.holes.holes_of_poly(boundary_id)
        ]
        geometry = shapely.Polygon(outer, holes)
        if not geometry.is_valid:
            repaired.append(boundary_id)
            geometry = shapely.box(*geometry.bounds)
        geometries.append(geometry)
    if repaired:
        print(
            f"NOTE: {len(repaired)} boundary polygons are not valid planar rings and "
            f"their candidate sets are computed from their bounding boxes instead, "
            f"which over-includes rather than risking an omission: {repaired}"
        )
    array = np.asarray(geometries, dtype=object)
    shapely.prepare(array)
    return array


def owned_pairs(
    polygons: np.ndarray,
    x0: np.ndarray,
    y0: np.ndarray,
    x1: np.ndarray,
    y1: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """``(cell, polygon)`` index pairs where the polygon can own a point of the cell.

    ``x0 .. y1`` are ``cell_bounds`` per cell, so cell ``i`` owns the integer points
    ``[x0[i], x1[i]] x [y0[i], y1[i]]``.

    The expensive predicate is ``touches``, so it is asked only where it can matter: a
    polygon reaching the box shrunk by a further quarter unit meets its interior, which
    settles the common case with a cheap ``intersects``. The quarter unit is arbitrary
    except that it is strictly inside the half-unit shift, so the core box is never empty
    for a cell of non-zero size.
    """
    outer = shapely.box(x0 - 0.5, y0 - 0.5, x1, y1)
    core = shapely.box(x0 - 0.25, y0 - 0.25, x1 - 0.25, y1 - 0.25)
    poly_idx, cell_idx = STRtree(outer).query(polygons, predicate="intersects")
    interior = shapely.intersects(polygons[poly_idx], core[cell_idx])
    edge = np.flatnonzero(~interior)
    if len(edge):
        interior[edge] = ~shapely.touches(
            polygons[poly_idx[edge]], outer[cell_idx[edge]]
        )
    return cell_idx[interior], poly_idx[interior]


def grouped(
    cell_idx: np.ndarray, poly_idx: np.ndarray, zone_ids: np.ndarray
) -> list[tuple[int, np.ndarray, int]]:
    """Per cell with any candidate: the cell, its polygon ids, and its single zone or -1.

    A list rather than a generator because the caller needs the count before it decides
    anything, and the reduceat below has already materialised the work.
    """
    order = np.lexsort((poly_idx, cell_idx))
    cells = cell_idx[order]
    polys = poly_idx[order]
    if not len(cells):
        return []
    starts = np.flatnonzero(np.r_[True, cells[1:] != cells[:-1]])
    ends = np.r_[starts[1:], len(cells)]
    zones = zone_ids[polys].astype(np.int64)
    # one zone, or several: `min == max` over the cell's candidates says which, in one
    # pass over the whole collection rather than a set per cell
    zmin = np.minimum.reduceat(zones, starts)
    zmax = np.maximum.reduceat(zones, starts)
    return [
        (
            int(cells[start]),
            polys[start:end],
            int(zmin[i]) if zmin[i] == zmax[i] else -1,
        )
        for i, (start, end) in enumerate(
            zip(starts.tolist(), ends.tolist(), strict=True)
        )
    ]
