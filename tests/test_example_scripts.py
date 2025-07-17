import subprocess
import sys


def test_aware_datetime_runs():
    result = subprocess.run(
        [sys.executable, "-m", "examples.aware_datetime"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Script failed: {result.stderr}"


def test_get_offset_runs():
    result = subprocess.run(
        [sys.executable, "-m", "examples.get_offset"], capture_output=True, text=True
    )
    assert result.returncode == 0, f"Script failed: {result.stderr}"


def test_get_geometry_runs():
    result = subprocess.run(
        [sys.executable, "-m", "examples.get_geometry"], capture_output=True, text=True
    )
    assert result.returncode == 0, f"get_geometry.py failed:\n{result.stderr}"
