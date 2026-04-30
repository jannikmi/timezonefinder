"""
Batch processing example: reusing a TimezoneFinder instance for many lookups.

This demonstrates the recommended pattern for processing multiple coordinates.
Due to significant initialization time, it is inefficient to create a new instance
for each lookup. Instead, create one instance and reuse it for all lookups.
"""

from timezonefinder import TimezoneFinder


def main():
    # Create the instance once
    tf = TimezoneFinder(in_memory=True)

    # Process many coordinates using the same instance
    coordinates = [
        (13.358, 52.5061),  # Berlin
        (2.3522, 48.8566),  # Paris
        (-74.0060, 40.7128),  # New York
        (139.6917, 35.6895),  # Tokyo
        (-43.1729, -22.9068),  # Rio de Janeiro
        (151.2093, -33.8688),  # Sydney
        (0.0, 0.0),  # Null Island
    ]

    print("Batch processing with a single reused instance:")
    print("=" * 60)

    for lng, lat in coordinates:
        tz = tf.timezone_at(lng=lng, lat=lat)
        print(f"({lng:9.4f}, {lat:9.4f}) -> {tz}")

    print("\n✓ Efficiently processed all coordinates with a single instance")


if __name__ == "__main__":
    main()
