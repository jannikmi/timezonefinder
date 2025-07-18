import subprocess
import sys
import tempfile
import os
import pytest


def run_timezonefinder_test(python_bin):
    code = "from timezonefinder import TimezoneFinder; tf = TimezoneFinder()"
    subprocess.check_call([python_bin, "-c", code])


def build_wheel():
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--upgrade",
            "pip",
            "setuptools",
            "wheel",
        ]
    )
    subprocess.check_call([sys.executable, "setup.py", "bdist_wheel"])
    wheel_dir = os.path.join(os.path.dirname(__file__), "..", "dist")
    wheels = [f for f in os.listdir(wheel_dir) if f.endswith(".whl")]
    assert wheels, "No wheel file found in dist/"
    return os.path.join(wheel_dir, wheels[0])


def build_sdist():
    subprocess.check_call([sys.executable, "setup.py", "sdist"])
    dist_dir = os.path.join(os.path.dirname(__file__), "..", "dist")
    sdists = [f for f in os.listdir(dist_dir) if f.endswith(".tar.gz")]
    assert sdists, "No sdist file found in dist/"
    return os.path.join(dist_dir, sdists[0])


def test_install_from_wheel():
    wheel_path = build_wheel()
    with tempfile.TemporaryDirectory() as tempdir:
        venv_dir = os.path.join(tempdir, "venv")
        subprocess.check_call([sys.executable, "-m", "venv", venv_dir])
        python_bin = os.path.join(venv_dir, "bin", "python")
        pip_bin = os.path.join(venv_dir, "bin", "pip")
        subprocess.check_call([python_bin, "-m", "pip", "install", "--upgrade", "pip"])
        subprocess.check_call([pip_bin, "install", wheel_path])
        try:
            run_timezonefinder_test(python_bin)
        except subprocess.CalledProcessError:
            pytest.fail("Failed to run TimezoneFinder from installed wheel")


def test_install_from_sdist():
    sdist_path = build_sdist()
    with tempfile.TemporaryDirectory() as tempdir:
        venv_dir = os.path.join(tempdir, "venv")
        subprocess.check_call([sys.executable, "-m", "venv", venv_dir])
        python_bin = os.path.join(venv_dir, "bin", "python")
        pip_bin = os.path.join(venv_dir, "bin", "pip")
        subprocess.check_call([python_bin, "-m", "pip", "install", "--upgrade", "pip"])
        subprocess.check_call([pip_bin, "install", sdist_path])
        try:
            run_timezonefinder_test(python_bin)
        except subprocess.CalledProcessError:
            pytest.fail("Failed to run TimezoneFinder from installed sdist")


def test_install_from_source():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    with tempfile.TemporaryDirectory() as tempdir:
        venv_dir = os.path.join(tempdir, "venv")
        subprocess.check_call([sys.executable, "-m", "venv", venv_dir])
        python_bin = os.path.join(venv_dir, "bin", "python")
        pip_bin = os.path.join(venv_dir, "bin", "pip")
        subprocess.check_call([python_bin, "-m", "pip", "install", "--upgrade", "pip"])
        subprocess.check_call([pip_bin, "install", project_root])
        try:
            run_timezonefinder_test(python_bin)
        except subprocess.CalledProcessError:
            pytest.fail("Failed to run TimezoneFinder from pip install .")
