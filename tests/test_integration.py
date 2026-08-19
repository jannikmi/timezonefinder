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

import shutil
import sys
from pathlib import Path

import pytest

from scripts.configs import DATA_DISTRIBUTION_NAME, DATA_PACKAGE_ROOT, PROJECT_ROOT
from tests.auxiliaries import (
    DIST_DIR,
    ROOT_DISTRIBUTION_NAME,
    build_sdist,
    build_wheel,
    run_command,
)

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration

# Define additional path constants
BIN_DIR = "Scripts" if sys.platform == "win32" else "bin"


def run_timezonefinder_test(python_bin: str) -> None:
    """Test importing and instantiating TimezoneFinder."""
    code = "from timezonefinder import TimezoneFinder; tf = TimezoneFinder(); print(tf.timezone_at(lat=40.5, lng=11.7))"
    run_command([python_bin, "-c", code])


def setup_venv(tempdir: str, upgrade_pip: bool = False) -> tuple[str, str]:
    """Set up a virtual environment and return paths to python and pip binaries.

    The venv is created from ``sys.executable`` because that is what
    ``BUILD_CMD`` pins the wheel build to; the wheel is only installable here
    while both name the same interpreter. Change one and you must change the
    other - ``test_build_commands_pin_the_running_interpreter`` guards the pin.
    """
    venv_dir = Path(tempdir) / "venv"
    run_command([sys.executable, "-m", "venv", str(venv_dir)])

    python_bin = str(venv_dir / BIN_DIR / "python")
    pip_bin = str(venv_dir / BIN_DIR / "pip")

    if upgrade_pip:
        run_command([python_bin, "-m", "pip", "install", "--upgrade", "pip"])

    return python_bin, pip_bin


def reinstall_and_test(package_path: Path, python_bin: str, pip_bin: str) -> None:
    """Reinstall timezonefinder from the given package and run a smoke test.

    ``--find-links`` is what makes the data dependency resolvable: ``timezonefinder``
    requires ``timezonefinder-data``, and this branch's build of it exists only in
    ``dist/``. Leaving pip to the index would either fail (before the first data
    release) or silently install a *published* dataset rather than the one this
    checkout produced, which is the opposite of what an install check should assert.
    """
    run_command(
        [pip_bin, "uninstall", "-y", ROOT_DISTRIBUTION_NAME, DATA_DISTRIBUTION_NAME]
    )
    run_command([pip_bin, "install", "--find-links", str(DIST_DIR), str(package_path)])
    run_timezonefinder_test(python_bin)


@pytest.fixture(scope="session")
def venv_bins(tmp_path_factory) -> tuple[str, str]:
    """Create a single virtual environment reused across package install checks."""
    tempdir = tmp_path_factory.mktemp("integration-venv")
    return setup_venv(str(tempdir), upgrade_pip=False)


@pytest.fixture(scope="session")
def package_paths() -> dict[str, Path]:
    """Build artifacts once and return all package paths.

    The data wheel is built alongside the code artefacts even though no case
    installs it directly: every case resolves it out of ``dist/`` as a dependency.
    """
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)

    wheel_path = build_wheel(clean_dist=True)
    build_wheel(
        clean_dist=False,
        package=DATA_DISTRIBUTION_NAME,
        source_root=DATA_PACKAGE_ROOT,
    )
    sdist_path = build_sdist(clean_dist=False)
    return {
        "wheel": wheel_path,
        "sdist": sdist_path,
        "source": PROJECT_ROOT,
    }


@pytest.mark.parametrize("package_key", ["wheel", "sdist", "source"])
def test_install_from_artifacts(
    package_key: str, package_paths: dict[str, Path], venv_bins: tuple[str, str]
) -> None:
    python_bin, pip_bin = venv_bins
    package_path = package_paths[package_key]
    reinstall_and_test(package_path, python_bin, pip_bin)
