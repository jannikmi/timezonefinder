import argparse
import csv
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

# Header names recognised for each axis, lowercased. Auto-detection exists so the
# common case - a CSV exported from a database or a dataframe - needs no flags at
# all; anything unrecognised is an error naming the columns that were found,
# never a guess. Guessing the order is the one thing this must not do: a swapped
# pair is still a valid coordinate for any point with |lng| <= 90, which is most
# of the populated world, so it yields a confident wrong answer rather than a
# failure.
LNG_COLUMN_NAMES = ("lng", "lon", "long", "longitude", "x")
LAT_COLUMN_NAMES = ("lat", "latitude", "y")
TIMEZONE_COLUMN = "timezone"

# Per function id, the global function and the name of the equivalent
# ``TimezoneFinder`` method. The globals share a singleton whose access mode
# cannot be configured from here, so the in-memory case has to bind its method
# on an instance of its own - which is the only thing the two columns differ in.
TIMEZONE_FINDER_FUNCTIONS: dict[int, tuple[Callable[..., str | None], str]] = {
    0: (timezone_at, "timezone_at"),
    1: (certain_timezone_at, "certain_timezone_at"),
    5: (timezone_at_land, "timezone_at_land"),
}

# The ids dispatching to TimezoneFinderL rather than TimezoneFinder.
TIMEZONE_FINDER_L_FUNCTIONS = (3, 4)

