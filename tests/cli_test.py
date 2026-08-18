"""Tests for the ``timezonefinder`` console script.

The end-to-end cases run the installed entry point in a subprocess, so they
cover the ``[project.scripts]`` wiring in ``pyproject.toml`` as well as the code
in :mod:`timezonefinder.command_line`.
"""

import csv
import subprocess
import sys

import pytest

from timezonefinder.command_line import _format_lookup_details, get_timezone_function
from timezonefinder.configs import DEFAULT_DATA_DIR
from timezonefinder.zone_names import read_zone_names

timezone_names = read_zone_names(DEFAULT_DATA_DIR)

FUNCTION_IDS = [0, 1, 3, 4, 5]
# The ids that reach TimezoneFinder, the only class with polygon data to hold.
IN_MEMORY_FUNCTION_IDS = [0, 1, 5]

# A land point deep enough inland that every lookup agrees on it, and whose
# timezone name happens to end in a character a naive `rstrip("\n\x1b[0m")`
# would eat - `str.rstrip` takes a *set* of characters, not a suffix, so it
# turns "Europe/Amsterdam" into "Europe/Amsterda". 12 of the packaged zone
# names end in one of those characters.
AMSTERDAM = ("4.89", "52.37")
# Open ocean. The land-only lookups (-f 4, -f 5) find nothing here; the others
# fall back to the Etc/GMT± zone of the longitude band, which is likewise a
# name the strip above would truncate ("Etc/GMT+10" -> "Etc/GMT+1").
PACIFIC = ("-150.0", "0.0")


