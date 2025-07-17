import subprocess
import sys
import pytest


@pytest.mark.parametrize(
    "script_name",
    [
        "aware_datetime",
        "get_offset",
        "get_geometry",
    ],
)
def test_example_script_runs(script_name):
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
