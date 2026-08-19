"""Tests for verifying the contents of the package distributions.

This repository publishes two distributions: ``timezonefinder``, the
code, and ``timezonefinder-data``, the boundary data. Each is described by a
:class:`Distribution` naming its source directory, the artefact types it publishes
and its own pattern sets - a single global set cannot express both, since
``packages/`` is unwanted in the code distribution and is the entire content of the
data one.

This module tests that:
1. All required files are included in every artefact each distribution publishes
2. No unwanted files are included (cache, .env, temporary files, etc.) in any of them
3. Every hand-written "unwanted" pattern still names a path that exists here - the two
   checks above pass for a pattern that matches nothing, so nothing else would notice
   one going stale
4. Every path ``MANIFEST.in`` excludes is in turn named by one of those patterns.
   ``MANIFEST.in`` and the pattern set are two hand-maintained statements of the same
   intent, and check 2 only ever looks at what a *successful* build produced - so an
   exclusion that lives in ``MANIFEST.in`` alone is enforced by the build and verified
   by nothing, and deleting that line would leave the suite green
5. Neither distribution carries the other's payload. That is the separation the split
   exists for, and unlike a directory convention it is something that can actually
   fail: a wrongly-packaged file is caught, and re-adding ``**/*.npy`` to the root's
   ``package-data`` fails check 5 rather than merely re-inflating the wheel

The module uses parameterized tests and per-distribution constants to minimize code
duplication and make the tests more maintainable. It builds each distribution's
artefacts and verifies their contents independently.
"""

import fnmatch
from pathlib import Path
import sys
import tarfile
import tempfile
import zipfile
from typing import Iterator, NamedTuple

