"""
Test script for demonstrating the new global functions in timezonefinder
"""

from timezonefinder import timezone_at, TimezoneFinder


def main():
    # Using the global function
    test_lng, test_lat = 13.358, 52.5061  # Berlin

    print("Using global function:")
    tz_global = timezone_at(lng=test_lng, lat=test_lat)
    print(f"Timezone at ({test_lng}, {test_lat}): {tz_global}")

    # Using an instance for comparison
    print("\nUsing instance method:")
    tf = TimezoneFinder()
    tz_instance = tf.timezone_at(lng=test_lng, lat=test_lat)
    print(f"Timezone at ({test_lng}, {test_lat}): {tz_instance}")

    print("\nResults match:", tz_global == tz_instance)


if __name__ == "__main__":
    main()
