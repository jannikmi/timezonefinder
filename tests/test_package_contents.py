"""Tests for verifying the contents of the package distribution.

This module tests that:
1. All required files are included in both source (sdist) and binary (wheel) distributions
2. No unwanted files are included (cache, .env, temporary files, etc.) in either distribution type
3. Every hand-written "unwanted" pattern still names a path that exists here - the two
   checks above pass for a pattern that matches nothing, so nothing else would notice
   one going stale

The module uses parameterized tests and global constants to minimize code
duplication and make the tests more maintainable. It builds both distribution types
and verifies their contents independently.
"""

from pathlib import Path
import sys
import tarfile
import tempfile
import zipfile
from typing import Iterator

import pytest
from tests.auxiliaries import (
    BUILD_SDIST_CMD,
    BUILD_WHEEL_CMD,
    PROJECT_ROOT,
    any_filter_paths,
    build_sdist,
    build_wheel,
    file_path_iterator,
    filter_paths,
    matches_pattern,
)

# NOTE: no module-level ``integration`` mark. Building a distribution is what makes a
# test in here an integration test, and the pattern checks need no build - marking the
# whole module would keep them out of ``make test``, which is where a mistyped pattern
# should surface.

GITIGNORE_PATH = PROJECT_ROOT / ".gitignore"


SDIST_TYPE = "sdist"
WHEEL_TYPE = "wheel"
DIST_TYPES = [SDIST_TYPE, WHEEL_TYPE]


#######################
# FILE PATTERN CONSTANTS
#######################

# Additional patterns to ignore beyond what's in .gitignore.
# No file matching one of these may appear in a distribution. A pattern naming a
# directory needs its trailing slash - ``matches_pattern`` appends the wildcard only
# for those - and one naming a file has to spell it exactly, since ``fnmatch`` is
# case-sensitive on POSIX. Get either wrong and the entry silently guards nothing,
# which is what ``test_every_unwanted_pattern_matches_a_project_file`` now catches.
# ``build/`` and the other build artefacts are not listed here: .gitignore already
# contributes them below.
UNWANTED_DIST_PATTERNS = {
    ".github/",
    ".git/*",
    ".vscode/",
    ".cursor/",
    "examples/",
    "docs/",
    "scripts/",
    "benchmarks/",
    "prototypes/",
    # "tests/", # NOTE: tests should be included in the package for users to validate the package
    ".coveragerc",
    ".editorconfig",
    ".gitignore",
    ".pre-commit-config.yaml",
    "CHANGELOG*",
    "CONTRIBUTING.*",
    # the agent instruction files MANIFEST.in excludes by name
    "AGENTS.md",
    "CLAUDE.md",
    "potential-improvements.md",
    "Makefile",
    "update_data.sh",
    "readthedocs.yml",
    "test_musllinux_wheel.sh",
    "tox.ini",
    "uv.lock",
}

# ``.git`` holds repository metadata rather than project files, and in a linked
# worktree it is a file instead of a directory - so this one pattern matches nothing
# in the working tree by design, and is exempt from the check above.
PATTERNS_WITHOUT_PROJECT_FILES = {".git/*"}

ALLOWED_IGNORED_PATTERNS = {
    "*.egg-info/",
    "*.so",  # Compiled shared objects, are ok in wheels
}  # not under version control, but should be included in the distribution


#######################
# ESSENTIAL PATTERNS
#######################

# all files matching these patterns should be included in source distribution
ESSENTIAL_SOURCE_PATTERNS = {
    "setup.py",
    "pyproject.toml",
    # "MANIFEST.in",
    # "requirements.txt",
    "*py.typed",
    "README*",
    "*LICENSE*",
    # FILE EXTENSIONS:
    # source:
    "*.py",  # all Python source files
    "*.c",  # C source files
    "*.h",  # C header files
    "*.so",  # Compiled shared objects
    # data files:
    "*.npy",  # Numpy binary data files
    "*.fbs",  # Flatbuffer schema files
    "*.json",  # used for hole registry
    "*.txt",  # Text files (used for timezone names)
}

