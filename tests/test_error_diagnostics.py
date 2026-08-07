"""tests pinning what the error paths actually report

These cover diagnostics rather than control flow: the exception type and the fact that
something is raised were already exercised elsewhere, what was unverified is whether the
message and the exception chain name the offending input.
"""

import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from scripts.helper_classes import Boundaries
from scripts.reporting import load_binary_data
from scripts.timezone_data import PolygonCollection
from tests.auxiliaries import run_command
from tests.test_flatbuf_format_guard import build_collection
from timezonefinder import TimezoneFinder
from timezonefinder.configs import DEFAULT_DATA_DIR
from timezonefinder.flatbuf.io.polygons import get_coordinate_path
from timezonefinder.utils import get_boundaries_dir

# Echoes a marker on each stream, then fails. The markers are split across implicitly
# concatenated literals so that neither appears verbatim in the snippet itself:
# ``run_command`` echoes the command line it is about to run, and a marker visible there
# would satisfy the assertions below without the child's output being reported at all.
FAILING_SNIPPET = (
    "import sys; "
    "sys.stdout.write('STDOUT_' 'MARKER'); "
    "sys.stderr.write('STDERR_' 'MARKER'); "
    "sys.exit(3)"
)
STDOUT_MARKER = "STDOUT_MARKER"
STDERR_MARKER = "STDERR_MARKER"
assert STDOUT_MARKER not in FAILING_SNIPPET
assert STDERR_MARKER not in FAILING_SNIPPET


@pytest.mark.unit
def test_run_command_reports_the_child_output(capsys):
    """A failing captured command must surface the streams it swallowed.

    ``CalledProcessError.__str__`` carries only the exit code, and with
    ``capture_output`` the child's streams never reach the terminal either, so a
    packaging failure under ``make testint`` would otherwise report nothing usable.
    """
    with pytest.raises(subprocess.CalledProcessError) as exc_info:
        run_command([sys.executable, "-c", FAILING_SNIPPET], capture_output=True)

    error = exc_info.value
    assert error.returncode == 3
    # the original exception is re-raised, so its captured streams stay attached
    assert STDOUT_MARKER in error.stdout
    assert STDERR_MARKER in error.stderr

    printed = capsys.readouterr().out
    assert STDOUT_MARKER in printed
    assert STDERR_MARKER in printed


@pytest.mark.unit
def test_run_command_stays_quiet_without_capture(capsys):
    """Without ``capture_output`` the child already wrote to the terminal itself."""
    with pytest.raises(subprocess.CalledProcessError):
        run_command([sys.executable, "-c", FAILING_SNIPPET], capture_output=False)

    assert "of failed command" not in capsys.readouterr().out


def _mirror_data_dir(source: Path, destination: Path) -> None:
    """Symlink every packaged data file into ``destination``, so a single one can be
    replaced without copying the whole (large) binary data directory."""
    for item in sorted(source.rglob("*")):
        target = destination / item.relative_to(source)
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(item)


@pytest.mark.unit
def test_report_generation_names_the_incompatible_file(tmp_path):
    """``make reports`` against a stale data directory must say which file was stale.

    The layout guard can only name the file it was handed one, and the reporting call
    sites are the ones that used to omit it.
    """
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _mirror_data_dir(DEFAULT_DATA_DIR, data_dir)

    stale_file = get_coordinate_path(get_boundaries_dir(data_dir))
    stale_file.unlink()  # drop the symlink, do not write through it
    stale_file.write_bytes(build_collection(with_identifier=False, layout_version=None))

    with pytest.raises(ValueError) as exc_info:
        load_binary_data(data_dir)

    assert str(stale_file) in str(exc_info.value)


@pytest.mark.unit
def test_overlaps_names_the_rejected_argument():
    box = Boundaries(xmax=1.0, xmin=0.0, ymax=1.0, ymin=0.0)
    with pytest.raises(TypeError) as exc_info:
        box.overlaps((1.0, 0.0, 1.0, 0.0))  # type: ignore[arg-type]

    message = str(exc_info.value)
    assert "tuple" in message
    assert "Boundaries" in message


@pytest.mark.unit
def test_unknown_zone_name_error_is_deliberately_unchained(tf: TimezoneFinder):
    """``list.index``'s "x is not in list" adds nothing, so it is suppressed on purpose.

    Pinned because an unchained raise is indistinguishable from a forgotten ``from``.
    """
    with pytest.raises(ValueError) as exc_info:
        tf.get_geometry(tz_name="Nonexistent/Zone")

    error = exc_info.value
    assert "Nonexistent/Zone" in str(error)
    assert error.__cause__ is None
    assert error.__suppress_context__


@pytest.mark.unit
def test_missing_original_polygons_names_the_polygon():
    """The cache miss that enters the handler is not the cause of the failure."""
    triangle = np.array([[0, 1, 0], [0, 0, 1]], dtype=np.int32)
    collection = PolygonCollection(polygons=[triangle], lengths=[3])
    assert collection.original_polygons is None

    with pytest.raises(RuntimeError) as exc_info:
        collection.polygon_vertex_hexes(poly_nr=0, res=3)

    error = exc_info.value
    message = str(error)
    assert "polygon 0" in message
    assert "resolution 3" in message
    assert error.__cause__ is None
    assert error.__suppress_context__
