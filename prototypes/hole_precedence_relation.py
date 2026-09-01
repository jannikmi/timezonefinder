"""Derive the zone precedence relation dropping holes would need, and test it for cycles.

Dropping holes is only safe if, wherever two zones' rings overlap, the lookup reaches the
right one first. `A recorded decision
<../contributing/improvements/decisions/geometry-data-format-and-validation-decisions.md>`_
forbids stating that as a property of the H3 shortcut index, so it has to be a relation
over **zones**: ``A < B`` meaning "where A and B both cover a point, A is the answer".

This script builds exactly that relation from the geometry, with no reference to the
index, and then asks whether it can exist at all:

1. sample interior points of every hole - the only places where dropping a hole can
   change an answer, since elsewhere no ring is being subtracted;
2. per point, collect the zones whose rings contain it **ignoring holes** (what the
   hole-free lookup would have to choose between) and the zones that contain it **with
   holes applied** (the answer that must be preserved);
3. emit one required edge ``true -> other`` per competing zone, i.e. "the true zone must
   be reached before this one";
4. report whether the resulting digraph is acyclic - a cyclic relation admits no
   candidate ordering whatsoever - and whether zone area orders it, which is the
   size-derived rule proposed on issue #513.

Run with::

    PYTHONPATH=. uv run python prototypes/hole_precedence_relation.py


FINDINGS (timezonefinder-data 2.2026.3, release 2026c; 756 holes, 12,096 interior probes):

    required precedence edges        216, over 218 zones
    holes needing an edge at all     756 of 756
    probes with no competing zone    0            ambiguous probes  0
    cycles in the relation           7
    edges the area rule gets wrong   20 of 216

**The relation is cyclic, so no candidate ordering satisfies it and none ever will.** Seven
zone pairs each have to precede the other, and every one is a second-order enclave - a zone
inside a zone inside the first zone again:

    Europe/Amsterdam / Europe/Brussels     Baarle-Hertog and its Dutch counter-enclaves
    Asia/Dubai / Asia/Muscat               Nahwa inside Madha inside the UAE
    America/Denver / America/Phoenix       the Hopi reservation inside the Navajo Nation
    America/Argentina/Cordoba / America/Asuncion
    Asia/Omsk / Asia/Yekaterinburg
    Europe/Astrakhan / Europe/Moscow
    Pacific/Tahiti / Etc/GMT+10            a lagoon inside an atoll

The Dubai/Muscat pair is the sharpest: both witnesses lie inside **the same hole**, hole 137
of boundary 471, so not even a per-hole rule could break the tie. This is what makes the
refutation structural rather than a property of one release. Precedence is a relation
between *zones*, but containment is a relation between *rings*, and nesting deeper than one
level maps two opposite ring relations onto one zone pair.

Nor does the formulation the recorded H3-independence decision forbids rescue it: all seven
pairs have a shortcut cell at the shipped resolution whose single candidate list would have
to order the pair both ways (e.g. 841fa4bffffffff for Amsterdam/Brussels). Per-cell ordering
is not merely the wrong place to state the invariant - here it cannot state it either.

The size-derived rule proposed on issue #513 ("smaller zones take precedence") fails
separately, on 20 of the 216 edges, and the ocean zones are the systematic half of it: an
``Etc/GMT±XX`` polygon covers a hemisphere and has a handful of vertices, so it is huge by
area and first by the vertex-count key ``optimise_shortcut_ordering`` actually sorts on.
``Etc/GMT-3`` has to precede ``Africa/Djibouti`` while being 583x its area. The composite
case named on the issue is here too: ``Asia/Shanghai`` before ``Asia/Ho_Chi_Minh``, 36x.

A partial drop keeping only the contradictory holes leaves 171 of 756 - and leaves the whole
subsystem, since ``HoleArray``, ``hole_registry``, ``poly_ref.npy``, the holes-before-boundary
branch and the validator's hole checks are all still needed for those 171. It would add a
precedence compiler to buy a fraction of ~180 KB, so it is worse than doing nothing.

One caveat stated rather than hidden: the relation here is *discovered* by sampling hole
interiors, so it is a lower bound on the edges. That direction is the safe one for a
refutation - more sampling can only add edges and cycles - and it is exactly why the
positive result could not have been trusted from this instrument.

CONCLUSION: GH-513 is refused. ``hole_removal_impact.py`` measures the damage, this script
explains why it is not fixable, and ``tests/test_hole_lookup_regression.py`` is the gate.
"""

