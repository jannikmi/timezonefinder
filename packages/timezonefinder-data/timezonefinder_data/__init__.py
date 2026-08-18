"""The timezone boundary data ``timezonefinder`` answers lookups from.

This distribution exists to give the ~63 MB dataset a release cadence of its own:
an upstream boundary release ships as a new ``timezonefinder-data`` without a
``timezonefinder`` release, and a user who needs the answers of a particular
dataset can pin it without giving up code fixes.
"""

from importlib.metadata import PackageNotFoundError, version as _metadata_version
from pathlib import Path

# The packaged data directory. A real filesystem path rather than an
# ``importlib.resources`` traversable, because ``FileCoordAccessor`` memory-maps the
# coordinate files via ``fileno()`` - which is also why the data ships inside an
# importable package instead of as bare package data.
DATA_DIR: Path = Path(__file__).parent / "data"

# The installed distribution's version, read the way ``timezonefinder.__version__``
# reads its own: from the installed metadata rather than a hand-maintained constant,
# which drifts from what is actually installed. A bug report wants both numbers, and
# only the pair says which dataset answered. ``PackageNotFoundError`` bites when the
# package is imported without being installed (a source checkout with no metadata),
# where "unknown" is honest.
try:
    __version__ = _metadata_version("timezonefinder-data")
except PackageNotFoundError:  # pragma: no cover - source checkout without install
    __version__ = "unknown"

__all__ = (
    "DATA_DIR",
    "__version__",
)
