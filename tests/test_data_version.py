"""Tests for the DATA_VERSION file tracking the packaged boundary data release.

The file is read by .github/workflows/check_data_updates.yml to detect new
timezone-boundary-builder releases and written by update_data.sh on data updates.
"""

import re
import shutil
import tomllib

import pytest

import timezonefinder
from scripts.configs import (
    DATA_REPORT_FILE,
    DATA_VERSION_FILE,
    DEFAULT_INPUT_PATH,
    PROJECT_ROOT,
    PYPROJECT_FILE,
    UPSTREAM_INPUT_STEMS,
    read_data_version,
    resolve_data_version,
)
from scripts.reporting import DATA_VERSION_LABEL
from timezonefinder import TimezoneFinder
from timezonefinder.configs import (
    DATA_VERSION_FILENAME,
    DEFAULT_DATA_DIR,
    UNKNOWN_DATA_VERSION,
)

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
        f"repo-root DATA_VERSION ({read_data_version()!r}). If the packaged "
        "binaries are the ones DATA_VERSION names, copy the tag across:\n"
        f"    cp {DATA_VERSION_FILE.name} {DEFAULT_DATA_DIR.relative_to(PROJECT_ROOT)}/{DATA_VERSION_FILENAME}\n"
        "Only regenerate the data (`update_data.sh`) if they are not - that "
        "downloads the boundary release and takes hours."
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


def test_package_exposes_the_declared_version():
    # the package itself must state its own version - previously it did not
    # (hasattr(timezonefinder, "__version__") was False), which is why
    # scripts/benchmark_utils.py fell back to "Unknown" for every report.
    #
    # Compared against what pyproject.toml declares rather than merely against the
    # "unknown" fallback: __version__ comes from the *installed* distribution's
    # metadata, so an environment left behind by a version bump answers with the
    # previous release - which is not the fallback, reads like a real answer, and
    # is what every benchmark report would then record.
    assert hasattr(timezonefinder, "__version__"), (
        "timezonefinder.__version__ is not exposed"
    )
    declared = tomllib.loads(PYPROJECT_FILE.read_text(encoding="utf-8"))["project"][
        "version"
    ]
    assert timezonefinder.__version__ == declared, (
        f"timezonefinder.__version__ is {timezonefinder.__version__!r}, but "
        f"pyproject.toml declares {declared!r}. The installed distribution's "
        "metadata is stale (or missing, reading as 'unknown') - re-sync the "
        "environment with `uv sync --all-groups`."
    )


def test_a_tagged_input_states_its_own_release():
    # the normal path: update_data.sh names its download after the release it
    # resolved, and the parse reads it back off the name
    assert resolve_data_version(DEFAULT_INPUT_PATH) == read_data_version()
    assert resolve_data_version("/anywhere/combined-with-oceans-2099z.json") == "2099z"
    assert resolve_data_version("/anywhere/combined-now-2099z.json") == "2099z"


@pytest.mark.parametrize("stem", sorted(UPSTREAM_INPUT_STEMS))
def test_an_untagged_upstream_file_is_refused(stem):
    # the failure this exists to stop is silent and permanent: an unpacked release
    # that lost its tag would compile into data whose data_version says "unknown"
    # forever, when the answer was knowable at that moment
    with pytest.raises(ValueError, match="does not say which release it is"):
        resolve_data_version(f"tmp/{stem}.json")


def test_the_refusal_names_both_ways_out():
    with pytest.raises(ValueError) as excinfo:
        resolve_data_version("tmp/combined-with-oceans.json")
    message = str(excinfo.value)
    assert "tmp/combined-with-oceans-<release>.json" in message, (
        "the error must show the rename, since that is the fix that sticks to the file"
    )
    assert "--data-version" in message, (
        "the error must name the flag too, for an input that cannot be renamed"
    )


def test_data_that_is_not_a_release_is_stamped_unattributed():
    # compiling your own GeoJSON is supported (docs/2_use_cases.rst) and has no
    # release to name - "unknown" is the true answer, not a gap
    assert resolve_data_version("my_boundaries.json") == UNKNOWN_DATA_VERSION
    assert resolve_data_version("tests/test_input.json") == UNKNOWN_DATA_VERSION


def test_an_explicitly_named_release_wins():
    # for an input that cannot carry the release in its name
    assert resolve_data_version("my_boundaries.json", "2099z") == "2099z"
    assert resolve_data_version("tmp/combined-with-oceans.json", "2099z") == "2099z"


def test_a_data_directory_without_a_stamp_says_how_to_fix_it(tmp_path):
    # a data directory compiled before the stamp existed loads and answers lookups
    # as it always did, so the one thing that fails has to say why on its own
    data_dir = tmp_path / "data"
    shutil.copytree(DEFAULT_DATA_DIR, data_dir)
    (data_dir / DATA_VERSION_FILENAME).unlink()

    with TimezoneFinder(bin_file_location=data_dir) as tf:
        with pytest.raises(FileNotFoundError, match="no dataset version stamp"):
            tf.data_version
