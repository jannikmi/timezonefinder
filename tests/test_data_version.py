"""Tests for the DATA_VERSION file tracking the packaged boundary data release.

The file is read by .github/workflows/check_data_updates.yml to detect new
timezone-boundary-builder releases and written by update_data.sh on data updates.
"""

import re

from scripts.configs import DATA_REPORT_FILE, DATA_VERSION_FILE, read_data_version
from scripts.reporting import DATA_VERSION_LABEL

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


def test_committed_data_report_states_the_packaged_data_version():
    # every figure in the data report is derived from the packaged binaries, so
    # a data update shifts all of them while leaving each one plausible. The
    # stamp is what makes a report left behind by an update visibly stale
    # instead of quietly wrong.
    data_version = read_data_version()
    text = DATA_REPORT_FILE.read_text(encoding="utf-8")

    assert f"{DATA_VERSION_LABEL}: {data_version}" in text, (
        f"{DATA_REPORT_FILE.name} does not state {DATA_VERSION_LABEL}: "
        f"{data_version} - it describes different boundary data. Regenerate it "
        "with `uv run python -m scripts.reporting`."
    )
