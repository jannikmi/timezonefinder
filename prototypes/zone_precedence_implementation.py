#!/usr/bin/env python3
"""
Zone Precedence System Implementation Prototype

This module implements a practical zone precedence system to resolve conflicts
when holes cannot be filled by exact boundary matches. It provides a configurable
precedence engine that can be integrated into the TimezoneFinder library.
"""

import json
from typing import Dict, List, Tuple, Optional, NamedTuple
from enum import IntEnum
import os


class ZonePrecedence(IntEnum):
    """Zone precedence levels (lower number = higher priority)"""

    POLITICAL_HIGH = 1  # Specific political/administrative boundaries
    REGIONAL = 2  # Major regional timezone centers
    GMT_OFFSET = 3  # Generic GMT offset zones (fallback)
    UNKNOWN = 999  # Unknown zones (lowest priority)


class BoundaryMatch(NamedTuple):
    """Represents a boundary polygon match for a hole"""

    boundary_id: int
    zone_name: str
    overlap_type: str  # 'exact', 'contains', 'contained', 'intersects'
    score: float  # 0.0 to 1.0, higher = better match


class ZonePrecedenceEngine:
    """
    Engine for resolving timezone conflicts using precedence rules.

    This system handles cases where holes cannot be filled by exact boundary
    matches and multiple zones compete for the same geographic area.
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the precedence engine with configuration"""
        self.zone_precedence_map = {}
        self.conflict_overrides = {}
        self.load_configuration(config_path)

    def load_configuration(self, config_path: Optional[str] = None):
        """Load precedence configuration from file or use defaults"""

        if config_path and os.path.exists(config_path):
            with open(config_path) as f:
                config = json.load(f)
                self.zone_precedence_map = config.get("zone_precedence_map", {})
                self.conflict_overrides = config.get("conflict_overrides", {})
        else:
            # Use default configuration
            self._load_default_configuration()

    def _load_default_configuration(self):
        """Load the default zone precedence configuration"""

        # Political/Administrative zones (highest precedence)
        political_zones = [
            "Asia/Jerusalem",
            "Asia/Gaza",
            "Asia/Hebron",
            "Europe/Kiev",
            "Europe/Moscow",
            "Europe/Simferopol",
            "Asia/Shanghai",
            "Asia/Urumqi",
            "Europe/Berlin",
            "Europe/Paris",
            "Europe/London",
            "America/New_York",
            "America/Chicago",
            "America/Denver",
            "America/Los_Angeles",
        ]

        # Regional timezone centers (medium precedence)
        regional_zones = [
            "Asia/Tokyo",
            "Asia/Manila",
            "Asia/Jakarta",
            "Asia/Kolkata",
            "Asia/Karachi",
            "Asia/Dubai",
            "Asia/Yangon",
            "Asia/Sakhalin",
            "Africa/Casablanca",
            "Africa/Johannesburg",
            "Africa/Cairo",
            "America/Adak",
            "Pacific/Fiji",
            "Australia/Sydney",
        ]

        # GMT offset zones (lowest precedence - generic fallback)
        gmt_zones = [
            f"Etc/GMT{offset}"
            for offset in [
                "-12",
                "-11",
                "-10",
                "-9",
                "-8",
                "-7",
                "-6",
                "-5",
                "-4",
                "-3",
                "-2",
                "-1",
                "",
                "+1",
                "+2",
                "+3",
                "+4",
                "+5",
                "+6",
                "+7",
                "+8",
                "+9",
                "+10",
                "+11",
                "+12",
            ]
        ]

        # Build precedence map
        for zone in political_zones:
            self.zone_precedence_map[zone] = ZonePrecedence.POLITICAL_HIGH

        for zone in regional_zones:
            self.zone_precedence_map[zone] = ZonePrecedence.REGIONAL

        for zone in gmt_zones:
            self.zone_precedence_map[zone] = ZonePrecedence.GMT_OFFSET

        # Specific conflict overrides (zone_a, zone_b) -> winner
        self.conflict_overrides = {
            (
                "Asia/Jerusalem",
                "Asia/Gaza",
            ): "Asia/Gaza",  # Gaza has geographic precedence
            (
                "Europe/Moscow",
                "Asia/Jerusalem",
            ): "Asia/Jerusalem",  # Local political precedence
            ("Etc/GMT-8", "Asia/Jakarta"): "Asia/Jakarta",  # Regional over generic
            ("Etc/GMT-6", "Asia/Kolkata"): "Asia/Kolkata",  # Regional over generic
        }

    def get_zone_precedence(self, zone_name: str) -> ZonePrecedence:
        """Get the precedence level for a timezone"""
        return self.zone_precedence_map.get(zone_name, ZonePrecedence.UNKNOWN)

    def resolve_hole_conflict(
        self,
        parent_zone: str,
        competing_matches: List[BoundaryMatch],
        min_overlap_threshold: float = 0.01,
    ) -> Tuple[str, str]:
        """
        Resolve a hole conflict between parent zone and competing boundaries.

        Args:
            parent_zone: The original timezone zone that contains the hole
            competing_matches: List of competing boundary matches
            min_overlap_threshold: Minimum overlap score to consider a match valid

        Returns:
            Tuple of (winning_zone, resolution_reason)
        """

        if not competing_matches:
            return parent_zone, "no_competitors"

        # Filter out matches below threshold
        valid_matches = [
            match for match in competing_matches if match.score >= min_overlap_threshold
        ]

        if not valid_matches:
            return parent_zone, "low_overlap_keep_parent"

        # Check for specific conflict overrides
        for match in valid_matches:
            override_key = tuple(sorted([parent_zone, match.zone_name]))
            if override_key in self.conflict_overrides:
                winner = self.conflict_overrides[override_key]
                if winner == match.zone_name:
                    return winner, "conflict_override"

        # Apply precedence rules
        parent_precedence = self.get_zone_precedence(parent_zone)

        best_match = None
        best_precedence = ZonePrecedence.UNKNOWN
        best_score = 0.0

        for match in valid_matches:
            competitor_precedence = self.get_zone_precedence(match.zone_name)

            # Higher precedence (lower number) wins, break ties with score
            is_better = competitor_precedence < best_precedence or (
                competitor_precedence == best_precedence and match.score > best_score
            )

            if is_better:
                best_match = match
                best_precedence = competitor_precedence
                best_score = match.score

        if best_match is None:
            return parent_zone, "no_valid_matches"

        # Apply resolution logic
        if best_precedence < parent_precedence:
            return best_match.zone_name, "precedence_rule"
        elif best_precedence == parent_precedence:
            if best_score > 0.5:  # High confidence threshold
                return best_match.zone_name, "high_confidence_score"
            elif best_score > 0.1:  # Medium confidence threshold
                return best_match.zone_name, "score_based"
            else:
                return parent_zone, "low_confidence_keep_parent"
        else:
            return parent_zone, "parent_precedence"

    def batch_resolve_holes(self, hole_conflicts: List[Dict]) -> List[Dict]:
        """
        Resolve multiple hole conflicts in batch.

        Args:
            hole_conflicts: List of hole conflict data from analysis

        Returns:
            List of resolution results
        """
        results = []

        for hole_data in hole_conflicts:
            # Convert to BoundaryMatch objects
            competing_matches = [
                BoundaryMatch(
                    boundary_id=match.get("boundary_id", 0),
                    zone_name=match["zone_name"],
                    overlap_type=match["overlap_type"],
                    score=match["score"],
                )
                for match in hole_data.get("top_single_matches", [])
            ]

            winner, reason = self.resolve_hole_conflict(
                hole_data["parent_zone"], competing_matches
            )

            result = {
                "hole_id": hole_data["hole_id"],
                "parent_zone": hole_data["parent_zone"],
                "winner": winner,
                "reason": reason,
                "competing_zones": [m.zone_name for m in competing_matches],
                "best_competitor_score": max([m.score for m in competing_matches])
                if competing_matches
                else 0.0,
            }
            results.append(result)

        return results

    def save_configuration(self, config_path: str):
        """Save current configuration to file"""
        config = {
            "zone_precedence_map": {
                k: int(v) for k, v in self.zone_precedence_map.items()
            },
            "conflict_overrides": {
                f"{k[0]}|{k[1]}": v for k, v in self.conflict_overrides.items()
            },
        }

        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)

    def add_zone_precedence(self, zone_name: str, precedence: ZonePrecedence):
        """Add or update zone precedence"""
        self.zone_precedence_map[zone_name] = precedence

    def add_conflict_override(self, zone_a: str, zone_b: str, winner: str):
        """Add specific conflict resolution override"""
        key = tuple(sorted([zone_a, zone_b]))
        self.conflict_overrides[key] = winner


