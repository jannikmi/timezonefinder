"""Tests for ensuring the package can be installed and used from distributions.

Run the test with:
    uv run pytest tests/test_distributions.py -v
"""

import subprocess
import tempfile
import sys
import pytest
from pathlib import Path


def test_sdist_installation():
    """Test that the package can be installed and used from an sdist distribution."""
    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Build the sdist package
        build_cmd = ["uv", "build", "-v", "--sdist", "--outdir", temp_dir]
        subprocess.check_call(build_cmd, cwd=str(Path(__file__).parent.parent))

        # Find the generated sdist file
        sdist_files = list(temp_path.glob("*.tar.gz"))
        assert sdist_files, "No sdist package was created"
        sdist_path = sdist_files[0]

        # Create a virtual environment for testing the installation
        venv_path = temp_path / "venv"
        subprocess.check_call([sys.executable, "-m", "venv", str(venv_path)])

        # Get the path to python in the virtual environment
        if sys.platform == "win32":
            python_bin = str(venv_path / "Scripts" / "python.exe")
        else:
            python_bin = str(venv_path / "bin" / "python")

        # Install the sdist package
        subprocess.check_call([python_bin, "-m", "pip", "install", str(sdist_path)])

        # Test that the package can be used
        test_code = "from timezonefinder import TimezoneFinder; tf = TimezoneFinder()"
        try:
            subprocess.check_call([python_bin, "-c", test_code])
        except subprocess.CalledProcessError as e:
            pytest.fail(f"Failed to import and instantiate TimezoneFinder: {e}")

        # Test basic functionality
        test_code_london = (
            "from timezonefinder import TimezoneFinder; "
            "tf = TimezoneFinder(); "
            "tz = tf.timezone_at(lat=51.5, lng=-0.1); "
            "assert tz == 'Europe/London', f'Expected Europe/London, got {tz}'"
        )
        try:
            subprocess.check_call([python_bin, "-c", test_code_london])
        except subprocess.CalledProcessError as e:
            pytest.fail(f"TimezoneFinder failed basic functionality test: {e}")


def test_wheel_installation():
    """Test that the package can be installed and used from a wheel distribution."""
    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Build the wheel package
        build_cmd = ["uv", "build", "-v", "--wheel", "--outdir", temp_dir]
        subprocess.check_call(build_cmd, cwd=str(Path(__file__).parent.parent))

        # Find the generated wheel file
        wheel_files = list(temp_path.glob("*.whl"))
        assert wheel_files, "No wheel package was created"
        wheel_path = wheel_files[0]

        # Create a virtual environment for testing the installation
        venv_path = temp_path / "venv"
        subprocess.check_call([sys.executable, "-m", "venv", str(venv_path)])

        # Get the path to python in the virtual environment
        if sys.platform == "win32":
            python_bin = str(venv_path / "Scripts" / "python.exe")
        else:
            python_bin = str(venv_path / "bin" / "python")

        # Install the wheel package
        subprocess.check_call([python_bin, "-m", "pip", "install", str(wheel_path)])

        # Test that the package can be used
        test_code = "from timezonefinder import TimezoneFinder; tf = TimezoneFinder()"
        try:
            subprocess.check_call([python_bin, "-c", test_code])
        except subprocess.CalledProcessError as e:
            pytest.fail(f"Failed to import and instantiate TimezoneFinder: {e}")

        # Test basic functionality
        test_code_ny = (
            "from timezonefinder import TimezoneFinder; "
            "tf = TimezoneFinder(); "
            "tz = tf.timezone_at(lat=40.7, lng=-74.0); "
            "assert tz == 'America/New_York', f'Expected America/New_York, got {tz}'"
        )
        try:
            subprocess.check_call([python_bin, "-c", test_code_ny])
        except subprocess.CalledProcessError as e:
            pytest.fail(f"TimezoneFinder failed basic functionality test: {e}")


if __name__ == "__main__":
    # Allow direct execution of this test module
    pytest.main([__file__])
