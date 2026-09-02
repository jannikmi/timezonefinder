"""The public API of ``timezonefinder``: the finder classes and the global functions.

Every name below is resolved on first access rather than at import time (:pep:`562`),
which is what keeps the package's attribute surface equal to :data:`__all__`. Importing
the classes eagerly here would bind ``timezonefinder.timezonefinder`` - and through it
``utils``, ``configs``, ``polygon_array``, ``coord_accessors``, ``flatbuf`` and the rest
- as attributes of the package, making roughly twenty internal modules as reachable as
the seven documented names while carrying no stability promise. ``import
timezonefinder.utils`` still works, and still binds the submodule; what changed is that
``import timezonefinder`` alone no longer does it, which also makes the bare import
cheap.
"""

from importlib import import_module as _import_module

# The installed package version is read from the installed distribution's metadata
# (the wheel ships it via pyproject.toml's ``version``), so it stays correct across
# editable installs and built wheels without a hand-maintained ``_version.py``.
# ``_PackageNotFoundError`` only bites when the package is imported without being
# installed (running straight out of a source checkout with no metadata), where
# "unknown" is honest rather than pretending to a value that is not actually pinned.
# It is bound under a private name because it is the standard library's exception and
# not part of this package's surface.
from importlib.metadata import (
    PackageNotFoundError as _PackageNotFoundError,
    version as _metadata_version,
)
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # the lazy names, for type checkers and IDEs
    from timezonefinder.configs import NO_ZONE_ID
    from timezonefinder.global_functions import (
        certain_timezone_at,
        get_geometry,
        localize,
        timezone_at,
        timezone_at_land,
        timezone_ids_at,
        timezone_names_at,
        unique_timezone_at,
        utc_offset_at,
        zoneinfo_at,
    )
    from timezonefinder.timezonefinder import TimezoneFinder, TimezoneFinderL

try:
    __version__ = _metadata_version("timezonefinder")
except _PackageNotFoundError:  # pragma: no cover - source checkout without install
    __version__ = "unknown"

# which module each public name is imported from on first access. The finder classes
# and the global functions are separate modules, so a caller using only the global
# functions never imports the class module's dependencies either.
_LAZY_ATTRIBUTES: dict[str, str] = {
    "TimezoneFinder": "timezonefinder.timezonefinder",
    "TimezoneFinderL": "timezonefinder.timezonefinder",
    # the sentinel a batch answer holds where a scalar lookup would answer ``None``
    "NO_ZONE_ID": "timezonefinder.configs",
    "timezone_at": "timezonefinder.global_functions",
    "timezone_ids_at": "timezonefinder.global_functions",
    "timezone_names_at": "timezonefinder.global_functions",
    "timezone_at_land": "timezonefinder.global_functions",
    "unique_timezone_at": "timezonefinder.global_functions",
    "certain_timezone_at": "timezonefinder.global_functions",
    "get_geometry": "timezonefinder.global_functions",
    "zoneinfo_at": "timezonefinder.global_functions",
    "utc_offset_at": "timezonefinder.global_functions",
    "localize": "timezonefinder.global_functions",
}


def __getattr__(name: str) -> Any:
    """Resolve a public name on first access (:pep:`562`).

    Only the names in :data:`__all__` are served. Anything else raises the same
    ``AttributeError`` an ordinary missing attribute would, which is what stops an
    internal module from being reachable here merely because it exists.
    """
    try:
        module_name = _LAZY_ATTRIBUTES[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    value = getattr(_import_module(module_name), name)
    # cache on the module, so the lookup happens once rather than per access
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """The public surface, for ``dir()`` and interactive completion.

    Deliberately *not* the module's globals: reporting those is what let every
    transitively imported submodule read as part of the package.
    """
    return sorted({*__all__, "__version__"})


# https://docs.python.org/3/tutorial/modules.html#importing-from-a-package
# determines which objects will be imported with "import *"
__all__ = (
    "TimezoneFinder",
    "TimezoneFinderL",
    "NO_ZONE_ID",
    "timezone_at",
    "timezone_ids_at",
    "timezone_names_at",
    "timezone_at_land",
    "unique_timezone_at",
    "certain_timezone_at",
    "get_geometry",
    "zoneinfo_at",
    "utc_offset_at",
    "localize",
)
