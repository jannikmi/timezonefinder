import json
import subprocess
from pathlib import Path

import pytest

from timezonefinder.configs import TIMEZONE_NAMES_FILE

PROJECT_DIR = Path(__file__).parent.parent
TIMEZONE_FILE = PROJECT_DIR / "timezonefinder" / TIMEZONE_NAMES_FILE
with open(TIMEZONE_FILE, "r") as json_file:
    timezone_names = json.loads(json_file.read())


@pytest.mark.parametrize(
    "cmd",
    [
        "timezonefinder 40.5 11.7",
        "timezonefinder -f 0 40.5 11.7",
        "timezonefinder -f 1 40.5 11.7",
        "timezonefinder -f 3 40.5 11.7",
        "timezonefinder -f 4 40.5 11.7",
        "timezonefinder -f 5 40.5 11.7",
    ],
)
def test_main(cmd: str):
    res = subprocess.getoutput(cmd).rstrip("\n\x1b[0m")
    assert not res.endswith("command not found"), "package not installed"
    assert res == "None" or res in timezone_names
