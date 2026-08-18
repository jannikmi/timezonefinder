"""Measure what actually changes if hole polygons are dropped from the packaged data.

Every hole says "this area is *not* the surrounding zone". The area is always some other
zone's polygon, and the lookup already tests those polygons - so if a covering polygon
were guaranteed to be tested before the surrounding one, holes would carry no
information and the whole subsystem could go. This script tests that by doing it:
rewriting the hole files of a mirrored data directory and diffing ``timezone_at``
against the packaged data.

Two variants:

* ``no_inline`` - drop only the holes that have no identical boundary polygon (the ones
  stored as their own ring; the rest stay as references)
* ``no_holes``  - drop every hole, i.e. switch the mechanism off entirely

Sampled over interior points of *every* hole - the points that actually exercise the
hole path, which a uniform global sample hits far too rarely - plus a uniform sample for
the blast radius on ordinary queries.

Run with::

    PYTHONPATH=. uv run python prototypes/hole_removal_impact.py


FINDINGS (release 2026c: 756 holes, 729 of them stored as boundary references):

    variant     hole interior pts changed   holes affected   random global pts changed
    no_inline            160 / 6,048           20 of 27              0 / 20,000
    no_holes           1,703 / 6,048          224 of 756           16 / 20,000

The changed answers are wrong, not merely different (correct -> what you get instead):

    no_inline     152  Asia/Hebron                ->  Asia/Jerusalem
                    8  Asia/Kolkata               ->  Etc/GMT-6

    no_holes      760  America/Argentina/Cordoba  ->  America/Asuncion
                  168  Europe/Brussels            ->  Europe/Amsterdam
                  152  Asia/Hebron                ->  Asia/Jerusalem
                  126  Europe/Athens              ->  Etc/GMT-2
                   40  Europe/Berlin              ->  Europe/Brussels
                   ... 46 distinct transitions in total

CONCLUSION: holes cannot be dropped, in either variant, and the reason is worth stating
because the opposite conclusion is easy to reach. Its companion script
``hole_boundary_redundancy.py`` shows every unmatched hole is *fully covered* by other
zones - 0 of 1,620 sampled interior points fell outside every other zone - which reads
like "the hole is redundant". It is not sufficient: coverage says the right zone is
among the shortcut candidates, ordering decides whether it is reached first.
``optimise_shortcut_ordering`` sorts zones by total size ascending, which gets many
enclaves right by accident and evidently not these.

So dropping holes needs a candidate-ordering guarantee *established* in shortcut
compilation, not merely verified. Two further complications belong to that guarantee:
the ``last_zone_change_idx`` early break in ``timezone_at`` returns the final candidate
untested, so "present in the list" is not "reached", and holes covered only by a
*union* of zones need all of those zones ordered correctly, not just one.

This is the evidence behind keeping the unmatched holes stored inline rather than
dropping them - see the "Holes without a twin" section of docs/data_format.rst.
"""

import json
import shutil
from collections import Counter
from pathlib import Path

import numpy as np

from timezonefinder import TimezoneFinder, utils
from timezonefinder.configs import DEFAULT_DATA_DIR
from timezonefinder.flatbuf.io.polygons import (
    get_coordinate_path,
    write_polygon_collection_flatbuffer,
)
from timezonefinder.np_binary_helpers import (
    get_poly_ref_path,
    get_xmax_path,
    get_xmin_path,
    get_ymax_path,
    get_ymin_path,
    store_per_polygon_vector,
)
from timezonefinder.utils import get_hole_registry_path, get_holes_dir

WORK_DIR = Path("tmp/hole_removal_impact")
PROBES_PER_HOLE = 8
MAX_REJECTION_TRIES = 6_000
RANDOM_SAMPLE = 20_000
SEED = 17


def parents_of_holes(finder: TimezoneFinder) -> dict[int, int]:
    """hole id -> the boundary polygon it was cut out of."""
    parent = {}
    for poly_id, (count, first) in finder.hole_registry.items():
        for offset in range(count):
            parent[first + offset] = poly_id
    return parent