import pytest
from scripts.configs import DATA_DISTRIBUTION_NAME, DATA_PACKAGE_ROOT, SOURCE_DATA_DIR
from timezonefinder.configs import DATA_VERSION_FILENAME
from tests.auxiliaries import (
    BUILD_SDIST_CMD,
    BUILD_WHEEL_CMD,
    PROJECT_ROOT,
    ROOT_DISTRIBUTION_NAME,
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
UNWANTED_CODE_DIST_PATTERNS = {
    ".github/",
    ".git/*",
    ".vscode/",
    ".cursor/",
    "examples/",
    "docs/",
    "scripts/",
    "benchmarks/",
    "prototypes/",
    # the other distribution in this workspace, built and published on its own
    "packages/",
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

# The data distribution's source directory holds nothing but what it publishes, so it
# has no hand-written exclusions of its own - what must stay out of it is the *code*
# distribution's payload, which does not exist under that directory and so cannot be
# named by a pattern this module requires to match something. That separation is
# asserted directly instead, by ``test_no_distribution_carries_the_others_payload``.
UNWANTED_DATA_DIST_PATTERNS: set[str] = set()

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

ALLOWED_IGNORED_CODE_PATTERNS = {
    "*.egg-info/",
    "*.so",  # Compiled shared objects, are ok in wheels
}  # not under version control, but should be included in the distribution

# The data distribution ships no compiled anything, so ``*.so`` is *not* bought out of
# .gitignore's exclusions here: an extension module appearing in the data wheel fails
# ``test_no_unwanted_files_in_distribution`` on its own.
ALLOWED_IGNORED_DATA_PATTERNS = {
    "*.egg-info/",
}


#######################
# ESSENTIAL PATTERNS
#######################

# all files matching these patterns should be included in the code distribution.
# The data payload extensions (*.npy, *.json, the timezone-name *.txt) are the data
# distribution's, below - after the split this one carries no dataset at all.
ESSENTIAL_CODE_PATTERNS = {
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
    "*.fbs",  # Flatbuffer schema files
    # The dataset is the data distribution's, below - this one carries none of it.
    # These two match only under tests/, which the sdist grafts and whose suite cannot
    # run without them: the benchmark fixtures and the converter's test input. No
    # "*.txt" entry, because after the split nothing in this distribution matches one,
    # and a pattern matching nothing asserts nothing.
    "*.npy",
    "*.json",
}

# these files are not included in wheels
WHEEL_EXCEPTION_CODE_PATTERNS = {
    "pyproject.toml",
    "setup.py",
    "README*",
    # wheels define what is installed. tests should not be included
    "tests/*",
}

# What the data distribution exists to ship: the binaries, the licence that has to
# travel with them (the ODbL is share-alike on the database), and the one module that
# gives them an importable path. Its ``pyproject.toml`` and ``README.md`` are not
# listed - they are build inputs, and the README travels as the wheel's long
# description rather than as a file.
ESSENTIAL_DATA_PATTERNS = {
    "*LICENSE*",
    "*__init__.py",
    # data files:
    "*.npy",  # Numpy binary data files
    "*.bin",  # Flatbuffer binaries (the serialised polygon and shortcut data)
    "*.fbs",  # the schema definitions describing them, under data/schemas/
    "*.json",  # used for hole registry
    "*.txt",  # Text files (timezone names, the dataset version stamp)
}


class Distribution(NamedTuple):
    """One published distribution, and everything the checks below need about it.

    Both the pattern sets and the file walk are per-distribution: ``packages/`` is
    unwanted in the code distribution and is the whole of the data one, so no single
    global set can describe both.
    """

    name: str
    # where this distribution's files live in the checkout
    source_root: Path
    # the artefact types it publishes. The data distribution ships a wheel and no
    # sdist: there is no build-from-source case for a pure-data py3-none-any wheel,
    # and an sdist would double the ~63 MB each data release costs.
    dist_types: tuple[str, ...]
    # the ``uv build --package`` argument, or None for the root distribution
    build_package: str | None
    essential_patterns: frozenset[str]
    unwanted_patterns: frozenset[str]
    allowed_ignored_patterns: frozenset[str]
    wheel_exception_patterns: frozenset[str]

    @property
    def cases(self) -> list[tuple["Distribution", str]]:
        return [(self, dist_type) for dist_type in self.dist_types]


CODE_DIST = Distribution(
    name=ROOT_DISTRIBUTION_NAME,
    source_root=PROJECT_ROOT,
    dist_types=(SDIST_TYPE, WHEEL_TYPE),
    build_package=None,
    essential_patterns=frozenset(ESSENTIAL_CODE_PATTERNS),
    unwanted_patterns=frozenset(UNWANTED_CODE_DIST_PATTERNS),
    allowed_ignored_patterns=frozenset(ALLOWED_IGNORED_CODE_PATTERNS),
    wheel_exception_patterns=frozenset(WHEEL_EXCEPTION_CODE_PATTERNS),
)

DATA_DIST = Distribution(
    name=DATA_DISTRIBUTION_NAME,
    source_root=DATA_PACKAGE_ROOT,
    dist_types=(WHEEL_TYPE,),
    build_package=DATA_DISTRIBUTION_NAME,
    essential_patterns=frozenset(ESSENTIAL_DATA_PATTERNS),
    unwanted_patterns=frozenset(UNWANTED_DATA_DIST_PATTERNS),
    allowed_ignored_patterns=frozenset(ALLOWED_IGNORED_DATA_PATTERNS),
    wheel_exception_patterns=frozenset(),
)

DISTRIBUTIONS = (CODE_DIST, DATA_DIST)
DIST_CASES = [case for dist in DISTRIBUTIONS for case in dist.cases]
DIST_CASE_IDS = [f"{dist.name}-{dist_type}" for dist, dist_type in DIST_CASES]


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
MANIFEST_EXCLUSIONS = load_manifest_exclusions()


def ignored_patterns(dist: Distribution) -> set[str]:
    """Every pattern naming a file that must not be in ``dist``."""
    return set(dist.unwanted_patterns) | NON_VERSION_CONTROL_PATTERNS


def unwanted_patterns_to_scan(dist: Distribution) -> set[str]:
    """The patterns the built artefacts are actually scanned for.

    NOTE: some patterns are not under version control, but should be included in the
    distribution - those are bought out per distribution, which is how ``*.so`` is
    legitimate in the code wheel and a failure in the data one.
    """
    return ignored_patterns(dist) - set(dist.allowed_ignored_patterns)


# One walk per distribution source root, shared by the essential-file parametrisation
# and the pattern checks below. Walking a developer checkout means descending into
# .venv/, .tox/ and the build artefacts, which is not cheap enough to repeat.
PROJECT_FILES: dict[str, tuple[Path, ...]] = {
    dist.name: tuple(file_path_iterator(dist.source_root, relative=True))
    for dist in DISTRIBUTIONS
}


def get_distributable_files(dist: Distribution) -> Iterator[Path]:
    """
    Get all files that should be included in the distribution.

    This function filters out files matching the distribution's ignore patterns.

    Returns:
        Iterator of Path objects for files that should be included in the distribution
    """
    return any_filter_paths(
        iter(PROJECT_FILES[dist.name]), ignored_patterns(dist), include_matches=False
    )


def iter_expected_distribution_files(dist: Distribution) -> Iterator[Path]:
    """
    Get all essential source files that should be included in the distribution.

    This function filters out files matching the distribution's ignore patterns.

    Returns:
        Iterator of Path objects for essential source files
    """
    return any_filter_paths(
        get_distributable_files(dist), dist.essential_patterns, include_matches=True
    )


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

    One instance per (distribution, artefact type). Each builds its artefact once
    and provides access to the files for all tests, improving performance
    significantly.
    """

    def __init__(self, dist: Distribution, dist_type: str = SDIST_TYPE):
        """Initialize the fixture with empty attributes."""
        self.dist = dist
        self.dist_type = dist_type  # "sdist" or "wheel"
        self.archive_path = None
        self.archive_files = None
        self._initialized = False

    def initialize(self):
        """Initialize the fixture by building and extracting the distribution."""
        if self._initialized:
            return

        # Build the distribution based on type
        if self.dist_type == SDIST_TYPE:
            self.archive_path = build_sdist()
            self.archive_files = extract_archive(self.archive_path)
        elif self.dist_type == WHEEL_TYPE:
            self.archive_path = build_wheel(
                package=self.dist.build_package, source_root=self.dist.source_root
            )
            self.archive_files = extract_wheel(self.archive_path)
        else:
            raise ValueError(f"Unknown distribution type: {self.dist_type}")

        self._initialized = True
        print(
            f"Built and extracted the {self.dist.name} {self.dist_type} "
            f"with {len(self.archive_files)} files"
        )


# Create singleton instances for the fixtures
fixtures = {
    (dist.name, dist_type): DistributionFilesFixture(dist, dist_type)
    for dist, dist_type in DIST_CASES
}


def built_files(dist: Distribution, dist_type: str) -> list[Path]:
    """The files in ``dist``'s built ``dist_type`` artefact, building it if needed."""
    fixture = fixtures[(dist.name, dist_type)]
    fixture.initialize()
    return fixture.archive_files


@pytest.mark.unit
@pytest.mark.parametrize(
    "build_cmd",
    [BUILD_SDIST_CMD, BUILD_WHEEL_CMD],
    ids=[SDIST_TYPE, WHEEL_TYPE],
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
@pytest.mark.parametrize("dist", DISTRIBUTIONS, ids=[d.name for d in DISTRIBUTIONS])
def test_every_unwanted_pattern_matches_a_project_file(dist: Distribution):
    """A pattern matching nothing here can never catch that thing being packaged.

    ``test_no_unwanted_files_in_distribution`` only ever asserts that *nothing*
    matched, so it passes for a mistyped pattern exactly as it does for a correct
    one. Three had drifted from the paths they name and were guarding nothing:
    ``.github`` without the trailing slash a directory pattern needs, ``Agents.*``
    after the file became ``AGENTS.md``, and ``readthedocs.yaml`` against a file
    that has always been ``readthedocs.yml``.

    Only the hand-written set is checked, and only against its own distribution's
    source tree. The patterns read out of ``.gitignore`` legitimately name build
    artefacts and caches that need not exist in any given checkout, so requiring
    them to match something would be flaky.
    """
    unmatched = sorted(
        pattern
        for pattern in dist.unwanted_patterns - PATTERNS_WITHOUT_PROJECT_FILES
        if not any(matches_pattern(path, pattern) for path in PROJECT_FILES[dist.name])
    )
    assert not unmatched, (
        f"unwanted-file patterns matching nothing under {dist.source_root}: "
        f"{unmatched}. A pattern that matches no path cannot fail, so the files it "
        "names are not guarded against being packaged - correct it, or drop it if "
        "the file is gone."
    )


@pytest.mark.unit
def test_every_manifest_exclusion_is_guarded():
    """A file kept out of the build by ``MANIFEST.in`` alone is kept out unverifiably.

    ``MANIFEST.in`` and the ignored-pattern set are two hand-written statements of the
    same intent, and they have drifted before - which is why
    ``test_every_unwanted_pattern_matches_a_project_file`` exists. That covers one
    direction: a pattern naming nothing now fails. This is the other one. An
    ``exclude``/``recursive-exclude``/``prune`` line added without a matching pattern
    leaves ``test_no_unwanted_files_in_distribution`` with nothing to look for, so the
    day that line is deleted or stops matching, the file ships and the suite stays
    green.

    ``MANIFEST.in`` governs sdists, and the code distribution publishes the only one -
    so this is asserted against that distribution alone rather than per distribution.

    Note this asserts against the union, not against the hand-written set:
    several exclusions (``.claude/*``, ``__pycache__/``) are already covered by a
    ``.gitignore`` pattern, and demanding a hand-written duplicate of those would only
    give the two copies a new way to disagree.
    """
    patterns = ignored_patterns(CODE_DIST)
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
                for path in PROJECT_FILES[CODE_DIST.name]
                if exclusion.matches(path)
                and not any(matches_pattern(path, p) for p in patterns)
            ]
        )
    }
    assert not unguarded, (
        f"{MANIFEST_PATH.name} excludes paths that no pattern in this module names "
        f"(up to 5 shown per directive): {unguarded}. Only the build keeps them out, "
        "so nothing would fail if that exclusion went away - add a pattern covering "
        "them to UNWANTED_CODE_DIST_PATTERNS."
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
    patterns = ignored_patterns(CODE_DIST)
    unbacked = sorted(
        f"{line!r} -> {pattern!r}"
        for line, pattern in EXCLUSIONS_GUARDED_BY_PATTERN_ONLY.items()
        if pattern not in patterns
    )
    assert not unbacked, (
        f"exemptions naming a pattern that is no longer ignored: "
        f"{unbacked}. The exclusion is now stated in {MANIFEST_PATH.name} alone - "
        "restore the pattern, or drop the exemption so the path scan covers it."
    )


# One case per (distribution, artefact, pattern/file), as before the split: an
# aggregate assertion would name the distribution but not the entry that broke it.
UNWANTED_CASES = [
    (dist, dist_type, pattern)
    for dist, dist_type in DIST_CASES
    for pattern in sorted(unwanted_patterns_to_scan(dist))
]
UNWANTED_CASE_IDS = [
    f"{dist.name}-{dist_type}-{pattern}" for dist, dist_type, pattern in UNWANTED_CASES
]

ESSENTIAL_CASES = [
    (dist, dist_type, expected_file)
    for dist, dist_type in DIST_CASES
    for expected_file in iter_expected_distribution_files(dist)
]
ESSENTIAL_CASE_IDS = [
    f"{dist.name}-{dist_type}-{expected_file}"
    for dist, dist_type, expected_file in ESSENTIAL_CASES
]


@pytest.mark.integration
@pytest.mark.parametrize(
    ("dist", "dist_type", "pattern"), UNWANTED_CASES, ids=UNWANTED_CASE_IDS
)
def test_no_unwanted_files_in_distribution(
    dist: Distribution, dist_type: str, pattern: str
):
    """Test that no unwanted files are included in the distribution."""
    dist_files = built_files(dist, dist_type)

    # Filter out files that match the ignore patterns
    ignored_files = filter_paths(iter(dist_files), pattern, include_matches=True)

    ignored_file_repr = [str(f) for f in ignored_files]
    nr_ignored_files = len(ignored_file_repr)
    assert nr_ignored_files == 0, (
        f"Found {nr_ignored_files} unwanted files matching pattern '{pattern}' in "
        f"the {dist.name} {dist_type}: {', '.join(ignored_file_repr)}"
    )


# parameterised pytest test case for testing that all essential source files are included in the distribution
@pytest.mark.integration
@pytest.mark.parametrize(
    ("dist", "dist_type", "expected_file"), ESSENTIAL_CASES, ids=ESSENTIAL_CASE_IDS
)
def test_essential_files_in_distribution(
    dist: Distribution, dist_type: str, expected_file: Path
):
    """Test that all essential source files are included in the distribution."""
    pattern = str(expected_file)
    dist_files = built_files(dist, dist_type)

    # NOTE: in wheels the files may be in a subdirectory, relax the pattern matching
    if dist_type == WHEEL_TYPE:
        if any(
            matches_pattern(expected_file, p) for p in dist.wheel_exception_patterns
        ):
            # some files are ok to not exist in wheels
            print(f"Skipping {expected_file} in {dist_type} due to wheel exceptions")
            return
        patterns = [
            pattern,
            f"**/{pattern}",
        ]
    else:
        patterns = [pattern]
    matched_files = any_filter_paths(iter(dist_files), patterns, include_matches=True)
    matched_file_repr = [str(f) for f in matched_files]
    nr_matched_files = len(matched_file_repr)
    assert nr_matched_files < 2, (
        f"multiple files matched pattern '{pattern}' in the {dist.name} "
        f"{dist_type}: {', '.join(matched_file_repr)}"
    )
    assert nr_matched_files == 1, (
        f"Essential file '{pattern}' not found in the {dist.name} {dist_type}."
    )


# where the dataset sits inside the data wheel, and inside its source tree
DATA_PAYLOAD_PREFIX = ("timezonefinder_data", "data")


def _payload(paths) -> set[Path]:
    """The dataset entries among ``paths``, relative to the data directory."""
    depth = len(DATA_PAYLOAD_PREFIX)
    return {
        Path(*path.parts[depth:])
        for path in paths
        if path.parts[:depth] == DATA_PAYLOAD_PREFIX
    }


@pytest.mark.integration
def test_the_data_wheel_carries_exactly_the_committed_dataset():
    """Set equality, because both directions are silent failures with real cost.

    A missing binary is a lookup that raises on first use. An *extra* one is worse to
    catch: setuptools copies package data into ``build/lib`` and never prunes it, so a
    file renamed in the source tree keeps being zipped into every later wheel from a
    developer checkout. That is not hypothetical - the ``.fbs`` -> ``.bin`` rename left
    a 63 MB ``coordinates.fbs`` shipping next to its replacement, doubling a wheel
    whose size is the entire reason this distribution was split out. Every other check
    in this module looked straight past it: the unwanted-file scan only knows
    ``.gitignore`` patterns, which are repo-relative and cannot match a path inside an
    archive, and the essential-file checks ask only whether each expected file is
    present.
    """
    shipped = _payload(built_files(DATA_DIST, WHEEL_TYPE))
    committed = _payload(get_distributable_files(DATA_DIST))

    assert committed, (
        f"no dataset found under {'/'.join(DATA_PAYLOAD_PREFIX)} in "
        f"{DATA_DIST.source_root} - this check is vacuous, so the layout has moved"
    )
    extra = sorted(str(path) for path in shipped - committed)
    missing = sorted(str(path) for path in committed - shipped)
    assert not (extra or missing), (
        f"the {DATA_DIST.name} wheel does not carry the committed dataset.\n"
        f"  shipped but not in the source tree: {extra}\n"
        f"  in the source tree but not shipped: {missing}\n"
        "Stale entries are usually a previous build left in "
        f"{DATA_DIST.source_root / 'build'}; missing ones mean "
        "[tool.setuptools.package-data] does not name their extension."
    )


@pytest.mark.integration
def test_no_distribution_carries_the_others_payload():
    """The separation the split exists for, stated as something that can fail.

    A layout convention is enforced by nothing; a wrongly-packaged file is. Every
    assertion here corresponds to a way the split silently un-does itself: re-adding
    ``**/*.npy`` to the root's ``package-data`` puts 63 MB back into every code
    release, and any importable module in the data package turns a dataset update
    into a code deployment.
    """
    code_files = {
        dist_type: built_files(CODE_DIST, dist_type)
        for dist_type in CODE_DIST.dist_types
    }
    data_files = built_files(DATA_DIST, WHEEL_TYPE)

    for dist_type, files in code_files.items():
        payload = sorted(
            str(path)
            for path in files
            # scoped to the package directory: the sdist legitimately grafts
            # tests/, whose benchmark fixtures are .npy and whose input is .json
            if any(part == ROOT_DISTRIBUTION_NAME for part in path.parts)
            and path.suffix in {".npy", ".json"}
        )
        assert not payload, (
            f"the {CODE_DIST.name} {dist_type} carries boundary data payload: "
            f"{payload}. It belongs in {DATA_DIST.name} - check the root's "
            "[tool.setuptools.package-data] and MANIFEST.in."
        )
        packaged_workspace = sorted(
            str(path) for path in files if path.parts[:1] == ("packages",)
        )
        assert not packaged_workspace, (
            f"the {CODE_DIST.name} {dist_type} carries the other distribution's "
            f"source tree: {packaged_workspace}"
        )

    compiled = sorted(
        str(path) for path in data_files if path.suffix in {".so", ".c", ".h", ".pyd"}
    )
    assert not compiled, (
        f"the {DATA_DIST.name} wheel carries compiled code: {compiled}. It ships data "
        "only - the extension module belongs to the lookup layer."
    )
    importable = sorted(
        str(path)
        for path in data_files
        if path.suffix == ".py" and path.name != "__init__.py"
    )
    assert not importable, (
        f"the {DATA_DIST.name} wheel carries importable code beyond its __init__.py: "
        f"{importable}. A reader shipped with the data would make a reader bug cost a "
        "63 MB upload, and needs a version the data's own numbering has no room for."
    )


@pytest.mark.unit
def test_the_packaged_data_version_stamp_is_an_essential_file():
    """The stamp must stay in the set the distribution checks above cover.

    ``AbstractTimezoneFinder.data_version`` reads it out of the installed data
    package, so a build that drops it breaks a public property of ``timezonefinder``
    across the distribution boundary. It is covered by the ``*.txt`` entry in
    ``ESSENTIAL_DATA_PATTERNS`` rather than by name, which is what this pins: narrow
    that pattern set and the wheel check would stop looking for the stamp without
    failing.
    """
    stamp = SOURCE_DATA_DIR.relative_to(DATA_DIST.source_root) / DATA_VERSION_FILENAME
    assert stamp in set(iter_expected_distribution_files(DATA_DIST)), (
        f"{stamp} is no longer among the files "
        f"test_essential_files_in_distribution checks for. Add a pattern matching "
        f"it to ESSENTIAL_DATA_PATTERNS."
    )
