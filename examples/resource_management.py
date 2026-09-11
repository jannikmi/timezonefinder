"""
Resource management example: proper cleanup of TimezoneFinder instances.

Prefer a context manager for bounded work. Keep one instance for the lifetime of a
service or worker and call cleanup() during its orderly shutdown.
"""

from timezonefinder import TimezoneFinder


def example_1_context_manager():
    """Method 1: context manager (recommended for bounded work)."""
    print("Method 1: Context manager (recommended)")
    print("-" * 60)

    with TimezoneFinder(in_memory=True) as tf:
        tz = tf.timezone_at(lng=13.358, lat=52.5061)
        print(f"Berlin timezone: {tz}")
    print("Cleanup ran at block exit\n")


def example_2_exception_safety():
    """Method 2: cleanup also runs when work raises."""
    print("Method 2: Exception-safe cleanup")
    print("-" * 60)

    try:
        with TimezoneFinder(in_memory=True) as tf:
            print(tf.timezone_at(lng=13.358, lat=52.5061))
            raise ValueError("the job failed")
    except ValueError as e:
        print(f"Exception occurred: {e}")
    print("Cleanup ran and the exception still propagated\n")


def example_3_application_owned_lifetime():
    """Method 3: explicit shutdown for a long-lived application."""
    print("Method 3: Application-owned lifetime")
    print("-" * 60)

    tf = TimezoneFinder(in_memory=True)
    try:
        # A real service would reuse this instance for all work until shutdown.
        print(tf.timezone_at(lng=13.358, lat=52.5061))
    finally:
        tf.cleanup()
    print("Cleanup ran during orderly shutdown\n")


def main():
    print("\n" + "=" * 60)
    print("RESOURCE MANAGEMENT EXAMPLES")
    print("=" * 60 + "\n")

    example_1_context_manager()
    example_2_exception_safety()
    example_3_application_owned_lifetime()

    print("=" * 60)
    print("RECOMMENDATIONS")
    print("=" * 60)
    print("""
1. For scripts, jobs, and bounded batches:
   Use a context manager for deterministic, exception-safe cleanup.

2. For long-running applications:
   Keep one instance alive, reuse it, and call cleanup() during shutdown.

3. Do not use del for resource management:
   It removes one reference but does not express or guarantee timely cleanup.

4. For thread-safe parallel processing:
   Create one instance per worker and clean it up when the worker exits.

The context manager makes ownership visible and closes mapped coordinate files even
when an operation raises. It must not be used again after its with block exits.
""")


if __name__ == "__main__":
    main()
