import argparse
import sys
from collections.abc import Callable

from timezonefinder import (
    TimezoneFinderL,
    timezone_at,
    certain_timezone_at,
    timezone_at_land,
)

# The lookup functions this CLI dispatches to return their result, they never
# print. Nothing else writes to stdout between argument parsing and the final
# print either, so the only output is the one `main` emits deliberately -
# which is what lets a caller pipe the non-verbose output straight into
# another command. `tests/cli_test.py` pins that contract.


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

    In stdin mode ``lng`` and ``lat`` become optional — coordinates are read
    from stdin instead, one ``lng,lat`` pair per line.

    :return: Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(description="parse TimezoneFinder parameters")
    parser.add_argument("lng", type=float, nargs="?", help="longitude to be queried")
    parser.add_argument("lat", type=float, nargs="?", help="latitude to be queried")
    parser.add_argument("-v", action="store_true", help="verbosity flag")
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="read lng,lat pairs from stdin, one per line, and print one result "
        "per line. The TimezoneFinder instance is constructed once, amortising "
        "initialisation across the whole input.",
    )
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
    args = parser.parse_args()  # takes input from sys.argv

    if not args.stdin and (args.lng is None or args.lat is None):
        parser.error("the following arguments are required: lng, lat")

    if args.stdin and args.v:
        parser.error("--stdin and -v are mutually exclusive")

    return args


def _format_lookup_details(
    lng: float,
    lat: float,
    function_id: int,
    timezone_function: Callable[..., str | None],
    timezone_result: str | None,
) -> str:
    """
    Format the details of a completed lookup for the verbose output.

    :param lng: Longitude queried
    :param lat: Latitude queried
    :param function_id: The ID of the function used
    :param timezone_function: The function that produced ``timezone_result``.
        Passed in rather than re-resolved from ``function_id``, since resolving
        ids 3 and 4 constructs a ``TimezoneFinderL`` and loads its shortcut data.
    :param timezone_result: The timezone result or None
    :return: Formatted lookup details as a string
    """
    lines = [
        "=" * 60,
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


def _parse_coordinate_line(line: str) -> tuple[float, float] | None:
    """Parse a single ``lng,lat`` line from stdin.

    Returns ``(lng, lat)`` on success or ``None`` when the line is blank,
    contains only whitespace, or cannot be parsed as two floats separated by
    a comma.

    :param line: One line of input (without the trailing newline)
    :return: A ``(lng, lat)`` tuple, or ``None`` for blank/malformed lines
    """
    stripped = line.strip()
    if not stripped:
        return None
    parts = stripped.split(",")
    if len(parts) != 2:
        return None
    try:
        return float(parts[0].strip()), float(parts[1].strip())
    except ValueError:
        return None


def _run_stdin(
    timezone_function: Callable[..., str | None],
    function_id: int,
) -> None:
    """Read ``lng,lat`` pairs from stdin and print one result per line.

    Malformed or out-of-range lines produce a warning on stderr and an empty
    line on stdout, so that a caller reading one line per query stays in step
    with its inputs.

    :param timezone_function: The lookup function to call for each pair
    :param function_id: The function ID (used only for stderr diagnostics)
    """
    for line_no, raw_line in enumerate(sys.stdin, start=1):
        parsed = _parse_coordinate_line(raw_line)
        if parsed is None:
            sys.stderr.write(
                f"warning: skipping malformed input on line {line_no}: "
                f"{raw_line.strip()!r}\n"
            )
            # keep stdout aligned with stdin
            print()
            continue

        lng, lat = parsed
        tz = timezone_function(lng=lng, lat=lat)
        # an empty line when no timezone was found, same contract as single mode
        print(tz if tz else "")


def main() -> None:
    """Main entry point for the CLI."""
    args = _parse_arguments()

    timezone_function = get_timezone_function(args.function)

    if args.stdin:
        _run_stdin(timezone_function, args.function)
        return

    tz = timezone_function(lng=args.lng, lat=args.lat)

    if args.v:
        print(
            _format_lookup_details(
                args.lng, args.lat, args.function, timezone_function, tz
            )
        )
    else:
        # an empty line when no timezone was found, so that a caller reading
        # one line per query stays in step with its inputs
        print(tz if tz else "")