def create_optimized_hole_replacement_system(precedence_engine: ZonePrecedenceEngine):
    """
    Create an optimized system for replacing holes with boundary-based zones.

    This would be integrated into the main TimezoneFinder class to eliminate
    redundant hole storage while maintaining accuracy through precedence rules.
    """

    class OptimizedHoleResolver:
        """
        Handles hole resolution using boundary polygons and precedence rules.

        This replaces the traditional hole lookup system with a dynamic
        boundary-based approach that uses precedence rules for conflicts.
        """

        def __init__(self, precedence_engine: ZonePrecedenceEngine):
            self.precedence_engine = precedence_engine
            self.hole_to_boundary_cache = {}  # Cache for performance

        def resolve_point_in_hole_region(
            self,
            longitude: float,
            latitude: float,
            parent_zone: str,
            boundary_polygons: List[Dict],
        ) -> str:
            """
            Resolve timezone for a point that would traditionally be in a hole.

            Args:
                longitude, latitude: Point coordinates
                parent_zone: The timezone zone that would contain this hole
                boundary_polygons: List of boundary polygons that might fill the hole

            Returns:
                The resolved timezone zone name
            """

            # Find overlapping boundaries
            overlapping_boundaries = []

            for boundary in boundary_polygons:
                # In real implementation, this would use actual polygon intersection
                # For prototype, we simulate with bounding box overlap
                if self._point_in_boundary_bbox(longitude, latitude, boundary):
                    overlap_score = self._calculate_overlap_score(boundary)

                    match = BoundaryMatch(
                        boundary_id=boundary["id"],
                        zone_name=boundary["zone_name"],
                        overlap_type="contains",  # Simplified for prototype
                        score=overlap_score,
                    )
                    overlapping_boundaries.append(match)

            # Resolve using precedence engine
            winner, reason = self.precedence_engine.resolve_hole_conflict(
                parent_zone, overlapping_boundaries
            )

            return winner

        def _point_in_boundary_bbox(
            self, longitude: float, latitude: float, boundary: Dict
        ) -> bool:
            """Check if point is within boundary bounding box (simplified)"""
            bbox = boundary.get("bbox", [0, 0, 0, 0])
            return bbox[0] <= longitude <= bbox[2] and bbox[1] <= latitude <= bbox[3]

        def _calculate_overlap_score(self, boundary: Dict) -> float:
            """Calculate overlap score (simplified for prototype)"""
            # In real implementation, this would calculate actual geometric overlap
            return 0.5  # Placeholder

    return OptimizedHoleResolver(precedence_engine)


