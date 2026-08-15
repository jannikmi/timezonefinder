"""Tests for the ``timezonefinder`` console script.

The end-to-end cases run the installed entry point in a subprocess, so they
cover the ``[project.scripts]`` wiring in ``pyproject.toml`` as well as the code
in :mod:`timezonefinder.command_line`.
"""

import subprocess
import sys

import pytest

from timezonefinder.command_line import _format_lookup_details, get_timezone_function
from timezonefinder.configs import DEFAULT_DATA_DIR
from timezonefinder.zone_names import read_zone_names

timezone_names = read_zone_names(DEFAULT_DATA_DIR)

FUNCTION_IDS = [0, 1, 3, 4, 5]

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


@pytest.mark.unit
def test_stdin_mode_prints_one_result_per_line():
    """--stdin reads lng,lat pairs from stdin and writes one result per line."""
    stdin_input = f"{AMSTERDAM[0]},{AMSTERDAM[1]}\n{PACIFIC[0]},{PACIFIC[1]}\n"
    result = run_cli("--stdin", input=stdin_input)
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert len(lines) == 2, f"expected 2 lines, got {lines}"
    assert lines[0] == "Europe/Amsterdam"
    assert lines[1] == "Etc/GMT+10"


@pytest.mark.unit
def test_stdin_mode_respects_function_flag():
    """-f applies to every lookup in the stream.

    The ocean point is what makes this discriminating: it is the only one of
    the two whose answer differs between the default `-f 0` (`Etc/GMT+10`, the
    zone of the longitude band) and `-f 5` (empty, since it is not on land).
    Asserting only the land point would pass with the flag ignored entirely.
    """
    stdin_input = f"{AMSTERDAM[0]},{AMSTERDAM[1]}\n{PACIFIC[0]},{PACIFIC[1]}\n"
    result = run_cli("--stdin", "-f", "5", input=stdin_input)
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert len(lines) == 2, f"expected 2 lines, got {lines}"
    assert lines[0] == "Europe/Amsterdam"
    assert lines[1] == "", "-f 5 is land-only, so the ocean point has no answer"


@pytest.mark.unit
def test_stdin_mode_skips_malformed_lines():
    """Malformed lines produce a stderr warning, an empty stdout line and exit 1.

    The empty line is what keeps a caller reading one line per query in step
    with its inputs, but it is also what a genuine "no timezone here" looks
    like, so the exit code is the only thing distinguishing a stream that was
    fully answered from one that silently dropped inputs.
    """
    stdin_input = (
        f"{AMSTERDAM[0]},{AMSTERDAM[1]}\n"
        "not-a-coordinate\n"
        f"{PACIFIC[0]},{PACIFIC[1]}\n"
        "\n"  # blank line
    )
    result = run_cli("--stdin", input=stdin_input)
    assert result.returncode == 1, "a stream with rejected lines must not exit 0"
    lines = result.stdout.splitlines()
    assert len(lines) == 4, f"expected 4 lines (one per input line), got {lines}"
    assert lines[0] == "Europe/Amsterdam"
    assert lines[1] == ""  # malformed -> empty
    assert lines[2] == "Etc/GMT+10"
    assert lines[3] == ""  # blank -> empty
    assert "malformed input" in result.stderr


@pytest.mark.unit
def test_stdin_mode_empty_input_produces_no_output():
    """An empty stream produces no output lines."""
    result = run_cli("--stdin", input="")
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""


@pytest.mark.unit
def test_stdin_mode_land_only_returns_empty_for_ocean():
    """Land-only lookups in stdin mode print an empty line for ocean points."""
    stdin_input = f"{PACIFIC[0]},{PACIFIC[1]}\n"
    result = run_cli("--stdin", "-f", "5", input=stdin_input)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "\n"


@pytest.mark.unit
def test_stdin_and_verbose_are_mutually_exclusive():
    """--stdin and -v cannot be used together."""
    result = run_cli("--stdin", "-v")
    assert result.returncode == 2
    assert "mutually exclusive" in result.stderr


@pytest.mark.unit
@pytest.mark.parametrize(
    "bad_line",
    ["200,100", "0,91", "nan,nan", "inf,0", "1,2,3", "not-a-coordinate", "   "],
)
def test_stdin_mode_survives_an_unusable_line(bad_line: str):
    """One unusable line must not cost the caller the rest of the stream.

    Out-of-range coordinates are the case worth pinning: they parse as two
    floats and only fail inside the lookup, so before the bounds check moved
    into the line parser they raised past the loop and discarded every input
    after them - the outcome issue #504 called hostile.
    """
    stdin_input = f"{bad_line}\n{AMSTERDAM[0]},{AMSTERDAM[1]}\n"
    result = run_cli("--stdin", input=stdin_input)
    assert result.returncode == 1, "a rejected line must be visible in the exit code"
    assert "Traceback" not in result.stderr, result.stderr
    lines = result.stdout.splitlines()
    assert lines == ["", "Europe/Amsterdam"], (
        f"the line after {bad_line!r} must still be answered, got {lines}"
    )


@pytest.mark.unit
def test_stdin_mode_warning_names_the_line_and_the_reason():
    """A rejected line is diagnosable: its number, its content and why it failed."""
    result = run_cli("--stdin", input=f"{AMSTERDAM[0]},{AMSTERDAM[1]}\n200,100\n")
    assert "line 2" in result.stderr
    assert "'200,100'" in result.stderr
    assert "must be in range" in result.stderr


