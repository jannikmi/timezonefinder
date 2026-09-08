"""Which of two overlapping timezone zones takes precedence, and why.

Timezone boundaries overlap: 118 zone pairs do so in the 2026c dataset, most of them
coastal slivers, a few of them genuine enclaves where one zone lies wholly inside
another. A query point in an overlap belongs to both, so *something* has to choose, and
today nothing does - the candidate loop returns whichever polygon it happens to test
first, which is an artefact of the shortcut ordering rather than a decision.

**The rule, decided 2026-09-08.** Of two overlapping zones, the one for which the shared
area is the larger share of *itself* is the enclave, and takes precedence. It is a
property of the two zones computed once from their full geometry, so it is the same
wherever they meet - it does not state a correctness property in terms of the H3
shortcut index, which
``contributing/improvements/decisions/geometry-data-format-and-validation-decisions.md``
forbids. `resolve_covered_cells` is the only caller, and it applies the rule only inside
a cell one polygon covers entirely.

**Not the relation `prototypes/hole_precedence_relation.py` refuted.** That study derives
the precedence a *hole-free* lookup would need and finds it cyclic, and it finds the
size-derived rule failing on 20 of 216 edges, systematically on the ocean zones -
``Etc/GMT-3`` has to precede ``Africa/Djibouti`` there while being 583x its area, the
opposite of what the rule below would say. The two never meet, because they are asked
about different geometry: those edges exist to answer a point inside a *hole* that its
own zone no longer claims, and `Hex.covers_cell` refuses coverage outright when any hole
reaches the cell. What is left for this rule is genuine boundary overlap, where the
enclave is the answer and the ocean zone is not.

**Why no polygon clipping is needed.** The two ratios the rule compares,
``shared / area(A)`` and ``shared / area(B)``, share a numerator: the shared area is one
number, the same set measured once. So ``shared/area(A) > shared/area(B)`` holds exactly
when ``area(A) < area(B)``, and the intersection never has to be constructed. That is why
this module is numpy and no geometry library - and it is also why the "smaller total zone
area wins" alternative the decision records as refused disagreed with containment on 0 of
118 pairs: inside the scope where it is applied, it is not a proxy for the rule, it is
the rule.
"""

from typing import TYPE_CHECKING

import numpy as np

from scripts.configs import ShortcutMapping
from timezonefinder.configs import INT2COORD_FACTOR

if TYPE_CHECKING:
    from scripts.timezone_data import TimezoneData

#: Steradians in a sphere. A zone larger than half of one would break `zone_areas`'
#: choice of side for a ring enclosing a pole, and is asserted against there.
FULL_SPHERE = 4 * np.pi


def spherical_ring_area(ring: np.ndarray) -> float:
    """Area of the closed ``ring`` on the unit sphere, in steradians.

    Measured on the sphere rather than by a shoelace sum over the stored coordinates,
    which are plate-carree and would price a square degree in Svalbard the same as one on
    the equator. Zone areas are compared against each other here, so that distortion
    would decide precedence between a high-latitude zone and a tropical one on latitude.

    Two properties come for free and both are load-bearing. Each edge's longitude step is
    taken the short way round, so a ring straddling the antimeridian needs no rotation
    into another frame - unlike every Euclidean test in `scripts.hex_utils`. And a ring
    enclosing a pole, which no rotation can put in a planar frame at all, still divides
    the sphere in two; the sum gives one of the two parts and the smaller is taken, which
    is the zone for as long as no zone covers half the globe.
    """
    # `int2coord` is the scalar form of this and cannot take an array
    lng = np.radians(ring[0].astype(np.float64) * INT2COORD_FACTOR)
    lat = np.radians(ring[1].astype(np.float64) * INT2COORD_FACTOR)
    lng_next = np.roll(lng, -1)
    lat_next = np.roll(lat, -1)
    # the short way round the sphere for every edge, which is what makes the cut irrelevant
    delta_lng = (lng_next - lng + np.pi) % (2 * np.pi) - np.pi
    area = abs(float(np.sum(delta_lng * (2 + np.sin(lat) + np.sin(lat_next))) / 2))
    return min(area, FULL_SPHERE - area)


def zone_areas(data: "TimezoneData") -> np.ndarray:
    """Area in steradians per zone id: its boundary polygons, less their holes."""
    areas = np.zeros(len(data.all_tz_names), dtype=np.float64)
    for poly_id in range(data.nr_of_polygons):
        zone_id = int(data.poly_zone_ids[poly_id])
        areas[zone_id] += spherical_ring_area(data.polygons[poly_id])
        for hole in data.holes_in_poly(poly_id):
            areas[zone_id] -= spherical_ring_area(hole)
    if areas.max() > FULL_SPHERE / 2:
        raise ValueError(
            f"zone '{data.all_tz_names[int(areas.argmax())]}' measures "
            f"{areas.max():.3f} steradian, more than the hemisphere "
            f"{spherical_ring_area.__name__} assumes when it picks the smaller side of a "
            "ring enclosing a pole; that choice has to be made explicit before this "
            "dataset can be compiled"
        )
    if areas.min() <= 0:
        raise ValueError(
            f"zone '{data.all_tz_names[int(areas.argmin())]}' measures "
            f"{areas.min():.3g} steradian; a zone whose holes cancel its boundary cannot "
            "be ordered against another by containment"
        )
    return areas


def resolve_covered_cells(
    data: "TimezoneData", shortcuts: ShortcutMapping
) -> dict[int, int]:
    """Hex id -> zone id, for every cell a single boundary polygon covers entirely.

    Such a cell needs no geometry at query time: no point in it can fall outside the
    covering polygon, so the shortcut index can hold the zone id the reader already
    understands instead of a candidate list, and the whole point-in-polygon loop for that
    cell disappears.

    A covering polygon is not by itself enough, because the cell can hold candidates of
    *other* zones - and it always does, or the cell would already be a unique-zone entry.
    Every one of them overlaps the coverer inside this cell, since the coverer contains
    the whole cell, so the containment rule above is exactly what decides them. The cell
    converts only when the covering zone takes precedence over every other candidate
    zone; where a smaller zone merely reaches into the cell, part of the cell answers one
    way and part the other, and the cell keeps its candidate list.
    """
    areas = zone_areas(data)
    poly_zone_ids = data.poly_zone_ids
    resolved: dict[int, int] = {}
    for hex_id, poly_ids in shortcuts.items():
        candidate_zones = {int(poly_zone_ids[p]) for p in poly_ids}
        if len(candidate_zones) < 2:
            # already answered without geometry by `compute_unique_shortcut_mapping`
            continue
        cell = data.get_hex(hex_id)
        covering_zones = {
            int(poly_zone_ids[p]) for p in poly_ids if cell.covers_cell(p)
        }
        if not covering_zones:
            continue
        winner = min(covering_zones, key=areas.__getitem__)
        if all(areas[winner] < areas[other] for other in candidate_zones - {winner}):
            resolved[hex_id] = winner
    return resolved
