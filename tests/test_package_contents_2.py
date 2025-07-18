"""Tests for verifying the contents of the package distribution.

This module tests that:
1. All required files are included in the distribution
2. No unwanted files are included (cache, .env, temporary files, etc.)

The module uses parameterized tests and global constants to minimize code
duplication and make the tests more maintainable.
"""

from collections.abc import Iterable
import fnmatch
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
from typing import Iterator, Pattern, Set, Tuple, Union
import re

import pytest
from timezonefinder.configs import PACKAGE_DIR

#######################
# PATH CONSTANTS
#######################

PROJECT_ROOT = PACKAGE_DIR.parent
DIST_DIR = PROJECT_ROOT / "dist"
GITIGNORE_PATH = PROJECT_ROOT / ".gitignore"

# Command constants
BUILD_CMD = ["make", "buildsingle"]

#######################
# FILE PATTERN CONSTANTS
#######################

# Additional patterns to ignore beyond what's in .gitignore
# TODO test
# no files matching these patterns should be included in the distribution
UNWANTED_DIST_PATTERNS = {
    ".github",
    ".git",
    ".vscode",
    "build/",
    "examples/",
    "docs/",
    "scripts/",
    # "tests/", # NOTE: tests should be included in the package for users to validate the package
    ".coveragerc",
    ".editorconfig",
    ".gitignore",
    ".pre-commit-config.yaml",
    "CHANGELOG*",
    "CONTRIBUTING.*",
    "Makefile",
    "parse_data.sh",
    "readthedocs.yaml",
    "test_musllinux_wheel.sh",
    "tox.ini",
    "uv.lock",
}

ALLOWED_IGNORED_PATTERNS = {
    "*.egg-info/"
}  # not under version control, but should be included in the distribution


#######################
# ESSENTIAL PATTERNS
#######################

# TODO test
# these files are not part of the source code, but must be included in the distribution
EXPECTED_DIST_PATTERNS = {
    "PKG-INFO",
} | ALLOWED_IGNORED_PATTERNS


# all files matching these patterns should be included
ESSENTIAL_SOURCE_PATTERNS = {
    "setup.py",
    "pyproject.toml",
    # "MANIFEST.in",
    # "requirements.txt",
    "*py.typed",
    "README*",
    "*LICENSE*",
    # FILE EXTENSIONS:
    "*.py",  # all Python source files
    "*.so",  # Compiled shared objects
    "*.npy",  # Numpy binary data files
    "*.fbs",  # Flatbuffer schema files
    "*.c",  # C source files
    "*.h",  # C header files
    "*.txt",  # Text files (used for timezone names)
}


#######################
# UTILITY FUNCTIONS
#######################


def file_path_iterator(
    path: Path = PROJECT_ROOT, relative: bool = False
) -> Iterator[Path]:
    """
    Recursively iterate over all files in the given path.

    Args:
        path: The root path to start the iteration from (default: PROJECT_ROOT)

    Yields:
        Path objects for each file found
    """
    assert isinstance(path, Path), "path must be a Path object"
    assert path.is_dir(), f"path must be a directory, got {path}"

    # recursively walk through the directory
    for root, _, files in os.walk(path):
        for file in files:
            # yield the full path to the file
            # using Path to ensure compatibility with different OS path formats
            file_path = Path(root) / file
            if relative:
                # yield relative to the project root
                file_path = file_path.relative_to(path)
            yield file_path


def load_gitignore_patterns() -> Set[str]:
    """
    Load patterns from a .gitignore file.

    Args:
        gitignore_path: Path to the .gitignore file (default: PROJECT_ROOT/.gitignore)

    Returns:
        A set of patterns loaded from the .gitignore file.
    """
    with open(GITIGNORE_PATH, encoding="utf-8") as f:
        # Read lines and strip whitespace
        return {line.strip() for line in f if line.strip() and not line.startswith("#")}


# any file not under version control should not be included in the distribution
NON_VERSION_CONTROL_PATTERNS = load_gitignore_patterns()
IGNORED_PATTERNS = UNWANTED_DIST_PATTERNS | NON_VERSION_CONTROL_PATTERNS


