import argparse
import os
import sys
from collections.abc import Callable

from timezonefinder import (
    TimezoneFinder,
    TimezoneFinderL,
    timezone_at,
    certain_timezone_at,
    timezone_at_land,
)
from timezonefinder.utils import validate_coordinates

# The lookup functions this CLI dispatches to return their result, they never
# print. Nothing else writes to stdout between argument parsing and the final
# print either, so the only output is the one `main` emits deliberately -
# which is what lets a caller pipe the non-verbose output straight into
# another command. `tests/cli_test.py` pins that contract.


def get_timezone_function(
    function_id: int, in_memory: bool = False
) -> Callable[..., str | None]:
    """
    Get the appropriate timezone function based on the function ID.

    Uses global functions when available, otherwise creates instances as needed.
    ``in_memory`` forces an own instance for every id, since the global functions
    share a singleton this cannot configure.

    :param function_id: The ID of the function to retrieve (0, 1, 3, 4, or 5)
    :param in_memory: Whether to read the coordinate data into RAM instead of
        memory-mapping it. Only worth its footprint across many lookups
    :return: A callable that accepts lng and lat as keyword arguments and returns a timezone name or None
    :raises ValueError: If function_id is not in the valid range [0, 1, 3, 4, 5]
    """
    # Use global functions for TimezoneFinder methods
    match function_id:
        case 0:
            return (
                TimezoneFinder(in_memory=True).timezone_at if in_memory else timezone_at
            )
        case 1:
            return (
                TimezoneFinder(in_memory=True).certain_timezone_at
                if in_memory
                else certain_timezone_at
            )
        case 5:
            return (
                TimezoneFinder(in_memory=True).timezone_at_land
                if in_memory
                else timezone_at_land
            )
        case 3 | 4:
            # For TimezoneFinderL methods, create an instance
            tf_instance = TimezoneFinderL(in_memory=in_memory)
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
        "--in-memory",
        action="store_true",
        help="read the coordinate data into RAM instead of memory-mapping it. "
        "Costs tens of MB for roughly 1.3x faster lookups once the page cache "
        "is warm, so it only pays for itself over a long --stdin stream.",
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

    # `nargs="?"` moved the required-argument check off argparse, which named
    # only what was actually missing. Rebuild that: telling someone who forgot
    # the latitude that the longitude is missing too sends them to check the
    # half they got right.
    missing = [
        name for name, value in (("lng", args.lng), ("lat", args.lat)) if value is None
    ]
    if not args.stdin and missing:
        parser.error(f"the following arguments are required: {', '.join(missing)}")

    # len(missing) != 2 rather than `not missing`: a lone `--stdin 5` supplies
    # one positional, which would otherwise still be discarded in silence.
    if args.stdin and len(missing) != 2:
        parser.error(
            "--stdin reads the coordinates from stdin: do not pass lng and lat"
        )

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


def _parse_coordinate_line(line: str) -> tuple[float, float]:
    """Parse and validate a single ``lng,lat`` line from stdin.

    The bounds check is the same one every lookup performs, so a coordinate
    that reaches the lookup from here cannot raise there. That is what keeps
    one unusable line from ending the stream: the caller learns *this line*
    is unusable, not that the process is over.

    :param line: One line of input (with or without the trailing newline)
    :return: The validated ``(lng, lat)`` pair
    :raises ValueError: If the line is blank, is not two comma-separated
        numbers, or names a coordinate outside the valid range
    """
    stripped = line.strip()
    if not stripped:
        raise ValueError("blank line")
    parts = stripped.split(",")
    if len(parts) != 2:
        raise ValueError(
            f"expected 'lng,lat', got {len(parts)} comma-separated field(s)"
        )
    try:
        lng, lat = float(parts[0]), float(parts[1])
    except ValueError:
        raise ValueError("both fields must be numbers") from None
    return validate_coordinates(lng, lat)


def _run_stdin(timezone_function: Callable[..., str | None]) -> int:
    """Read ``lng,lat`` pairs from stdin and print one result per line.

    Unusable lines - blank, unparseable, or naming a coordinate outside the
    valid range - produce a warning on stderr and an empty line on stdout, so
    that a caller reading one line per query stays in step with its inputs and
    one bad line among a thousand does not discard the other 999.

    The empty line that marks a rejected input is indistinguishable on stdout
    from the empty line that marks a genuine "no timezone here" - which ``-f 4``
    and ``-f 5`` produce for every ocean point. The count returned here is what
    lets the caller tell the two apart without parsing stderr.

    :param timezone_function: The lookup function to call for each pair
    :return: How many input lines were rejected
    """
    rejected = 0
    for line_no, raw_line in enumerate(sys.stdin, start=1):
        try:
            lng, lat = _parse_coordinate_line(raw_line)
        except ValueError as e:
            sys.stderr.write(
                f"warning: skipping malformed input on line {line_no}: "
                f"{raw_line.strip()!r} ({e})\n"
            )
            # keep stdout aligned with stdin
            print(flush=True)
            rejected += 1
            continue

        tz = timezone_function(lng=lng, lat=lat)
        # an empty line when no timezone was found, same contract as single mode.
        # Flushed per line because Python block-buffers stdout whenever it is not
        # a terminal - which is every case this mode exists for. Without this a
        # consumer receives nothing until ~8 KB of results has accumulated, and
        # the unbuffered warnings on stderr arrive detached from the output lines
        # they refer to.
        print(tz if tz else "", flush=True)

    return rejected


def main() -> None:
    """Main entry point for the CLI."""
    args = _parse_arguments()

    timezone_function = get_timezone_function(args.function, args.in_memory)

    if args.stdin:
        try:
            rejected = _run_stdin(timezone_function)
        except BrokenPipeError:
            # The consumer stopped reading (`| head -5`, a closed reader).
            # Python flushes stdout again on shutdown, which would raise a
            # second time and print "Exception ignored in ..." after the
            # traceback, so point the fd at the null device first. This is
            # the idiom the Python docs prescribe for a filter like this one.
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
            raise SystemExit(1) from None
        if rejected:
            raise SystemExit(1)
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
