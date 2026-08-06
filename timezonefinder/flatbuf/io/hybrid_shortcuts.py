"""Utilities for working with optimized hybrid shortcut FlatBuffer data."""

from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

import flatbuffers
import numpy as np

from timezonefinder.configs import DEFAULT_DATA_DIR

# The two generated packages describe the same tables and differ only in the width of
# `UniqueZone.zone_id` (ubyte vs ushort), so they export identically named symbols.
# Bind the generated *modules* (each holds a table class next to its builder helpers)
# instead of re-aliasing every symbol per width: one SHORTCUT_SCHEMAS entry below is
# then all a zone id width needs.
from timezonefinder.flatbuf.generated.shortcuts_uint8 import (
    HybridShortcutCollection as _uint8_collection,
    HybridShortcutEntry as _uint8_entry,
    PolygonList as _uint8_polygon_list,
    UniqueZone as _uint8_unique_zone,
)
from timezonefinder.flatbuf.generated.shortcuts_uint8.ShortcutValue import (
    ShortcutValue as _Uint8ShortcutValue,
)
from timezonefinder.flatbuf.generated.shortcuts_uint16 import (
    HybridShortcutCollection as _uint16_collection,
    HybridShortcutEntry as _uint16_entry,
    PolygonList as _uint16_polygon_list,
    UniqueZone as _uint16_unique_zone,
)
from timezonefinder.flatbuf.generated.shortcuts_uint16.ShortcutValue import (
    ShortcutValue as _Uint16ShortcutValue,
)


@dataclass(frozen=True)
class ShortcutSchema:
    """Everything that differs between the hybrid shortcut schemas.

    One instance per supported zone id width. The generated modules carry both the
    table classes used when reading and the ``<Table><Verb>`` builder helpers used
    when writing.
    """

    #: width of the zone ids this schema stores; the single source of the width
    zone_id_dtype: np.dtype
    collection: ModuleType
    entry: ModuleType
    unique_zone: ModuleType
    polygon_list: ModuleType
    #: ``ShortcutValue`` union tags, as stored in and read back from ``entry.ValueType()``
    unique_zone_tag: int
    polygon_list_tag: int

    @property
    def dtype_name(self) -> str:
        """``"uint8"`` / ``"uint16"`` - the marker embedded in the binary's file name."""
        return self.zone_id_dtype.name

    @property
    def file_name(self) -> str:
        """Name of the shortcut binary written with this schema."""
        return f"hybrid_shortcuts_{self.dtype_name}.fbs"

    @property
    def max_zone_id(self) -> int:
        """Largest zone id representable in this schema."""
        return int(np.iinfo(self.zone_id_dtype).max)


#: Supported zone id widths, narrowest first. `_schema_for_file_name` scans this in
#: order, so a name matching several markers resolves to the narrowest - as the
#: previous `if "uint8" ... elif "uint16" ...` chain did.
SHORTCUT_SCHEMAS: tuple[ShortcutSchema, ...] = (
    ShortcutSchema(
        zone_id_dtype=np.dtype("<u1"),
        collection=_uint8_collection,
        entry=_uint8_entry,
        unique_zone=_uint8_unique_zone,
        polygon_list=_uint8_polygon_list,
        unique_zone_tag=_Uint8ShortcutValue.UniqueZone,
        polygon_list_tag=_Uint8ShortcutValue.PolygonList,
    ),
    ShortcutSchema(
        zone_id_dtype=np.dtype("<u2"),
        collection=_uint16_collection,
        entry=_uint16_entry,
        unique_zone=_uint16_unique_zone,
        polygon_list=_uint16_polygon_list,
        unique_zone_tag=_Uint16ShortcutValue.UniqueZone,
        polygon_list_tag=_Uint16ShortcutValue.PolygonList,
    ),
)

_SUPPORTED_DTYPE_NAMES = ", ".join(f"'{s.dtype_name}'" for s in SHORTCUT_SCHEMAS)


def _schema_for_zone_id_width(zone_id_dtype: np.dtype) -> ShortcutSchema:
    """Select the schema storing zone ids of the same width as ``zone_id_dtype``."""
    for schema in SHORTCUT_SCHEMAS:
        if schema.zone_id_dtype.itemsize == zone_id_dtype.itemsize:
            return schema
    raise ValueError(
        f"Unsupported zone_id_dtype: {zone_id_dtype}. "
        f"Supported: {_SUPPORTED_DTYPE_NAMES}."
    )


