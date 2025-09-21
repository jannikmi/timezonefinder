#!/usr/bin/env python3
"""
Advanced analysis to check if holes are filled by combinations of multiple boundary polygons.
This tests the hypothesis that holes represent areas covered by the union of multiple boundaries
from different timezone zones, rather than just single boundary matches.
"""

import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, NamedTuple
import numpy as np
from itertools import combinations
import json

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from timezonefinder import TimezoneFinder

# From timezonefinder config
DECIMAL_PLACES_SHIFT = 7
INT2COORD_FACTOR = 10 ** (-DECIMAL_PLACES_SHIFT)


class BoundaryMatch(NamedTuple):
    """Represents a boundary polygon that overlaps with a hole."""

    boundary_id: int
    zone_id: int
    zone_name: str
    bbox: Tuple[int, int, int, int]
    overlap_type: str  # 'exact', 'contains', 'contained', 'intersects'
    overlap_score: float  # measure of overlap quality


def bbox_intersects(
    bbox1: Tuple[int, int, int, int], bbox2: Tuple[int, int, int, int]
) -> bool:
    """Check if two bounding boxes intersect."""
    x1_min, y1_min, x1_max, y1_max = bbox1
    x2_min, y2_min, x2_max, y2_max = bbox2

    return not (
        x1_max < x2_min or x2_max < x1_min or y1_max < y2_min or y2_max < y1_min
    )


def bbox_contains(
    outer_bbox: Tuple[int, int, int, int], inner_bbox: Tuple[int, int, int, int]
) -> bool:
    """Check if outer_bbox completely contains inner_bbox."""
    x1_min, y1_min, x1_max, y1_max = outer_bbox
    x2_min, y2_min, x2_max, y2_max = inner_bbox

    return (
        x1_min <= x2_min and y1_min <= y2_min and x1_max >= x2_max and y1_max >= y2_max
    )


def bbox_union(bboxes: List[Tuple[int, int, int, int]]) -> Tuple[int, int, int, int]:
    """Calculate the union (bounding box) of multiple bounding boxes."""
    if not bboxes:
        return (0, 0, 0, 0)

    min_x = min(bbox[0] for bbox in bboxes)
    min_y = min(bbox[1] for bbox in bboxes)
    max_x = max(bbox[2] for bbox in bboxes)
    max_y = max(bbox[3] for bbox in bboxes)

    return (min_x, min_y, max_x, max_y)


def bbox_area(bbox: Tuple[int, int, int, int]) -> int:
    """Calculate area of bounding box."""
    x_min, y_min, x_max, y_max = bbox
    return (x_max - x_min) * (y_max - y_min)


def calculate_overlap_score(
    hole_bbox: Tuple[int, int, int, int], boundary_bbox: Tuple[int, int, int, int]
) -> float:
    """Calculate a score representing how well a boundary bbox matches a hole bbox."""
    if hole_bbox == boundary_bbox:
        return 1.0  # Perfect match

    if bbox_contains(boundary_bbox, hole_bbox):
        # Boundary contains hole - good match
        hole_area = bbox_area(hole_bbox)
        boundary_area = bbox_area(boundary_bbox)
        return hole_area / boundary_area if boundary_area > 0 else 0.0

    if bbox_contains(hole_bbox, boundary_bbox):
        # Hole contains boundary - partial fill
        hole_area = bbox_area(hole_bbox)
        boundary_area = bbox_area(boundary_bbox)
        return boundary_area / hole_area if hole_area > 0 else 0.0

    if bbox_intersects(hole_bbox, boundary_bbox):
        # Calculate intersection area approximation
        x1_min, y1_min, x1_max, y1_max = hole_bbox
        x2_min, y2_min, x2_max, y2_max = boundary_bbox

        intersect_min_x = max(x1_min, x2_min)
        intersect_min_y = max(y1_min, y2_min)
        intersect_max_x = min(x1_max, x2_max)
        intersect_max_y = min(y1_max, y2_max)

        if intersect_max_x > intersect_min_x and intersect_max_y > intersect_min_y:
            intersect_area = (intersect_max_x - intersect_min_x) * (
                intersect_max_y - intersect_min_y
            )
            hole_area = bbox_area(hole_bbox)
            return intersect_area / hole_area if hole_area > 0 else 0.0

    return 0.0  # No overlap


