"""
Tests for the global functions in timezonefinder
"""

import pytest
import threading
from concurrent.futures import ThreadPoolExecutor

from tests.auxiliaries import single_location_test
from tests.locations import BASIC_TEST_LOCATIONS, TEST_LOCATIONS_AT_LAND, TEST_LOCATIONS
from timezonefinder import (
    TimezoneFinder,
    certain_timezone_at,
    get_geometry,
    timezone_at,
    timezone_at_land,
    unique_timezone_at,
)
from timezonefinder.configs import DEFAULT_DATA_DIR
from timezonefinder.zone_names import read_zone_names
from timezonefinder import global_functions

# Load all timezone names for parameterization
all_timezone_names = read_zone_names(DEFAULT_DATA_DIR)

FUNC2TEST_CASES = {
    timezone_at: TEST_LOCATIONS,
    certain_timezone_at: TEST_LOCATIONS,
    unique_timezone_at: BASIC_TEST_LOCATIONS,
    timezone_at_land: TEST_LOCATIONS_AT_LAND,
}


@pytest.fixture(scope="session")
def timezonefinder_instance() -> TimezoneFinder:
    """Provide a single, reusable TimezoneFinder instance for all tests.

    Using in_memory=True avoids repeated disk I/O and initialization overhead
    while preserving the behaviour of the public API.
    """
    return TimezoneFinder(in_memory=True)


# Create parameterized test data from FUNC2TEST_CASES mapping
def create_test_params():
    """Create test parameters from FUNC2TEST_CASES mapping"""
    params = []
    ids = []
    for func, test_cases in FUNC2TEST_CASES.items():
        for lat, lng, description, expected in test_cases:
            params.append((func, lat, lng, description, expected))
            ids.append(f"{func.__name__}-{description}")
    return params, ids


# Generate test parameters and IDs once
TEST_PARAMS, TEST_IDS = create_test_params()


@pytest.mark.unit
class TestGlobalFunctions:
    """Test the global functions that use the global TimezoneFinder instance"""

    @pytest.mark.parametrize(
        "func, lat, lng, description, expected", TEST_PARAMS, ids=TEST_IDS
    )
    def test_global_functions_parameterized(
        self, func, lat, lng, description, expected
    ):
        """Test global functions with their respective test cases defined in FUNC2TEST_CASES"""
        single_location_test(func, lat, lng, description, expected)

    @pytest.mark.slow
    @pytest.mark.parametrize("tz_name", all_timezone_names)
    def test_get_geometry(self, tz_name, timezonefinder_instance: TimezoneFinder):
        """Test the global get_geometry function for all timezones"""
        expected = timezonefinder_instance.get_geometry(tz_name=tz_name)
        result = get_geometry(tz_name=tz_name)
        assert isinstance(result, type(expected)), (
            f"Type mismatch for {tz_name}: {type(result)} != {type(expected)}"
        )
        assert len(result) == len(expected), (
            f"Length mismatch for {tz_name}: {len(result)} != {len(expected)}"
        )


