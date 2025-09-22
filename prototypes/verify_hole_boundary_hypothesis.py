#!/usr/bin/env python3
"""
Script to verify that every hole has exactly one matching boundary polygon
from a different zone with equal bounding box.

This validates the hypothesis that holes are redundant because they are
always filled by boundary polygons of another timezone.
"""

import sys
from pathlib import Path
from typing import Dict, Tuple

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from timezonefinder import TimezoneFinder


class HoleBoundaryAnalyzer:
    """Analyzes the relationship between holes and boundary polygons."""

    def __init__(self):
        """Initialize with loaded timezonefinder data."""
        print("Loading TimezoneFinder data...")
        self.tf = TimezoneFinder()
        print(f"Loaded {self.tf.nr_of_polygons} boundary polygons")
        print(f"Loaded {self.tf.nr_of_holes} holes")

    def get_bbox(self, polygon_array, polygon_id: int) -> Tuple[int, int, int, int]:
        """Get bounding box for a polygon as (xmin, ymin, xmax, ymax)."""
        return (
            polygon_array.xmin[polygon_id],
            polygon_array.ymin[polygon_id],
            polygon_array.xmax[polygon_id],
            polygon_array.ymax[polygon_id],
        )

    def analyze_hole_boundary_relationship(self) -> Dict[str, any]:
        """
        Analyze the relationship between holes and boundary polygons.

        For each hole, check:
        1. How many boundary polygons have the exact same bbox
        2. Which zones those boundary polygons belong to
        3. Whether the hole's parent polygon zone is different from matching boundaries

        Returns:
            Dictionary with analysis results
        """
        print("\nAnalyzing hole-boundary relationships...")

        results = {
            "total_holes": self.tf.nr_of_holes,
            "holes_with_matches": 0,
            "holes_with_exactly_one_match": 0,
            "holes_with_multiple_matches": 0,
            "holes_without_matches": 0,
            "zone_mismatch_count": 0,
            "detailed_results": [],
        }

        # Get all hole information
        hole_registry = self.tf.hole_registry

        # Build reverse mapping: hole_id -> parent_polygon_id
        hole_to_parent: Dict[int, int] = {}
        for polygon_id, (num_holes, first_hole_id) in hole_registry.items():
            for i in range(num_holes):
                hole_id = first_hole_id + i
                hole_to_parent[hole_id] = polygon_id

        print(f"Processing {len(hole_to_parent)} holes...")

        for hole_id in range(self.tf.nr_of_holes):
            if hole_id not in hole_to_parent:
                print(f"Warning: Hole {hole_id} not found in hole registry!")
                continue

            parent_polygon_id = hole_to_parent[hole_id]
            parent_zone_id = self.tf.zone_id_of(parent_polygon_id)

            # Get hole bounding box
            hole_bbox = self.get_bbox(self.tf.holes, hole_id)

            # Find all boundary polygons with matching bbox
            matching_boundaries = []
            for boundary_id in range(self.tf.nr_of_polygons):
                boundary_bbox = self.get_bbox(self.tf.boundaries, boundary_id)
                if boundary_bbox == hole_bbox:
                    boundary_zone_id = self.tf.zone_id_of(boundary_id)
                    matching_boundaries.append(
                        {
                            "boundary_id": boundary_id,
                            "zone_id": boundary_zone_id,
                            "zone_name": self.tf.zone_name_from_id(boundary_zone_id),
                            "different_zone": boundary_zone_id != parent_zone_id,
                        }
                    )

            # Analyze results for this hole
            num_matches = len(matching_boundaries)
            different_zone_matches = [
                m for m in matching_boundaries if m["different_zone"]
            ]

            hole_result = {
                "hole_id": hole_id,
                "parent_polygon_id": parent_polygon_id,
                "parent_zone_id": parent_zone_id,
                "parent_zone_name": self.tf.zone_name_from_id(parent_zone_id),
                "bbox": hole_bbox,
                "total_matches": num_matches,
                "different_zone_matches": len(different_zone_matches),
                "matching_boundaries": matching_boundaries,
            }

            results["detailed_results"].append(hole_result)

            # Update counters
            if num_matches > 0:
                results["holes_with_matches"] += 1
                if num_matches == 1:
                    results["holes_with_exactly_one_match"] += 1
                else:
                    results["holes_with_multiple_matches"] += 1
            else:
                results["holes_without_matches"] += 1

            if len(different_zone_matches) > 0:
                results["zone_mismatch_count"] += 1

            # Progress indicator
            if (hole_id + 1) % 100 == 0:
                print(f"  Processed {hole_id + 1}/{self.tf.nr_of_holes} holes")

        return results

    def print_summary(self, results: Dict[str, any]):
        """Print a summary of the analysis results."""
        print("\n" + "=" * 60)
        print("HOLE-BOUNDARY ANALYSIS SUMMARY")
        print("=" * 60)

        total = results["total_holes"]
        with_matches = results["holes_with_matches"]
        exactly_one = results["holes_with_exactly_one_match"]
        multiple = results["holes_with_multiple_matches"]
        without = results["holes_without_matches"]
        zone_mismatches = results["zone_mismatch_count"]

        print(f"Total holes analyzed: {total}")
        print(
            f"Holes with matching boundary polygons: {with_matches} ({with_matches / total * 100:.1f}%)"
        )
        print(
            f"  - With exactly 1 match: {exactly_one} ({exactly_one / total * 100:.1f}%)"
        )
        print(f"  - With multiple matches: {multiple} ({multiple / total * 100:.1f}%)")
        print(f"Holes without matches: {without} ({without / total * 100:.1f}%)")
        print(
            f"Holes with matches from different zones: {zone_mismatches} ({zone_mismatches / total * 100:.1f}%)"
        )

        # Check hypothesis
        print("\n" + "-" * 40)
        print("HYPOTHESIS VALIDATION:")
        print("-" * 40)

        if exactly_one == total:
            print(
                "✅ HYPOTHESIS CONFIRMED: Every hole has exactly one matching boundary polygon!"
            )
        elif with_matches == total and zone_mismatches == total:
            print(
                "⚠️  PARTIAL CONFIRMATION: Every hole has matches, all from different zones,"
            )
            print("   but some holes have multiple matches.")
        else:
            print(
                "❌ HYPOTHESIS REJECTED: Not all holes have exactly one matching boundary polygon."
            )

        # Show problematic cases
        if without > 0:
            print(f"\n⚠️  {without} holes have NO matching boundary polygons")

        if multiple > 0:
            print(f"\n⚠️  {multiple} holes have MULTIPLE matching boundary polygons")

        if zone_mismatches < with_matches:
            same_zone_matches = with_matches - zone_mismatches
            print(f"\n⚠️  {same_zone_matches} holes have matches from the SAME zone")

    def print_detailed_examples(self, results: Dict[str, any], max_examples: int = 5):
        """Print detailed examples of different cases."""
        print("\n" + "=" * 60)
        print("DETAILED EXAMPLES")
        print("=" * 60)

        # Examples of holes without matches
        no_matches = [r for r in results["detailed_results"] if r["total_matches"] == 0]
        if no_matches:
            print(
                f"\nHoles WITHOUT matching boundaries (showing first {max_examples}):"
            )
            for i, hole in enumerate(no_matches[:max_examples]):
                print(
                    f"  Hole {hole['hole_id']}: parent={hole['parent_polygon_id']} "
                    f"zone={hole['parent_zone_name']} bbox={hole['bbox']}"
                )

        # Examples of holes with multiple matches
        multiple_matches = [
            r for r in results["detailed_results"] if r["total_matches"] > 1
        ]
        if multiple_matches:
            print(
                f"\nHoles with MULTIPLE matching boundaries (showing first {max_examples}):"
            )
            for i, hole in enumerate(multiple_matches[:max_examples]):
                print(
                    f"  Hole {hole['hole_id']}: parent={hole['parent_polygon_id']} "
                    f"zone={hole['parent_zone_name']} matches={hole['total_matches']}"
                )
                for match in hole["matching_boundaries"]:
                    marker = "✓" if match["different_zone"] else "✗"
                    print(
                        f"    {marker} Boundary {match['boundary_id']}: {match['zone_name']}"
                    )

        # Examples of perfect matches (exactly one match from different zone)
        perfect_matches = [
            r
            for r in results["detailed_results"]
            if r["total_matches"] == 1 and r["different_zone_matches"] == 1
        ]
        if perfect_matches:
            print(
                f"\nPERFECT matches (exactly 1 boundary from different zone, showing first {max_examples}):"
            )
            for i, hole in enumerate(perfect_matches[:max_examples]):
                match = hole["matching_boundaries"][0]
                print(
                    f"  Hole {hole['hole_id']}: {hole['parent_zone_name']} -> {match['zone_name']}"
                )


