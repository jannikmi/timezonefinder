#!/usr/bin/env python3
"""
Convert the distance analysis results to coordinate degrees for better interpretation.
"""

# From timezonefinder config
DECIMAL_PLACES_SHIFT = 7
INT2COORD_FACTOR = 10 ** (-DECIMAL_PLACES_SHIFT)  # 0.0000001


def convert_distances():
    """Convert key distances from integer units to coordinate degrees."""

    # Key distances from the analysis
    distances = {
        "Asia/Jerusalem closest match range": (14_926_435, 19_490_431),
        "Asia/Manila closest match": (1_708_205, 1_708_205),
        "Etc/GMT-8 closest match": (16_665_897, 16_665_897),
        "Etc/GMT-6 closest match": (5_687_242, 5_687_242),
        # Distance thresholds used in analysis
        "Very close threshold": (1_000, 1_000),
        "Close threshold": (10_000, 10_000),
        "Moderate threshold": (100_000, 100_000),
        # Sample specific distances
        "Asia/Jerusalem hole 78 → Asia/Gaza": (17_231_202, 17_231_202),
        "Etc/GMT-6 hole 275 → Asia/Kolkata": (5_687_242, 5_687_242),
    }

    print("DISTANCE CONVERSION TABLE")
    print("=" * 80)
    print(
        f"{'Description':<40} {'Integer Units':<15} {'Degrees':<10} {'Geographic Context'}"
    )
    print("-" * 80)

    for desc, (min_val, max_val) in distances.items():
        min_deg = min_val * INT2COORD_FACTOR
        max_deg = max_val * INT2COORD_FACTOR

        if min_val == max_val:
            unit_str = f"{min_val:,}"
            deg_str = f"{min_deg:.4f}°"
        else:
            unit_str = f"{min_val:,}-{max_val:,}"
            deg_str = f"{min_deg:.4f}°-{max_deg:.4f}°"

        # Add geographic context
        avg_deg = (min_deg + max_deg) / 2
        if avg_deg < 0.001:
            context = "Sub-kilometer precision"
        elif avg_deg < 0.01:
            context = "City-level precision"
        elif avg_deg < 0.1:
            context = "Regional precision"
        elif avg_deg < 1.0:
            context = "Country-level precision"
        else:
            context = "Continental-level distances"

        print(f"{desc:<40} {unit_str:<15} {deg_str:<10} {context}")

    print("\n" + "=" * 80)
    print("INTERPRETATION")
    print("=" * 80)

    print("\nDistance Categories:")
    print(
        "• Very close (≤0.0001°): Sub-kilometer differences - likely coordinate precision issues"
    )
    print(
        "• Close (≤0.001°): City-block level differences - possible data alignment issues"
    )
    print(
        "• Moderate (≤0.01°): City-level differences - might be substitutable with tolerance"
    )
    print("• Distant (>0.01°): Regional+ differences - genuine geometric differences")

    print("\nKey Insights:")
    print("• All unmatched holes fall in 'Distant' category (>0.01° = >100k units)")
    print("• Asia/Jerusalem holes: 1.5°-1.9° gaps (150+ km distances)")
    print("• Smallest gap is Asia/Manila → Asia/Tokyo: 0.17° (~19 km)")
    print("• These distances confirm legitimate geometric edge cases")

    print("\nGeographic Context:")
    print("• 1° ≈ 111 km at equator")
    print("• 0.1° ≈ 11 km")
    print("• 0.01° ≈ 1.1 km")
    print("• 0.001° ≈ 110 m")


if __name__ == "__main__":
    convert_distances()