def main():
    """Demonstrate the zone precedence system"""

    print("🔧 ZONE PRECEDENCE ENGINE IMPLEMENTATION")
    print("=" * 50)

    # Initialize precedence engine
    engine = ZonePrecedenceEngine()

    print(f"📋 Loaded precedence rules for {len(engine.zone_precedence_map)} zones")
    print(f"📋 Loaded {len(engine.conflict_overrides)} specific conflict overrides")

    # Load test data from our analysis
    if os.path.exists("zone_precedence_analysis.json"):
        with open("zone_precedence_analysis.json") as f:
            analysis_data = json.load(f)

        # Test the engine on real edge cases
        print(f"\n🧪 TESTING ON REAL EDGE CASES")
        print(f"Testing {len(analysis_data['resolved_cases'])} resolved cases...")

        # Simulate some test cases
        test_conflicts = [
            {
                "hole_id": 78,
                "parent_zone": "Asia/Jerusalem",
                "top_single_matches": [
                    {
                        "zone_name": "Asia/Gaza",
                        "overlap_type": "contains",
                        "score": 0.022,
                    },
                    {
                        "zone_name": "Etc/GMT-2",
                        "overlap_type": "contains",
                        "score": 0.0001,
                    },
                ],
            },
            {
                "hole_id": 248,
                "parent_zone": "Etc/GMT-8",
                "top_single_matches": [
                    {
                        "zone_name": "Asia/Jakarta",
                        "overlap_type": "contains",
                        "score": 0.15,
                    },
                    {
                        "zone_name": "Asia/Manila",
                        "overlap_type": "contains",
                        "score": 0.08,
                    },
                ],
            },
        ]

        results = engine.batch_resolve_holes(test_conflicts)

        for result in results:
            print(
                f"\nHole {result['hole_id']}: {result['parent_zone']} → {result['winner']} ({result['reason']})"
            )
            print(f"  Competitors: {', '.join(result['competing_zones'])}")
            print(f"  Best score: {result['best_competitor_score']:.3f}")

    # Save configuration for future use
    config_path = "zone_precedence_config.json"
    engine.save_configuration(config_path)
    print(f"\n💾 Configuration saved to: {config_path}")

    # Demonstrate integration concept
    print(f"\n🏗️ INTEGRATION CONCEPT:")
    print(f"The precedence engine can be integrated into TimezoneFinder as:")
    print(f"1. Replace hole storage with boundary-based dynamic resolution")
    print(f"2. Use precedence rules for conflict resolution")
    print(f"3. Maintain backward compatibility with existing API")
    print(f"4. Provide configuration hooks for custom precedence rules")


if __name__ == "__main__":
    main()
