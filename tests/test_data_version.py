"""Tests for the DATA_VERSION file tracking the packaged boundary data release.

The file is read by .github/workflows/check_data_updates.yml to detect new
timezone-boundary-builder releases and written by update_data.sh on data updates.
"""

import shutil
import tomllib
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

import timezonefinder
from scripts.configs import (
    DATA_DISTRIBUTION_NAME,
    DATA_PYPROJECT_FILE,
    DATA_REPORT_FILE,
    DATA_VERSION_FILE,
    DATA_VERSION_TAG_PATTERN,
    DEFAULT_INPUT_PATH,
    PROJECT_ROOT,
    PYPROJECT_FILE,
    SOURCE_DATA_DIR,
    UPSTREAM_INPUT_STEMS,
    data_distribution_version,
    read_data_version,
    resolve_data_version,
)
from scripts.reporting import DATA_VERSION_LABEL
from timezonefinder import TimezoneFinder
from timezonefinder.configs import (
    DATA_FORMAT_LAYOUT_VERSIONS,
    DATA_FORMAT_VERSION,
    DATA_VERSION_FILENAME,
    DEFAULT_DATA_DIR,
    UNKNOWN_DATA_VERSION,
)
from timezonefinder.flatbuf.io.hybrid_shortcuts import SHORTCUT_LAYOUT_VERSION
from timezonefinder.flatbuf.io.polygons import POLYGON_LAYOUT_VERSION


def _declared_version(pyproject: Path) -> str:
    return tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"]


def _declared_data_requirement() -> Requirement:
    """The root distribution's dependency on the data distribution."""
    dependencies = tomllib.loads(PYPROJECT_FILE.read_text(encoding="utf-8"))["project"][
        "dependencies"
    ]
    requirements = [
        requirement
        for requirement in map(Requirement, dependencies)
        if canonicalize_name(requirement.name) == DATA_DISTRIBUTION_NAME
    ]
    assert len(requirements) == 1, (
        f"expected exactly one {DATA_DISTRIBUTION_NAME} dependency in "
        f"{PYPROJECT_FILE.name}, found {len(requirements)}"
    )
    return requirements[0]


def test_data_version_file_exists():
    assert DATA_VERSION_FILE.is_file(), (
        "DATA_VERSION file is missing from the project root"
    )


