"""
Parallel computation example: using TimezoneFinder with threading.

Due to significant initialization time, creating a new instance for each lookup is inefficient.
This example shows the recommended pattern:
- Create one TimezoneFinder instance per thread
- Reuse that instance for all lookups within the thread

This balances the cost of initialization with the overhead of a shared global singleton.
"""

import threading
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
    (-0.1278, 51.5074),  # London
    (55.2761, 25.2048),  # Dubai
    (-58.3816, -34.6037),  # Buenos Aires
]


def process_coordinates_in_thread(thread_id, coordinates, results):
    """
    Process a batch of coordinates in a single thread.
    Creates ONE instance per thread and reuses it for all lookups.
    """
    # Create the instance once per thread
    tf = TimezoneFinder(in_memory=True)

    print(f"  Thread {thread_id}: processing {len(coordinates)} coordinates...")
    thread_results = []

    for lng, lat in coordinates:
        # Reuse the same instance for all lookups in this thread
        tz = tf.timezone_at(lng=lng, lat=lat)
        thread_results.append((lng, lat, tz))

    results[thread_id] = thread_results
    print(f"  Thread {thread_id}: completed ✓")


def main():
    num_threads = 3

    # Distribute coordinates among threads
    chunk_size = len(COORDINATES) // num_threads
    chunks = []
    for i in range(num_threads):
        start = i * chunk_size
        end = start + chunk_size if i < num_threads - 1 else len(COORDINATES)
        chunks.append(COORDINATES[start:end])

    print("Parallel processing with instance reuse per thread:")
    print("=" * 60)
    print(f"Processing {len(COORDINATES)} coordinates across {num_threads} threads\n")

    # Create and start threads
    threads = []
    results = [None] * num_threads

    for thread_id, chunk in enumerate(chunks):
        thread = threading.Thread(
            target=process_coordinates_in_thread,
            args=(thread_id, chunk, results),
        )
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Display results
    print("\nResults from all threads:")
    print("-" * 60)
    for thread_id, thread_results in enumerate(results):
        print(f"\nThread {thread_id}:")
        for lng, lat, tz in thread_results:
            print(f"  ({lng:9.4f}, {lat:9.4f}) -> {tz}")

    print("\n✓ All threads completed successfully")


if __name__ == "__main__":
    main()