def analyze_multi_boundary_hole_filling():
    """Analyze if holes can be filled by combinations of multiple boundary polygons."""
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
            int(polygon_array.xmin[polygon_id]),
            int(polygon_array.ymin[polygon_id]),
            int(polygon_array.xmax[polygon_id]),
            int(polygon_array.ymax[polygon_id]),
        )

    print(f"Analyzing {len(hole_to_parent)} holes for multi-boundary filling...")

    analysis_results = []

    for hole_id in range(tf.nr_of_holes):
        if hole_id not in hole_to_parent:
            continue

        parent_polygon_id = hole_to_parent[hole_id]
        parent_zone_id = tf.zone_id_of(parent_polygon_id)
        parent_zone_name = tf.zone_name_from_id(parent_zone_id)
        hole_bbox = get_bbox(tf.holes, hole_id)

        print(
            f"\rAnalyzing hole {hole_id + 1}/{len(hole_to_parent)}: {parent_zone_name}",
            end="",
            flush=True,
        )

        # Find all boundary polygons that intersect or relate to this hole
        all_boundary_matches = []
        exact_match_count = 0
        containing_count = 0
        contained_count = 0
        intersecting_count = 0

        for boundary_id in range(tf.nr_of_polygons):
            boundary_bbox = get_bbox(tf.boundaries, boundary_id)
            boundary_zone_id = tf.zone_id_of(boundary_id)
            boundary_zone_name = tf.zone_name_from_id(boundary_zone_id)

            # Skip boundaries from the same zone as the hole's parent
            if boundary_zone_id == parent_zone_id:
                continue

            overlap_score = calculate_overlap_score(hole_bbox, boundary_bbox)

            if overlap_score > 0:
                if hole_bbox == boundary_bbox:
                    match_type = "exact"
                    exact_match_count += 1
                elif bbox_contains(boundary_bbox, hole_bbox):
                    match_type = "contains"
                    containing_count += 1
                elif bbox_contains(hole_bbox, boundary_bbox):
                    match_type = "contained"
                    contained_count += 1
                else:
                    match_type = "intersects"
                    intersecting_count += 1

                boundary_match = BoundaryMatch(
                    boundary_id=boundary_id,
                    zone_id=boundary_zone_id,
                    zone_name=boundary_zone_name,
                    bbox=boundary_bbox,
                    overlap_type=match_type,
                    overlap_score=overlap_score,
                )

                all_boundary_matches.append(boundary_match)

        # Sort by overlap score (best matches first)
        all_matches = sorted(
            all_boundary_matches, key=lambda x: x.overlap_score, reverse=True
        )

        # Test combinations of boundaries to see if they can fill the hole
        combination_results = []

        if len(all_matches) > 1:
            # Test combinations of 2, 3, 4, etc. boundaries
            for combo_size in range(
                2, min(6, len(all_matches) + 1)
            ):  # Max 5 boundaries
                for combo in combinations(
                    all_matches[:10], combo_size
                ):  # Test top 10 matches
                    combo_bboxes = [match.bbox for match in combo]
                    combo_union = bbox_union(combo_bboxes)
                    combo_zones = [match.zone_name for match in combo]
                    combo_ids = [match.boundary_id for match in combo]

                    # Check how well this combination matches the hole
                    if combo_union == hole_bbox:
                        # Perfect union match!
                        combination_results.append(
                            {
                                "type": "perfect_union",
                                "boundaries": combo_ids,
                                "zones": combo_zones,
                                "union_bbox": combo_union,
                                "score": 1.0,
                            }
                        )
                    elif bbox_contains(combo_union, hole_bbox):
                        # Union contains hole
                        hole_area = bbox_area(hole_bbox)
                        union_area = bbox_area(combo_union)
                        containment_score = (
                            hole_area / union_area if union_area > 0 else 0.0
                        )

                        if containment_score > 0.8:  # Very good containment
                            combination_results.append(
                                {
                                    "type": "good_containment",
                                    "boundaries": combo_ids,
                                    "zones": combo_zones,
                                    "union_bbox": combo_union,
                                    "score": containment_score,
                                }
                            )

        # Sort combination results by score
        combination_results.sort(key=lambda x: x["score"], reverse=True)

        # Store analysis results
        hole_analysis = {
            "hole_id": hole_id,
            "parent_polygon_id": parent_polygon_id,
            "parent_zone": parent_zone_name,
            "hole_bbox": hole_bbox,
            "exact_matches": exact_match_count,
            "containing_boundaries": containing_count,
            "contained_boundaries": contained_count,
            "intersecting_boundaries": intersecting_count,
            "total_related_boundaries": len(all_matches),
            "top_single_matches": [
                {
                    "boundary_id": match.boundary_id,
                    "zone_name": match.zone_name,
                    "overlap_type": match.overlap_type,
                    "score": match.overlap_score,
                }
                for match in all_matches[:5]
            ],
            "combination_matches": combination_results[:5],  # Top 5 combinations
        }

        analysis_results.append(hole_analysis)

    print()  # New line after progress indicator
    return analysis_results


