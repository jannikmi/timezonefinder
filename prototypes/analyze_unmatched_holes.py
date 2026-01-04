#!/usr/bin/env python3
"""
Follow-up analysis to investigate the 19 holes that don't have matching boundary polygons.
This will help understand if they are edge cases or if the hypothesis needs refinement.
"""

import sys
from pathlib import Path
from typing import Dict, Tuple

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from timezonefinder import TimezoneFinder


def analyze_unmatched_holes():
    """Analyze the holes that don't have matching boundary polygons."""
    print("Loading TimezoneFinder data...")
    tf = TimezoneFinder()

    # Get all hole information
    hole_registry = tf.hole_registry

    # Build reverse mapping: hole_id -> parent_polygon_id
    hole_to_parent: Dict[int, int] = {}
    for polygon_id, (num_holes, first_hole_id) in hole_registry.items():
        for i in range(num_holes):
            hole_id = first_hole_id + i
            hole_to_parent[hole_id] = polygon_id

    def get_bbox(polygon_array, polygon_id: int) -> Tuple[int, int, int, int]:
        """Get bounding box for a polygon as (xmin, ymin, xmax, ymax)."""
        return (
            polygon_array.xmin[polygon_id],
            polygon_array.ymin[polygon_id],
            polygon_array.xmax[polygon_id],
            polygon_array.ymax[polygon_id],
        )

    print("Finding unmatched holes...")
    unmatched_holes = []

    for hole_id in range(tf.nr_of_holes):
        if hole_id not in hole_to_parent:
            continue

        parent_polygon_id = hole_to_parent[hole_id]
        parent_zone_id = tf.zone_id_of(parent_polygon_id)

        # Get hole bounding box
        hole_bbox = get_bbox(tf.holes, hole_id)

        # Find all boundary polygons with matching bbox
        matching_boundaries = []
        for boundary_id in range(tf.nr_of_polygons):
            boundary_bbox = get_bbox(tf.boundaries, boundary_id)
            if boundary_bbox == hole_bbox:
                boundary_zone_id = tf.zone_id_of(boundary_id)
                matching_boundaries.append(
                    {
                        "boundary_id": boundary_id,
                        "zone_id": boundary_zone_id,
                        "zone_name": tf.zone_name_from_id(boundary_zone_id),
                        "different_zone": boundary_zone_id != parent_zone_id,
                    }
                )

        if len(matching_boundaries) == 0:
            # Check for near matches (with small tolerance)
            near_matches = []
            hole_xmin, hole_ymin, hole_xmax, hole_ymax = hole_bbox
            tolerance = 1  # Allow 1 unit difference

            for boundary_id in range(tf.nr_of_polygons):
                boundary_bbox = get_bbox(tf.boundaries, boundary_id)
                b_xmin, b_ymin, b_xmax, b_ymax = boundary_bbox

                # Check if bboxes are close
                if (
                    abs(hole_xmin - b_xmin) <= tolerance
                    and abs(hole_ymin - b_ymin) <= tolerance
                    and abs(hole_xmax - b_xmax) <= tolerance
                    and abs(hole_ymax - b_ymax) <= tolerance
                ):
                    boundary_zone_id = tf.zone_id_of(boundary_id)
                    near_matches.append(
                        {
                            "boundary_id": boundary_id,
                            "zone_id": boundary_zone_id,
                            "zone_name": tf.zone_name_from_id(boundary_zone_id),
                            "bbox_diff": (
                                abs(hole_xmin - b_xmin),
                                abs(hole_ymin - b_ymin),
                                abs(hole_xmax - b_xmax),
                                abs(hole_ymax - b_ymax),
                            ),
                        }
                    )

            unmatched_holes.append(
                {
                    "hole_id": hole_id,
                    "parent_polygon_id": parent_polygon_id,
                    "parent_zone_name": tf.zone_name_from_id(parent_zone_id),
                    "hole_bbox": hole_bbox,
                    "near_matches": near_matches,
                }
            )

    print(f"\nFound {len(unmatched_holes)} unmatched holes:")
    print("=" * 80)

    for hole in unmatched_holes:
        print(f"\nHole {hole['hole_id']}:")
        print(
            f"  Parent polygon: {hole['parent_polygon_id']} ({hole['parent_zone_name']})"
        )
        print(f"  Hole bbox: {hole['hole_bbox']}")

        if hole["near_matches"]:
            print("  Near matches (tolerance=1):")
            for match in hole["near_matches"]:
                print(f"    Boundary {match['boundary_id']}: {match['zone_name']}")
                print(f"      Bbox difference: {match['bbox_diff']}")
        else:
            print("  No near matches found")

    # Summary statistics about these unmatched holes
    print(f"\n{'=' * 80}")
    print("UNMATCHED HOLES ANALYSIS SUMMARY")
    print(f"{'=' * 80}")

    total_unmatched = len(unmatched_holes)
    with_near_matches = len([h for h in unmatched_holes if h["near_matches"]])

    print(f"Total unmatched holes: {total_unmatched}")
    print(f"Holes with near matches (tolerance=1): {with_near_matches}")
    print(f"Holes with no near matches: {total_unmatched - with_near_matches}")

    # Look at the zones of unmatched holes
    zones_with_unmatched = {}
    for hole in unmatched_holes:
        zone = hole["parent_zone_name"]
        if zone not in zones_with_unmatched:
            zones_with_unmatched[zone] = 0
        zones_with_unmatched[zone] += 1

    print("\nZones with unmatched holes:")
    for zone, count in sorted(zones_with_unmatched.items()):
        print(f"  {zone}: {count} holes")

    return unmatched_holes


if __name__ == "__main__":
    analyze_unmatched_holes()