def run_cli(*args: str, input: str | None = None) -> subprocess.CompletedProcess:
    """Run the installed console script.

    Invoked as an argument list rather than through a shell, so that an
    argument is passed through verbatim and a missing entry point raises
    ``FileNotFoundError`` here instead of turning into a shell error message
    that has to be recognised in the captured output.

    Every case goes through the console script rather than ``python -m``, so
    that the ``[project.scripts]`` wiring in ``pyproject.toml`` is covered too -
    a ``-m`` invocation reaches ``main`` without it and would stay green if that
    entry point were broken or removed.

    :param input: Text to feed to the process on stdin, for the ``--stdin`` cases
    """
    return subprocess.run(
        ["timezonefinder", *args],
        input=input,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.unit
@pytest.mark.parametrize("function_id", FUNCTION_IDS)
def test_lookup_prints_the_zone_name_and_nothing_else(function_id: int):
    """Non-verbose output is exactly one line, and that line is the result.

    Nothing on the lookup path writes to stdout, and this pins that: a lookup
    function (or anything it imports) that started printing would add a line
    here and break callers that read one line per query.
    """
    result = run_cli("-f", str(function_id), "--", *AMSTERDAM)
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert len(lines) == 1, f"expected a single line of output, got {lines}"
    assert lines[0] in timezone_names


@pytest.mark.unit
@pytest.mark.parametrize(
    ("coordinates", "expected"),
    [
        pytest.param(AMSTERDAM, "Europe/Amsterdam", id="land"),
        pytest.param(PACIFIC, "Etc/GMT+10", id="ocean"),
    ],
)
def test_result_is_printed_verbatim(coordinates: tuple[str, str], expected: str):
    """The printed name is the full name, character for character."""
    result = run_cli("-f", "0", "--", *coordinates)
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"{expected}\n"


@pytest.mark.unit
@pytest.mark.parametrize("function_id", [4, 5])
def test_land_only_lookup_prints_an_empty_line_over_the_ocean(function_id: int):
    """No match prints an empty line rather than nothing, so that a caller
    reading one line per query stays in step with its inputs."""
    result = run_cli("-f", str(function_id), "--", *PACIFIC)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "\n"


@pytest.mark.unit
@pytest.mark.parametrize("function_id", [0, 3])
def test_verbose_output_reports_the_lookup(function_id: int):
    """``-v`` replaces the bare result with the details block, reporting the
    same timezone the library returns for those coordinates."""
    lng, lat = (float(value) for value in AMSTERDAM)
    zone_name = get_timezone_function(function_id)(lng=lng, lat=lat)

    verbose = run_cli("-f", str(function_id), "-v", "--", *AMSTERDAM)
    assert verbose.returncode == 0, verbose.stderr

    lines = verbose.stdout.splitlines()
    assert lines[0] == "=" * 60
    assert lines[-1] == "=" * 60
    assert "TIMEZONEFINDER LOOKUP DETAILS" in lines
    assert "Coordinates: 52.370000°, 4.890000° (lat, lng)" in lines
    assert f"(function ID: {function_id})" in "\n".join(lines)
    assert f"Result: Found timezone '{zone_name}'" in lines


@pytest.mark.unit
def test_verbose_output_reports_a_missing_result():
    result = run_cli("-f", "5", "-v", "--", *PACIFIC)
    assert result.returncode == 0, result.stderr
    assert "Result: No timezone found at this location" in result.stdout.splitlines()


@pytest.mark.unit
def test_removed_function_id_is_rejected():
    """Function id 2 was removed; argparse must reject it before any lookup runs.

    Only the parts of argparse's message that are stable across the supported
    Python versions are asserted. It renders the rejected value quoted from
    3.12 on (``invalid choice: '2'``) and bare on 3.11 (``invalid choice: 2``),
    so matching the value would pin the test to one interpreter.
    """
    result = run_cli("-f", "2", "--", *AMSTERDAM)
    assert result.returncode == 2
    assert result.stdout == "", "a rejected function id must not reach the lookup"
    assert "invalid choice" in result.stderr
    assert "-f/--function" in result.stderr


@pytest.mark.unit
def test_get_timezone_function_rejects_an_unknown_id():
    """The ``ValueError`` branch, which argparse makes unreachable from the CLI."""
    with pytest.raises(ValueError, match="Invalid function ID: 2"):
        get_timezone_function(2)


@pytest.mark.unit
def test_details_name_the_function_they_were_given():
    """The details report the function that produced the result, rather than
    resolving the id a second time - which for ids 3 and 4 would construct a
    second ``TimezoneFinderL`` and reload its shortcut data."""

    def stub_lookup(lng: float, lat: float) -> str | None:
        return "Europe/Amsterdam"

    details = _format_lookup_details(4.89, 52.37, 3, stub_lookup, "Europe/Amsterdam")
    assert "Function stub_lookup (function ID: 3)" in details
    assert "Result: Found timezone 'Europe/Amsterdam'" in details


# --- stdin streaming mode tests ---

# A header naming the two axes, so most cases need no column flags. `lat` comes
# first deliberately: the whole point of resolving columns by name is that the
# file's own order stops mattering.
HEADER = "name,lat,lng"


def csv_input(*rows: str, header: str = HEADER) -> str:
    """Build a delimited input with a header row."""
    return "".join(f"{line}\n" for line in (header, *rows))


AMSTERDAM_ROW = f"Amsterdam,{AMSTERDAM[1]},{AMSTERDAM[0]}"
PACIFIC_ROW = f"Pacific,{PACIFIC[1]},{PACIFIC[0]}"


@pytest.mark.unit
def test_stdin_mode_appends_a_timezone_column():
    """Each input row comes back with its answer attached, header included."""
    result = run_cli("--stdin", input=csv_input(AMSTERDAM_ROW, PACIFIC_ROW))
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        f"{HEADER},timezone",
        f"{AMSTERDAM_ROW},Europe/Amsterdam",
        f"{PACIFIC_ROW},Etc/GMT+10",
    ]


@pytest.mark.unit
def test_stdin_mode_reads_columns_by_name_not_position():
    """The header decides which column is which, whatever order they are in.

    This is what makes a swapped pair impossible rather than merely unlikely:
    `lat` precedes `lng` here, and a positional reader would answer with the
    Indian Ocean instead of Amsterdam.
    """
    reversed_header = "name,lng,lat"
    reversed_row = f"Amsterdam,{AMSTERDAM[0]},{AMSTERDAM[1]}"
    result = run_cli("--stdin", input=csv_input(reversed_row, header=reversed_header))
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[1].endswith(",Europe/Amsterdam")


@pytest.mark.unit
@pytest.mark.parametrize(
    "lng_name, lat_name",
    [("lng", "lat"), ("lon", "latitude"), ("LONGITUDE", "LAT"), ("x", "y")],
)
def test_stdin_mode_recognises_header_name_variants(lng_name: str, lat_name: str):
    """The documented header spellings are matched case-insensitively."""
    header = f"{lng_name},{lat_name}"
    row = f"{AMSTERDAM[0]},{AMSTERDAM[1]}"
    result = run_cli("--stdin", input=csv_input(row, header=header))
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[1] == f"{row},Europe/Amsterdam"