@pytest.mark.unit
def test_stdin_mode_exits_zero_when_every_line_was_answered():
    """An empty answer is not a rejected line: ocean points under -f 5 exit 0."""
    result = run_cli("--stdin", "-f", "5", input=f"{PACIFIC[0]},{PACIFIC[1]}\n")
    assert result.returncode == 0, result.stderr
    assert result.stdout == "\n"
    assert result.stderr == ""


@pytest.mark.unit
def test_stdin_mode_exits_quietly_when_the_consumer_stops_reading():
    """`--stdin | head -1` must not end in a BrokenPipeError traceback.

    Stopping early is how a shell pipeline is normally driven, so this is the
    advertised use case rather than an edge case. The input has to outrun the
    stdout buffer for the writer to still be writing once the reader is gone.
    """
    stdin_input = f"{AMSTERDAM[0]},{AMSTERDAM[1]}\n" * 20000
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
    assert reader.communicate()[0] == "Europe/Amsterdam\n"
    stderr = writer.communicate()[1]
    assert "BrokenPipeError" not in stderr, stderr
    assert "Exception ignored" not in stderr, stderr


@pytest.mark.unit
@pytest.mark.parametrize("extra_args", [("4.89", "52.37"), ("4.89",)])
def test_stdin_mode_rejects_coordinates_on_the_command_line(extra_args):
    """Coordinates passed alongside --stdin are an error, not silently dropped."""
    result = run_cli("--stdin", *extra_args, input="")
    assert result.returncode == 2
    assert result.stdout == ""
    assert "do not pass lng and lat" in result.stderr


@pytest.mark.unit
def test_missing_argument_error_names_only_what_is_missing():
    """A partial invocation must not report the argument that was supplied."""
    result = run_cli("--", *AMSTERDAM[:1])
    assert result.returncode == 2
    assert "required: lat" in result.stderr
    assert "lng" not in result.stderr.rsplit("required:", 1)[-1]


@pytest.mark.unit
@pytest.mark.parametrize(
    "stdin_input, description",
    [
        ("4.89,52.37\n", "plain"),
        ("  4.89 , 52.37  \n", "whitespace around the fields and the separator"),
        ("4.89,52.37\r\n", "CRLF line ending"),
        ("4.89,52.37", "no trailing newline on the final line"),
    ],
)
def test_stdin_mode_input_tolerances(stdin_input: str, description: str):
    """The tolerances the usage guide promises for an input line."""
    result = run_cli("--stdin", input=stdin_input)
    assert result.returncode == 0, f"{description}: {result.stderr}"
    assert result.stdout == "Europe/Amsterdam\n", description


@pytest.mark.unit
@pytest.mark.parametrize(
    "line",
    [
        "lng,lat",  # a header row
        '"4.89","52.37"',  # quoted fields
        "1,4.89,52.37",  # an extra id column
        "4.89\t52.37",  # tab separated
        "4.89 52.37",  # space separated
    ],
)
def test_stdin_mode_is_not_a_csv_parser(line: str):
    """Input is two comma-separated numbers per line, not a CSV dialect.

    Pinned because the obvious way to reach for this mode is `cat points.csv |
    timezonefinder --stdin`, and a real CSV rarely holds exactly two bare
    numeric columns. Each of these must be rejected as an unusable line rather
    than silently misread as a coordinate.
    """
    result = run_cli("--stdin", input=f"{line}\n")
    assert result.returncode == 1
    assert result.stdout == "\n"
    assert "skipping malformed input" in result.stderr


@pytest.mark.unit
def test_stdin_mode_reads_longitude_first():
    """The pair is lng,lat - the reverse order is a different, valid point.

    A swapped pair does not raise, so nothing but this ordering stands between
    a caller and a confidently wrong answer.
    """
    result = run_cli("--stdin", input="4.89,52.37\n52.37,4.89\n")
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert lines[0] == "Europe/Amsterdam"
    assert lines[1] != "Europe/Amsterdam", (
        "a swapped pair must not resolve to the same zone, or this pins nothing"
    )


@pytest.mark.unit
@pytest.mark.parametrize("function_id", FUNCTION_IDS)
def test_in_memory_flag_returns_the_same_answers(function_id: int):
    """--in-memory only changes how the coordinate data is held, never the result."""
    coordinates = f"{AMSTERDAM[0]},{AMSTERDAM[1]}\n{PACIFIC[0]},{PACIFIC[1]}\n"
    mapped = run_cli("--stdin", "-f", str(function_id), input=coordinates)
    in_memory = run_cli(
        "--stdin", "--in-memory", "-f", str(function_id), input=coordinates
    )
    assert in_memory.returncode == 0, in_memory.stderr
    assert in_memory.stdout == mapped.stdout


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
    stdin_input = f"{AMSTERDAM[0]},{AMSTERDAM[1]}\n"
    module = subprocess.run(
        [sys.executable, "-m", "timezonefinder", "--stdin"],
        input=stdin_input,
        capture_output=True,
        text=True,
        check=False,
    )
    assert module.returncode == 0, module.stderr
    assert module.stdout == run_cli("--stdin", input=stdin_input).stdout
