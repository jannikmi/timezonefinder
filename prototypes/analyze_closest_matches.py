#!/usr/bin/env python3
"""
Enhanced analysis to find the closest similar matches for unmatched holes.
This will help understand if the unmatched holes have near-matches that could
reveal patterns or data processing issues.
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple, NamedTuple
import numpy as np

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from timezonefinder import TimezoneFinder


class SimilarMatch(NamedTuple):
    """Represents a similar boundary polygon match for a hole."""

    boundary_id: int
    zone_id: int
    zone_name: str
    bbox: Tuple[int, int, int, int]
    distance_score: float
    bbox_differences: Tuple[int, int, int, int]  # (dx_min, dy_min, dx_max, dy_max)
    area_difference: int


def bbox_distance(
    bbox1: Tuple[int, int, int, int], bbox2: Tuple[int, int, int, int]
) -> float:
    """Calculate a distance score between two bounding boxes."""
    x1_min, y1_min, x1_max, y1_max = bbox1
    x2_min, y2_min, x2_max, y2_max = bbox2

    # Calculate differences for each coordinate
    dx_min = abs(x1_min - x2_min)
    dy_min = abs(y1_min - y2_min)
    dx_max = abs(x1_max - x2_max)
    dy_max = abs(y1_max - y2_max)

    # Use Manhattan distance as the primary metric
    manhattan_distance = dx_min + dy_min + dx_max + dy_max

    # Also consider the maximum individual difference (Chebyshev distance component)
    max_diff = max(dx_min, dy_min, dx_max, dy_max)

    # Combine both metrics - weight Manhattan distance more heavily
    return manhattan_distance + (0.1 * max_diff)


def bbox_area(bbox: Tuple[int, int, int, int]) -> int:
    """Calculate the area of a bounding box."""
    x_min, y_min, x_max, y_max = bbox
    width = x_max - x_min
    height = y_max - y_min
    return width * height


def analyze_closest_matches():
    """Find the closest similar matches for unmatched holes."""
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

    print("Finding unmatched holes and their closest matches...")

    # First, identify unmatched holes
    unmatched_holes = []
    for hole_id in range(tf.nr_of_holes):
        if hole_id not in hole_to_parent:
            continue

        parent_polygon_id = hole_to_parent[hole_id]
        parent_zone_id = tf.zone_id_of(parent_polygon_id)
        hole_bbox = get_bbox(tf.holes, hole_id)

        # Check if this hole has exact matches
        has_exact_match = False
        for boundary_id in range(tf.nr_of_polygons):
            boundary_bbox = get_bbox(tf.boundaries, boundary_id)
            if boundary_bbox == hole_bbox:
                has_exact_match = True
                break

        if not has_exact_match:
            unmatched_holes.append(
                {
                    "hole_id": hole_id,
                    "parent_polygon_id": parent_polygon_id,
                    "parent_zone_id": parent_zone_id,
                    "parent_zone_name": tf.zone_name_from_id(parent_zone_id),
                    "hole_bbox": hole_bbox,
                    "hole_area": bbox_area(hole_bbox),
                }
            )

    print(f"Found {len(unmatched_holes)} unmatched holes")

    # For each unmatched hole, find the closest boundary polygons
    analysis_results = []

    for hole_info in unmatched_holes:
        hole_id = hole_info["hole_id"]
        hole_bbox = hole_info["hole_bbox"]
        hole_area = hole_info["hole_area"]
        parent_zone_id = hole_info["parent_zone_id"]

        print(f"Analyzing hole {hole_id}...")

        # Find all boundary polygons and calculate similarity scores
        similar_matches = []

        for boundary_id in range(tf.nr_of_polygons):
            boundary_bbox = get_bbox(tf.boundaries, boundary_id)
            boundary_zone_id = tf.zone_id_of(boundary_id)

            # Skip if it's the same zone (not interesting for hole filling)
            if boundary_zone_id == parent_zone_id:
                continue

            # Calculate similarity metrics
            distance = bbox_distance(hole_bbox, boundary_bbox)
            boundary_area = bbox_area(boundary_bbox)
            area_diff = abs(hole_area - boundary_area)

            # Calculate coordinate differences
            h_xmin, h_ymin, h_xmax, h_ymax = hole_bbox
            b_xmin, b_ymin, b_xmax, b_ymax = boundary_bbox
            bbox_diffs = (
                abs(h_xmin - b_xmin),
                abs(h_ymin - b_ymin),
                abs(h_xmax - b_xmax),
                abs(h_ymax - b_ymax),
            )

            similar_match = SimilarMatch(
                boundary_id=boundary_id,
                zone_id=boundary_zone_id,
                zone_name=tf.zone_name_from_id(boundary_zone_id),
                bbox=boundary_bbox,
                distance_score=distance,
                bbox_differences=bbox_diffs,
                area_difference=area_diff,
            )

            similar_matches.append(similar_match)

        # Sort by distance score (best matches first)
        similar_matches.sort(key=lambda x: x.distance_score)

        # Keep only the top 10 matches
        top_matches = similar_matches[:10]

        analysis_results.append({"hole_info": hole_info, "top_matches": top_matches})

    return analysis_results


def print_closest_matches_analysis(results: List[Dict]):
    """Print detailed analysis of closest matches for unmatched holes."""
    print(f"\n{'=' * 100}")
    print("CLOSEST MATCHES ANALYSIS FOR UNMATCHED HOLES")
    print(f"{'=' * 100}")

    for result in results:
        hole_info = result["hole_info"]
        top_matches = result["top_matches"]

        hole_id = hole_info["hole_id"]
        parent_zone = hole_info["parent_zone_name"]
        hole_bbox = hole_info["hole_bbox"]
        hole_area = hole_info["hole_area"]

        print(f"\n🔍 HOLE {hole_id} (Parent: {parent_zone})")
        print(f"   Bbox: {hole_bbox}")
        print(f"   Area: {hole_area:,}")
        print(f"   Top {min(5, len(top_matches))} closest boundary matches:")

        for i, match in enumerate(top_matches[:5]):
            # Format the distance score
            distance_str = f"{match.distance_score:,.0f}"

            # Format bbox differences
            dx_min, dy_min, dx_max, dy_max = match.bbox_differences
            max_diff = max(match.bbox_differences)

            print(
                f"     {i + 1:2d}. Boundary {match.boundary_id:3d} ({match.zone_name})"
            )
            print(f"         Distance Score: {distance_str:>12}")
            print(f"         Max Coord Diff: {max_diff:>12,}")
            print(f"         Area Diff: {match.area_difference:>16,}")
            print(
                f"         Bbox Diffs: Δx_min={dx_min:,}, Δy_min={dy_min:,}, Δx_max={dx_max:,}, Δy_max={dy_max:,}"
            )

            # Show if this is a particularly close match
            if max_diff <= 1000:  # Very close
                print("         🟢 VERY CLOSE MATCH (max diff ≤ 1,000)")
            elif max_diff <= 10000:  # Close
                print("         🟡 CLOSE MATCH (max diff ≤ 10,000)")
            elif max_diff <= 100000:  # Moderate
                print("         🟠 MODERATE MATCH (max diff ≤ 100,000)")

        print()

    # Summary statistics
    print(f"\n{'=' * 100}")
    print("SUMMARY STATISTICS")
    print(f"{'=' * 100}")

    # Analyze the quality of closest matches
    very_close_count = 0
    close_count = 0
    moderate_count = 0

    for result in results:
        top_match = result["top_matches"][0] if result["top_matches"] else None
        if top_match:
            max_diff = max(top_match.bbox_differences)
            if max_diff <= 1000:
                very_close_count += 1
            elif max_diff <= 10000:
                close_count += 1
            elif max_diff <= 100000:
                moderate_count += 1

    total = len(results)
    print(
        f"Unmatched holes with very close matches (≤1,000): {very_close_count}/{total} ({very_close_count / total * 100:.1f}%)"
    )
    print(
        f"Unmatched holes with close matches (≤10,000): {close_count}/{total} ({close_count / total * 100:.1f}%)"
    )
    print(
        f"Unmatched holes with moderate matches (≤100,000): {moderate_count}/{total} ({moderate_count / total * 100:.1f}%)"
    )

    far_count = total - very_close_count - close_count - moderate_count
    print(
        f"Unmatched holes with only distant matches (>100,000): {far_count}/{total} ({far_count / total * 100:.1f}%)"
    )

    # Analyze patterns by timezone
    print("\nPatterns by parent timezone:")
    timezone_analysis = {}
    for result in results:
        parent_zone = result["hole_info"]["parent_zone_name"]
        if parent_zone not in timezone_analysis:
            timezone_analysis[parent_zone] = {
                "count": 0,
                "avg_closest_distance": 0,
                "best_distances": [],
            }

        timezone_analysis[parent_zone]["count"] += 1
        if result["top_matches"]:
            best_distance = result["top_matches"][0].distance_score
            timezone_analysis[parent_zone]["best_distances"].append(best_distance)

    for zone, data in timezone_analysis.items():
        if data["best_distances"]:
            avg_distance = np.mean(data["best_distances"])
            min_distance = min(data["best_distances"])
            max_distance = max(data["best_distances"])
            print(
                f"  {zone}: {data['count']} holes, avg closest distance: {avg_distance:,.0f}, range: {min_distance:,.0f}-{max_distance:,.0f}"
            )


def main():
    """Run the closest matches analysis."""
    try:
        results = analyze_closest_matches()
        print_closest_matches_analysis(results)

        # Save detailed results to JSON for further analysis
        import json

        # Convert results to JSON-serializable format
        json_results = []
        for result in results:
            hole_info = result["hole_info"]
            top_matches = []

            for match in result["top_matches"][:10]:  # Keep top 10
                top_matches.append(
                    {
                        "boundary_id": match.boundary_id,
                        "zone_name": match.zone_name,
                        "distance_score": float(match.distance_score),
                        "bbox_differences": list(match.bbox_differences),
                        "area_difference": match.area_difference,
                        "bbox": list(match.bbox),
                    }
                )

            json_results.append(
                {
                    "hole_id": hole_info["hole_id"],
                    "parent_zone": hole_info["parent_zone_name"],
                    "hole_bbox": list(hole_info["hole_bbox"]),
                    "hole_area": hole_info["hole_area"],
                    "top_matches": top_matches,
                }
            )

        output_file = Path(__file__).parent / "unmatched_holes_closest_matches.json"
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