@pytest.mark.unit
def test_stdin_mode_matches_a_header_carrying_a_byte_order_mark():
    """A spreadsheet exported as "CSV UTF-8" starts with a BOM; it must not hide
    the first column's name from the matcher.

    The BOM is echoed back with the row rather than swallowed, so the annotated
    output stays the same flavour of CSV that was fed in.
    """
    result = run_cli("--stdin", input=f"\ufefflng,lat\n{AMSTERDAM[0]},{AMSTERDAM[1]}\n")
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        "\ufefflng,lat,timezone",
        f"{AMSTERDAM[0]},{AMSTERDAM[1]},Europe/Amsterdam",
    ]


@pytest.mark.unit
def test_stdin_mode_refuses_to_guess_the_column_order():
    """Headerless input without column flags is an error, never a positional guess.

    A guess would be wrong silently: for any point with |lng| <= 90 - most of
    the populated world - the swapped pair is still a valid coordinate, so it
    resolves to a real timezone rather than raising.
    """
    result = run_cli("--stdin", input=f"{AMSTERDAM[0]},{AMSTERDAM[1]}\n")
    assert result.returncode == 2
    assert result.stdout == "", "nothing may be answered before the columns are known"
    assert "--lng-col" in result.stderr


@pytest.mark.unit
def test_stdin_mode_header_flag_overrides_the_probe():
    """--header states what probing the first row can only infer.

    A header of purely numeric names looks like data to any probe, and the
    coordinate columns are then never found - so without a way to state it, a
    perfectly well-formed input is unusable.
    """
    probed = run_cli("--stdin", input="2024,lat,lng\n5,52.37,4.89\n")
    assert probed.returncode == 2
    assert "no header row" in probed.stderr

    stated = run_cli("--stdin", "--header", input="2024,lat,lng\n5,52.37,4.89\n")
    assert stated.returncode == 0, stated.stderr
    assert stated.stdout.splitlines() == [
        "2024,lat,lng,timezone",
        "5,52.37,4.89,Europe/Amsterdam",
    ]


@pytest.mark.unit
def test_stdin_mode_no_header_flag_keeps_the_first_row_as_data():
    """--no-header states that every row is data, first one included."""
    result = run_cli(
        "--stdin",
        "--no-header",
        "--lng-col",
        "1",
        "--lat-col",
        "2",
        input=f"{AMSTERDAM[0]},{AMSTERDAM[1]}\n",
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        f"{AMSTERDAM[0]},{AMSTERDAM[1]},Europe/Amsterdam"
    ]


@pytest.mark.unit
def test_stdin_mode_header_flags_are_mutually_exclusive():
    """The first row is one thing or the other, so both flags cannot be given."""
    result = run_cli("--stdin", "--header", "--no-header", input="")
    assert result.returncode == 2
    assert "not allowed with argument" in result.stderr


@pytest.mark.unit
def test_stdin_mode_takes_explicit_1_based_columns():
    """--lng-col/--lat-col address a headerless input by column number."""
    rows = f"S-1,{AMSTERDAM[0]},{AMSTERDAM[1]}\nS-2,{PACIFIC[0]},{PACIFIC[1]}\n"
    result = run_cli("--stdin", "--lng-col", "2", "--lat-col", "3", input=rows)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        f"S-1,{AMSTERDAM[0]},{AMSTERDAM[1]},Europe/Amsterdam",
        f"S-2,{PACIFIC[0]},{PACIFIC[1]},Etc/GMT+10",
    ]


@pytest.mark.unit
def test_stdin_mode_does_not_mistake_a_data_row_for_a_header():
    """A row addressed by column number is data, even if nothing in it parses.

    Probing the row is only meaningful when the header is needed to resolve a
    column. With both columns given as numbers it decides nothing else, and
    reading this row as a header would drop it in silence and still exit 0 -
    the failure mode column numbers were meant to rule out.
    """
    result = run_cli(
        "--stdin", "--lng-col", "2", "--lat-col", "3", input="S-1,N/A,N/A\n"
    )
    assert result.returncode == 1, "the unusable row must reach the exit code"
    assert result.stdout.splitlines() == ["S-1,N/A,N/A,"]
    assert "row 1" in result.stderr