def _schema_for_file_name(file_name: str) -> ShortcutSchema:
    """Detect which schema a shortcut binary uses from the zone id width in its name.

    Matches the ``uintN`` marker anywhere in the name rather than requiring
    ``ShortcutSchema.file_name`` exactly, so binaries written to a scratch path
    (as the tests do) are still readable.
    """
    for schema in SHORTCUT_SCHEMAS:
        if schema.dtype_name in file_name:
            return schema
    raise ValueError(
        f"Cannot determine schema from filename: {file_name}. "
        f"Filename must include one of: {_SUPPORTED_DTYPE_NAMES}."
    )


def get_hybrid_shortcut_file_path(
    zone_id_dtype: np.dtype, output_path: Path = DEFAULT_DATA_DIR
) -> Path:
    """Return the path to the appropriate hybrid shortcut FlatBuffer binary file."""
    return output_path / _schema_for_zone_id_width(zone_id_dtype).file_name


def _schema_for_zone_ids(zone_id_dtype: np.dtype) -> ShortcutSchema:
    """Validate a zone ID dtype and return the schema that can store it."""
    dtype = np.dtype(zone_id_dtype)
    if dtype.kind != "u":
        raise ValueError(f"Zone id dtype must be unsigned integer, got {dtype}")
    if dtype.itemsize not in (1, 2):
        raise ValueError(
            f"Zone id dtype must be 1 or 2 bytes, got {dtype.itemsize} bytes"
        )
    return _schema_for_zone_id_width(dtype)


def write_hybrid_shortcuts_flatbuffers(
    hybrid_mapping: dict[int, int | list[int]],
    zone_id_dtype: np.dtype,
    output_file: Path,
) -> None:
    """
    Write hybrid shortcut mapping to the appropriate optimized FlatBuffer binary file.

    Args:
        hybrid_mapping: Dictionary mapping H3 hexagon IDs to either:
                       - int: unique zone ID (when all polygons share same zone)
                       - list[int]: list of polygon IDs (when multiple zones)
        zone_id_dtype: numpy dtype for zone IDs (uint8 or uint16)
        output_file: Path to save the FlatBuffer file
    """
    print(f"Writing {len(hybrid_mapping)} optimized hybrid shortcuts to {output_file}")

    schema = _schema_for_zone_ids(zone_id_dtype)
    _write_hybrid_shortcuts_with_schema(hybrid_mapping, output_file, schema)


def _write_hybrid_shortcuts_with_schema(
    hybrid_mapping: dict[int, int | list[int]],
    output_file: Path,
    schema: ShortcutSchema,
) -> None:
    """Write hybrid shortcuts using the provided schema."""
    builder = flatbuffers.Builder(0)
    entry_offsets = []

    # Validate zone IDs fit in dtype
    for value in hybrid_mapping.values():
        if isinstance(value, int) and value > schema.max_zone_id:
            raise ValueError(
                f"Zone ID {value} exceeds {schema.dtype_name} maximum ({schema.max_zone_id})"
            )

    for hex_id, value in hybrid_mapping.items():
        if isinstance(value, int):
            # Create UniqueZone with direct storage
            schema.unique_zone.UniqueZoneStart(builder)
            schema.unique_zone.UniqueZoneAddZoneId(builder, value)
            unique_zone_offset = schema.unique_zone.UniqueZoneEnd(builder)

            # Create entry with UniqueZone
            schema.entry.HybridShortcutEntryStart(builder)
            schema.entry.HybridShortcutEntryAddHexId(builder, hex_id)
            schema.entry.HybridShortcutEntryAddValueType(
                builder, schema.unique_zone_tag
            )
            schema.entry.HybridShortcutEntryAddValue(builder, unique_zone_offset)
            entry_offset = schema.entry.HybridShortcutEntryEnd(builder)

        else:
            # Create PolygonList. `poly_ids` is `[ushort]` in both schemas - only the
            # width of `UniqueZone.zone_id` varies - hence the fixed PrependUint16.
            poly_ids = list(value)
            schema.polygon_list.PolygonListStartPolyIdsVector(builder, len(poly_ids))
            for i in range(len(poly_ids) - 1, -1, -1):
                builder.PrependUint16(poly_ids[i])
            poly_ids_vector = builder.EndVector()

            schema.polygon_list.PolygonListStart(builder)
            schema.polygon_list.PolygonListAddPolyIds(builder, poly_ids_vector)
            polygon_list_offset = schema.polygon_list.PolygonListEnd(builder)

            # Create entry with PolygonList
            schema.entry.HybridShortcutEntryStart(builder)
            schema.entry.HybridShortcutEntryAddHexId(builder, hex_id)
            schema.entry.HybridShortcutEntryAddValueType(
                builder, schema.polygon_list_tag
            )
            schema.entry.HybridShortcutEntryAddValue(builder, polygon_list_offset)
            entry_offset = schema.entry.HybridShortcutEntryEnd(builder)

        entry_offsets.append(entry_offset)

    # Create entries vector
    schema.collection.HybridShortcutCollectionStartEntriesVector(
        builder, len(entry_offsets)
    )
    for offset in reversed(entry_offsets):
        builder.PrependUOffsetTRelative(offset)
    entries_vector = builder.EndVector()

    # Create HybridShortcutCollection
    schema.collection.HybridShortcutCollectionStart(builder)
    schema.collection.HybridShortcutCollectionAddEntries(builder, entries_vector)
    collection = schema.collection.HybridShortcutCollectionEnd(builder)

    builder.Finish(collection)

    # Write to file
    with open(output_file, "wb") as f:
        f.write(builder.Output())


