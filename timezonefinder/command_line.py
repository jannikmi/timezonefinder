import argparse
import contextlib
import os
import sys
import tempfile
from typing import Callable, Union

from timezonefinder import TimezoneFinder, TimezoneFinderL


@contextlib.contextmanager
def redirect_stdout_to_temp_file():
    """
    Context manager that redirects stdout to a temporary file for the duration of the context.
    The temporary file is created but not deleted when the context exits.
    Returns the path to the temporary file.
    """
    # Save the original stdout
    original_stdout = sys.stdout

    # Create a temporary file that will NOT be automatically deleted
    temp_fd, temp_path = tempfile.mkstemp(text=True)
    temp_file = os.fdopen(temp_fd, "w")

    try:
        # Redirect stdout to the temporary file
        sys.stdout = temp_file
        yield temp_path
    finally:
        # Restore the original stdout and close the file
        sys.stdout = original_stdout
        temp_file.close()


def get_timezone_function(function_id: int) -> Callable:
    """
    Note: script is being called for each point individually. Caching TimezoneFinder() instances is useless.
    -> avoid constructing unnecessary instances
    """
    tf_instance: Union[TimezoneFinder, TimezoneFinderL]
    if function_id in [0, 1, 5]:
        tf_instance = TimezoneFinder()
        functions = {
            0: tf_instance.timezone_at,
            1: tf_instance.certain_timezone_at,
            5: tf_instance.timezone_at_land,
        }
    else:
        tf_instance = TimezoneFinderL()
        functions = {
            3: tf_instance.timezone_at,
            4: tf_instance.timezone_at_land,
        }
    return functions[function_id]


def main():
    parser = argparse.ArgumentParser(description="parse TimezoneFinder parameters")
    parser.add_argument("lng", type=float, help="longitude to be queried")
    parser.add_argument("lat", type=float, help="latitude to be queried")
    parser.add_argument("-v", action="store_true", help="verbosity flag")
    parser.add_argument(
        "-f",
        "--function",
        type=int,
        choices=[0, 1, 3, 4, 5],
        default=0,
        help="function to be called:"
        "0: TimezoneFinder.timezone_at(), "
        "1: TimezoneFinder.certain_timezone_at(), "
        "2: removed, "
        "3: TimezoneFinderL.timezone_at(), "
        "4: TimezoneFinderL.timezone_at_land(), "
        "5: TimezoneFinder.timezone_at_land(), ",
    )
    parsed_args = parser.parse_args()  # takes input from sys.argv
    timezone_function = get_timezone_function(parsed_args.function)

    verbose_mode = parsed_args.v

    # Always redirect stdout to a temp file
    with redirect_stdout_to_temp_file() as temp_file_path:
        print("\n" + "=" * 60)
        print("TIMEZONEFINDER LOOKUP DETAILS")
        print("-" * 60)
        print(f"Coordinates: {parsed_args.lat:.6f}°, {parsed_args.lng:.6f}° (lat, lng)")
        print(
            f"Function {timezone_function.__name__} (function ID: {parsed_args.function})"
        )

        # Execute the timezone function
        tz = timezone_function(lng=parsed_args.lng, lat=parsed_args.lat)

        if tz:
            print(f"Result: Found timezone '{tz}'")
        else:
            print("Result: No timezone found at this location")
        print("=" * 60)

    if verbose_mode:
        # In verbose mode, print the contents of the temp file
        try:
            with open(temp_file_path) as f:
                captured_output = f.read().strip()
                if captured_output:
                    print(captured_output)
        except Exception as e:
            print(f"Warning: Could not read captured output: {e}")
    else:
        # In non-verbose mode, just print the result
        print(tz if tz else "")

    # Always clean up the temp file
    try:
        os.remove(temp_file_path)
    except Exception:
        pass