import sys
from collections import defaultdict

import h3.api.numpy_int as h3
import numpy as np

from timezonefinder import TimezoneFinder, utils
from timezonefinder.configs import SHORTCUT_H3_RES

PROBES_PER_HOLE = 16
MAX_REJECTION_TRIES = 8_000
SEED = 17


def parents_of_holes(finder: TimezoneFinder) -> dict[int, int]:
    """hole id -> the boundary polygon it was cut out of."""
    parent = {}
    for poly_id, (count, first) in finder.hole_registry.items():
        for offset in range(count):
            parent[first + offset] = poly_id
    return parent


def sample_hole_interiors(finder: TimezoneFinder, rng) -> list[tuple[int, int, int]]:
    """``(x, y, hole_id)`` interior points of every hole, in integer coordinates."""
    probes: list[tuple[int, int, int]] = []
    for hole_id in range(len(finder.holes)):
        ring = finder.holes.coords_of(hole_id)
        xmin, xmax = int(finder.holes.xmin[hole_id]), int(finder.holes.xmax[hole_id])
        ymin, ymax = int(finder.holes.ymin[hole_id]), int(finder.holes.ymax[hole_id])
        found = 0
        for _ in range(MAX_REJECTION_TRIES):
            if found >= PROBES_PER_HOLE:
                break
            x = int(rng.integers(xmin, xmax + 1))
            y = int(rng.integers(ymin, ymax + 1))
            if utils.inside_polygon(x, y, ring):
                probes.append((x, y, hole_id))
                found += 1
    return probes


def zone_areas(finder: TimezoneFinder) -> np.ndarray:
    """Total shoelace area of every zone's boundary rings, holes subtracted."""
    areas = np.zeros(finder.nr_of_zones, dtype=np.float64)
    for boundary_id in range(finder.nr_of_polygons):
        ring = finder.boundaries.coords_of(boundary_id)
        area = shoelace(ring)
        for hole_ring in finder._holes_of_poly(boundary_id):
            area -= shoelace(hole_ring)
        areas[int(finder.zone_ids[boundary_id])] += area
    return areas


def shoelace(ring: np.ndarray) -> float:
    x = ring[0].astype(np.float64)
    y = ring[1].astype(np.float64)
    return 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))


def zones_containing(
    finder: TimezoneFinder, x: int, y: int, *, apply_holes: bool
) -> set[int]:
    """Every zone whose geometry contains the point, found without the shortcut index.

    The bbox vectors filter the ~1,200 boundary polygons down to a handful; the survivors
    get a real point-in-polygon test. Deliberately exhaustive: using the shortcut
    candidates here would make the derived relation a property of the index.
    """
    candidates = np.nonzero(
        (finder.boundaries.xmin <= x)
        & (x <= finder.boundaries.xmax)
        & (finder.boundaries.ymin <= y)
        & (y <= finder.boundaries.ymax)
    )[0]
    found = set()
    for boundary_id in candidates.tolist():
        hit = (
            finder.inside_of_polygon(boundary_id, x, y)
            if apply_holes
            else finder.boundaries.pip(boundary_id, x, y)
        )
        if hit:
            found.add(int(finder.zone_ids[boundary_id]))
    return found


def find_cycles(edges: dict[int, set[int]]) -> list[list[int]]:
    """Every elementary cycle reachable by DFS, one representative per back edge."""
    cycles: list[list[int]] = []
    colour: dict[int, int] = {}
    stack: list[int] = []

    def visit(node: int) -> None:
        colour[node] = 1
        stack.append(node)
        for nxt in sorted(edges.get(node, ())):
            if colour.get(nxt, 0) == 0:
                visit(nxt)
            elif colour[nxt] == 1:
                cycles.append(stack[stack.index(nxt) :] + [nxt])
        stack.pop()
        colour[node] = 2

    for node in sorted(edges):
        if colour.get(node, 0) == 0:
            visit(node)
    return cycles


