#!/usr/bin/env python3
"""
Detailed bounding box analysis for each unmatched hole and its closest boundary match.
Shows coordinates in both integer units and converted degrees.
"""

import sys
from pathlib import Path
import json
from typing import Tuple

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# From timezonefinder config
DECIMAL_PLACES_SHIFT = 7
INT2COORD_FACTOR = 10 ** (-DECIMAL_PLACES_SHIFT)  # 0.0000001


def int_coords_to_degrees(
    bbox: Tuple[int, int, int, int],
) -> Tuple[float, float, float, float]:
    """Convert integer coordinates to degrees."""
    xmin, ymin, xmax, ymax = bbox
    return (
        xmin * INT2COORD_FACTOR,
        ymin * INT2COORD_FACTOR,
        xmax * INT2COORD_FACTOR,
        ymax * INT2COORD_FACTOR,
    )


def bbox_center(bbox: Tuple[float, float, float, float]) -> Tuple[float, float]:
    """Calculate center point of bounding box."""
    xmin, ymin, xmax, ymax = bbox
    return ((xmin + xmax) / 2, (ymin + ymax) / 2)


def bbox_dimensions(bbox: Tuple[float, float, float, float]) -> Tuple[float, float]:
    """Calculate width and height of bounding box in degrees."""
    xmin, ymin, xmax, ymax = bbox
    return (xmax - xmin, ymax - ymin)


