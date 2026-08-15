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


def run_cli(*args: str) -> subprocess.CompletedProcess:
    """Run the installed console script.

    Invoked as an argument list rather than through a shell, so that an
    argument is passed through verbatim and a missing entry point raises
    ``FileNotFoundError`` here instead of turning into a shell error message
    that has to be recognised in the captured output.
    """
    return subprocess.run(
        ["timezonefinder", *args], capture_output=True, text=True, check=False
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
    result = subprocess.run(
        [sys.executable, "-m", "timezonefinder", "--stdin"],
        input=stdin_input,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert len(lines) == 2, f"expected 2 lines, got {lines}"
    assert lines[0] == "Europe/Amsterdam"
    assert lines[1] == "Etc/GMT+10"


@pytest.mark.unit
def test_stdin_mode_respects_function_flag():
    """-f applies to every lookup in the stream."""
    stdin_input = f"{AMSTERDAM[0]},{AMSTERDAM[1]}\n"
    result = subprocess.run(
        [sys.executable, "-m", "timezonefinder", "--stdin", "-f", "5"],
        input=stdin_input,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert len(lines) == 1
    assert lines[0] == "Europe/Amsterdam"


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
    result = subprocess.run(
        [sys.executable, "-m", "timezonefinder", "--stdin"],
        input=stdin_input,
        capture_output=True,
        text=True,
        check=False,
    )
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
    result = subprocess.run(
        [sys.executable, "-m", "timezonefinder", "--stdin"],
        input="",
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""


@pytest.mark.unit
def test_stdin_mode_land_only_returns_empty_for_ocean():
    """Land-only lookups in stdin mode print an empty line for ocean points."""
    stdin_input = f"{PACIFIC[0]},{PACIFIC[1]}\n"
    result = subprocess.run(
        [sys.executable, "-m", "timezonefinder", "--stdin", "-f", "5"],
        input=stdin_input,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == "\n"


@pytest.mark.unit
def test_stdin_and_verbose_are_mutually_exclusive():
    """--stdin and -v cannot be used together."""
    result = run_cli("--stdin", "-v", "0", "0")
    assert result.returncode == 2
    assert "mutually exclusive" in result.stderr
