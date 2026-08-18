from timezonefinder.timezonefinder import (
    TimezoneFinder,
    TimezoneFinderL,
)

# Import module-level functions
from timezonefinder.global_functions import (
    timezone_at,
    timezone_at_land,
    unique_timezone_at,
    certain_timezone_at,
    get_geometry,
)

# The installed package version. ``importlib.metadata`` reads it from the
# installed distribution's metadata (the wheel ships it via pyproject.toml's
# ``version``), so this stays correct across editable installs and built
# wheels without a hand-maintained ``_version.py``. ``PackageNotFoundError``
# only bites when the package is imported without being installed (running
# straight out of a source checkout with no metadata), where "unknown" is
# honest rather than pretending to a value that is not actually pinned.
from importlib.metadata import PackageNotFoundError, version as _metadata_version

try:
    __version__ = _metadata_version("timezonefinder")
except PackageNotFoundError:  # pragma: no cover - source checkout without install
    __version__ = "unknown"

# https://docs.python.org/3/tutorial/modules.html#importing-from-a-package
# determines which objects will be imported with "import *"
__all__ = (
    "TimezoneFinder",
    "TimezoneFinderL",
    "timezone_at",
    "timezone_at_land",
    "unique_timezone_at",
    "certain_timezone_at",
    "get_geometry",
)
