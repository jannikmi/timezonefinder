"""FlatBuffer schema definitions for timezonefinder."""

from collections.abc import Iterator
from pathlib import Path

# The canonical schemas, and what ``make flatbuf`` compiles the Python bindings from.
# A compiled data directory carries a *copy* of them (see ``get_schemas_dir``), written
# by scripts/file_converter.py - so this is the one place the originals are named.
SCHEMA_DIR: Path = Path(__file__).parent
SCHEMA_SUFFIX = ".fbs"


def iter_schema_files() -> Iterator[Path]:
    """The schema definitions, in a stable order."""
    return iter(sorted(SCHEMA_DIR.glob(f"*{SCHEMA_SUFFIX}")))


def get_schemas_dir(data_dir: Path) -> Path:
    """Where a compiled data directory keeps the schemas describing its own binaries.

    A subdirectory rather than the data root, so that the schemas stay separable from
    the buffers they describe: the data root is regenerated from the upstream boundary
    release, these are copied from this package, and only one of the two is rewritten
    by a schema change.
    """
    return data_dir / "schemas"


__all__ = [
    "SCHEMA_DIR",
    "SCHEMA_SUFFIX",
    "get_schemas_dir",
    "iter_schema_files",
    "polygons",
    "hybrid_shortcuts_uint8",
    "hybrid_shortcuts_uint16",
]