@pytest.mark.unit
class TestGlobalFunctionsThreadSafety:
    """Test thread safety of global functions and singleton initialization"""

    def test_singleton_instance_accessed_safely(self):
        """Test that _get_tf_instance returns a valid instance"""
        # Reset the singleton to test initialization
        global_functions.TF_INSTANCE = None

        instance = global_functions._get_tf_instance()
        assert instance is not None
        assert isinstance(instance, TimezoneFinder)

    def test_singleton_returns_same_instance(self):
        """Test that _get_tf_instance always returns the same instance"""
        # Reset to test singleton behavior
        global_functions.TF_INSTANCE = None

        instance1 = global_functions._get_tf_instance()
        instance2 = global_functions._get_tf_instance()
        instance3 = global_functions._get_tf_instance()

        # All calls should return the exact same object
        assert instance1 is instance2
        assert instance2 is instance3

    def test_concurrent_initialization_creates_single_instance(self):
        """Test that concurrent calls to _get_tf_instance result in a single instance.

        This test verifies that the double-checked locking implementation works correctly
        and only one TimezoneFinder instance is created even with multiple threads
        trying to initialize simultaneously.
        """
        # Reset singleton before test
        global_functions.TF_INSTANCE = None
        results = []

        def get_instance_thread_safe():
            """Worker function to get the singleton instance from a thread"""
            instance = global_functions._get_tf_instance()
            results.append(instance)

        num_threads = 10

        # Create and start threads that will all try to get the instance
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(get_instance_thread_safe) for _ in range(num_threads)
            ]
            # Wait for all threads to complete
            _ = [f.result() for f in futures]

        # All results should be the exact same instance object
        assert len(results) == num_threads
        assert all(results[0] is r for r in results), (
            "Concurrent initialization should return the same instance to all threads"
        )

        # Verify it's actually a TimezoneFinder
        assert isinstance(results[0], TimezoneFinder)

    def test_concurrent_global_function_calls(self):
        """Test that multiple threads can safely call global functions concurrently.

        This verifies that the global functions are thread-safe for concurrent
        read operations on a shared singleton instance.
        """
        # Use a well-known location for testing
        test_coords = [
            (13.4, 52.5),  # Berlin
            (-74.0, 40.7),  # New York
            (139.7, 35.7),  # Tokyo
            (2.3, 48.9),  # Paris
            (151.2, -33.9),  # Sydney
        ]

        results = []
        lock = threading.Lock()

        def call_global_function(lng, lat):
            """Worker function to call timezone_at from a thread"""
            tz = timezone_at(lng=lng, lat=lat)
            with lock:
                results.append((lng, lat, tz))

        # Create threads that call global functions with different parameters
        threads = []
        for lng, lat in test_coords * 2:  # 10 total calls, some duplicates
            t = threading.Thread(target=call_global_function, args=(lng, lat))
            threads.append(t)

        # Start all threads
        for t in threads:
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # Verify all calls completed successfully
        assert len(results) == 10

        # Verify timezone results are valid (non-None for these land locations)
        for lng, lat, tz in results:
            assert tz is not None, (
                f"timezone_at({lng}, {lat}) returned None unexpectedly"
            )

    @pytest.mark.parametrize("num_threads", [5, 10, 20])
    def test_concurrent_reads_with_variable_thread_count(self, num_threads):
        """Test concurrent reads with different thread counts.

        Verify that the singleton instance handles high concurrency correctly.
        """
        results = []
        lock = threading.Lock()

        def concurrent_lookup(thread_id):
            """Worker function for concurrent timezone lookup"""
            # Each thread does multiple lookups
            tz = timezone_at(lng=13.4, lat=52.5)
            with lock:
                results.append((thread_id, tz))

        # Create and run threads
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(concurrent_lookup, i) for i in range(num_threads)
            ]
            _ = [f.result() for f in futures]

        # Verify all lookups completed
        assert len(results) == num_threads

        # Verify all results are consistent
        expected_tz = "Europe/Berlin"
        for thread_id, tz in results:
            assert tz == expected_tz, (
                f"Thread {thread_id} got {tz} instead of {expected_tz}"
            )

    def test_singleton_state_consistency_after_concurrent_calls(self):
        """Test that the singleton instance state remains consistent after concurrent access"""
        # Reset singleton
        global_functions.TF_INSTANCE = None

        instance_ids = []
        lock = threading.Lock()

        def fetch_instance_id():
            """Fetch the singleton and record its id()"""
            instance = global_functions._get_tf_instance()
            with lock:
                instance_ids.append(id(instance))

        # Concurrent initialization
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_instance_id) for _ in range(10)]
            _ = [f.result() for f in futures]

        # All id() values should be identical (same object in memory)
        assert len(set(instance_ids)) == 1, (
            "All instances should have the same id (be the same object)"
        )