def print_multi_boundary_analysis(results: List[Dict]):
    """Print analysis results for multi-boundary hole filling."""
    print(f"\n{'=' * 100}")
    print("MULTI-BOUNDARY HOLE FILLING ANALYSIS")
    print(f"{'=' * 100}")

    # Summary statistics
    perfect_unions = 0
    good_containments = 0
    exact_single_matches = 0
    no_good_matches = 0
    has_combinations = 0

    for result in results:
        if result["exact_matches"] > 0:
            exact_single_matches += 1
        elif result["combination_matches"]:
            has_combinations += 1
            for combo in result["combination_matches"]:
                if combo["type"] == "perfect_union":
                    perfect_unions += 1
                    break
                elif combo["type"] == "good_containment" and combo["score"] > 0.9:
                    good_containments += 1
                    break
        else:
            no_good_matches += 1

    total = len(results)
    print(f"\nSUMMARY STATISTICS:")
    print(f"{'=' * 50}")
    print(f"Total holes analyzed: {total}")
    print(
        f"Exact single boundary matches: {exact_single_matches} ({exact_single_matches / total * 100:.1f}%)"
    )
    print(
        f"Perfect union combinations: {perfect_unions} ({perfect_unions / total * 100:.1f}%)"
    )
    print(
        f"Good containment combinations: {good_containments} ({good_containments / total * 100:.1f}%)"
    )
    print(
        f"Holes with combination potential: {has_combinations} ({has_combinations / total * 100:.1f}%)"
    )
    print(
        f"No good matches found: {no_good_matches} ({no_good_matches / total * 100:.1f}%)"
    )

    # Show examples of perfect unions
    print(f"\n🎯 PERFECT UNION EXAMPLES:")
    print(f"{'=' * 50}")

    perfect_examples = []
    for result in results:
        for combo in result["combination_matches"]:
            if combo["type"] == "perfect_union":
                perfect_examples.append((result, combo))
                break

    for i, (hole_result, combo) in enumerate(perfect_examples[:5]):
        print(f"\nHole {hole_result['hole_id']} ({hole_result['parent_zone']}):")
        print(
            f"  Filled by {len(combo['boundaries'])} boundaries: {', '.join(combo['zones'])}"
        )
        print(f"  Boundary IDs: {combo['boundaries']}")
        hole_bbox_deg = tuple(
            coord * INT2COORD_FACTOR for coord in hole_result["hole_bbox"]
        )
        union_bbox_deg = tuple(
            coord * INT2COORD_FACTOR for coord in combo["union_bbox"]
        )
        print(f"  Hole bbox: {hole_bbox_deg}")
        print(f"  Union bbox: {union_bbox_deg}")

    # Show examples of good containments
    print(f"\n🎯 GOOD CONTAINMENT EXAMPLES:")
    print(f"{'=' * 50}")

    containment_examples = []
    for result in results:
        for combo in result["combination_matches"]:
            if combo["type"] == "good_containment" and combo["score"] > 0.8:
                containment_examples.append((result, combo))
                break

    for i, (hole_result, combo) in enumerate(containment_examples[:5]):
        print(f"\nHole {hole_result['hole_id']} ({hole_result['parent_zone']}):")
        print(
            f"  ~{combo['score'] * 100:.1f}% filled by {len(combo['boundaries'])} boundaries: {', '.join(combo['zones'])}"
        )
        print(f"  Boundary IDs: {combo['boundaries']}")

    # Show holes with no good matches (the problematic cases)
    print(f"\n⚠️  HOLES WITH NO GOOD MATCHES:")
    print(f"{'=' * 50}")

    no_match_examples = [
        r for r in results if r["exact_matches"] == 0 and not r["combination_matches"]
    ][:10]

    for result in no_match_examples:
        print(f"\nHole {result['hole_id']} ({result['parent_zone']}):")
        print(f"  Total related boundaries: {result['total_related_boundaries']}")
        if result["top_single_matches"]:
            best = result["top_single_matches"][0]
            print(
                f"  Best single match: {best['zone_name']} (score: {best['score']:.3f}, type: {best['overlap_type']})"
            )


def main():
    """Run the multi-boundary hole filling analysis."""
    try:
        results = analyze_multi_boundary_hole_filling()
        print_multi_boundary_analysis(results)

        # Save detailed results
        output_file = Path(__file__).parent / "multi_boundary_hole_analysis.json"

        # Convert to JSON-serializable format
        json_results = []
        for result in results:
            json_result = {
                "hole_id": result["hole_id"],
                "parent_zone": result["parent_zone"],
                "hole_bbox": list(result["hole_bbox"]),
                "exact_matches": result["exact_matches"],
                "total_related_boundaries": result["total_related_boundaries"],
                "top_single_matches": result["top_single_matches"],
                "combination_matches": result["combination_matches"],
            }
            json_results.append(json_result)

        with open(output_file, "w") as f:
            json.dump(json_results, f, indent=2)

        print(f"\nDetailed results saved to: {output_file}")

    except Exception as e:
        print(f"Error during analysis: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