# these files are not included in wheels
WHEEL_EXCEPTION_PATTERNS = {
    "pyproject.toml",
    "setup.py",
    "README*",
    # wheels define what is installed. tests should not be included
    "tests/*",
}


def load_gitignore_patterns() -> set[str]:
    """
    Load the exclusion patterns from the repository's .gitignore (``GITIGNORE_PATH``).

    Comments, blank lines and ``!`` re-includes are skipped. A re-include is not an
    exclusion, and kept verbatim it becomes a pattern beginning with ``!`` that
    matches no path at all - a parametrised case that can never fail. Dropping it
    leaves the enclosing exclusion in force, which is the right answer here: what
    git re-includes for version control (``.claude/skills/``) is still excluded from
    the distribution by ``MANIFEST.in``.

    Returns:
        A set of patterns loaded from the .gitignore file.
    """
    with open(GITIGNORE_PATH, encoding="utf-8") as f:
        lines = (line.strip() for line in f)
        return {line for line in lines if line and not line.startswith(("#", "!"))}


# any file not under version control should not be included in the distribution
NON_VERSION_CONTROL_PATTERNS = load_gitignore_patterns()
IGNORED_PATTERNS = UNWANTED_DIST_PATTERNS | NON_VERSION_CONTROL_PATTERNS
# NOTE: some patterns are not under version control, but should be included in the distribution
UNWANTED_DIST_PATTERNS_FINAL = IGNORED_PATTERNS - ALLOWED_IGNORED_PATTERNS


def filter_ignore_patterns(paths: Iterator[Path]) -> Iterator[Path]:
    """
    Filter out paths that match any pattern in IGNORE_PATTERNS.

    Args:
        paths: An iterator of Path objects to filter

    Yields:
        Path objects that don't match any ignore pattern

    Examples:
        # Get all files except those matching ignore patterns
        all_files = iterate_files_by_pattern()
        valid_files = list(filter_ignore_patterns(all_files))
    """
    return any_filter_paths(paths, IGNORED_PATTERNS, include_matches=False)


# One walk of the working tree, shared by the essential-file parametrisation and the
# pattern check below. Walking a developer checkout means descending into .venv/,
# .tox/ and the build artefacts, which is not cheap enough to repeat.
ALL_PROJECT_FILES = tuple(file_path_iterator(PROJECT_ROOT, relative=True))


def get_distributable_files() -> Iterator[Path]:
    """
    Get all files that should be included in the distribution.

    This function filters out files matching IGNORE_PATTERNS.

    Returns:
        Iterator of Path objects for files that should be included in the distribution
    """
    # Filter out ignored files
    return filter_ignore_patterns(iter(ALL_PROJECT_FILES))


def iter_expected_distribution_files() -> Iterator[Path]:
    """
    Get all essential source files that should be included in the distribution.

    This function filters out files matching IGNORE_PATTERNS.

    Returns:
        Iterator of Path objects for essential source files
    """
    all_files = get_distributable_files()

    # Filter out ignored files
    return any_filter_paths(all_files, ESSENTIAL_SOURCE_PATTERNS, include_matches=True)


def extract_archive(archive_path: Path) -> list[Path]:
    """Extract the tar.gz archive in the given path and return a list of the contained files."""
    with tarfile.open(archive_path, "r:gz") as tar:
        # Get the name of the top-level directory in the archive
        top_level_dirs = {member.name.split("/")[0] for member in tar.getmembers()}
        if len(top_level_dirs) == 0:
            raise ValueError("The archive does not contain any files.")

        # work in a temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            extract_to = Path(tmpdir)
            # Extract all files with the 'data' filter to allow all files but avoid the deprecation warning
            tar.extractall(path=extract_to, filter="data")

            # Find the package directory (it should contain setup.py or pyproject.toml)
            pkg_dir = None
            for dir_name in top_level_dirs:
                pkg_dir = Path(extract_to) / dir_name
                if (pkg_dir / "pyproject.toml").exists():
                    break

            if pkg_dir is None:
                raise ValueError("No package directory found in the archive.")

            archive_files = file_path_iterator(pkg_dir, relative=True)
            file_list = list(archive_files)

    assert len(file_list) > 0, "The archive does not contain any files."
    return file_list