def main():
    """Run the hole-boundary analysis."""
    try:
        analyzer = HoleBoundaryAnalyzer()
        results = analyzer.analyze_hole_boundary_relationship()

        analyzer.print_summary(results)
        analyzer.print_detailed_examples(results)

        # Write results to file for further analysis if needed
        import json

        output_file = Path(__file__).parent / "hole_boundary_analysis_results.json"

        # Convert results to JSON-serializable format
        json_results = {
            "total_holes": results["total_holes"],
            "holes_with_matches": results["holes_with_matches"],
            "holes_with_exactly_one_match": results["holes_with_exactly_one_match"],
            "holes_with_multiple_matches": results["holes_with_multiple_matches"],
            "holes_without_matches": results["holes_without_matches"],
            "zone_mismatch_count": results["zone_mismatch_count"],
            "summary_stats": {
                "hypothesis_confirmed": results["holes_with_exactly_one_match"]
                == results["total_holes"],
                "all_have_matches": results["holes_with_matches"]
                == results["total_holes"],
                "all_different_zones": results["zone_mismatch_count"]
                == results["holes_with_matches"],
            },
        }

        with open(output_file, "w") as f:
            json.dump(json_results, f, indent=2)

        print(f"\nDetailed results written to: {output_file}")

    except Exception as e:
        print(f"Error during analysis: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