def matches_pattern(path: Path, pattern: Union[str, Pattern, None]) -> bool:
    r"""
    Check if a path matches a given pattern.

    Args:
        path: The path to check
        pattern: A glob pattern string or compiled regex pattern to match against
                 If None, always returns True (matches everything)
                 you can use:
                   - Simple filename patterns: '*.py' matches any Python file
                   - Directory patterns: 'tests/*.py' matches Python files in tests directory
                   - Path patterns: '*/data/*.json' matches JSON files in any data directory

    Returns:
        bool: True if the path matches the pattern, False otherwise

    Examples:
        # Check if file matches a glob pattern (filename only)
        is_python_file = matches_pattern(Path('script.py'), '*.py')  # True

        # Match against full path including directories
        in_tests_dir = matches_pattern(Path('tests/test_data.py'), 'tests/*.py')  # True

        # Match files in any data directory
        data_file = matches_pattern(Path('src/data/config.json'), '*/data/*.json')  # True

        # Check with regex pattern against full path
        import re
        is_test_file = matches_pattern(
            Path('tests/unit/test_utils.py'),
            re.compile(r'tests/.*\.py$')
        )  # True

        # Always matches when pattern is None
        matches_all = matches_pattern(Path('any_file.txt'), None)  # True
    """
    if pattern is None:
        return True
    assert isinstance(path, Path), "path must be a Path object"
    # Remove assert for is_file() to allow matching directories too
    assert isinstance(pattern, (str, re.Pattern)), (
        "pattern must be a string or a compiled regex pattern"
    )

    # Get the relative path as string for matching
    path_str = str(path)
    if isinstance(pattern, str):
        if pattern.endswith("/"):
            # pattern points to a directory
            # all content should be matched
            pattern = pattern + "*"

        # For string patterns, check against both the full path
        # Try matching against the full path first
        return fnmatch.fnmatch(path_str, pattern)
    elif isinstance(pattern, re.Pattern):
        # For regex patterns, always match against the full path
        return bool(pattern.search(path_str))


def filter_paths(
    paths: Iterator[Path],
    pattern: Union[str, Pattern, None] = None,
    include_matches: bool = True,
) -> Iterator[Path]:
    """
    Filter paths based on a pattern, either keeping matches or non-matches.

    Args:
        paths: An iterator of Path objects to filter (can be files or directories)
        pattern: A glob pattern string or compiled regex pattern to filter by
                 If None, behavior depends on include_matches
                 Patterns can include directory parts, e.g. 'tests/*.py'
        include_matches: If True, yield paths that match the pattern
                         If False, yield paths that don't match the pattern

    Yields:
        Path objects that match (or don't match) the pattern based on include_matches
    """
    for path in paths:
        is_match = matches_pattern(path, pattern)
        if (
            is_match == include_matches
        ):  # Yield when match status matches desired include status
            yield path


def any_filter_paths(
    paths: Iterator[Path], patterns: Iterable[str], include_matches: bool = True
) -> Iterator[Path]:
    """Filter paths by multiple patterns, yielding paths that match any of the patterns."""
    for path in paths:
        is_match = any(matches_pattern(path, pattern) for pattern in patterns)
        if is_match == include_matches:
            yield path


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


def get_distributable_files() -> Iterator[Path]:
    """
    Get all files that should be included in the distribution.

    This function filters out files matching IGNORE_PATTERNS.

    Returns:
        Iterator of Path objects for files that should be included in the distribution
    """
    all_files = file_path_iterator(PROJECT_ROOT, relative=True)

    # Filter out ignored files
    return filter_ignore_patterns(all_files)


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


def build_distribution() -> Tuple[Path, Path]:
    """Build the distribution using 'make buildsingle' and return the path to the archive."""
    temp_dir = tempfile.mkdtemp()
    try:
        temp_path = Path(temp_dir)

        # Clean up dist directory if it exists
        if DIST_DIR.exists():
            shutil.rmtree(DIST_DIR)

        # Run make buildsingle
        print(f"Building distribution with '{' '.join(BUILD_CMD)}'...")
        subprocess.check_call(BUILD_CMD, cwd=str(PROJECT_ROOT))

        dist_files = file_path_iterator(DIST_DIR, relative=False)
        # Find the generated .tar.gz file in the dist directory
        sdist_files = list(filter_paths(dist_files, "*.tar.gz"))
        assert len(sdist_files) == 1, "Expected exactly one .tar.gz distribution file"
        sdist = sdist_files[0]
        print(f"Found distribution file: {sdist}")

        # Copy the file to the temp directory
        archive_path = temp_path / sdist.name
        shutil.copy2(sdist, archive_path)

        return archive_path, temp_path
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise e