def extract_wheel(wheel_path: Path) -> list[Path]:
    """Extract the wheel (.whl) file in the given path and return a list of the contained files."""
    with zipfile.ZipFile(wheel_path) as wheel:
        # List all files in the wheel
        wheel_files = wheel.namelist()

        if len(wheel_files) == 0:
            raise ValueError("The wheel does not contain any files.")

        # work in a temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            extract_to = Path(tmpdir)
            # Extract all files
            wheel.extractall(path=extract_to)
            # wheel.extractall(path=PROJECT_ROOT/"tmp"/"wheel")

            # Get list of all files (relative paths)
            archive_files = file_path_iterator(extract_to, relative=True)
            file_list = list(archive_files)

    assert len(file_list) > 0, "The wheel does not contain any files."
    return file_list


class DistributionFilesFixture:
    """A fixture class to manage the distribution files testing context.

    This singleton class builds the distribution once and provides access
    to the files for all tests, improving performance significantly.
    """

    def __init__(self, dist_type="sdist"):
        """Initialize the fixture with empty attributes."""
        self.dist_type = dist_type  # "sdist" or "wheel"
        self.temp_dir = None
        self.archive_path = None
        self.extract_dir = None
        self.project_files = None
        self.archive_files = None
        self.package_name = None
        self._initialized = False

    def initialize(self):
        """Initialize the fixture by building and extracting the distribution."""
        if self._initialized:
            return

        # Build the distribution based on type
        if self.dist_type == "sdist":
            self.archive_path = build_sdist()
            self.archive_files = extract_archive(self.archive_path)
        elif self.dist_type == "wheel":
            self.archive_path = build_wheel()
            self.archive_files = extract_wheel(self.archive_path)
        else:
            raise ValueError(f"Unknown distribution type: {self.dist_type}")

        self._initialized = True
        print(
            f"Built and extracted {self.dist_type} distribution with {len(self.archive_files)} files"
        )


# Create singleton instances for the fixtures
sdist_fixture = DistributionFilesFixture("sdist")
wheel_fixture = DistributionFilesFixture("wheel")

fixtures = {SDIST_TYPE: sdist_fixture, WHEEL_TYPE: wheel_fixture}


@pytest.mark.unit
@pytest.mark.parametrize(
    "build_cmd",
    [BUILD_SDIST_CMD, BUILD_WHEEL_CMD],
    ids=DIST_TYPES,
)
def test_build_commands_pin_the_running_interpreter(build_cmd):
    """Unpinned, ``uv build`` targets the newest interpreter on the machine.

    That it is the pytest interpreter is a coincidence. Once the two differ - a
    project ``.venv`` older than the newest Python installed - the wheel comes out
    tagged for the wrong one, and ``test_install_from_artifacts[wheel]`` fails with
    a pip error about an unsupported platform, nowhere near the build that caused
    it. Every tox env offers a single interpreter, so no CI run can reproduce the
    mismatch; this check needs no build and catches it anywhere.

    The sdist carries no interpreter tag and is checked only to keep the two
    artefacts in ``dist/`` coming from one interpreter.
    """
    assert "--python" in build_cmd, (
        f"{build_cmd} does not pin an interpreter, so uv will build for the newest "
        "Python it finds rather than the one running the tests"
    )
    pinned = build_cmd[build_cmd.index("--python") + 1]
    assert pinned == sys.executable, (
        f"build pinned to {pinned}, but the tests run on {sys.executable}"
    )


