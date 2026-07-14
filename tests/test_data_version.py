"""Tests for the DATA_VERSION file tracking the packaged boundary data release.

The file is read by .github/workflows/check_data_updates.yml to detect new
timezone-boundary-builder releases and written by parse_data.sh on data updates.
"""

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_VERSION_FILE = PROJECT_ROOT / "DATA_VERSION"

# release tags of timezone-boundary-builder, e.g. "2026c"
DATA_VERSION_PATTERN = re.compile(r"\d{4}[a-z]+")


def test_data_version_file_exists():
    assert DATA_VERSION_FILE.is_file(), (
        "DATA_VERSION file is missing from the project root"
    )


def test_data_version_format():
    content = DATA_VERSION_FILE.read_text(encoding="utf-8").strip()
    assert DATA_VERSION_PATTERN.fullmatch(content), (
        f"DATA_VERSION content {content!r} does not match the "
        "timezone-boundary-builder release tag format (e.g. '2026c')"
    )