def read_hybrid_shortcuts_binary(
    file_path: Path,
) -> dict[int, int | np.ndarray]:
    """
    Read hybrid shortcut mapping from an optimized FlatBuffer binary file.

    Auto-detects whether the file uses uint8 or uint16 schema based on filename.

    Args:
        file_path: Path to the hybrid shortcut FlatBuffer file

    Returns:
        Dictionary mapping H3 hexagon IDs to either:
        - int: unique zone ID (when all polygons share same zone)
        - np.ndarray: array of polygon IDs (when multiple zones)
    """
    schema = _schema_for_file_name(file_path.name)
    return _read_hybrid_shortcuts_with_schema(file_path, schema)


def _read_hybrid_shortcuts_with_schema(
    file_path: Path, schema: ShortcutSchema
) -> dict[int, int | np.ndarray]:
    """Read hybrid shortcuts using the provided schema."""
    with open(file_path, "rb") as f:
        buf = f.read()

    collection = schema.collection.HybridShortcutCollection.GetRootAs(buf, 0)

    hybrid_mapping: dict[int, int | np.ndarray] = {}
    # `PolyIdsAsNumpy()` is `np.frombuffer` under the hood, i.e. a view onto `buf`.
    # Keeping those views would pin the whole file (~1.5 MB) for the lifetime of every
    # finder instance although only ~47 KB of poly ids are ever read. So copy each one
    # out as it is decoded and let it die immediately, accumulating the payload in
    # `poly_id_payload`; the entries are filled in with slices of it below.
    #
    # The copy has to happen here, in the same iteration that decodes the view. Holding
    # the views to concatenate them afterwards frees `buf` just as well, but then the
    # whole set of views is alive while the replacement arrays are being built, and that
    # transient peak (measured: 8.98 MiB against 7.09 MiB for the pinning version) ends
    # up as permanent RSS - the allocator does not return the pages. Heap and resident
    # set move in opposite directions, which is the wrong trade for the constrained
    # containers this saves memory for.
    poly_id_payload = bytearray()
    poly_id_dtype: np.dtype | None = None
    poly_id_hex_ids: list[int] = []
    poly_id_lengths: list[int] = []
    for i in range(collection.EntriesLength()):
        entry = collection.Entries(i)
        hex_id = entry.HexId()

        # Determine value type and extract data
        value_type = entry.ValueType()
        value = entry.Value()

        if value_type == schema.unique_zone_tag:
            unique_zone = schema.unique_zone.UniqueZone()
            unique_zone.Init(value.Bytes, value.Pos)
            zone_id = unique_zone.ZoneId()  # Direct zone ID, no lookup needed
            hybrid_mapping[hex_id] = int(zone_id)

        elif value_type == schema.polygon_list_tag:
            polygon_list = schema.polygon_list.PolygonList()
            polygon_list.Init(value.Bytes, value.Pos)
            poly_ids = polygon_list.PolyIdsAsNumpy()
            poly_id_dtype = poly_ids.dtype
            poly_id_payload += poly_ids.tobytes()
            poly_id_hex_ids.append(hex_id)
            poly_id_lengths.append(len(poly_ids))
            # placeholder, replaced below - claims the key's position in the mapping so
            # that it keeps being iterated in file order (`test_shortcut_sorting`,
            # `scripts/reporting.py`), which overwriting an existing key preserves
            hybrid_mapping[hex_id] = 0

        else:
            raise ValueError(f"Unknown ShortcutValue type: {value_type}")

    if poly_id_dtype is not None:
        # `np.frombuffer` on `bytes` yields exactly what the entries held before: a
        # read-only view, so no cell can write into a neighbour's block - only now the
        # object behind them is 47 KB rather than the whole file.
        flat = np.frombuffer(bytes(poly_id_payload), dtype=poly_id_dtype)
        offset = 0
        for hex_id, length in zip(poly_id_hex_ids, poly_id_lengths):
            end = offset + length
            hybrid_mapping[hex_id] = flat[offset:end]
            offset = end

    return hybrid_mapping