# parameterised pytest test case for testing that all distribution files do not match any of the unwanted patterns


@pytest.mark.unit
def test_every_unwanted_pattern_matches_a_project_file():
    """A pattern matching nothing here can never catch that thing being packaged.

    ``test_no_unwanted_files_in_distribution`` only ever asserts that *nothing*
    matched, so it passes for a mistyped pattern exactly as it does for a correct
    one. Three had drifted from the paths they name and were guarding nothing:
    ``.github`` without the trailing slash a directory pattern needs, ``Agents.*``
    after the file became ``AGENTS.md``, and ``readthedocs.yaml`` against a file
    that has always been ``readthedocs.yml``.

    Only the hand-written set is checked. The patterns read out of ``.gitignore``
    legitimately name build artefacts and caches that need not exist in any given
    checkout, so requiring them to match something would be flaky.
    """
    unmatched = sorted(
        pattern
        for pattern in UNWANTED_DIST_PATTERNS - PATTERNS_WITHOUT_PROJECT_FILES
        if not any(matches_pattern(path, pattern) for path in ALL_PROJECT_FILES)
    )
    assert not unmatched, (
        f"unwanted-file patterns matching nothing under {PROJECT_ROOT}: {unmatched}. "
        "A pattern that matches no path cannot fail, so the files it names are not "
        "guarded against being packaged - correct it, or drop it if the file is gone."
    )


@pytest.mark.integration
@pytest.mark.parametrize("pattern", UNWANTED_DIST_PATTERNS_FINAL)
@pytest.mark.parametrize("dist_type", DIST_TYPES)
def test_no_unwanted_files_in_distribution(
    pattern: str,
    dist_type: str,
):
    """Test that no unwanted files are included in the distribution."""

    # Get all files in the distribution
    fixture = fixtures[dist_type]
    fixture.initialize()
    dist_files = fixture.archive_files

    # Filter out files that match the ignore patterns
    ignored_files = filter_paths(dist_files, pattern, include_matches=True)

    ignored_file_repr = [str(f) for f in ignored_files]
    nr_ignored_files = len(ignored_file_repr)
    assert nr_ignored_files == 0, (
        f"Found {nr_ignored_files} unwanted files matching pattern '{pattern}' in {dist_type}: {', '.join(ignored_file_repr)}"
    )


# parameterised pytest test case for testing that all essential source files are included in the distribution
@pytest.mark.integration
@pytest.mark.parametrize("expected_file", iter_expected_distribution_files())
@pytest.mark.parametrize("dist_type", DIST_TYPES)
def test_essential_files_in_distribution(expected_file: Path, dist_type: str):
    """Test that all essential source files are included in the distribution."""
    pattern = str(expected_file)
    # Get all files in the distribution
    fixture = fixtures[dist_type]
    fixture.initialize()
    dist_files = fixture.archive_files

    # NOTE: in wheels the files may be in a subdirectory, relax the pattern matching
    if dist_type == WHEEL_TYPE:
        if any(matches_pattern(expected_file, p) for p in WHEEL_EXCEPTION_PATTERNS):
            # some files are ok to not exist in wheels
            print(f"Skipping {expected_file} in {dist_type} due to wheel exceptions")
            return
        patterns = [
            pattern,
            f"**/{pattern}",
        ]
    else:
        patterns = [pattern]
    matched_files = any_filter_paths(dist_files, patterns, include_matches=True)
    matched_file_repr = [str(f) for f in matched_files]
    nr_matched_files = len(matched_file_repr)
    assert nr_matched_files < 2, (
        f"multiple files matched pattern '{pattern}' in {dist_type}: {', '.join(matched_file_repr)}"
    )
    assert nr_matched_files == 1, (
        f"Essential file '{pattern}' not found in {dist_type}."
    )
