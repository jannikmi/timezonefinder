"""Measure how much of the hole data is a duplicate of a boundary polygon.

Reads the **upstream GeoJSON**, not the packaged binaries: the shipped data already has
the duplicates removed, so measuring it would only confirm the encoding rather than the
property the encoding relies on. Run this against a new timezone-boundary-builder
release to re-verify the assumption before trusting it — that is what it is for.

Two questions:

1. **Redundancy.** How many hole rings trace exactly the same closed path as some
   boundary polygon, and what would dropping those copies save? Matching is exact:
   rings are compared as integer coordinates under a canonical form (rotated to the
   lexicographically smallest vertex, both winding directions tried), with bounding box
   and vertex count as a prefilter only. No tolerance, no bounding box heuristics.

2. **Coverage of the remainder.** For the holes that match nothing, are they real gaps
   in the map, or covered by other zones anyway? Probed by sampling interior points of
   each such hole and testing them against every other boundary polygon.

Needs the input dataset in ``tmp/`` (``bash update_data.sh --dataset=full --with-oceans``,
or the pinned release asset). Run with::

    PYTHONPATH=. uv run python prototypes/hole_boundary_redundancy.py


FINDINGS (release 2026c: 1322 boundary polygons, 756 holes):

    ring-identical to a boundary polygon     : 729 / 756  (96.4%)
    bounding box matched, coordinates differ :   0     <- no near misses at all
    matched more than one boundary           :   0     <- never ambiguous
    no match                                 :  27

    hole vertices total      : 262,417  (3.2% of all coordinate data)
      deduplicable (729)     : 241,525  (92.0%)  ~1.84 MiB on disk
      stored inline (27)     :  20,892  ( 8.0%)

Of the 729, only 463 are stored byte for byte identically; the other 266 trace the same
path from a different starting vertex or in the opposite winding direction. Ray casting
is insensitive to both, verified over every vertex and edge midpoint of the affected
rings on both point in polygon backends.

The 27 without a twin are NOT geometric outliers. Sampling 60 interior points each and
testing them against every other boundary polygon, *no* sampled point fell outside all
other zones — each hole is fully covered, usually by a union of two or three zones:

    Asia/Jerusalem  19 holes  <- Asia/Hebron (100%)
    Etc/GMT+4        2        <- America/Antigua, Grenada, Guadeloupe, ...
    Etc/GMT+5        1        <- America/Curacao (60%), America/Kralendijk (40%)
    Etc/GMT-10       1        <- Asia/Srednekolymsk (65%), Asia/Magadan (35%)
    Etc/GMT-11       1        <- Pacific/Majuro (87%), Pacific/Kwajalein (13%)
    Etc/GMT-2        1        <- Asia/Nicosia (63%), Asia/Famagusta (37%)
    Etc/GMT-6        1        <- Asia/Kolkata (93%), Asia/Yangon (7%)
    Etc/GMT-8        1        <- Asia/Ho_Chi_Minh (50%), Shanghai (25%), Manila (23%)

So these holes are an *ordering* question, not a geometry one: dropping them would only
change an answer if the parent polygon were tested before the covering polygon. They are
therefore kept inline rather than dropped, and no zone precedence machinery is needed to
resolve them — a rules engine deciding which zone "wins" a hole would make timezone
answers depend on hand-maintained political configuration for a case that needs no
resolution at all. That idea was explored and rejected on this evidence.

The redundancy result shipped: see the "Holes as Boundary References" section of
docs/data_format.rst for the encoding that resulted.
"""

from collections import Counter, defaultdict

import numpy as np

from scripts.configs import DEFAULT_INPUT_PATH
from scripts.timezone_data import TimezoneData
from scripts.utils import canonical_ring_key
from timezonefinder import utils

SAMPLES_PER_HOLE = 60
MAX_REJECTION_TRIES = 200_000
SEED = 42


def bbox_key(bounds, nr_vertices: int) -> tuple:
    return (bounds.xmin, bounds.xmax, bounds.ymin, bounds.ymax, nr_vertices)


