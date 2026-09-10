"""
Test script for demonstrating the new global functions in timezonefinder
"""

from timezonefinder import timezone_at, TimezoneFinder


test_lng, test_lat = 13.358, 52.5061  # coordinates of Berlin

# Using the global function
tz_global = timezone_at(lng=test_lng, lat=test_lat)

# Reuse a class instance for the bounded job; it is cleaned up at block exit.
with TimezoneFinder(in_memory=True) as tf:
    tz_instance = tf.timezone_at(lng=test_lng, lat=test_lat)

print(f"Timezone at ({test_lng}, {test_lat}):")
print("global function:", tz_global)
print("instance method:", tz_instance)
