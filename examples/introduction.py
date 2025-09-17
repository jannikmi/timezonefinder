"""
Test script for demonstrating the new global functions in timezonefinder
"""

from timezonefinder import timezone_at, TimezoneFinder


test_lng, test_lat = 13.358, 52.5061  # coordinates of Berlin

# Using the global function
tz_global = timezone_at(lng=test_lng, lat=test_lat)

# Using a class instance for increased control and thread safety
tf = TimezoneFinder(in_memory=True)  # Load data into memory for faster access
tz_instance = tf.timezone_at(lng=test_lng, lat=test_lat)
# delete the instance after use to free resources
del tf

# use a context manager to ensure proper cleanup
with TimezoneFinder(in_memory=True) as tf:
    tz_context = tf.timezone_at(lng=test_lng, lat=test_lat)

print(f"Timezone at ({test_lng}, {test_lat}):")
print("global function:", tz_global)
print("instance method:", tz_instance)
print("context manager:", tz_context)
