"""
Resource management example: proper cleanup of TimezoneFinder instances.

This demonstrates different ways to manage instance lifecycle and ensure
proper cleanup of resources.
"""

from timezonefinder import TimezoneFinder


def example_1_manual_cleanup():
    """Method 1: Manual cleanup with del statement."""
    print("Method 1: Manual cleanup with 'del'")
    print("-" * 60)

    tf = TimezoneFinder(in_memory=True)
    tz = tf.timezone_at(lng=13.358, lat=52.5061)
    print(f"Berlin timezone: {tz}")

    # Manually delete to trigger cleanup (optional but good practice)
    del tf
    print("Instance deleted\n")


def example_2_context_manager():
    """Method 2: Context manager (automatic cleanup)."""
    print("Method 2: Context manager (recommended)")
    print("-" * 60)

    # Using 'with' statement ensures cleanup happens automatically
    with TimezoneFinder(in_memory=True) as tf:
        tz = tf.timezone_at(lng=13.358, lat=52.5061)
        print(f"Berlin timezone: {tz}")
    # Cleanup happens automatically when exiting the 'with' block
    print("Cleanup automatic\n")


def example_3_batch_with_context_manager():
    """Method 3: Batch processing with context manager."""
    print("Method 3: Batch processing with context manager")
    print("-" * 60)

    coordinates = [
        (13.358, 52.5061),  # Berlin
        (2.3522, 48.8566),  # Paris
        (-74.0060, 40.7128),  # New York
    ]

    # Create instance once and reuse it
    with TimezoneFinder(in_memory=True) as tf:
        for lng, lat in coordinates:
            tz = tf.timezone_at(lng=lng, lat=lat)
            print(f"  ({lng:9.4f}, {lat:9.4f}) -> {tz}")
    # Cleanup happens automatically when exiting the 'with' block
    print("Cleanup automatic\n")


def example_4_exception_safety():
    """Method 4: Exception safety with context manager."""
    print("Method 4: Exception safety with context manager")
    print("-" * 60)

    try:
        with TimezoneFinder(in_memory=True) as tf:
            # Even if an exception occurs...
            tz = tf.timezone_at(lng=13.358, lat=52.5061)
            print(f"Berlin timezone: {tz}")
            # ... cleanup still happens automatically
    except Exception as e:
        print(f"Exception occurred: {e}")
    finally:
        print("Cleanup happened even though exception occurred\n")


def main():
    print("\n" + "=" * 60)
    print("RESOURCE MANAGEMENT EXAMPLES")
    print("=" * 60 + "\n")

    example_1_manual_cleanup()
    example_2_context_manager()
    example_3_batch_with_context_manager()
    example_4_exception_safety()

    print("=" * 60)
    print("RECOMMENDATIONS")
    print("=" * 60)
    print("""
1. For simple scripts and batch processing:
   Use context manager (with statement) for automatic cleanup

2. For long-running applications:
   Keep instance alive and reuse it (cleanup on shutdown)

3. For libraries/packages:
   Use context manager to avoid resource leaks

4. For thread-safe parallel processing:
   Create one instance per thread and clean up after thread exits

Key benefit: Context managers ensure cleanup even if exceptions occur.
""")


if __name__ == "__main__":
    main()
