"""
Integration tests for the timezonefinder package installation and functionality.

This module contains tests that verify the correct installation and basic functionality
of the package through different distribution methods:
- Installation from a wheel package
- Installation from a source distribution (sdist)
- Installation directly from the source code

Each test creates a fresh virtual environment, installs the package using the specified
method, and then performs a basic test to ensure that the package can be imported and
that its core functionality works properly.
"""

import sys
import tempfile
from pathlib import Path
from typing import Tuple
import pytest

from scripts.configs import PROJECT_ROOT

from tests.auxiliaries import build_sdist, build_wheel, run_command

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration

# Define additional path constants
BIN_DIR = "Scripts" if sys.platform == "win32" else "bin"


def run_timezonefinder_test(python_bin: str) -> None:
    """Test importing and instantiating TimezoneFinder."""
    code = "from timezonefinder import TimezoneFinder; tf = TimezoneFinder(); print(tf.timezone_at(lat=40.5, lng=11.7))"
    run_command([python_bin, "-c", code])


def setup_venv(tempdir: str) -> Tuple[str, str]:
    """Set up a virtual environment and return paths to python and pip binaries."""
    venv_dir = Path(tempdir) / "venv"
    run_command([sys.executable, "-m", "venv", str(venv_dir)])

    python_bin = str(venv_dir / BIN_DIR / "python")
    pip_bin = str(venv_dir / BIN_DIR / "pip")

    # Upgrade pip
    run_command([python_bin, "-m", "pip", "install", "--upgrade", "pip"])

    return python_bin, pip_bin


def check_install_package(package_path: Path) -> None:
    """
    Generic test function for installing and testing timezonefinder.

    Args:
        package_path: path to project for direct installation
    """
    with tempfile.TemporaryDirectory() as tempdir:
        temp_path = Path(tempdir)
        # Setup virtual environment
        python_bin, pip_bin = setup_venv(str(temp_path))

        # Install the package
        run_command([pip_bin, "install", str(package_path)])

        run_timezonefinder_test(python_bin)


def test_install_from_wheel():
    package_path = build_wheel()
    check_install_package(
        package_path,
    )


def test_install_from_sdist():
    package_path = build_sdist()
    check_install_package(
        package_path,
    )


def test_install_from_source():
    check_install_package(PROJECT_ROOT)
