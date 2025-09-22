#!/usr/bin/env python3
"""
Zone Precedence Analysis for Complex Overlapping Borders

This script analyzes the remaining edge cases from the hole-boundary analysis and proposes
a precedence system to resolve overlapping zones when no exact boundary match exists.

The goal is to implement a ranking system where one timezone takes precedence over another
in cases of complex overlapping borders or geometric ambiguity.
"""

import json
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Set
import sys
import os

# Add parent directory to path to import timezonefinder
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from timezonefinder import TimezoneFinder


def load_multi_boundary_results():
    """Load the multi-boundary analysis results"""
    with open("multi_boundary_hole_analysis.json") as f:
        return json.load(f)


def analyze_overlapping_patterns(results):
    """Analyze patterns in overlapping zones for edge cases"""

    # Focus on holes with no exact matches but multiple competing boundaries
    edge_cases = [
        hole
        for hole in results
        if hole["exact_matches"] == 0 and len(hole["top_single_matches"]) > 1
    ]

    print(f"\n📊 OVERLAPPING BORDER ANALYSIS")
    print("=" * 60)
    print(f"Total edge cases with overlapping borders: {len(edge_cases)}")

    # Group by parent zone
    by_parent_zone = defaultdict(list)
    for hole in edge_cases:
        by_parent_zone[hole["parent_zone"]].append(hole)

    print(f"\nDistribution by parent timezone:")
    for zone, holes in sorted(by_parent_zone.items()):
        print(f"  {zone}: {len(holes)} holes")

    # Analyze competing zones
    competing_zones = defaultdict(int)
    zone_pairs = defaultdict(int)

    for hole in edge_cases:
        parent = hole["parent_zone"]
        competitors = [match["zone_name"] for match in hole["top_single_matches"]]

        for competitor in competitors:
            competing_zones[competitor] += 1

        # Track zone pairs (parent vs competitor)
        for competitor in competitors:
            pair = tuple(sorted([parent, competitor]))
            zone_pairs[pair] += 1

    print(f"\n🎯 MOST FREQUENT COMPETING ZONES:")
    for zone, count in sorted(
        competing_zones.items(), key=lambda x: x[1], reverse=True
    )[:10]:
        print(f"  {zone}: {count} conflicts")

    print(f"\n🔀 MOST FREQUENT ZONE CONFLICTS:")
    for pair, count in sorted(zone_pairs.items(), key=lambda x: x[1], reverse=True)[
        :10
    ]:
        print(f"  {pair[0]} vs {pair[1]}: {count} conflicts")

    return edge_cases, by_parent_zone, competing_zones, zone_pairs


def calculate_geographic_precedence():
    """Calculate geographic/political precedence rules based on timezone characteristics"""

    # Define timezone categories with precedence levels (lower number = higher precedence)
    precedence_rules = {
        # Political/Administrative zones (highest precedence - more specific)
        "political_high": {
            "precedence": 1,
            "zones": [
                "Asia/Jerusalem",
                "Asia/Gaza",
                "Asia/Hebron",  # Middle East political
                "Europe/Kiev",
                "Europe/Moscow",
                "Europe/Simferopol",  # Eastern Europe
                "Asia/Shanghai",
                "Asia/Urumqi",  # China zones
            ],
            "description": "Specific political/administrative boundaries",
        },
        # Regional timezone zones (medium precedence)
        "regional": {
            "precedence": 2,
            "zones": [
                "Asia/Tokyo",
                "Asia/Manila",
                "Asia/Jakarta",
                "Asia/Kolkata",
                "Asia/Karachi",
                "Asia/Dubai",
                "Asia/Yangon",
                "Asia/Sakhalin",
                "Europe/Paris",
                "Africa/Casablanca",
                "Africa/Johannesburg",
                "America/New_York",
                "America/Los_Angeles",
                "America/Adak",
            ],
            "description": "Major regional timezone centers",
        },
        # GMT offset zones (lowest precedence - generic)
        "gmt_offset": {
            "precedence": 3,
            "zones": [
                "Etc/GMT-12",
                "Etc/GMT-11",
                "Etc/GMT-10",
                "Etc/GMT-9",
                "Etc/GMT-8",
                "Etc/GMT-7",
                "Etc/GMT-6",
                "Etc/GMT-5",
                "Etc/GMT-4",
                "Etc/GMT-3",
                "Etc/GMT-2",
                "Etc/GMT-1",
                "Etc/GMT",
                "Etc/GMT+1",
                "Etc/GMT+2",
                "Etc/GMT+3",
                "Etc/GMT+4",
                "Etc/GMT+5",
                "Etc/GMT+6",
                "Etc/GMT+7",
                "Etc/GMT+8",
                "Etc/GMT+9",
                "Etc/GMT+10",
                "Etc/GMT+11",
                "Etc/GMT+12",
            ],
            "description": "Generic GMT offset zones (fallback)",
        },
    }

    # Create zone -> precedence mapping
    zone_precedence = {}
    for category, info in precedence_rules.items():
        for zone in info["zones"]:
            zone_precedence[zone] = info["precedence"]

    return zone_precedence, precedence_rules


