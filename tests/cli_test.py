import subprocess

import pytest

from timezonefinder.configs import DEFAULT_DATA_DIR
from timezonefinder.zone_names import read_zone_names

timezone_names = read_zone_names(DEFAULT_DATA_DIR)


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
    run_result = subprocess.run(cmd, shell=True, check=True, capture_output=True)
    res = run_result.stdout.decode("utf-8").rstrip("\n\x1b[0m")
    assert not res.endswith("command not found"), "package not installed"
    assert res == "None" or res in timezone_names