def test_data_version_format():
    content = DATA_VERSION_FILE.read_text(encoding="utf-8").strip()
    assert DATA_VERSION_TAG_PATTERN.fullmatch(content), (
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
    # the runtime stamp (the data package's data/data_version.txt) and the
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
        f"    cp {DATA_VERSION_FILE.name} {SOURCE_DATA_DIR.relative_to(PROJECT_ROOT)}/{DATA_VERSION_FILENAME}\n"
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


@pytest.mark.parametrize(
    ("data_tag", "format_version", "expected"),
    [
        ("2026a", 1, "1.2026.1"),
        ("2026c", 1, "1.2026.3"),
        # the letter suffix is bijective base-26, not one character: upstream tags are
        # `[a-z]+` and a 27th release of a year is `aa`, which a lookup table would
        # either crash on or collide with `a`
        ("2026z", 1, "1.2026.26"),
        ("2026aa", 1, "1.2026.27"),
        ("2026ab", 1, "1.2026.28"),
        # a format bump moves the major, and only the major
        ("2026c", 2, "2.2026.3"),
    ],
)
def test_the_data_distribution_version_is_derived_from_the_release_tag(
    data_tag: str, format_version: int, expected: str
) -> None:
    assert data_distribution_version(data_tag, format_version) == expected


@pytest.mark.parametrize("data_tag", ["2026", "v2026c", "2026C", "202c", "20261"])
def test_a_version_cannot_be_derived_from_a_non_release_tag(data_tag: str) -> None:
    # update_data.sh feeds this whatever upstream tagged, and a malformed tag has to
    # stop the release rather than produce a version number that sorts arbitrarily
    with pytest.raises(ValueError, match="not a timezone-boundary-builder release"):
        data_distribution_version(data_tag)


def test_the_data_distribution_version_matches_the_packaged_release() -> None:
    # the second of the two hand-touchable copies of DATA_FORMAT_VERSION: the data
    # package's own version. update_data.sh writes it from the tag it just parsed, so
    # this catches a hand-edit and a half-applied update alike - a version naming a
    # release other than the one whose binaries sit next to it would publish data
    # under a number no consumer could use to pin it.
    assert _declared_version(DATA_PYPROJECT_FILE) == data_distribution_version(
        read_data_version()
    ), (
        f"{DATA_PYPROJECT_FILE} declares "
        f"{_declared_version(DATA_PYPROJECT_FILE)!r}, but the packaged release "
        f"{read_data_version()!r} at format version {DATA_FORMAT_VERSION} derives "
        f"{data_distribution_version(read_data_version())!r}."
    )


def test_the_declared_data_bound_brackets_the_current_format_generation() -> None:
    """The bound is the one copy of the format version a person types.

    The floor deliberately is *not* pinned to the packaged version: data updates move
    the data package forward while this bound stays put, which is the whole point of
    the split. What must hold is that both ends name the current format generation -
    a ceiling left at the old one makes the next data release uninstallable, and one
    raised early admits data this code cannot read.
    """
    specifier = _declared_data_requirement().specifier
    bounds = {spec.operator: Version(spec.version) for spec in specifier}
    assert set(bounds) == {">=", "<"}, (
        f"expected a floor and a format ceiling on {DATA_DISTRIBUTION_NAME}, got "
        f"{str(specifier)!r}"
    )

    assert bounds["<"] == Version(str(DATA_FORMAT_VERSION + 1)), (
        f"{PYPROJECT_FILE.name} caps {DATA_DISTRIBUTION_NAME} at <{bounds['<']}, but the "
        f"format generation this code reads is {DATA_FORMAT_VERSION}, so the cap "
        f"belongs at <{DATA_FORMAT_VERSION + 1}."
    )
    assert bounds[">="].major == DATA_FORMAT_VERSION, (
        f"the floor {bounds['>=']} names format generation {bounds['>='].major}, not "
        f"{DATA_FORMAT_VERSION} - it can no longer be satisfied by data this code reads"
    )
    packaged = Version(_declared_version(DATA_PYPROJECT_FILE))
    assert packaged in specifier, (
        f"the packaged data version {packaged} does not satisfy the declared bound "
        f"{str(specifier)!r}, so `pip install timezonefinder` cannot resolve to the "
        "data this repository ships"
    )


def test_the_format_version_moves_with_the_layouts_it_is_made_of() -> None:
    """A per-file layout bump that leaves DATA_FORMAT_VERSION behind ships silently.

    The per-file versions are not derived from DATA_FORMAT_VERSION and must not be -
    a shortcut-format change would otherwise rewrite the 63 MB coordinate file. The
    implication runs the other way: whichever of them moves, the packaging-level
    number has to move too, or the data goes out under a version whose bound says it
    is readable by code that cannot read it. Nothing else notices - the in-file guard
    only fires once the wrong pair is already installed.
    """
    in_effect = {
        "POLYGON_LAYOUT_VERSION": POLYGON_LAYOUT_VERSION,
        "SHORTCUT_LAYOUT_VERSION": SHORTCUT_LAYOUT_VERSION,
    }
    assert DATA_FORMAT_LAYOUT_VERSIONS == in_effect, (
        f"the layout versions this data format generation records "
        f"{DATA_FORMAT_LAYOUT_VERSIONS} are no longer the ones in force {in_effect}. "
        "Bump DATA_FORMAT_VERSION and update the record - and remember that the data "
        "distribution must then be published before the code release requiring it."
    )