def apply_precedence_rules(edge_cases, zone_precedence):
    """Apply precedence rules to resolve overlapping border conflicts"""

    resolved_cases = []
    unresolved_cases = []

    for hole in edge_cases:
        parent = hole["parent_zone"]
        matches = hole["top_single_matches"]

        if not matches:
            unresolved_cases.append({**hole, "reason": "no_competing_boundaries"})
            continue

        # Get precedence for parent zone
        parent_precedence = zone_precedence.get(parent, 999)  # 999 = unknown zone

        # Find best competing zone based on precedence and score
        best_competitor = None
        best_score = 0
        best_precedence = 999

        for match in matches:
            competitor = match["zone_name"]
            score = match["score"]
            competitor_precedence = zone_precedence.get(competitor, 999)

            # Higher precedence (lower number) wins, break ties with score
            is_better = competitor_precedence < best_precedence or (
                competitor_precedence == best_precedence and score > best_score
            )

            if is_better:
                best_competitor = match
                best_score = score
                best_precedence = competitor_precedence

        # Determine resolution
        if best_competitor is None:
            unresolved_cases.append({**hole, "reason": "no_valid_competitors"})
            continue

        # Apply precedence logic
        competitor_zone = best_competitor["zone_name"]
        competitor_precedence = zone_precedence.get(competitor_zone, 999)

        if competitor_precedence < parent_precedence:
            # Competitor wins (higher precedence)
            resolution = {
                "hole_id": hole["hole_id"],
                "parent_zone": parent,
                "winner": competitor_zone,
                "reason": "precedence_rule",
                "winner_precedence": competitor_precedence,
                "parent_precedence": parent_precedence,
                "winner_score": best_competitor["score"],
                "winner_type": best_competitor["overlap_type"],
            }
            resolved_cases.append(resolution)
        elif competitor_precedence == parent_precedence:
            # Same precedence - use highest score
            if best_score > 0.1:  # Significant overlap threshold
                resolution = {
                    "hole_id": hole["hole_id"],
                    "parent_zone": parent,
                    "winner": competitor_zone,
                    "reason": "score_based",
                    "winner_precedence": competitor_precedence,
                    "parent_precedence": parent_precedence,
                    "winner_score": best_competitor["score"],
                    "winner_type": best_competitor["overlap_type"],
                }
                resolved_cases.append(resolution)
            else:
                # Keep parent zone (low overlap)
                resolution = {
                    "hole_id": hole["hole_id"],
                    "parent_zone": parent,
                    "winner": parent,
                    "reason": "low_overlap_keep_parent",
                    "winner_precedence": parent_precedence,
                    "parent_precedence": parent_precedence,
                    "winner_score": 0,
                    "winner_type": "parent",
                }
                resolved_cases.append(resolution)
        else:
            # Parent wins (higher precedence)
            resolution = {
                "hole_id": hole["hole_id"],
                "parent_zone": parent,
                "winner": parent,
                "reason": "parent_precedence",
                "winner_precedence": parent_precedence,
                "parent_precedence": parent_precedence,
                "winner_score": 0,
                "winner_type": "parent",
            }
            resolved_cases.append(resolution)

    return resolved_cases, unresolved_cases


def analyze_resolution_patterns(resolved_cases):
    """Analyze patterns in the precedence-based resolutions"""

    print(f"\n🎯 PRECEDENCE RESOLUTION ANALYSIS")
    print("=" * 50)

    # Count by resolution reason
    by_reason = Counter(case["reason"] for case in resolved_cases)
    print(f"\nResolution strategies:")
    for reason, count in by_reason.most_common():
        print(f"  {reason}: {count} cases")

    # Count zone changes
    zone_changes = [
        case for case in resolved_cases if case["winner"] != case["parent_zone"]
    ]
    zone_keeps = [
        case for case in resolved_cases if case["winner"] == case["parent_zone"]
    ]

    print(f"\nZone assignment results:")
    print(
        f"  Zone changes: {len(zone_changes)} ({len(zone_changes) / len(resolved_cases) * 100:.1f}%)"
    )
    print(
        f"  Zone preserved: {len(zone_keeps)} ({len(zone_keeps) / len(resolved_cases) * 100:.1f}%)"
    )

    # Analyze zone changes by parent
    parent_changes = defaultdict(list)
    for case in zone_changes:
        parent_changes[case["parent_zone"]].append(case["winner"])

    print(f"\nZone reassignments:")
    for parent, winners in sorted(parent_changes.items()):
        winner_counts = Counter(winners)
        print(f"  {parent} →")
        for winner, count in winner_counts.most_common():
            print(f"    {winner}: {count} holes")


