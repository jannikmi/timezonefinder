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
    matrix_entries, tox_minors
):
    # the envlist generates py3XY plus the -numba / -pytz variants; `slow` and
    # `docs` are standalone testenv sections
    generated = {
        f"py3{minor}{suffix}"
        for minor in tox_minors
        for suffix in ("", "-numba", "-pytz")
    }
    generated |= {"slow", "docs"}
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
