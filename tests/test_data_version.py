"""Tests for the DATA_VERSION file tracking the packaged boundary data release.

The file is read by .github/workflows/check_data_updates.yml to detect new
timezone-boundary-builder releases and written by update_data.sh on data updates.
"""

import re

import timezonefinder
from scripts.configs import DATA_REPORT_FILE, DATA_VERSION_FILE, read_data_version
from scripts.reporting import DATA_VERSION_LABEL
from timezonefinder import TimezoneFinder
from timezonefinder.configs import DATA_VERSION_FILENAME, DEFAULT_DATA_DIR

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


def test_packaged_data_version_file_matches_repo_root():
    # the runtime stamp (timezonefinder/data/data_version.txt) and the
    # build-source stamp (repo-root DATA_VERSION) are two copies of the same
    # fact: which boundary data release is packaged. A data update writes both
    # via update_data.sh; if the two drift, AbstractTimezoneFinder.data_version
    # answers from a different release than CI's update-detection reads.
    packaged = (
        (DEFAULT_DATA_DIR / DATA_VERSION_FILENAME).read_text(encoding="utf-8").strip()
    )
    assert packaged == read_data_version(), (
        f"packaged data version stamp ({packaged!r}) disagrees with the "
        f"repo-root DATA_VERSION ({read_data_version()!r}). Regenerate the "
        "packaged data with `uv run python -m scripts.file_converter` so the "
        "two stay in sync."
    )


def test_finder_exposes_packaged_data_version():
    # the public runtime surface - an installed timezonefinder stating which
    # dataset it answers from. Reads the packaged stamp, not the repo-root
    # file, so it works against a built wheel that ships no repo-root file.
    with TimezoneFinder() as tf:
        assert tf.data_version == read_data_version(), (
            f"TimezoneFinder().data_version is {tf.data_version!r}, but the "
            f"repo-root DATA_VERSION is {read_data_version()!r}."
        )


def test_package_exposes_version():
    # the package itself must state its own version - previously it did not
    # (hasattr(timezonefinder, "__version__") was False), which is why
    # scripts/benchmark_utils.py fell back to "Unknown" for every report.
    assert hasattr(timezonefinder, "__version__"), (
        "timezonefinder.__version__ is not exposed"
    )
    assert timezonefinder.__version__ != "unknown", (
        f"timezonefinder.__version__ is {timezonefinder.__version__!r}; the "
        "package must be installed for importlib.metadata to resolve its version."
    )
