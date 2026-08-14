"""Keep every Python invocation of a `scripts/` module in the `-m` module form.

`scripts/` is a package: its modules import each other as `scripts.<module>`.
Running one by path (`python ./scripts/file_converter.py`) puts `scripts/` itself
on `sys.path[0]` rather than the repository root, so the first such import raises
`ModuleNotFoundError: No module named 'scripts'` before any work starts.

The failure is total but invisible from CI, which runs neither `make parse` nor
`make testparse` - both sat broken until someone regenerated the packaged data by
hand. `make testparse` is the only cheap end-to-end exercise of the converter, so
while it is broken the converter has no smoke test at all.
"""

import re
from pathlib import Path

import pytest

from tests.auxiliaries import PROJECT_ROOT

# Files that invoke the converter or its siblings as shell commands.
INVOKING_FILES = ("Makefile", "update_data.sh")

# `python <anything>/scripts/<module>.py` - a path invocation, whatever the
# interpreter prefix (`uv run python`, `python3`, ...) or leading `./`.
BY_PATH_INVOCATION = re.compile(r"python[0-9.]*\s+(?:[^\s]*/)?scripts/[\w/]+\.py")


@pytest.mark.parametrize("filename", INVOKING_FILES)
@pytest.mark.unit
def test_scripts_are_invoked_as_modules(filename: str) -> None:
    """No file may run a `scripts/` module by path instead of with `-m`."""
    path: Path = PROJECT_ROOT / filename
    offenders = [
        line.strip()
        for line in path.read_text().splitlines()
        # Comments name the by-path form to explain why it is wrong.
        if not line.lstrip().startswith("#") and BY_PATH_INVOCATION.search(line)
    ]
    assert not offenders, (
        f"{filename} invokes a scripts/ module by path, which cannot resolve its "
        f"own `scripts.*` imports. Use `python -m scripts.<module>` instead: {offenders}"
    )