@pytest.mark.unit
def test_stdin_mode_takes_explicit_column_names():
    """A header with unrecognised names is addressable by naming the columns."""
    result = run_cli(
        "--stdin",
        "--lng-col",
        "longitude_deg",
        "--lat-col",
        "latitude_deg",
        input=csv_input(
            f"{AMSTERDAM[0]},{AMSTERDAM[1]}", header="longitude_deg,latitude_deg"
        ),
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[1].endswith(",Europe/Amsterdam")


@pytest.mark.unit
@pytest.mark.parametrize(
    "header", ["LONGITUDE_DEG,LATITUDE_DEG", "longitude_deg , latitude_deg"]
)
def test_stdin_mode_matches_an_explicit_column_name_loosely(header: str):
    """--lng-col/--lat-col compare names the way auto-detection does.

    These flags are the fallback for a header auto-detection could not match,
    so matching case- or whitespace-sensitively here would refuse the very
    headers they exist to rescue.
    """
    result = run_cli(
        "--stdin",
        "--lng-col",
        "longitude_deg",
        "--lat-col",
        "latitude_deg",
        input=csv_input(f"{AMSTERDAM[0]},{AMSTERDAM[1]}", header=header),
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[1].endswith(",Europe/Amsterdam")


@pytest.mark.unit
def test_stdin_mode_names_the_header_it_could_not_match():
    """An unmatchable header reports what it found, not just that it failed."""
    result = run_cli("--stdin", input=csv_input("4.89,52.37", header="a,b"))
    assert result.returncode == 2
    assert "'a', 'b'" in result.stderr
    assert "--lng-col" in result.stderr


@pytest.mark.unit
def test_stdin_mode_rejects_a_column_number_wider_than_the_input():
    """A typo in --lng-col is one usage error, not a warning per row.

    It is a property of the flag, not of any row, so diagnosing it per row
    would bury it under a warning and a useless echo for every line of the
    input - millions of them for the file sizes this mode is for.
    """
    result = run_cli(
        "--stdin",
        "--lng-col",
        "9",
        "--lat-col",
        "2",
        input=csv_input(AMSTERDAM_ROW, PACIFIC_ROW),
    )
    assert result.returncode == 2
    assert result.stdout == "", (
        "nothing may be answered against a column that is absent"
    )
    assert result.stderr.count("\n") == 1, result.stderr
    assert "--lng-col addresses column 9" in result.stderr


@pytest.mark.unit
@pytest.mark.parametrize("delimiter, flag", [(";", ";"), ("\t", "\\t"), ("|", "|")])
def test_stdin_mode_honours_the_delimiter_flag(delimiter: str, flag: str):
    """-d sets the delimiter for input and output alike."""
    header = delimiter.join(["lng", "lat"])
    row = delimiter.join([AMSTERDAM[0], AMSTERDAM[1]])
    result = run_cli("--stdin", "-d", flag, input=f"{header}\n{row}\n")
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        delimiter.join(["lng", "lat", "timezone"]),
        delimiter.join([AMSTERDAM[0], AMSTERDAM[1], "Europe/Amsterdam"]),
    ]


@pytest.mark.unit
def test_stdin_mode_rejects_a_multi_character_delimiter():
    """csv needs a single character, so anything longer is a usage error."""
    result = run_cli("--stdin", "-d", "::", input=csv_input(AMSTERDAM_ROW))
    assert result.returncode == 2
    assert "single character" in result.stderr


@pytest.mark.unit
def test_stdin_mode_preserves_quoted_fields():
    """A field containing the delimiter survives the round trip intact."""
    result = run_cli(
        "--stdin", input=csv_input(f'"Amsterdam, NL",{AMSTERDAM[1]},{AMSTERDAM[0]}')
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[1] == (
        f'"Amsterdam, NL",{AMSTERDAM[1]},{AMSTERDAM[0]},Europe/Amsterdam'
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "bad_row",
    [
        "Bad,100,200",  # longitude out of range
        "Bad,91,0",  # latitude out of range
        "Bad,nan,nan",
        "Bad,inf,0",
        "Bad,,",  # empty coordinate cells
        "Bad",  # row too short to hold either column
    ],
)
def test_stdin_mode_survives_an_unusable_row(bad_row: str):
    """One unusable row must not cost the caller the rest of the stream.

    Out-of-range coordinates are the case worth pinning: they parse as numbers
    and only fail inside the lookup, so before the bounds check moved into the
    row parser they raised past the loop and discarded every row after them,
    which is a hostile outcome for a stream the caller cannot re-read.
    """
    result = run_cli("--stdin", input=csv_input(bad_row, AMSTERDAM_ROW))
    assert result.returncode == 1, "a rejected row must be visible in the exit code"
    assert "Traceback" not in result.stderr, result.stderr
    lines = result.stdout.splitlines()
    assert lines[-1] == f"{AMSTERDAM_ROW},Europe/Amsterdam", (
        f"the row after {bad_row!r} must still be answered, got {lines}"
    )


@pytest.mark.unit
def test_stdin_mode_survives_a_row_csv_itself_rejects():
    """A line csv cannot parse costs one row, not the rest of the stream.

    ``csv.Error`` derives from ``Exception`` rather than ``ValueError``, so it
    escapes every handler written for a bad coordinate; before it was caught
    where the rows are read, an over-long field ended the run with a traceback.
    """
    oversized = "x" * (csv.field_size_limit() + 1)
    result = run_cli(
        "--stdin",
        input=csv_input(f"{oversized},{AMSTERDAM[1]},{AMSTERDAM[0]}", AMSTERDAM_ROW),
    )
    assert result.returncode == 1, "a rejected row must be visible in the exit code"
    assert "Traceback" not in result.stderr, result.stderr
    assert "field larger than field limit" in result.stderr
    assert result.stdout.splitlines()[-1] == f"{AMSTERDAM_ROW},Europe/Amsterdam"


@pytest.mark.unit
def test_stdin_mode_writes_a_rejected_row_back_with_an_empty_answer():
    """A rejected row identifies itself, rather than becoming an anonymous blank."""
    result = run_cli("--stdin", input=csv_input("Bad,100,200"))
    assert result.stdout.splitlines()[1] == "Bad,100,200,"


@pytest.mark.unit
def test_stdin_mode_echoes_a_blank_row_back_blank():
    """A blank row must not turn into a one-column row in a rectangular file.

    ``csv`` writes a lone empty field as ``""`` to keep it distinguishable from
    an empty row, which is exactly the ragged row a consumer of the output
    trips over. There is no row to append a cell to, so none is appended.
    """
    result = run_cli("--stdin", input=csv_input(AMSTERDAM_ROW, "", PACIFIC_ROW))
    assert result.returncode == 1, "a rejected row must be visible in the exit code"
    assert result.stdout.splitlines() == [
        f"{HEADER},timezone",
        f"{AMSTERDAM_ROW},Europe/Amsterdam",
        "",
        f"{PACIFIC_ROW},Etc/GMT+10",
    ]
    widths = {len(row) for row in csv.reader(result.stdout.splitlines()) if row}
    assert widths == {len(HEADER.split(",")) + 1}, "the output must stay rectangular"


@pytest.mark.unit
def test_stdin_mode_warning_names_the_row_and_the_reason():
    """A rejected row is diagnosable: its number and why it failed."""
    result = run_cli("--stdin", input=csv_input(AMSTERDAM_ROW, "Bad,100,200"))
    assert "row 3" in result.stderr
    assert "must be in range" in result.stderr


@pytest.mark.unit
def test_stdin_mode_exits_zero_when_every_row_was_answered():
    """An empty answer is not a rejected row: ocean points under -f 5 exit 0."""
    result = run_cli("--stdin", "-f", "5", input=csv_input(PACIFIC_ROW))
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[1] == f"{PACIFIC_ROW},"


@pytest.mark.unit
def test_stdin_mode_respects_function_flag():
    """-f applies to every lookup in the stream.

    The ocean point is what makes this discriminating: it is the only one of
    the two whose answer differs between the default `-f 0` (`Etc/GMT+10`) and
    `-f 5` (empty, since it is not on land). Asserting only the land point
    would pass with the flag ignored entirely.
    """
    result = run_cli("--stdin", "-f", "5", input=csv_input(AMSTERDAM_ROW, PACIFIC_ROW))
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert lines[1] == f"{AMSTERDAM_ROW},Europe/Amsterdam"
    assert lines[2] == f"{PACIFIC_ROW},", (
        "-f 5 is land-only: the ocean row has no answer"
    )


@pytest.mark.unit
def test_stdin_mode_empty_input_produces_no_output():
    """An empty stream produces no output rows."""
    result = run_cli("--stdin", input="")
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""


@pytest.mark.unit
def test_stdin_mode_exits_quietly_when_the_consumer_stops_reading():
    """`--stdin | head -1` must not end in a BrokenPipeError traceback.

    Stopping early is how a shell pipeline is normally driven, so this is the
    advertised use case rather than an edge case. The input has to outrun the
    stdout buffer for the writer to still be writing once the reader is gone.
    """
    stdin_input = csv_input(*[AMSTERDAM_ROW] * 20000)
    writer = subprocess.Popen(
        ["timezonefinder", "--stdin"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    reader = subprocess.Popen(
        ["head", "-1"], stdin=writer.stdout, stdout=subprocess.PIPE, text=True
    )
    # the parent must drop its own handle, or the pipe never reports as closed
    assert writer.stdout is not None
    writer.stdout.close()
    try:
        writer.stdin.write(stdin_input)
        writer.stdin.close()
    except BrokenPipeError:  # pragma: no cover - the writer may exit first
        pass
    assert reader.communicate()[0] == f"{HEADER},timezone\n"
    stderr = writer.communicate()[1]
    assert "BrokenPipeError" not in stderr, stderr
    assert "Exception ignored" not in stderr, stderr
    assert writer.returncode == 141, (
        "a truncated pipeline must not report the exit code that means "
        "rows were rejected"
    )


@pytest.mark.unit
def test_stdin_and_verbose_are_mutually_exclusive():
    """--stdin and -v cannot be used together."""
    result = run_cli("--stdin", "-v")
    assert result.returncode == 2
    assert "mutually exclusive" in result.stderr


@pytest.mark.unit
@pytest.mark.parametrize("extra_args", [("4.89", "52.37"), ("4.89",)])
def test_stdin_mode_rejects_coordinates_on_the_command_line(extra_args):
    """Coordinates passed alongside --stdin are an error, not silently dropped."""
    result = run_cli("--stdin", *extra_args, input="")
    assert result.returncode == 2
    assert result.stdout == ""
    assert "do not pass lng and lat" in result.stderr


@pytest.mark.unit
@pytest.mark.parametrize(
    "flag_args",
    [
        ("-d", ";"),
        ("--lng-col", "2"),
        ("--lat-col", "3"),
        ("--header",),
        ("--no-header",),
    ],
)
def test_stdin_only_flags_are_rejected_for_a_single_query(flag_args):
    """The row-format flags mean nothing without --stdin, so they are refused."""
    result = run_cli(*flag_args, "--", *AMSTERDAM)
    assert result.returncode == 2
    assert "only apply to --stdin" in result.stderr


@pytest.mark.unit
def test_missing_argument_error_names_only_what_is_missing():
    """A partial invocation must not report the argument that was supplied."""
    result = run_cli("--", *AMSTERDAM[:1])
    assert result.returncode == 2
    assert "required: lat" in result.stderr
    assert "lng" not in result.stderr.rsplit("required:", 1)[-1]


@pytest.mark.unit
@pytest.mark.parametrize("function_id", IN_MEMORY_FUNCTION_IDS)
def test_in_memory_flag_returns_the_same_answers(function_id: int):
    """--in-memory only changes how the coordinate data is held, never the result."""
    rows = csv_input(AMSTERDAM_ROW, PACIFIC_ROW)
    mapped = run_cli("--stdin", "-f", str(function_id), input=rows)
    in_memory = run_cli("--stdin", "--in-memory", "-f", str(function_id), input=rows)
    assert in_memory.returncode == 0, in_memory.stderr
    assert in_memory.stdout == mapped.stdout


@pytest.mark.unit
@pytest.mark.parametrize("function_id", [3, 4])
def test_in_memory_flag_is_refused_where_it_cannot_apply(function_id: int):
    """TimezoneFinderL holds no polygon data, so the flag is rejected, not ignored.

    Accepting it would promise the speedup its help text advertises and deliver
    nothing, which no output of a passing run would reveal.
    """
    result = run_cli("--in-memory", "-f", str(function_id), "--", *AMSTERDAM)
    assert result.returncode == 2
    assert result.stdout == ""
    assert "does not apply" in result.stderr


@pytest.mark.unit
def test_in_memory_flag_applies_to_a_single_query():
    """The flag is not stdin-only: a one-shot lookup accepts it too."""
    result = run_cli("--in-memory", "--", *AMSTERDAM)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "Europe/Amsterdam\n"


@pytest.mark.unit
def test_module_entry_point_matches_the_console_script():
    """`python -m timezonefinder` reaches the same CLI as the console script.

    Every other case here runs the console script, so without this the
    ``__main__`` module added for the streaming mode has no coverage at all.
    """
    rows = csv_input(AMSTERDAM_ROW)
    module = subprocess.run(
        [sys.executable, "-m", "timezonefinder", "--stdin"],
        input=rows,
        capture_output=True,
        text=True,
        check=False,
    )
    assert module.returncode == 0, module.stderr
    assert module.stdout == run_cli("--stdin", input=rows).stdout