def generate_implementation_strategy(resolved_cases, precedence_rules):
    """Generate implementation strategy for the precedence system"""

    print(f"\n🔧 IMPLEMENTATION STRATEGY")
    print("=" * 50)

    print(f"\n1. PRECEDENCE RULE ENGINE:")
    print(f"   - Define zone categories with precedence levels")
    print(f"   - Political zones (precedence 1): Highest priority")
    print(f"   - Regional zones (precedence 2): Medium priority")
    print(f"   - GMT offset zones (precedence 3): Lowest priority")

    print(f"\n2. CONFLICT RESOLUTION ALGORITHM:")
    print(f"   ```python")
    print(f"   def resolve_hole_zone(hole_bbox, competing_boundaries):")
    print(f"       # 1. Calculate overlap scores for all boundaries")
    print(f"       # 2. Filter boundaries with score > threshold (e.g., 0.01)")
    print(f"       # 3. Apply precedence rules:")
    print(f"       #    - Higher precedence (lower number) wins")
    print(f"       #    - Break ties with overlap score")
    print(f"       #    - Fall back to parent zone if no good match")
    print(f"   ```")

    print(f"\n3. CONFIGURATION APPROACH:")
    print(f"   - Store precedence rules in configuration file")
    print(f"   - Allow runtime override for specific zone pairs")
    print(f"   - Support geographic/political boundary updates")

    print(f"\n4. PERFORMANCE CONSIDERATIONS:")
    print(f"   - Cache precedence lookups")
    print(f"   - Pre-compute common conflict resolutions")
    print(f"   - Minimal impact on normal timezone lookup")

    # Generate specific rule examples
    zone_changes = [
        case for case in resolved_cases if case["winner"] != case["parent_zone"]
    ]

    print(f"\n5. SPECIFIC RULE EXAMPLES (from current data):")
    for case in zone_changes[:5]:
        print(
            f"   Hole {case['hole_id']}: {case['parent_zone']} → {case['winner']} ({case['reason']})"
        )


def main():
    print("🔍 ZONE PRECEDENCE ANALYSIS FOR COMPLEX OVERLAPPING BORDERS")
    print("=" * 70)

    # Load analysis results
    print("Loading multi-boundary analysis results...")
    results = load_multi_boundary_results()

    # Analyze overlapping patterns
    edge_cases, by_parent_zone, competing_zones, zone_pairs = (
        analyze_overlapping_patterns(results)
    )

    # Calculate precedence rules
    zone_precedence, precedence_rules = calculate_geographic_precedence()

    print(f"\n📋 PRECEDENCE RULE CATEGORIES:")
    for category, info in precedence_rules.items():
        print(f"  {category} (precedence {info['precedence']}): {info['description']}")
        print(f"    Example zones: {', '.join(info['zones'][:5])}...")

    # Apply precedence rules
    resolved_cases, unresolved_cases = apply_precedence_rules(
        edge_cases, zone_precedence
    )

    print(f"\n📊 RESOLUTION SUMMARY:")
    print(f"  Total edge cases: {len(edge_cases)}")
    print(f"  Resolved by precedence: {len(resolved_cases)}")
    print(f"  Still unresolved: {len(unresolved_cases)}")

    # Analyze resolution patterns
    if resolved_cases:
        analyze_resolution_patterns(resolved_cases)

    # Generate implementation strategy
    generate_implementation_strategy(resolved_cases, precedence_rules)

    # Save detailed results
    output = {
        "summary": {
            "total_edge_cases": len(edge_cases),
            "resolved_cases": len(resolved_cases),
            "unresolved_cases": len(unresolved_cases),
            "resolution_rate": len(resolved_cases) / len(edge_cases) * 100
            if edge_cases
            else 0,
        },
        "precedence_rules": precedence_rules,
        "zone_precedence_map": zone_precedence,
        "resolved_cases": resolved_cases,
        "unresolved_cases": unresolved_cases,
        "competing_zone_stats": dict(competing_zones),
        "zone_conflict_pairs": {str(k): v for k, v in zone_pairs.items()},
    }

    output_file = "zone_precedence_analysis.json"
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n💾 Detailed results saved to: {os.path.abspath(output_file)}")


if __name__ == "__main__":
    main()
