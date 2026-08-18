"""Tests for verifying the contents of the package distribution.

This module tests that:
1. All required files are included in both source (sdist) and binary (wheel) distributions
2. No unwanted files are included (cache, .env, temporary files, etc.) in either distribution type
3. Every hand-written "unwanted" pattern still names a path that exists here - the two
   checks above pass for a pattern that matches nothing, so nothing else would notice
   one going stale
4. Every path ``MANIFEST.in`` excludes is in turn named by one of those patterns.
   ``MANIFEST.in`` and the pattern set are two hand-maintained statements of the same
   intent, and check 2 only ever looks at what a *successful* build produced - so an
   exclusion that lives in ``MANIFEST.in`` alone is enforced by the build and verified
   by nothing, and deleting that line would leave the suite green

The module uses parameterized tests and global constants to minimize code
duplication and make the tests more maintainable. It builds both distribution types
and verifies their contents independently.
"""

import fnmatch
from pathlib import Path
import sys
import tarfile
import tempfile
import zipfile
from typing import Iterator, NamedTuple

import pytest
from timezonefinder.configs import DATA_VERSION_FILENAME, DEFAULT_DATA_DIR
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
MANIFEST_PATH = PROJECT_ROOT / "MANIFEST.in"


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

# ``MANIFEST.in`` exclusions whose agreement with the patterns above cannot be shown
# from the paths in a checkout, mapped to the pattern that states the same intent.
# Each names repository metadata, a cache or byte-code - none of it under version
# control - so what it matches is a property of the machine rather than of the
# project: ``.git`` is a directory in a clone and a *file* in a linked worktree,
# ``tests/.pytest_cache`` need not exist at all, and ``timezonefinder/__pycache__/``
# holds numba's ``.nbi``/``.nbc`` cache only once a numba-enabled run has happened.
# Scanning those paths would make the check below depend on what a given machine had
# run, so the mapping is asserted instead, by
# ``test_pattern_only_exclusions_stay_current``.
# Neither ``global-exclude`` is load-bearing on its own: dropping either one changes
# neither distribution, because setuptools already prunes ``__pycache__`` from an
# sdist by default.
EXCLUSIONS_GUARDED_BY_PATTERN_ONLY = {
    "prune .git": ".git/*",
    "prune tests/.pytest_cache": "*.pytest_cache",
    "global-exclude __pycache__/*": "__pycache__/",
    "global-exclude *.pyc": "*.py[cod]",
}

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


class ManifestExclusion(NamedTuple):
    """One ``MANIFEST.in`` directive that keeps paths out of the distribution.

    The four exclusion directives differ only in where their glob is rooted and
    whether it is matched at that exact depth, so they collapse into one shape:

    =========================  ==========  ===========  ============
    directive                  ``prefix``  ``pattern``  ``anchored``
    =========================  ==========  ===========  ============
    ``exclude P``              ``()``      ``P``        yes
    ``recursive-exclude D P``  ``D``       ``P``        no
    ``global-exclude P``       ``()``      ``P``        no
    ``prune D``                ``D``       ``None``     -
    =========================  ==========  ===========  ============

    A ``None`` pattern means the whole subtree, which is what ``prune`` takes.
    Splitting the glob on ``/`` and matching it one path component at a time is
    what keeps ``*`` from crossing a separator, as it does in ``MANIFEST.in`` but
    not in ``matches_pattern``.
    """

    line: str  # the source line, whitespace collapsed, for messages and lookups
    prefix: tuple[str, ...]
    pattern: tuple[str, ...] | None
    anchored: bool

    def matches(self, path: Path) -> bool:
        """Whether ``path``, relative to the project root, is excluded by this directive."""
        parts = path.parts
        if parts[: len(self.prefix)] != self.prefix:
            return False
        below_prefix = parts[len(self.prefix) :]
        if self.pattern is None:
            return True
        if self.anchored:
            if len(below_prefix) != len(self.pattern):
                return False
            tail = below_prefix
        elif len(below_prefix) < len(self.pattern):
            return False
        else:
            tail = below_prefix[len(below_prefix) - len(self.pattern) :]
        return all(
            fnmatch.fnmatch(part, pat)
            for part, pat in zip(tail, self.pattern, strict=True)
        )


def _split(pattern: str) -> tuple[str, ...]:
    """Split a ``MANIFEST.in`` glob into path components, dropping a trailing slash."""
    return tuple(part for part in pattern.split("/") if part)


def load_manifest_exclusions() -> tuple[ManifestExclusion, ...]:
    """
    Read the exclusion directives out of ``MANIFEST.in`` (``MANIFEST_PATH``).

    The include side (``include``, ``recursive-include``, ``graft``) is not parsed:
    what belongs in a distribution is asserted from the other end, by
    ``test_essential_files_in_distribution``.

    Returns:
        One ``ManifestExclusion`` per directive, with a multi-pattern directive
        (``exclude A B``) split into one entry per pattern.
    """
    exclusions = []
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        for raw_line in f:
            line = " ".join(raw_line.split())
            if not line or line.startswith("#"):
                continue
            directive, *args = line.split(" ")
            if directive == "exclude":
                anchored = True
            elif directive in ("recursive-exclude", "global-exclude"):
                anchored = False
            elif directive == "prune":
                exclusions.append(ManifestExclusion(line, _split(args[0]), None, False))
                continue
            else:
                continue
            prefix, patterns = (
                (_split(args[0]), args[1:])
                if directive == "recursive-exclude"
                else ((), args)
            )
            exclusions.extend(
                ManifestExclusion(line, prefix, _split(pattern), anchored)
                for pattern in patterns
            )
    return tuple(exclusions)


