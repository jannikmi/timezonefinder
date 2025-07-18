import subprocess
import sys
import tempfile
import os
import pytest

# List of modules/subpackages that should be importable after installation
REQUIRED_MODULES = [
    "timezonefinder.flatbuf",
    "timezonefinder.inside_poly_extension",
    "timezonefinder.zone_names",
    "timezonefinder.utils",
    "timezonefinder.utils_numba",
    "timezonefinder.utils_clang",
]


def run_timezonefinder_test(python_bin):
    code = "from timezonefinder import TimezoneFinder; tf = TimezoneFinder()"
    subprocess.check_call([python_bin, "-c", code])


def check_module_imports(python_bin, modules_list):
    """Test that all required modules can be imported after installation."""
    for module in modules_list:
        code = f"import {module}"
        try:
            subprocess.check_call([python_bin, "-c", code])
        except subprocess.CalledProcessError:
            return module  # Return the module that failed to import
    return None  # All imports succeeded


def check_package_structure(python_bin):
    """Verify the installed package structure has all expected subpackages and files."""
    code = """
import os
import sys
import timezonefinder

# Check package structure
tf_dir = os.path.dirname(timezonefinder.__file__)

# Check for subpackages
required_dirs = ['flatbuf', 'inside_poly_extension', 'data']
missing_dirs = [d for d in required_dirs if not os.path.isdir(os.path.join(tf_dir, d))]

if missing_dirs:
    sys.exit(f"Missing directories: {missing_dirs}")

# Check for critical files
required_files = ['timezonefinder.py', 'utils.py', 'zone_names.py']
missing_files = [f for f in required_files if not os.path.isfile(os.path.join(tf_dir, f))]

if missing_files:
    sys.exit(f"Missing files: {missing_files}")

# Check that flatbuf has expected modules
flatbuf_dir = os.path.join(tf_dir, 'flatbuf')
required_flatbuf_files = ['__init__.py', 'Polygon.py', 'PolygonCollection.py', 'ShortcutCollection.py']
missing_flatbuf_files = [f for f in required_flatbuf_files if not os.path.isfile(os.path.join(flatbuf_dir, f))]

if missing_flatbuf_files:
    sys.exit(f"Missing flatbuf files: {missing_flatbuf_files}")
"""
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

            # Check all required modules can be imported
            failed_module = check_module_imports(python_bin, REQUIRED_MODULES)
            assert failed_module is None, (
                f"Failed to import {failed_module} from wheel installation"
            )

            # Verify package structure
            check_package_structure(python_bin)

        except subprocess.CalledProcessError as e:
            pytest.fail(f"Failed to run TimezoneFinder from installed wheel: {str(e)}")


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

            # Check all required modules can be imported
            failed_module = check_module_imports(python_bin, REQUIRED_MODULES)
            assert failed_module is None, (
                f"Failed to import {failed_module} from sdist installation"
            )

            # Verify package structure
            check_package_structure(python_bin)

        except subprocess.CalledProcessError as e:
            pytest.fail(f"Failed to run TimezoneFinder from installed sdist: {str(e)}")


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

            # Check all required modules can be imported
            failed_module = check_module_imports(python_bin, REQUIRED_MODULES)
            assert failed_module is None, (
                f"Failed to import {failed_module} from source installation"
            )

            # Verify package structure
            check_package_structure(python_bin)

        except subprocess.CalledProcessError as e:
            pytest.fail(f"Failed to run TimezoneFinder from pip install: {str(e)}")


def test_wheel_contains_required_files():
    """Test that wheel distribution contains all required files."""
    wheel_path = build_wheel()

    with tempfile.TemporaryDirectory() as tempdir:
        # Extract wheel contents
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--no-deps",
                "--target",
                tempdir,
                wheel_path,
            ]
        )

        # Check for the presence of flatbuf package
        flatbuf_dir = os.path.join(tempdir, "timezonefinder", "flatbuf")
        assert os.path.isdir(flatbuf_dir), (
            f"flatbuf directory not found in wheel: {flatbuf_dir}"
        )

        # Verify __init__.py exists in flatbuf directory
        init_file = os.path.join(flatbuf_dir, "__init__.py")
        assert os.path.isfile(init_file), "__init__.py missing in flatbuf directory"

        # Check for specific flatbuf modules
        required_modules = [
            "Polygon.py",
            "PolygonCollection.py",
            "ShortcutCollection.py",
        ]
        for module in required_modules:
            module_path = os.path.join(flatbuf_dir, module)
            assert os.path.isfile(module_path), f"{module} missing in flatbuf directory"
