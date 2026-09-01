"""The package's own attribute surface, and the two ways it used to be wider than stated.

``timezonefinder/__init__.py`` resolves its public names lazily (:pep:`562`) so that the
package's attributes are the ones ``__all__`` declares, rather than every module the
eager imports happened to drag in. Nothing else pins that: an ordinary
``from timezonefinder.timezonefinder import TimezoneFinder`` at the top of the file
restores the wide surface silently, and every test in the suite still passes.
"""

import ast
import subprocess
import sys

import pytest

import timezonefinder

# the modules a single eager import used to bind as package attributes, through the
# chain ``timezonefinder`` -> ``timezonefinder.timezonefinder`` -> everything it imports
FORMERLY_REACHABLE_SUBMODULES = (
    "utils",
    "configs",
    "polygon_array",
    "coord_accessors",
    "np_binary_helpers",
    "zone_names",
    "shortcut_index",
    "flatbuf",
)


@pytest.mark.unit
def test_the_declared_surface_is_the_reachable_surface():
    """``dir(timezonefinder)`` answers ``__all__``, not the module's globals."""
    assert set(dir(timezonefinder)) == {*timezonefinder.__all__, "__version__"}


@pytest.mark.unit
def test_a_bare_import_binds_no_submodule():
    """Run in its own interpreter: any other test importing a submodule binds it here.

    The attribute is set by the import system on the parent package, so once anything in
    this process has imported ``timezonefinder.utils`` the attribute exists for good -
    which is exactly why this cannot be asserted in-process.
    """
    code = (
        "import sys, timezonefinder;"
        "print([m for m in sys.modules if m.startswith('timezonefinder.')])"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    imported = ast.literal_eval(result.stdout)
    assert imported == [], (
        f"`import timezonefinder` pulled in {imported}. The public names are meant to "
        "resolve on first access, so the bare import stays cheap and binds no submodule."
    )


@pytest.mark.unit
@pytest.mark.parametrize("submodule", FORMERLY_REACHABLE_SUBMODULES)
def test_a_submodule_is_still_importable(submodule: str):
    """The narrowing is attribute access, not importability - see the PEP 562 decision.

    ``import timezonefinder.utils`` keeps working and keeps binding the attribute; what
    changed is that nothing does it on the caller's behalf.
    """
    __import__(f"timezonefinder.{submodule}")


@pytest.mark.unit
def test_an_unknown_attribute_raises_attribute_error():
    """The lazy resolver serves ``__all__`` and nothing else."""
    with pytest.raises(AttributeError, match="no attribute 'does_not_exist'"):
        timezonefinder.does_not_exist


@pytest.mark.unit
@pytest.mark.parametrize("name", timezonefinder.__all__)
def test_every_declared_name_resolves(name: str):
    """Each entry of ``__all__`` is served by the lazy resolver."""
    assert getattr(timezonefinder, name) is not None


@pytest.mark.unit
def test_the_metadata_exception_is_private():
    """The stdlib exception the version lookup catches is not part of this surface."""
    assert not hasattr(timezonefinder, "PackageNotFoundError")