def extract_archive(archive_path: Path, extract_to: Path) -> Path:
    """Extract the tar.gz archive to the specified directory."""
    with tarfile.open(archive_path, "r:gz") as tar:
        # Get the name of the top-level directory in the archive
        top_level_dirs = {member.name.split("/")[0] for member in tar.getmembers()}

        # Extract all files
        tar.extractall(path=extract_to)

        # Return the path to the extracted package directory
        if top_level_dirs:
            # Find the package directory (it should contain setup.py or pyproject.toml)
            for dir_name in top_level_dirs:
                pkg_dir = Path(extract_to) / dir_name
                if (pkg_dir / "setup.py").exists() or (
                    pkg_dir / "pyproject.toml"
                ).exists():
                    return pkg_dir

            # If no setup.py found, just return the first directory
            return Path(extract_to) / list(top_level_dirs)[0]
        else:
            raise ValueError("No files found in the archive")


class DistributionFilesFixture:
    """A fixture class to manage the distribution files testing context.

    This singleton class builds the distribution once and provides access
    to the files for all tests, improving performance significantly.
    """

    def __init__(self):
        """Initialize the fixture with empty attributes."""
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

        # Build the distribution
        self.archive_path, self.temp_dir = build_distribution()

        # Extract the archive
        self.extract_dir = extract_archive(self.archive_path, self.temp_dir)

        # Store the package name for pattern matching
        self.package_name = Path(self.extract_dir).name

        # Get the archive files
        tmp_archive_files = file_path_iterator(self.extract_dir, relative=True)
        # TODO created in tmp folder, so make relative to the extract_dir
        # self.archive_files = [file.relative_to(self.extract_dir) for file in tmp_archive_files]
        self.archive_files = list(tmp_archive_files)

        # Get the project files (excluding those that should be ignored)
        self.project_files = get_distributable_files()

        self._initialized = True
        print(f"Built and extracted distribution with {len(self.archive_files)} files")

    def cleanup(self):
        """Clean up temporary files."""
        if self.temp_dir is not None and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def __del__(self):
        self.cleanup()


# Create a singleton instance for the fixture
distribution_fixture = DistributionFilesFixture()
distribution_fixture.initialize()


# parameterised pytest test case for testing that all distribution files do not match any of the unwanted patterns
# NOTE: some patterns are not under version control, but should be included in the distribution
UNWANTED_DIST_PATTERNS_FINAL = IGNORED_PATTERNS - ALLOWED_IGNORED_PATTERNS


@pytest.mark.parametrize("pattern", UNWANTED_DIST_PATTERNS_FINAL)
def test_no_unwanted_files_in_distribution(pattern: str):
    """Test that no unwanted files are included in the distribution."""

    # Get all files in the distribution
    dist_files = distribution_fixture.archive_files

    # Filter out files that match the ignore patterns
    ignored_files = filter_paths(dist_files, pattern, include_matches=True)

    ignored_file_repr = [str(f) for f in ignored_files]
    nr_ignored_files = len(ignored_file_repr)
    assert nr_ignored_files == 0, (
        f"Found {nr_ignored_files} unwanted files matching pattern '{pattern}': {', '.join(ignored_file_repr)}"
    )


# parameterised pytest test case for testing that all essential source files are included in the distribution
@pytest.mark.parametrize("expected_file", iter_expected_distribution_files())
def test_essential_files_in_distribution(expected_file: Path):
    """Test that all essential source files are included in the distribution."""
    pattern = str(expected_file)
    # Get all files in the distribution
    dist_files = distribution_fixture.archive_files

    matched_files = filter_paths(dist_files, pattern, include_matches=True)
    matched_file_repr = [str(f) for f in matched_files]
    nr_matched_files = len(matched_file_repr)
    assert nr_matched_files < 2, (
        f"multiple files matched pattern '{pattern}': {', '.join(matched_file_repr)}"
    )
    assert nr_matched_files == 1, (
        f"Essential file '{pattern}' not found in distribution."
    )