# any file not under version control should not be included in the distribution
NON_VERSION_CONTROL_PATTERNS = load_gitignore_patterns()
IGNORED_PATTERNS = UNWANTED_DIST_PATTERNS | NON_VERSION_CONTROL_PATTERNS
MANIFEST_EXCLUSIONS = load_manifest_exclusions()
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


@pytest.mark.unit
def test_every_manifest_exclusion_is_guarded():
    """A file kept out of the build by ``MANIFEST.in`` alone is kept out unverifiably.

    ``MANIFEST.in`` and ``IGNORED_PATTERNS`` are two hand-written statements of the
    same intent, and they have drifted before - which is why
    ``test_every_unwanted_pattern_matches_a_project_file`` exists. That covers one
    direction: a pattern naming nothing now fails. This is the other one. An
    ``exclude``/``recursive-exclude``/``prune`` line added without a matching pattern
    leaves ``test_no_unwanted_files_in_distribution`` with nothing to look for, so the
    day that line is deleted or stops matching, the file ships and the suite stays
    green.

    Note this asserts against the union, not against ``UNWANTED_DIST_PATTERNS``:
    several exclusions (``.claude/*``, ``__pycache__/``) are already covered by a
    ``.gitignore`` pattern, and demanding a hand-written duplicate of those would only
    give the two copies a new way to disagree.
    """
    scanned = [
        exclusion
        for exclusion in MANIFEST_EXCLUSIONS
        if exclusion.line not in EXCLUSIONS_GUARDED_BY_PATTERN_ONLY
    ]
    assert scanned, (
        f"no exclusion directives parsed out of {MANIFEST_PATH}. Every check below "
        "is vacuous in that state - fix the parser, or the path if the file moved."
    )
    unguarded = {
        exclusion.line: sorted(str(path) for path in unmatched)[:5]
        for exclusion in scanned
        if (
            unmatched := [
                path
                for path in ALL_PROJECT_FILES
                if exclusion.matches(path)
                and not any(matches_pattern(path, p) for p in IGNORED_PATTERNS)
            ]
        )
    }
    assert not unguarded, (
        f"{MANIFEST_PATH.name} excludes paths that no pattern in this module names "
        f"(up to 5 shown per directive): {unguarded}. Only the build keeps them out, "
        "so nothing would fail if that exclusion went away - add a pattern covering "
        "them to UNWANTED_DIST_PATTERNS."
    )


@pytest.mark.unit
def test_pattern_only_exclusions_stay_current():
    """The exemptions above are claims about other lines, and those lines move.

    ``EXCLUSIONS_GUARDED_BY_PATTERN_ONLY`` buys each entry out of the path scan
    against a named pattern that carries the same intent. Neither side is pinned by
    anything else: drop the ``MANIFEST.in`` directive and the exemption silently
    excuses a line that no longer exists, drop the pattern and the exemption points
    at nothing, which is the exact failure mode of an entry that guards nothing.
    """
    declared = {exclusion.line for exclusion in MANIFEST_EXCLUSIONS}
    stale = sorted(set(EXCLUSIONS_GUARDED_BY_PATTERN_ONLY) - declared)
    assert not stale, (
        f"EXCLUSIONS_GUARDED_BY_PATTERN_ONLY exempts directives {MANIFEST_PATH.name} "
        f"no longer contains: {stale}. Drop the entries."
    )
    unbacked = sorted(
        f"{line!r} -> {pattern!r}"
        for line, pattern in EXCLUSIONS_GUARDED_BY_PATTERN_ONLY.items()
        if pattern not in IGNORED_PATTERNS
    )
    assert not unbacked, (
        f"exemptions naming a pattern that is no longer in IGNORED_PATTERNS: "
        f"{unbacked}. The exclusion is now stated in {MANIFEST_PATH.name} alone - "
        "restore the pattern, or drop the exemption so the path scan covers it."
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


@pytest.mark.unit
def test_the_packaged_data_version_stamp_is_an_essential_file():
    """The stamp must stay in the set the distribution checks above cover.

    ``AbstractTimezoneFinder.data_version`` reads it out of the installed package,
    so a build that drops it breaks a public property. It is covered today by the
    ``*.txt`` entry in ``ESSENTIAL_SOURCE_PATTERNS`` rather than by name, which is
    what this pins: narrow that pattern set and the sdist/wheel checks would stop
    looking for the stamp without failing.
    """
    stamp = DEFAULT_DATA_DIR.relative_to(PROJECT_ROOT) / DATA_VERSION_FILENAME
    assert stamp in set(iter_expected_distribution_files()), (
        f"{stamp} is no longer among the files "
        f"test_essential_files_in_distribution checks for. Add a pattern matching "
        f"it to ESSENTIAL_SOURCE_PATTERNS."
    )