# What a shell reports for a process killed by a closed pipe: 128 + SIGPIPE.
# Exiting 1 there would be indistinguishable from a run that rejected rows,
# which is the one thing the exit code of this mode has to say. Spelled out
# rather than read off `signal`, which carries no SIGPIPE on Windows.
BROKEN_PIPE_EXIT_CODE = 141

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
    :param in_memory: Whether to read the polygon coordinate data into RAM
        instead of memory-mapping it. Only worth its footprint across many
        lookups, and without effect for the ``TimezoneFinderL`` ids, which load
        no polygon data - ``_parse_arguments`` refuses the combination
    :return: A callable that accepts lng and lat as keyword arguments and returns a timezone name or None
    :raises ValueError: If function_id is not in the valid range [0, 1, 3, 4, 5]
    """
    if function_id in TIMEZONE_FINDER_FUNCTIONS:
        global_function, method_name = TIMEZONE_FINDER_FUNCTIONS[function_id]
        if not in_memory:
            return global_function
        return getattr(TimezoneFinder(in_memory=True), method_name)

    if function_id in TIMEZONE_FINDER_L_FUNCTIONS:
        # For TimezoneFinderL methods, create an instance
        tf_instance = TimezoneFinderL(in_memory=in_memory)
        return (
            tf_instance.timezone_at
            if function_id == 3
            else tf_instance.timezone_at_land
        )

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
    from stdin instead, as delimited rows.

    :return: Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(description="parse TimezoneFinder parameters")
    parser.add_argument("lng", type=float, nargs="?", help="longitude to be queried")
    parser.add_argument("lat", type=float, nargs="?", help="latitude to be queried")
    parser.add_argument("-v", action="store_true", help="verbosity flag")
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="read delimited rows from stdin and write each back out with a "
        "timezone column appended. Coordinate columns are taken from the header "
        "row, or named with --lng-col/--lat-col. The TimezoneFinder instance is "
        "constructed once, amortising initialisation across the whole input.",
    )
    parser.add_argument(
        "-d",
        "--delimiter",
        default=",",
        help="field delimiter for --stdin input and output (default: ','). "
        "Spell tab as '\\t'.",
    )
    parser.add_argument(
        "--lng-col",
        help="which --stdin column holds the longitude: a header name, or a "
        "1-based column number for input without a header. Required when the "
        "input has no header, since the column order is never guessed.",
    )
    parser.add_argument(
        "--lat-col",
        help="which --stdin column holds the latitude: a header name, or a "
        "1-based column number for input without a header.",
    )
    header_group = parser.add_mutually_exclusive_group()
    header_group.add_argument(
        "--header",
        dest="header",
        action="store_const",
        const=True,
        default=None,
        help="treat the first --stdin row as a header naming the columns, "
        "rather than probing it. Worth stating whenever the first row could "
        "hold no recognisable number - a header of purely numeric names, or a "
        "data row whose coordinates are placeholders.",
    )
    header_group.add_argument(
        "--no-header",
        dest="header",
        action="store_const",
        const=False,
        help="treat every --stdin row as data, including the first.",
    )
    parser.add_argument(
        "--in-memory",
        action="store_true",
        help="read the polygon coordinate data into RAM instead of "
        "memory-mapping it. Costs tens of MB for faster lookups once the page "
        "cache is warm, so it only pays for itself over a long --stdin stream. "
        "Not available for -f 3 and -f 4, which load no polygon data.",
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

    # TimezoneFinderL holds no polygon data, so there is nothing for the flag to
    # read into memory. Accepting it there would promise a speedup it cannot
    # deliver, which is worse than refusing it.
    if args.in_memory and args.function in TIMEZONE_FINDER_L_FUNCTIONS:
        parser.error(
            f"--in-memory does not apply to -f {args.function}: TimezoneFinderL "
            f"loads no polygon data"
        )

    if args.stdin and args.v:
        parser.error("--stdin and -v are mutually exclusive")

    stdin_only = [
        flag
        for flag, value in (
            ("-d/--delimiter", args.delimiter != ","),
            ("--lng-col", args.lng_col is not None),
            ("--lat-col", args.lat_col is not None),
            ("--header/--no-header", args.header is not None),
        )
        if value
    ]
    if stdin_only and not args.stdin:
        parser.error(f"{', '.join(stdin_only)} only apply to --stdin")

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


def _resolve_delimiter(delimiter: str) -> str:
    """Turn the ``--delimiter`` value into the single character csv needs.

    ``\\t`` is accepted spelled out, since typing a literal tab into an argument
    means shell-specific quoting (``$'\\t'``) that not every shell offers.

    :param delimiter: The raw flag value
    :return: A single-character delimiter
    :raises ValueError: If the value is not one character
    """
    if delimiter == "\\t":
        return "\t"
    if len(delimiter) != 1:
        raise ValueError(
            f"--delimiter must be a single character, got {delimiter!r} "
            f"(use '\\t' for tab)"
        )
    return delimiter


def _normalise_header_name(name: str) -> str:
    """Reduce a header field to the form column matching compares.

    Strips a UTF-8 BOM along with the surrounding whitespace. A spreadsheet
    exported as "CSV UTF-8" - the format Excel offers by that name - starts the
    file with one, and it decodes onto the front of the first column's name,
    where it matches nothing and is invisible in the error saying so.

    :param name: The raw header field
    :return: The name to compare against
    """
    return name.lstrip("\ufeff").strip().lower()


def _column_flag(axis: str) -> str:
    """Name the flag that addresses one axis, for diagnostics.

    :param axis: "longitude" or "latitude"
    :return: The flag name
    """
    return f"--{'lng' if axis == 'longitude' else 'lat'}-col"


def _is_column_number(spec: str | None) -> bool:
    """Whether a ``--lng-col``/``--lat-col`` value addresses a column by number.

    :param spec: The flag value, or None if it was not given
    :return: True if the value is a 1-based column number
    """
    return spec is not None and spec.isdigit()


def _looks_like_data(row: list[str]) -> bool:
    """Decide whether a row is data rather than a header.

    A header row names its columns, so none of its fields is a number; a data
    row holds at least one coordinate, so at least one is. Probing the row
    itself keeps this streaming - ``csv.Sniffer`` wants a sample of the file,
    which a pipe cannot hand back once read.

    :param row: The first non-empty row of the input
    :return: True if the row holds data, False if it names columns
    """
    for field in row:
        try:
            float(field)
        except ValueError:
            continue
        return True
    return False


def _resolve_column(
    spec: str | None,
    header: list[str] | None,
    known_names: tuple[str, ...],
    axis: str,
) -> int:
    """Work out which column holds one axis, without ever guessing a position.

    An all-digit ``spec`` is a 1-based column number, anything else a header
    name; with no ``spec`` the header is searched for a known name.

    :param spec: The ``--lng-col``/``--lat-col`` value, or None
    :param header: The header row, or None if the input has none
    :param known_names: Header names recognised for this axis
    :param axis: "longitude" or "latitude", for diagnostics
    :return: The 0-based index of the column
    :raises ValueError: If the column cannot be determined. Whether it fits the
        input is checked once against the first row, by ``_check_columns_fit``
    """
    flag = _column_flag(axis)
    names = None if header is None else [_normalise_header_name(n) for n in header]

    if spec is not None:
        if _is_column_number(spec):
            index = int(spec) - 1
            if index < 0:
                raise ValueError(f"{flag} is 1-based, got {spec}")
            return index
        if names is None:
            raise ValueError(
                f"{flag}={spec!r} names a column, but the input has no header row"
            )
        # Compared through the same normalisation as the automatic lookup
        # below. This flag is the fallback for a header that lookup could not
        # match, so matching more strictly here would refuse the very cases it
        # exists to rescue - a name in another case, or padded with spaces.
        wanted = _normalise_header_name(spec)
        if wanted not in names:
            raise ValueError(
                f"{flag}={spec!r} is not among the header columns: {header}"
            )
        return names.index(wanted)

    if names is None:
        raise ValueError(
            f"cannot tell which column holds the {axis}: the input has no header "
            f"row, so pass {flag} with a 1-based column number"
        )
    for candidate in known_names:
        if candidate in names:
            return names.index(candidate)
    raise ValueError(
        f"no {axis} column found in the header {header}: expected one of "
        f"{list(known_names)}, or pass {flag}"
    )


def _check_columns_fit(row: list[str], indices: tuple[int, int]) -> None:
    """Check the resolved columns against the width of the first row.

    A column number wider than the input is a typo in the flag, not a property
    of one row, so it is diagnosed once here rather than becoming a warning per
    row plus a useless copy of the whole input.

    :param row: The first row, whose width the input is taken to have
    :param indices: The resolved ``(longitude, latitude)`` column indices
    :raises ValueError: If either column lies beyond the row
    """
    for index, axis in zip(indices, ("longitude", "latitude")):
        if index >= len(row):
            raise ValueError(
                f"{_column_flag(axis)} addresses column {index + 1}, but the "
                f"input has {len(row)} column(s)"
            )


def _coordinates_from_row(
    row: list[str], lng_index: int, lat_index: int
) -> tuple[float, float]:
    """Read and validate the coordinate pair out of one input row.

    The bounds check is the same one every lookup performs, so a coordinate
    that reaches the lookup from here cannot raise there. That is what keeps
    one unusable row from ending the stream.

    :param row: The row's fields
    :param lng_index: 0-based index of the longitude column
    :param lat_index: 0-based index of the latitude column
    :return: The validated ``(lng, lat)`` pair
    :raises ValueError: If the row is too short, either field is not a number,
        or the pair is outside the valid range
    """
    for index, axis in ((lng_index, "longitude"), (lat_index, "latitude")):
        if index >= len(row):
            raise ValueError(
                f"row has {len(row)} field(s), needs at least {index + 1} "
                f"for the {axis}"
            )
    try:
        lng, lat = float(row[lng_index]), float(row[lat_index])
    except ValueError:
        raise ValueError(
            f"longitude {row[lng_index]!r} and latitude {row[lat_index]!r} "
            f"must both be numbers"
        ) from None
    return validate_coordinates(lng, lat)


def _run_stdin(
    timezone_function: Callable[..., str | None],
    delimiter: str,
    lng_spec: str | None,
    lat_spec: str | None,
    has_header: bool | None,
) -> int:
    """Annotate delimited rows read from stdin with the timezone of each.

    Every input row is written back out with one column appended, so the answer
    arrives attached to the row it belongs to and a caller needs no second pass
    to rejoin the two. An input header gains a ``timezone`` column; a headerless
    input stays headerless. Which one it is is stated by ``--header`` /
    ``--no-header``, or probed for when neither is given.

    A row that cannot be used - blank, malformed as csv, too short, not
    numeric, or outside the valid coordinate range - produces a warning on
    stderr and is written out with that column empty, so one bad row among a
    thousand costs its own answer and no other. That empty cell is also what a genuine "no timezone here"
    looks like, which ``-f 4`` and ``-f 5`` return for every ocean point, so the
    count returned here is what lets a caller tell the two apart.

    :param timezone_function: The lookup function to call for each row
    :param delimiter: The single-character field delimiter
    :param lng_spec: ``--lng-col`` value, or None to take it from the header
    :param lat_spec: ``--lat-col`` value, or None to take it from the header
    :param has_header: ``--header``/``--no-header`` as stated, or None to probe
        the first row for one
    :return: How many input rows were rejected
    :raises ValueError: If the coordinate columns cannot be determined
    """
    reader = csv.reader(sys.stdin, delimiter=delimiter)
    # csv defaults to \r\n; the rest of this CLI emits \n and so should this.
    writer = csv.writer(sys.stdout, delimiter=delimiter, lineterminator="\n")

    def emit(fields: list[str]) -> None:
        # Flushed per row because Python block-buffers stdout whenever it is not
        # a terminal - which is every case this mode exists for. Without it a
        # consumer receives nothing until ~8 KB has accumulated, and the
        # unbuffered warnings on stderr arrive detached from the rows they name.
        writer.writerow(fields)
        sys.stdout.flush()

    rejected = 0
    lng_index: int | None = None
    lat_index: int | None = None

    # Driven by hand rather than with `enumerate`, so that a row csv itself
    # rejects can be caught without ending the loop. `csv.Error` derives from
    # `Exception`, not `ValueError`, so it would otherwise escape every handler
    # here and abort the stream with a traceback - the one outcome this mode
    # promises not to produce.
    rows = iter(reader)
    row_no = 0
    while True:
        row_no += 1
        try:
            row = next(rows)
        except StopIteration:
            break
        except csv.Error as e:
            # An unterminated quote, or a field past csv's size limit. The
            # reader resumes on the following line, so this costs one row like
            # any other unusable one - but the fields went with it, leaving
            # nothing to echo back.
            sys.stderr.write(f"warning: skipping row {row_no}: {e}\n")
            emit([])
            rejected += 1
            continue

        if not row:
            # A blank row carries no columns to resolve against, so it cannot
            # decide the header question either. Reject it and read on, echoing
            # a blank row back: writing one empty field instead would emit `""`
            # - a one-column row in an otherwise rectangular file, which is
            # what a csv consumer of the output chokes on.
            sys.stderr.write(f"warning: skipping row {row_no}: blank row\n")
            emit([])
            rejected += 1
            continue

        if lng_index is None or lat_index is None:
            # Probing the first row is only worth it when nothing states what
            # it is, and when the header is needed to resolve a column at all:
            # with both columns given as numbers it decides nothing but the
            # fate of this row. The two ways of being wrong are not symmetric -
            # reading a data row as a header drops it in silence, reading a
            # header as data costs one warning naming the row - so where the
            # probe cannot help, the row reads as data.
            if has_header is None:
                addressed_by_number = _is_column_number(lng_spec) and _is_column_number(
                    lat_spec
                )
                is_header = not (addressed_by_number or _looks_like_data(row))
            else:
                is_header = has_header
            header = row if is_header else None
            lng_index = _resolve_column(lng_spec, header, LNG_COLUMN_NAMES, "longitude")
            lat_index = _resolve_column(lat_spec, header, LAT_COLUMN_NAMES, "latitude")
            _check_columns_fit(row, (lng_index, lat_index))
            if header is not None:
                emit([*row, TIMEZONE_COLUMN])
                continue

        try:
            lng, lat = _coordinates_from_row(row, lng_index, lat_index)
        except ValueError as e:
            sys.stderr.write(f"warning: skipping row {row_no}: {e}\n")
            emit([*row, ""])
            rejected += 1
            continue

        tz = timezone_function(lng=lng, lat=lat)
        emit([*row, tz or ""])

    return rejected


def main() -> None:
    """Main entry point for the CLI."""
    args = _parse_arguments()

    timezone_function = get_timezone_function(args.function, args.in_memory)

    if args.stdin:
        try:
            rejected = _run_stdin(
                timezone_function,
                _resolve_delimiter(args.delimiter),
                args.lng_col,
                args.lat_col,
                args.header,
            )
        except ValueError as e:
            # The columns could not be determined - a usage problem, not a bad
            # row, so it ends the run rather than being skipped like one.
            sys.stderr.write(f"error: {e}\n")
            raise SystemExit(2) from None
        except BrokenPipeError:
            # The consumer stopped reading (`| head -5`, a closed reader).
            # Python flushes stdout again on shutdown, which would raise a
            # second time and print "Exception ignored in ..." after the
            # traceback, so point the fd at the null device first. This is
            # the idiom the Python docs prescribe for a filter like this one.
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
            raise SystemExit(BROKEN_PIPE_EXIT_CODE) from None
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
