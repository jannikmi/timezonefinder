import subprocess
import sys
from pathlib import Path
import pytest


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


@pytest.mark.parametrize(
    "script_name",
    get_example_scripts(),
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
