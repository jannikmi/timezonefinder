"""
Parallel computation example: using TimezoneFinder with multiprocessing.

Due to significant initialization time, creating a new instance for each lookup is inefficient.
This example shows the CORRECT pattern with guaranteed process isolation:
- Each worker process is a SEPARATE Python interpreter with its OWN memory space
- Each worker initializes ONE TimezoneFinder instance (via initializer function)
- The instance is stored as a global variable in that worker's memory space
- All lookups in that process reuse the same instance
- NO sharing between processes - each instance is completely independent

This pattern is safe and efficient for parallel workloads because:
1. Multiprocessing uses separate processes (not threads), so no race conditions
2. Each process has its own Python interpreter and memory
3. The initializer ensures each process initializes exactly once
4. The global variable in each process is isolated to that process only

This properly amortizes initialization cost across all coordinates processed by each worker.
"""

from multiprocessing import Pool
from timezonefinder import TimezoneFinder


# Sample data to process
COORDINATES = [
    (13.358, 52.5061),  # Berlin
    (2.3522, 48.8566),  # Paris
    (-74.0060, 40.7128),  # New York
    (139.6917, 35.6895),  # Tokyo
    (-43.1729, -22.9068),  # Rio de Janeiro
    (151.2093, -33.8688),  # Sydney
    (116.4074, 39.9042),  # Beijing
    (-51.5074, -0.1278),  # London
    (55.2761, 25.2048),  # Dubai
    (-58.3816, -34.6037),  # Buenos Aires
]

# Global variable in EACH worker process (completely independent instances)
# NOTE: This is NOT a shared global - each worker process has its own copy
tf = None


def initialize_worker():
    """
    Initialize a TimezoneFinder instance for this worker process.

    GUARANTEED BEHAVIOR:
    - Called exactly once per worker process at startup
    - Each call happens in a SEPARATE Python interpreter with its OWN memory space
    - The global tf variable is isolated to that specific process
    - Changes to tf in one worker do NOT affect other workers

    This is the key difference from threading: processes have isolated memory.
    """
    global tf
    tf = TimezoneFinder(in_memory=True)


def lookup_timezone(coord):
    """
    Lookup timezone for a single coordinate.
    Reuses the TimezoneFinder instance created in initialize_worker.

    Each invocation uses the instance from its own worker process.
    No coordination or locking needed - each process has its own instance.
    """
    lng, lat = coord
    # Use the instance initialized once per worker process (guaranteed independent)
    tz = tf.timezone_at(lng=lng, lat=lat)
    return lng, lat, tz


def main():
    num_processes = 3

    print("Parallel processing with multiprocessing (correct pattern):")
    print("=" * 60)
    print(
        f"Processing {len(COORDINATES)} coordinates across {num_processes} processes\n"
    )

    # Create pool with initializer function
    # GUARANTEE: Each of the 3 worker processes will:
    #   1. Get its own Python interpreter
    #   2. Get its own memory space
    #   3. Call initialize_worker() exactly once
    #   4. Have its own independent TimezoneFinder instance
    #   5. Reuse that instance for all lookups assigned to it
    #
    # There is NO sharing between processes - this is completely safe!
    with Pool(processes=num_processes, initializer=initialize_worker) as pool:
        # map() applies lookup_timezone to each coordinate
        # Each worker reuses its own independent instance for lookups
        # No race conditions, no locks needed - processes have isolated memory
        results = pool.map(lookup_timezone, COORDINATES)

    # Display results
    print("Results from parallel processes:")
    print("-" * 60)
    for lng, lat, tz in results:
        print(f"({lng:9.4f}, {lat:9.4f}) -> {tz}")

    print("\n✓ Parallel processing completed successfully")
    print(
        "✓ Each worker has its OWN independent instance (guaranteed by multiprocessing)"
    )
    print("✓ Each worker initialized once and reused for all lookups")


if __name__ == "__main__":
    main()