def analyze_unmatched_hole_bboxes():
    """Analyze bounding boxes of unmatched holes and their closest matches."""

    print("Loading analysis results...")
    results_file = Path(__file__).parent / "unmatched_holes_closest_matches.json"

    if not results_file.exists():
        print("❌ Results file not found. Please run analyze_closest_matches.py first.")
        return

    with open(results_file) as f:
        results = json.load(f)

    print(f"\n{'=' * 100}")
    print("DETAILED BOUNDING BOX ANALYSIS FOR UNMATCHED HOLES")
    print(f"{'=' * 100}")

    for i, hole_data in enumerate(results):
        hole_id = hole_data["hole_id"]
        parent_zone = hole_data["parent_zone"]
        hole_bbox_int = tuple(hole_data["hole_bbox"])
        hole_area = hole_data["hole_area"]

        # Get the closest match
        if not hole_data["top_matches"]:
            continue

        closest_match = hole_data["top_matches"][0]
        boundary_id = closest_match["boundary_id"]
        match_zone = closest_match["zone_name"]
        boundary_bbox_int = tuple(closest_match["bbox"])
        distance_score = closest_match["distance_score"]
        bbox_diffs = closest_match["bbox_differences"]

        # Convert to degrees
        hole_bbox_deg = int_coords_to_degrees(hole_bbox_int)
        boundary_bbox_deg = int_coords_to_degrees(boundary_bbox_int)

        # Calculate centers and dimensions
        hole_center = bbox_center(hole_bbox_deg)
        boundary_center = bbox_center(boundary_bbox_deg)
        hole_dims = bbox_dimensions(hole_bbox_deg)
        boundary_dims = bbox_dimensions(boundary_bbox_deg)

        print(f"\n🔍 HOLE {hole_id}: {parent_zone}")
        print(f"   └── Closest Match: Boundary {boundary_id} ({match_zone})")
        print(f"   └── Distance Score: {distance_score:,.0f}")

        print("\n   📦 HOLE BOUNDING BOX:")
        print(
            f"      Integer coords: ({hole_bbox_int[0]:,}, {hole_bbox_int[1]:,}, {hole_bbox_int[2]:,}, {hole_bbox_int[3]:,})"
        )
        print(
            f"      Degree coords:  ({hole_bbox_deg[0]:.6f}°, {hole_bbox_deg[1]:.6f}°, {hole_bbox_deg[2]:.6f}°, {hole_bbox_deg[3]:.6f}°)"
        )
        print(f"      Center point:   ({hole_center[0]:.6f}°, {hole_center[1]:.6f}°)")
        print(
            f"      Dimensions:     {hole_dims[0]:.6f}° × {hole_dims[1]:.6f}° (W × H)"
        )
        print(f"      Area:           {hole_area:,} int²")

        print("\n   🎯 CLOSEST BOUNDARY BOUNDING BOX:")
        print(
            f"      Integer coords: ({boundary_bbox_int[0]:,}, {boundary_bbox_int[1]:,}, {boundary_bbox_int[2]:,}, {boundary_bbox_int[3]:,})"
        )
        print(
            f"      Degree coords:  ({boundary_bbox_deg[0]:.6f}°, {boundary_bbox_deg[1]:.6f}°, {boundary_bbox_deg[2]:.6f}°, {boundary_bbox_deg[3]:.6f}°)"
        )
        print(
            f"      Center point:   ({boundary_center[0]:.6f}°, {boundary_center[1]:.6f}°)"
        )
        print(
            f"      Dimensions:     {boundary_dims[0]:.6f}° × {boundary_dims[1]:.6f}° (W × H)"
        )

        print("\n   📏 COORDINATE DIFFERENCES:")
        diff_xmin_deg = bbox_diffs[0] * INT2COORD_FACTOR
        diff_ymin_deg = bbox_diffs[1] * INT2COORD_FACTOR
        diff_xmax_deg = bbox_diffs[2] * INT2COORD_FACTOR
        diff_ymax_deg = bbox_diffs[3] * INT2COORD_FACTOR

        print(f"      Δx_min: {bbox_diffs[0]:,} units = {diff_xmin_deg:.6f}°")
        print(f"      Δy_min: {bbox_diffs[1]:,} units = {diff_ymin_deg:.6f}°")
        print(f"      Δx_max: {bbox_diffs[2]:,} units = {diff_xmax_deg:.6f}°")
        print(f"      Δy_max: {bbox_diffs[3]:,} units = {diff_ymax_deg:.6f}°")

        # Calculate center-to-center distance
        center_distance_deg = (
            (hole_center[0] - boundary_center[0]) ** 2
            + (hole_center[1] - boundary_center[1]) ** 2
        ) ** 0.5
        center_distance_km = center_distance_deg * 111  # Approximate km per degree

        print("\n   🌍 GEOGRAPHIC SEPARATION:")
        print(
            f"      Center-to-center: {center_distance_deg:.6f}° ≈ {center_distance_km:.1f} km"
        )
        print(
            f"      Max coord diff:   {max(bbox_diffs) * INT2COORD_FACTOR:.6f}° ≈ {max(bbox_diffs) * INT2COORD_FACTOR * 111:.1f} km"
        )

        if i < len(results) - 1:
            print(f"\n{'-' * 100}")

    # Summary statistics
    print(f"\n{'=' * 100}")
    print("SUMMARY STATISTICS")
    print(f"{'=' * 100}")

    # Group by parent timezone
    by_timezone = {}
    for hole_data in results:
        parent_zone = hole_data["parent_zone"]
        if parent_zone not in by_timezone:
            by_timezone[parent_zone] = []

        if hole_data["top_matches"]:
            closest_match = hole_data["top_matches"][0]
            max_diff_deg = max(closest_match["bbox_differences"]) * INT2COORD_FACTOR
            by_timezone[parent_zone].append(
                {
                    "hole_id": hole_data["hole_id"],
                    "max_diff_deg": max_diff_deg,
                    "match_zone": closest_match["zone_name"],
                }
            )

    print("\nBounding Box Separation by Parent Timezone:")
    print(
        f"{'Timezone':<20} {'Holes':<6} {'Avg Max Diff':<12} {'Range':<25} {'Typical Match Zone'}"
    )
    print(f"{'-' * 85}")

    for zone, holes in by_timezone.items():
        if not holes:
            continue

        max_diffs = [h["max_diff_deg"] for h in holes]
        avg_diff = sum(max_diffs) / len(max_diffs)
        min_diff = min(max_diffs)
        max_diff = max(max_diffs)

        # Find most common match zone
        match_zones = [h["match_zone"] for h in holes]
        most_common = max(set(match_zones), key=match_zones.count)

        range_str = f"{min_diff:.3f}° - {max_diff:.3f}°"

        print(
            f"{zone:<20} {len(holes):<6} {avg_diff:.3f}°{'':<4} {range_str:<25} {most_common}"
        )

    print("\nCoordinate Reference:")
    print("• 1° ≈ 111 km at equator")
    print("• 0.1° ≈ 11 km")
    print("• 0.01° ≈ 1.1 km")
    print("• 0.001° ≈ 110 m")


if __name__ == "__main__":
    analyze_unmatched_hole_bboxes()