def main() -> None:
    finder = TimezoneFinder(in_memory=True)
    names = finder.timezone_names
    parent = parents_of_holes(finder)
    rng = np.random.default_rng(SEED)
    probes = sample_hole_interiors(finder, rng)
    print(f"holes: {len(finder.holes)}   interior probe points: {len(probes)}")

    edges: dict[int, set[int]] = defaultdict(set)
    witness: dict[tuple[int, int], tuple[int, int, int]] = {}
    cells_of_edge: dict[tuple[int, int], set[int]] = defaultdict(set)
    edges_of_hole: dict[int, set[tuple[int, int]]] = defaultdict(set)
    holes_with_competition = set()
    ambiguous = 0
    uncovered = 0

    for x, y, hole_id in probes:
        hole_free = zones_containing(finder, x, y, apply_holes=False)
        corrected = zones_containing(finder, x, y, apply_holes=True)
        if len(corrected) != 1:
            # the packaged geometry does not single out an answer here
            ambiguous += 1
            continue
        (true_zone,) = corrected
        competitors = hole_free - {true_zone}
        if not competitors:
            uncovered += 1
            continue
        holes_with_competition.add(hole_id)
        cell = h3.latlng_to_cell(
            utils.int2coord(y), utils.int2coord(x), SHORTCUT_H3_RES
        )
        for other in competitors:
            edges[true_zone].add(other)
            witness.setdefault((true_zone, other), (x, y, hole_id))
            cells_of_edge[(true_zone, other)].add(cell)
            edges_of_hole[hole_id].add((true_zone, other))

    nr_edges = sum(len(v) for v in edges.values())
    print(
        f"required precedence edges: {nr_edges} over {len(set(edges) | {b for v in edges.values() for b in v})} zones"
    )
    print(f"holes that need one at all: {len(holes_with_competition)}")
    print(f"probes with no competing zone: {uncovered}   ambiguous probes: {ambiguous}")

    cycles = find_cycles(edges)
    print(f"\ncycles in the required relation: {len(cycles)}")
    for cycle in cycles[:20]:
        print("  " + " -> ".join(names[z] for z in cycle))
        for first, second in zip(cycle, cycle[1:]):
            wx, wy, whole = witness[(first, second)]
            print(
                f"      {names[first]} first at "
                f"lng={utils.int2coord(wx):.6f} lat={utils.int2coord(wy):.6f} "
                f"(hole {whole} of boundary {parent[whole]}, "
                f"zone {names[int(finder.zone_ids[parent[whole]])]})"
            )

    # Only for the two-cycles, and only to show that the formulation the recorded
    # decision forbids does not rescue this either: if both directions of a pair are
    # required inside one shortcut cell, that cell's candidate list has to order two
    # zones both ways, which no ordering does at any resolution that keeps them together.
    print("\ncells whose candidate list would need both orders of one zone pair:")
    contradictory = 0
    for a, targets in edges.items():
        for b in targets:
            if a not in edges.get(b, ()):
                continue
            if a > b:
                continue  # report each pair once
            shared = cells_of_edge[(a, b)] & cells_of_edge[(b, a)]
            if shared:
                contradictory += 1
                print(
                    f"  {names[a]} / {names[b]}: {len(shared)} cell(s), "
                    f"e.g. {h3.int_to_str(sorted(shared)[0])}"
                )
    if not contradictory:
        print("  none at this resolution")

    # What a partial drop - keeping only the holes whose precedence is contradictory -
    # would leave behind. It does not remove the subsystem, which is the point.
    cyclic_pairs = {
        (a, b) for a, targets in edges.items() for b in targets if a in edges.get(b, ())
    }
    blocked_holes = {
        hole_id
        for hole_id, hole_edges in edges_of_hole.items()
        if hole_edges & cyclic_pairs
    }
    print(
        f"\nholes a partial drop would still have to keep: {len(blocked_holes)} "
        f"of {len(finder.holes)}"
    )

    areas = zone_areas(finder)
    violations = [
        (a, b) for a, targets in edges.items() for b in targets if areas[a] >= areas[b]
    ]
    print(
        f"\nedges the area rule (smaller zone wins) gets wrong: "
        f"{len(violations)} of {nr_edges}"
    )
    for a, b in sorted(violations, key=lambda pair: -areas[pair[0]])[:15]:
        print(
            f"  {names[a]} must precede {names[b]}, but is "
            f"{areas[a] / max(areas[b], 1e-9):.1f}x its area"
        )

    return 0 if not cycles and not violations else 1


if __name__ == "__main__":
    sys.setrecursionlimit(10_000)
    sys.exit(main())