def build_variant(finder: TimezoneFinder, name: str, keep: set[int]) -> Path:
    """A data directory identical to the packaged one but keeping only ``keep`` holes.

    Every surviving hole is written as its own inline ring, so the variant needs no
    boundary references - what is being measured is the presence of the holes, not how
    they are stored.
    """
    dest = WORK_DIR / name
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True)
    # symlink the whole directory, then replace just the hole files: the boundary
    # coordinates alone are ~63 MB and are not what varies here
    for item in sorted(DEFAULT_DATA_DIR.rglob("*")):
        target = dest / item.relative_to(DEFAULT_DATA_DIR)
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(item)

    kept = sorted(keep)
    holes_dir = get_holes_dir(dest)
    rings = [finder.holes.coords_of(hole_id) for hole_id in kept]

    for path in (
        get_coordinate_path(holes_dir),
        get_poly_ref_path(holes_dir),
        get_xmin_path(holes_dir),
        get_xmax_path(holes_dir),
        get_ymin_path(holes_dir),
        get_ymax_path(holes_dir),
        get_hole_registry_path(dest),
    ):
        path.unlink()  # drop the symlink, never write through it

    write_polygon_collection_flatbuffer(get_coordinate_path(holes_dir), rings)
    store_per_polygon_vector(
        get_poly_ref_path(holes_dir),
        np.array([-(i + 1) for i in range(len(kept))], dtype=np.int32),
    )
    for getter, axis, reduce_fn in (
        (get_xmin_path, 0, np.min),
        (get_xmax_path, 0, np.max),
        (get_ymin_path, 1, np.min),
        (get_ymax_path, 1, np.max),
    ):
        store_per_polygon_vector(
            getter(holes_dir),
            np.array([int(reduce_fn(ring[axis])) for ring in rings], dtype=np.int32),
        )

    parent = parents_of_holes(finder)
    registry: dict[int, list[int]] = {}
    for new_id, old_id in enumerate(kept):
        poly_id = parent[old_id]
        if poly_id in registry:
            registry[poly_id][0] += 1
        else:
            registry[poly_id] = [1, new_id]
    with open(get_hole_registry_path(dest), "w") as f:
        json.dump({str(k): v for k, v in sorted(registry.items())}, f)
    return dest


def sample_hole_interiors(
    finder: TimezoneFinder, rng
) -> list[tuple[float, float, int]]:
    """Interior points of every hole, by rejection sampling its bounding box."""
    probes: list[tuple[float, float, int]] = []
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
                probes.append((utils.int2coord(x), utils.int2coord(y), hole_id))
                found += 1
    return probes


def compare(finder: TimezoneFinder, variant_dir: Path, probes, random_pts) -> None:
    other = TimezoneFinder(bin_file_location=variant_dir, in_memory=True)
    try:
        transitions: Counter = Counter()
        affected: set[int] = set()
        for lng, lat, hole_id in probes:
            expected = finder.timezone_at(lng=lng, lat=lat)
            got = other.timezone_at(lng=lng, lat=lat)
            if expected != got:
                transitions[(expected, got)] += 1
                affected.add(hole_id)
        changed_random = sum(
            finder.timezone_at(lng=lng, lat=lat) != other.timezone_at(lng=lng, lat=lat)
            for lng, lat in random_pts
        )

        changed = sum(transitions.values())
        print(f"\n=== {variant_dir.name} ===")
        print(f"  hole interior points changed : {changed} / {len(probes)}")
        print(f"  distinct holes affected      : {len(affected)}")
        print(f"  random global points changed : {changed_random} / {len(random_pts)}")
        if transitions:
            print("  correct -> what you would get instead:")
            for (expected, got), count in transitions.most_common(12):
                print(f"    {count:5d}  {expected}  ->  {got}")
            print(f"    ({len(transitions)} distinct transitions)")
    finally:
        del other


if __name__ == "__main__":
    packaged = TimezoneFinder(in_memory=True)
    all_ids = set(range(len(packaged.holes)))
    referenced = {i for i in all_ids if int(packaged.holes.poly_ref[i]) >= 0}
    print(
        f"holes: {len(all_ids)}  stored as a boundary reference: {len(referenced)}  "
        f"stored inline: {len(all_ids - referenced)}"
    )

    generator = np.random.default_rng(SEED)
    interior_probes = sample_hole_interiors(packaged, generator)
    uniform_pts = [
        (float(generator.uniform(-180, 180)), float(generator.uniform(-90, 90)))
        for _ in range(RANDOM_SAMPLE)
    ]
    print(f"interior probe points: {len(interior_probes)}")

    for variant_name, kept_ids in (
        ("no_inline", referenced),
        ("no_holes", set()),
    ):
        compare(
            packaged,
            build_variant(packaged, variant_name, kept_ids),
            interior_probes,
            uniform_pts,
        )