def measure_redundancy(data: TimezoneData) -> list[int]:
    """Match every hole ring against the boundary polygons. Returns the unmatched ids."""
    buckets: dict[tuple, list[int]] = defaultdict(list)
    for poly_id, bounds in enumerate(data.poly_boundaries):
        buckets[bbox_key(bounds, data.polygon_lengths[poly_id])].append(poly_id)

    cache: dict[int, bytes] = {}

    def boundary_key(poly_id: int) -> bytes:
        if poly_id not in cache:
            cache[poly_id] = canonical_ring_key(data.polygons[poly_id])
        return cache[poly_id]

    matches: dict[int, int] = {}
    bbox_only: list[int] = []
    unmatched: list[int] = []
    ambiguous = 0

    for hole_id, ring in enumerate(data.holes):
        key = bbox_key(data.hole_boundaries[hole_id], data.all_hole_lengths[hole_id])
        candidates = buckets.get(key, [])
        if not candidates:
            unmatched.append(hole_id)
            continue
        hole_key = canonical_ring_key(ring)
        hits = [p for p in candidates if boundary_key(p) == hole_key]
        if not hits:
            bbox_only.append(hole_id)
            continue
        matches[hole_id] = hits[0]
        if len(hits) > 1:
            ambiguous += 1

    misses = sorted(unmatched + bbox_only)
    nr_holes = len(data.holes)
    dedup_v = sum(data.all_hole_lengths[h] for h in matches)
    inline_v = sum(data.all_hole_lengths[h] for h in misses)
    boundary_v = sum(data.polygon_lengths)
    exact = sum(
        1 for h, p in matches.items() if np.array_equal(data.holes[h], data.polygons[p])
    )

    print(f"boundary polygons : {data.nr_of_polygons}")
    print(f"holes             : {nr_holes}")
    print(
        f"  ring-identical to a boundary     : {len(matches)} "
        f"({100 * len(matches) / nr_holes:.1f}%)"
    )
    print(f"  bbox matched, coordinates differ : {len(bbox_only)}")
    print(f"  no bbox candidate                : {len(unmatched)}")
    print(f"  matched more than one boundary   : {ambiguous}")
    print(
        f"  of the matches, byte-identical   : {exact} "
        f"(the rest differ only in starting vertex / winding)"
    )
    print(
        f"hole vertices     : {dedup_v + inline_v} "
        f"({100 * (dedup_v + inline_v) / (dedup_v + inline_v + boundary_v):.1f}% "
        f"of all coordinate data)"
    )
    print(
        f"  deduplicable    : {dedup_v} "
        f"({100 * dedup_v / (dedup_v + inline_v):.1f}%)  "
        f"~{dedup_v * 8 / 2**20:.2f} MiB"
    )
    print(f"  stored inline   : {inline_v}")
    return misses


def probe_coverage(data: TimezoneData, misses: list[int]) -> None:
    """For each unmatched hole, which other zones cover its interior?"""
    rng = np.random.default_rng(SEED)
    zone_of = [data.all_tz_names[int(z)] for z in data.poly_zone_ids]
    per_zone: dict[str, dict] = defaultdict(
        lambda: {"holes": 0, "points": 0, "uncovered": 0, "by": Counter()}
    )
    print(
        f"\ncoverage probe over {len(misses)} unmatched holes "
        f"({SAMPLES_PER_HOLE} interior points each):\n"
    )

    for hole_id in misses:
        poly_id = data.polynrs_of_holes[hole_id]
        ring = data.holes[hole_id]
        bounds = data.hole_boundaries[hole_id]

        points, tries = [], 0
        while len(points) < SAMPLES_PER_HOLE and tries < MAX_REJECTION_TRIES:
            tries += 1
            x = int(rng.integers(bounds.xmin, bounds.xmax + 1))
            y = int(rng.integers(bounds.ymin, bounds.ymax + 1))
            if utils.inside_polygon(x, y, ring):
                points.append((x, y))

        entry = per_zone[zone_of[poly_id]]
        entry["holes"] += 1
        entry["points"] += len(points)
        for x, y in points:
            covering = set()
            for other, other_bounds in enumerate(data.poly_boundaries):
                if other == poly_id:
                    continue
                if not (
                    other_bounds.xmin <= x <= other_bounds.xmax
                    and other_bounds.ymin <= y <= other_bounds.ymax
                ):
                    continue
                if utils.inside_polygon(x, y, data.polygons[other]):
                    covering.add(zone_of[other])
            if covering:
                entry["by"].update(covering)
            else:
                entry["uncovered"] += 1

    for zone, e in sorted(per_zone.items()):
        top = ", ".join(
            f"{z} {100 * c / e['points']:.0f}%" for z, c in e["by"].most_common(3)
        )
        print(
            f"  {zone:18s} holes={e['holes']:2d}  "
            f"uncovered={e['uncovered']}/{e['points']}  <- {top}"
        )

    total_uncovered = sum(e["uncovered"] for e in per_zone.values())
    total_points = sum(e["points"] for e in per_zone.values())
    print(
        f"\n  sampled points outside every other zone: "
        f"{total_uncovered} of {total_points}"
    )


if __name__ == "__main__":
    parsed = TimezoneData.from_path(DEFAULT_INPUT_PATH)
    unmatched_holes = measure_redundancy(parsed)
    probe_coverage(parsed, unmatched_holes)
