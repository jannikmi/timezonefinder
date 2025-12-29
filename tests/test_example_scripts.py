import subprocess
import sys
from pathlib import Path
import pytest

# Scripts that require pytz to run
PYTZ_REQUIRED_SCRIPTS = {"aware_datetime", "get_offset"}


def get_example_scripts():
    examples_dir = Path(__file__).parent.parent / "examples"
    scripts = []
    for file_path in examples_dir.iterdir():
        if (
            file_path.is_file()
            and file_path.suffix == ".py"
            and not file_path.name.startswith("__")
        ):
            scripts.append(file_path.stem)
    return scripts


def has_pytz():
    """Check if pytz is available."""
    try:
        import pytz  # noqa: F401

        return True
    except ImportError:
        return False


@pytest.mark.examples
@pytest.mark.parametrize(
    "script_name",
    get_example_scripts(),
)
def test_example_script_runs(script_name):
    # Skip scripts that require pytz when pytz is not available
    if script_name in PYTZ_REQUIRED_SCRIPTS and not has_pytz():
        pytest.skip(f"Script {script_name} requires pytz, but pytz is not available")

    module_name = f"examples.{script_name}"
    print(f"Running {module_name} script:")
    result = subprocess.run(
        [sys.executable, "-m", module_name],
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    print(result.stderr)
    assert result.returncode == 0, f"Script failed: {result.stderr}"
