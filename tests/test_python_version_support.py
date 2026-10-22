"""Assert every file that names a supported Python version agrees with the rest.

Six files declare the same fact and none of them can read the others:

    pyproject.toml   `requires-python`, and one classifier per minor version
    packages/timezonefinder-data/pyproject.toml   the same `requires-python`
    tox.ini          the `py{...}` factors of `envlist`
    build.yml        the `test` and `end-to-end-test` matrices, and
                     `CIBW_BUILD_VERSIONS` (the abi3 and abi3t bases)
    setup.py         `_ABI3_BASE` and `_ABI3T_BASE` (the same two bases)

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
import sys
import tomllib

import pytest
import yaml
from packaging.requirements import Requirement
from packaging.version import Version

from scripts.configs import DATA_PYPROJECT_FILE, PYPROJECT_FILE
from tests.auxiliaries import PROJECT_ROOT

TOX_INI = PROJECT_ROOT / "tox.ini"
BUILD_WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "build.yml"
SETUP_PY = PROJECT_ROOT / "setup.py"


def setup_constant(name: str) -> str:
    """A `cpXY` constant `setup.py` assigns at module level."""
    match = re.search(rf'^{name} = "(cp\d+)"$', SETUP_PY.read_text(), re.MULTILINE)
    assert match, f"setup.py no longer assigns {name} - update this test"
    return match.group(1)


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
    # a set: one version may carry several entries, e.g. one job for its expensive env
    matrix_minors = sorted(
        {int(str(entry["python-version"]).split(".")[1]) for entry in matrix_entries}
    )
    assert matrix_minors == classifier_minors, (
        "pyproject.toml classifiers and the build.yml test matrix disagree: a "
        "version claimed but not in the matrix is never tested"
    )


@pytest.mark.unit
def test_the_wheel_is_installed_on_exactly_the_advertised_versions(
    classifier_minors, build_workflow
):
    """The end-to-end job is what proves the built wheel loads on each version.

    Free-threaded identifiers (a trailing ``t``) are a separate claim, which
    `test_the_free_threaded_claim_is_tested_on_its_abi3t_base` holds.
    """
    versions = build_workflow["jobs"]["end-to-end-test"]["strategy"]["matrix"][
        "uv-python-version"
    ]
    installed_minors = sorted(int(v[3:]) for v in versions if not v.endswith("t"))
    assert installed_minors == classifier_minors, (
        "pyproject.toml classifiers and the build.yml end-to-end matrix disagree: a "
        "version claimed but not in that matrix never installs the built wheel"
    )


@pytest.mark.unit
def test_the_free_threaded_claim_is_tested_on_its_abi3t_base(
    classifier_minors, build_workflow, tox_config
):
    """The abi3t wheel is installed, and the suite run, on the interpreter it is built on.

    That interpreter is the oldest the wheel serves. Dropping the free-threaded
    end-to-end leg, or moving the free-threaded tox env to another interpreter, would
    leave the wheel shipped for a free-threaded build CI never runs.
    """
    abi3t_minor = max(classifier_minors[0], 15)
    versions = build_workflow["jobs"]["end-to-end-test"]["strategy"]["matrix"][
        "uv-python-version"
    ]
    assert [v for v in versions if v.endswith("t")] == [f"cp3{abi3t_minor}t"]
    setenv = tox_config["testenv:free-threaded"]["setenv"]
    assert f"UV_PYTHON = 3.{abi3t_minor}t" in setenv.splitlines()


@pytest.mark.unit
def test_the_data_distribution_mirrors_the_requires_python_floor():
    root = tomllib.loads(PYPROJECT_FILE.read_text())["project"]["requires-python"]
    data = tomllib.loads(DATA_PYPROJECT_FILE.read_text())["project"]["requires-python"]
    assert data == root, (
        "timezonefinder-data is only ever imported by timezonefinder, so its "
        "requires-python must be the root distribution's"
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
    assert setup_constant("_ABI3_BASE") == expected
    gil_identifiers = build_workflow["env"]["CIBW_BUILD_VERSIONS"].split()[0]
    assert gil_identifiers == f"{expected}-*"


@pytest.mark.unit
def test_the_abi3t_base_is_the_lowest_supported_free_threaded_version(
    classifier_minors, build_workflow
):
    """abi3t exists from 3.15, so its base is 3.15 until the floor passes it.

    A free-threaded wheel is built on its base interpreter alone and serves every
    later one, which is why `CIBW_BUILD_VERSIONS` names exactly that identifier.
    """
    expected = f"cp3{max(classifier_minors[0], 15)}"
    assert setup_constant("_ABI3T_BASE") == expected
    identifiers = build_workflow["env"]["CIBW_BUILD_VERSIONS"].split()
    assert identifiers[1:] == [f"{expected}t-*"]


@pytest.mark.unit
@pytest.mark.parametrize(
    ("build_abi3", "gil_disabled", "version", "setuptools_version", "limited_api"),
    [
        (True, 0, (3, 14), "84.0.0", "cp312"),
        (True, 1, (3, 14), "84.2.1", None),
        (True, 1, (3, 15), "84.1.0", None),
        (True, 1, (3, 15), "84.2.0", "cp315"),
        (True, 1, (3, 16), "85.0.0rc1", "cp315"),
        (True, 1, (3, 15), "0.dev0+unknown", None),
        (True, 0, (3, 15), "0.dev0+unknown", "cp312"),
        (False, 0, (3, 14), "84.2.1", None),
        (False, 1, (3, 15), "84.2.1", None),
    ],
    ids=[
        "gil-build",
        "free-threaded-before-3.15",
        "free-threaded-on-old-setuptools",
        "free-threaded-abi3t",
        "free-threaded-abi3t-later-minor",
        "free-threaded-unreadable-setuptools",
        "gil-build-unreadable-setuptools",
        "no-abi3-requested",
        "no-abi3t-requested",
    ],
)
def test_the_stable_abi_claim_is_gated_on_the_interpreter(
    monkeypatch, build_abi3, gil_disabled, version, setuptools_version, limited_api
):
    """`BUILD_ABI3` alone must not decide the stable-ABI claim.

    The cibuildwheel override sets it for every identifier, and setuptools raises
    on `py_limited_api` for a free-threaded build before 3.15 or before 84.2.0, so
    an environment-only guard turns such an identifier into a failed build. CI
    builds a free-threaded wheel only on its abi3t base, so `setup.py` is executed
    here with the interpreter's version, its `Py_GIL_DISABLED` answer and the
    setuptools version substituted. A setuptools version that cannot be read must
    neither raise nor claim abi3t, since a strict `int()` parse raises on one.
    """
    import setuptools
    import sysconfig

    captured = {}
    monkeypatch.setattr(setuptools, "setup", lambda **kwargs: captured.update(kwargs))
    monkeypatch.setattr(setuptools, "__version__", setuptools_version)
    monkeypatch.setattr(sys, "version_info", (*version, 0, "final", 0))
    real_get_config_var = sysconfig.get_config_var
    monkeypatch.setattr(
        sysconfig,
        "get_config_var",
        lambda name: (
            gil_disabled if name == "Py_GIL_DISABLED" else real_get_config_var(name)
        ),
    )
    if build_abi3:
        monkeypatch.setenv("BUILD_ABI3", "true")
    else:
        monkeypatch.delenv("BUILD_ABI3", raising=False)

    exec(compile(SETUP_PY.read_text(), str(SETUP_PY), "exec"), {"__name__": "setup"})

    assert captured["options"]["bdist_wheel"].get("py_limited_api") == limited_api


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
