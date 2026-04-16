import argparse
import contextlib
import logging
import os
import sys
import tempfile
import warnings
from collections.abc import Callable, Generator

from timezonefinder import (
    TimezoneFinderL,
    timezone_at,
    certain_timezone_at,
    timezone_at_land,
)

logger = logging.getLogger(__name__)


@contextlib.contextmanager
def redirect_stdout_to_temp_file() -> Generator[str, None, None]:
    """
    Context manager that redirects stdout to a temporary file.

    The temporary file is created but not automatically deleted when the context exits,
    allowing the caller to read or process the file after redirection stops.

    :yield: The absolute path to the temporary file
    """
    # Save the original stdout
    original_stdout = sys.stdout

    # Create a temporary file that will NOT be automatically deleted
    temp_fd, temp_path = tempfile.mkstemp(text=True)
    temp_file = os.fdopen(temp_fd, "w", encoding="utf-8")

    try:
        # Redirect stdout to the temporary file
        sys.stdout = temp_file
        yield temp_path
    finally:
        # Restore the original stdout and close the file
        sys.stdout = original_stdout
        temp_file.close()


def get_timezone_function(function_id: int) -> Callable[..., str | None]:
    """
    Get the appropriate timezone function based on the function ID.

    Uses global functions when available, otherwise creates instances as needed.

    :param function_id: The ID of the function to retrieve (0, 1, 3, 4, or 5)
    :return: A callable that accepts lng and lat as keyword arguments and returns a timezone name or None
    :raises ValueError: If function_id is not in the valid range [0, 1, 3, 4, 5]
    """
    # Use global functions for TimezoneFinder methods
    match function_id:
        case 0:
            return timezone_at
        case 1:
            return certain_timezone_at
        case 5:
            return timezone_at_land
        case 3 | 4:
            # For TimezoneFinderL methods, create an instance
            tf_instance = TimezoneFinderL()
            if function_id == 3:
                return tf_instance.timezone_at
            else:
                return tf_instance.timezone_at_land
        case _:
            raise ValueError(
                f"Invalid function ID: {function_id}. "
                f"Valid choices are: 0 (timezone_at), 1 (certain_timezone_at), "
                f"3 (TimezoneFinderL.timezone_at), 4 (TimezoneFinderL.timezone_at_land), "
                f"5 (timezone_at_land)"
            )


def _parse_arguments() -> argparse.Namespace:
    """
    Parse and validate command-line arguments.

    :return: Parsed command-line arguments
    """
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
    return parser.parse_args()  # takes input from sys.argv


def _lookup_timezone(lng: float, lat: float, function_id: int) -> str | None:
    """
    Perform timezone lookup with the specified function.

    :param lng: Longitude to query
    :param lat: Latitude to query
    :param function_id: The ID of the timezone function to use (0, 1, 3, 4, or 5)
    :return: The timezone name or None if not found
    """
    timezone_function = get_timezone_function(function_id)
    return timezone_function(lng=lng, lat=lat)


def _print_lookup_details(
    lng: float, lat: float, function_id: int, timezone_result: str | None
) -> str:
    """
    Generate lookup details output.

    :param lng: Longitude queried
    :param lat: Latitude queried
    :param function_id: The ID of the function used
    :param timezone_result: The timezone result or None
    :return: Formatted lookup details as a string
    """
    timezone_function = get_timezone_function(function_id)
    lines = [
        "\n" + "=" * 60,
        "TIMEZONEFINDER LOOKUP DETAILS",
        "-" * 60,
        f"Coordinates: {lat:.6f}°, {lng:.6f}° (lat, lng)",
        f"Function {timezone_function.__name__} (function ID: {function_id})",
    ]

    if timezone_result:
        lines.append(f"Result: Found timezone '{timezone_result}'")
    else:
        lines.append("Result: No timezone found at this location")
    lines.append("=" * 60)

    return "\n".join(lines)


def main() -> None:
    """Main entry point for the CLI."""
    args = _parse_arguments()

    # Always redirect stdout to a temp file
    with redirect_stdout_to_temp_file() as temp_file_path:
        # Perform lookup
        tz = _lookup_timezone(args.lng, args.lat, args.function)

        # Generate and print lookup details (captures to temp file)
        details = _print_lookup_details(args.lng, args.lat, args.function, tz)
        print(details)

    if args.v:
        # In verbose mode, print the contents of the temp file
        try:
            with open(temp_file_path, encoding="utf-8") as f:
                captured_output = f.read().strip()
                if captured_output:
                    print(captured_output)
        except (FileNotFoundError, OSError, UnicodeDecodeError) as e:
            warnings.warn(f"Could not read captured output: {e}")
    else:
        # In non-verbose mode, just print the result
        print(tz if tz else "")

    # Always clean up the temp file
    try:
        os.remove(temp_file_path)
    except FileNotFoundError:
        # File was already deleted or never created
        pass
    except OSError as e:
        # Log cleanup failures but don't break program flow
        logger.warning(f"Failed to clean up temporary file {temp_file_path}: {e}")
