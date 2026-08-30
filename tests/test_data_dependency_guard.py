"""The guard that keeps a `timezonefinder` release from outrunning its data.

The two distributions are released independently and, on a data format change, in a
fixed order. Publishing the code first puts a wheel on PyPI that nobody can install,
and PyPI never accepts a version number twice - so the mistake costs a whole release
and cannot be undone. Everything here is about that check being able to fail.
"""

import zipfile

import pytest
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import Version

from scripts.check_data_dependency import (
    EXIT_INCOMPATIBLE,
    EXIT_UNDETERMINED,
    UndeterminedError,
    find_wheels,
    main,
    read_requirement,
    released_versions,
)
from scripts.configs import DATA_DISTRIBUTION_NAME

REQUIREMENT = f"{DATA_DISTRIBUTION_NAME}>=1.2026.3,<2"


def _wheel(
    tmp_path,
    requires=(REQUIREMENT,),
    name="timezonefinder-8.2.5",
    tag="py3-none-any",
):
    """A wheel carrying just enough metadata for the guard to read."""
    distribution, version = name.rsplit("-", maxsplit=1)
    path = tmp_path / f"{distribution.replace('-', '_')}-{version}-{tag}.whl"
    metadata = "Metadata-Version: 2.4\nName: timezonefinder\nVersion: 8.2.5\n"
    metadata += "".join(f"Requires-Dist: {r}\n" for r in requires)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"{name.replace('-', '_')}.dist-info/METADATA", metadata)
    return path


def _payload(*versions, yanked=()):
    return {
        "releases": {
            v: [{"filename": f"x-{v}.whl", "yanked": v in yanked}] for v in versions
        }
    }


@pytest.mark.unit
def test_the_requirement_is_read_from_the_wheel_that_will_be_published(tmp_path):
    """Not from pyproject.toml: the wheel is the artefact a resolver actually reads."""
    wheel = _wheel(tmp_path, requires=("numpy>=2", REQUIREMENT, "h3>=4"))
    requirement = read_requirement(wheel, DATA_DISTRIBUTION_NAME)
    # compared as a SpecifierSet, not as text: str() sorts the clauses, so the
    # rendering differs from what the wheel declared
    assert requirement.specifier == SpecifierSet(">=1.2026.3,<2")


@pytest.mark.unit
def test_a_wheel_without_the_dependency_is_undetermined_rather_than_passing(tmp_path):
    """The failure mode of a guard is passing for the wrong reason.

    A wheel declaring no data dependency makes every version check below vacuously
    true, so it must stop the release and say so rather than wave it through.
    """
    wheel = _wheel(tmp_path, requires=("numpy>=2",))
    with pytest.raises(UndeterminedError, match="declares no dependency"):
        read_requirement(wheel, DATA_DISTRIBUTION_NAME)


@pytest.mark.unit
def test_a_fully_yanked_release_does_not_count_as_published():
    """pip will not select a yanked version to satisfy a range, so neither may this.

    Counting one would let the guard pass on exactly the release a yank was meant to
    take out of circulation.
    """
    payload = _payload("1.2026.3", "1.2026.4", yanked=("1.2026.4",))
    assert released_versions(payload) == [Version("1.2026.3")]


@pytest.mark.unit
def test_a_release_with_no_files_does_not_count_as_published():
    assert released_versions({"releases": {"1.2026.3": []}}) == []


@pytest.mark.unit
@pytest.mark.parametrize(
    ("published", "satisfied"),
    [
        ((), False),  # nothing published at all - the bootstrap case
        (("1.2026.3",), True),
        (("1.2026.4",), True),  # a later data release inside the format generation
        (("1.2026.2",), False),  # older than the floor
        (("2.2026.1",), False),  # the next format generation, excluded by the ceiling
        (("2.2026.1", "1.2026.3"), True),
    ],
)
def test_only_a_version_inside_the_declared_bound_satisfies_it(published, satisfied):
    requirement = Requirement(REQUIREMENT)
    versions = released_versions(_payload(*published))
    compatible = [v for v in versions if requirement.specifier.contains(v)]
    assert bool(compatible) is satisfied


@pytest.mark.unit
def test_a_missing_wheel_is_undetermined(tmp_path):
    with pytest.raises(UndeterminedError, match="no timezonefinder-\\*.whl"):
        find_wheels(tmp_path, "timezonefinder")


@pytest.mark.unit
def test_platform_wheels_for_one_version_are_all_accepted(tmp_path):
    first = _wheel(tmp_path)
    second = _wheel(tmp_path, tag="cp314-abi3-macosx_11_0_arm64")
    assert find_wheels(tmp_path, "timezonefinder") == sorted([first, second])


@pytest.mark.unit
def test_wheels_for_multiple_versions_are_undetermined(tmp_path):
    _wheel(tmp_path, name="timezonefinder-8.2.5")
    _wheel(tmp_path, name="timezonefinder-8.3.0")

    with pytest.raises(UndeterminedError, match="found 8.2.5, 8.3.0"):
        find_wheels(tmp_path, "timezonefinder")


@pytest.mark.unit
def test_an_invalid_wheel_filename_exits_undetermined(tmp_path, capsys):
    wheel = tmp_path / "timezonefinder-junk.whl"
    wheel.touch()

    assert main(["--dist-dir", str(tmp_path)]) == EXIT_UNDETERMINED
    assert wheel.name in capsys.readouterr().err


@pytest.mark.unit
def test_the_two_failure_kinds_have_distinct_exit_codes():
    """ "Nothing satisfies it" and "the check could not run" are different answers.

    A release blocked because PyPI was unreachable is a retry; one blocked because the
    data is genuinely missing needs the data published first. Collapsing them into a
    single non-zero code loses the only thing the operator needs to know.
    """
    assert EXIT_INCOMPATIBLE != EXIT_UNDETERMINED
    assert 0 not in (EXIT_INCOMPATIBLE, EXIT_UNDETERMINED)
