"""Assert every file that names a supported Python version agrees with the rest.

Five files declare the same fact and none of them can read the others:

    pyproject.toml   `requires-python`, and one classifier per minor version
    tox.ini          the `py{...}` factors of `envlist`
    build.yml        the `test` matrix, and `CIBW_BUILD_VERSIONS` (the abi3 base)
    setup.py         `py_limited_api` (the same abi3 base)

Two "must match" comments already point at this - one above `requires-python`,
one above the build matrix - and nothing enforced them. A one-sided edit fails
quietly rather than loudly: adding a minor version to the classifiers without
adding a matrix entry ships a version the package claims to support and CI
never runs, and raising `requires-python` without raising the abi3 base builds
wheels tagged for an interpreter the package no longer supports.

Same reasoning as tests/test_benchmark_workflows.py, for a different set of
files that repeat a constant across the workflow boundary.
"""

import configparser
import re
import tomllib

import pytest
import yaml
from packaging.requirements import Requirement
from packaging.version import Version

from scripts.configs import PYPROJECT_FILE
from tests.auxiliaries import PROJECT_ROOT

TOX_INI = PROJECT_ROOT / "tox.ini"
BUILD_WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "build.yml"
SETUP_PY = PROJECT_ROOT / "setup.py"


@pytest.fixture(scope="module")
def classifier_minors() -> list[int]:
    """The minor versions `pyproject.toml` advertises to PyPI."""
    classifiers = tomllib.loads(PYPROJECT_FILE.read_text())["project"]["classifiers"]
    matches = (
        re.fullmatch(r"Programming Language :: Python :: 3\.(\d+)", c)
        for c in classifiers
    )
    return sorted(int(m.group(1)) for m in matches if m)


@pytest.fixture(scope="module")
def tox_minors() -> list[int]:
    """The minor versions `tox.ini`'s envlist generates `py3XY` factors for."""
    parser = configparser.ConfigParser()
    parser.read_string(TOX_INI.read_text())
    factors = re.search(r"py\{([\d,]+)\}", parser["tox"]["envlist"])
    assert factors, "envlist no longer uses a py{...} factor - update this test"
    return sorted(int(v[1:]) for v in factors.group(1).split(","))


@pytest.fixture(scope="module")
def tox_config() -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    parser.read_string(TOX_INI.read_text())
    return parser


@pytest.fixture(scope="module")
def standalone_tox_envs(tox_config) -> set[str]:
    """The envs tox.ini declares by name, e.g. `slow`, `docs`, `py311-min`."""
    return {
        section.split(":", 1)[1]
        for section in tox_config.sections()
        if section.startswith("testenv:")
    }


@pytest.fixture(scope="module")
def build_workflow() -> dict:
    return yaml.safe_load(BUILD_WORKFLOW.read_text())


@pytest.fixture(scope="module")
def matrix_entries(build_workflow) -> list[dict]:
    return build_workflow["jobs"]["test"]["strategy"]["matrix"]["include"]


@pytest.mark.unit
def test_the_ci_matrix_covers_exactly_the_advertised_versions(
    classifier_minors, matrix_entries
):
    matrix_minors = sorted(
        int(str(entry["python-version"]).split(".")[1]) for entry in matrix_entries
    )
    assert matrix_minors == classifier_minors, (
        "pyproject.toml classifiers and the build.yml test matrix disagree: a "
        "version claimed but not in the matrix is never tested"
    )


@pytest.mark.unit
def test_tox_defines_an_env_for_exactly_the_advertised_versions(
    classifier_minors, tox_minors
):
    assert tox_minors == classifier_minors


@pytest.mark.unit
def test_every_tox_env_named_in_the_matrix_is_generated_by_the_envlist(
    matrix_entries, tox_minors, standalone_tox_envs
):
    # the envlist generates py3XY plus the -numba / -pytz variants; `slow`, `docs`
    # and the minimum-dependency env are standalone testenv sections, read off
    # tox.ini rather than listed here so adding one needs no edit to this test
    generated = {
        f"py3{minor}{suffix}"
        for minor in tox_minors
        for suffix in ("", "-numba", "-pytz")
    }
    generated |= standalone_tox_envs
    for entry in matrix_entries:
        for env in str(entry["tox-env"]).split(","):
            assert env in generated, (
                f"build.yml runs `tox -e {env}`, which tox.ini does not define"
            )


@pytest.mark.unit
def test_requires_python_floor_is_the_lowest_advertised_version(classifier_minors):
    requires = tomllib.loads(PYPROJECT_FILE.read_text())["project"]["requires-python"]
    floor = re.search(r">=\s*3\.(\d+)", requires)
    assert floor, f"cannot read a 3.x floor out of requires-python = {requires!r}"
    assert int(floor.group(1)) == classifier_minors[0]


@pytest.mark.unit
def test_the_abi3_base_is_the_lowest_supported_version(
    classifier_minors, build_workflow
):
    """The one comment above `requires-python` in pyproject.toml, enforced.

    An abi3 wheel is tagged for its base interpreter and works on everything
    above it, so the base has to be the *lowest* supported version - higher and
    the wheel is unusable on versions the package claims, lower and it targets
    an interpreter that is no longer supported.
    """
    expected = f"cp3{classifier_minors[0]}"
    setup_base = re.search(r'"py_limited_api":\s*"(cp\d+)"', SETUP_PY.read_text())
    assert setup_base, "setup.py no longer sets py_limited_api - update this test"
    assert setup_base.group(1) == expected
    assert build_workflow["env"]["CIBW_BUILD_VERSIONS"] == f"{expected}-*"


@pytest.mark.unit
def test_the_min_numpy_env_pins_the_declared_numpy_lower_bound(tox_config):
    """The `py311-min` pin is the floor `pyproject.toml` publishes, not a guess.

    The env exists to prove the declared `numpy` lower bound still works. Pinned
    to anything else it proves something the package never claimed, and the claim
    goes back to being untested - silently, because the env stays green. So the
    two numbers are compared here: moving the published bound without moving the
    pin (or the reverse) fails.
    """
    pinned = Version(tox_config["min-deps"]["numpy"])
    dependencies = tomllib.loads(PYPROJECT_FILE.read_text())["project"]["dependencies"]
    numpy_reqs = [
        Requirement(dep)
        for dep in dependencies
        if Requirement(dep).name.lower() == "numpy"
    ]
    assert len(numpy_reqs) == 1, "expected exactly one `numpy` dependency declaration"
    specifier = numpy_reqs[0].specifier
    assert pinned in specifier, (
        f"tox.ini pins numpy=={pinned}, which pyproject.toml's `numpy{specifier}` "
        "does not allow"
    )
    # the floor itself, not merely some allowed version: anything above it would
    # leave the lowest version the package promises to work with untested
    lower_bounds = [s for s in specifier if s.operator in (">=", "==", "~=")]
    assert len(lower_bounds) == 1, (
        f"cannot read a single lower bound out of `numpy{specifier}`"
    )
    declared_floor = Version(lower_bounds[0].version)
    assert (pinned.major, pinned.minor) == (
        declared_floor.major,
        declared_floor.minor,
    ), (
        f"tox.ini pins numpy=={pinned} while pyproject.toml declares a floor of "
        f"{declared_floor}: the minimum-dependency env would not exercise the "
        "published lower bound"
    )
