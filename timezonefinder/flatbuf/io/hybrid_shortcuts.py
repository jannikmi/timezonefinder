"""Utilities for working with optimized hybrid shortcut FlatBuffer data."""

from pathlib import Path
from typing import Dict, List, Union

import flatbuffers
import numpy as np

from timezonefinder.configs import DEFAULT_DATA_DIR


def get_hybrid_shortcut_file_path(
    zone_id_dtype: np.dtype, output_path: Path = DEFAULT_DATA_DIR
) -> Path:
    """Return the path to the appropriate hybrid shortcut FlatBuffer binary file."""
    if zone_id_dtype.itemsize == 1:
        return output_path / "hybrid_shortcuts_uint8.fbs"
    elif zone_id_dtype.itemsize == 2:
        return output_path / "hybrid_shortcuts_uint16.fbs"
    else:
        raise ValueError(
            f"Unsupported zone_id_dtype: {zone_id_dtype}. Use uint8 or uint16."
        )


def _validate_zone_id_dtype(zone_id_dtype: np.dtype) -> np.dtype:
    """Validate and normalize zone ID dtype."""
    dtype = np.dtype(zone_id_dtype)
    if dtype.kind != "u":
        raise ValueError(f"Zone id dtype must be unsigned integer, got {dtype}")
    if dtype.itemsize not in (1, 2):
        raise ValueError(
            f"Zone id dtype must be 1 or 2 bytes, got {dtype.itemsize} bytes"
        )
    return dtype.newbyteorder("<")


def write_hybrid_shortcuts_flatbuffers(
    hybrid_mapping: Dict[int, Union[int, List[int]]],
    zone_id_dtype: np.dtype,
    output_file: Path,
) -> None:
    """
    Write hybrid shortcut mapping to the appropriate optimized FlatBuffer binary file.

    Args:
        hybrid_mapping: Dictionary mapping H3 hexagon IDs to either:
                       - int: unique zone ID (when all polygons share same zone)
                       - List[int]: list of polygon IDs (when multiple zones)
        zone_id_dtype: numpy dtype for zone IDs (uint8 or uint16)
        output_file: Path to save the FlatBuffer file
    """
    print(f"Writing {len(hybrid_mapping)} optimized hybrid shortcuts to {output_file}")

    dtype = _validate_zone_id_dtype(zone_id_dtype)
    _write_hybrid_shortcuts_generic(hybrid_mapping, dtype, output_file)


def _write_hybrid_shortcuts_generic(
    hybrid_mapping: Dict[int, Union[int, List[int]]],
    zone_id_dtype: np.dtype,
    output_file: Path,
) -> None:
    """Write hybrid shortcuts using the appropriate schema based on dtype."""
    if zone_id_dtype.itemsize == 1:
        _write_hybrid_shortcuts_with_modules(
            hybrid_mapping, output_file, "shortcuts_uint8", 255, "uint8"
        )
    else:
        _write_hybrid_shortcuts_with_modules(
            hybrid_mapping, output_file, "shortcuts_uint16", 65535, "uint16"
        )


def _write_hybrid_shortcuts_with_modules(
    hybrid_mapping: Dict[int, Union[int, List[int]]],
    output_file: Path,
    module_name: str,
    max_zone_id: int,
    dtype_name: str,
) -> None:
    """Write hybrid shortcuts using specified module and validation."""
    # Dynamic import of schema-specific modules
    collection_module = __import__(
        f"timezonefinder.flatbuf.generated.{module_name}.HybridShortcutCollection",
        fromlist=["*"],
    )
    entry_module = __import__(
        f"timezonefinder.flatbuf.generated.{module_name}.HybridShortcutEntry",
        fromlist=["*"],
    )
    unique_zone_module = __import__(
        f"timezonefinder.flatbuf.generated.{module_name}.UniqueZone", fromlist=["*"]
    )
    polygon_list_module = __import__(
        f"timezonefinder.flatbuf.generated.{module_name}.PolygonList", fromlist=["*"]
    )
    shortcut_value_module = __import__(
        f"timezonefinder.flatbuf.generated.{module_name}.ShortcutValue",
        fromlist=["ShortcutValue"],
    )

    builder = flatbuffers.Builder(0)
    entry_offsets = []

    # Validate zone IDs fit in dtype
    for value in hybrid_mapping.values():
        if isinstance(value, int) and value > max_zone_id:
            raise ValueError(
                f"Zone ID {value} exceeds {dtype_name} maximum ({max_zone_id})"
            )

    for hex_id, value in hybrid_mapping.items():
        if isinstance(value, int):
            # Create UniqueZone with direct storage
            unique_zone_module.UniqueZoneStart(builder)
            unique_zone_module.UniqueZoneAddZoneId(builder, value)
            unique_zone_offset = unique_zone_module.UniqueZoneEnd(builder)

            # Create entry with UniqueZone
            entry_module.HybridShortcutEntryStart(builder)
            entry_module.HybridShortcutEntryAddHexId(builder, hex_id)
            entry_module.HybridShortcutEntryAddValueType(
                builder, shortcut_value_module.ShortcutValue.UniqueZone
            )
            entry_module.HybridShortcutEntryAddValue(builder, unique_zone_offset)
            entry_offset = entry_module.HybridShortcutEntryEnd(builder)

        else:
            # Create PolygonList
            poly_ids = list(value)
            polygon_list_module.PolygonListStartPolyIdsVector(builder, len(poly_ids))
            for i in range(len(poly_ids) - 1, -1, -1):
                builder.PrependUint16(poly_ids[i])
            poly_ids_vector = builder.EndVector()

            polygon_list_module.PolygonListStart(builder)
            polygon_list_module.PolygonListAddPolyIds(builder, poly_ids_vector)
            polygon_list_offset = polygon_list_module.PolygonListEnd(builder)

            # Create entry with PolygonList
            entry_module.HybridShortcutEntryStart(builder)
            entry_module.HybridShortcutEntryAddHexId(builder, hex_id)
            entry_module.HybridShortcutEntryAddValueType(
                builder, shortcut_value_module.ShortcutValue.PolygonList
            )
            entry_module.HybridShortcutEntryAddValue(builder, polygon_list_offset)
            entry_offset = entry_module.HybridShortcutEntryEnd(builder)

        entry_offsets.append(entry_offset)

    # Create entries vector
    collection_module.HybridShortcutCollectionStartEntriesVector(
        builder, len(entry_offsets)
    )
    for offset in reversed(entry_offsets):
        builder.PrependUOffsetTRelative(offset)
    entries_vector = builder.EndVector()

    # Create HybridShortcutCollection
    collection_module.HybridShortcutCollectionStart(builder)
    collection_module.HybridShortcutCollectionAddEntries(builder, entries_vector)
    collection = collection_module.HybridShortcutCollectionEnd(builder)

    builder.Finish(collection)

    # Write to file
    with open(output_file, "wb") as f:
        f.write(builder.Output())


def read_hybrid_shortcuts_binary(
    file_path: Path,
) -> Dict[int, Union[int, np.ndarray]]:
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
    # Determine schema type from filename
    if "uint8" in file_path.name:
        return _read_hybrid_shortcuts_with_modules(file_path, "shortcuts_uint8")
    elif "uint16" in file_path.name:
        return _read_hybrid_shortcuts_with_modules(file_path, "shortcuts_uint16")
    else:
        raise ValueError(
            f"Cannot determine schema from filename: {file_path.name}. "
            "Filename must include 'uint8' or 'uint16'."
        )


def _read_hybrid_shortcuts_with_modules(
    file_path: Path, module_name: str
) -> Dict[int, Union[int, np.ndarray]]:
    """Read hybrid shortcuts using specified module."""
    # Dynamic import of schema-specific modules
    collection_module = __import__(
        f"timezonefinder.flatbuf.generated.{module_name}.HybridShortcutCollection",
        fromlist=["HybridShortcutCollection"],
    )
    unique_zone_module = __import__(
        f"timezonefinder.flatbuf.generated.{module_name}.UniqueZone",
        fromlist=["UniqueZone"],
    )
    polygon_list_module = __import__(
        f"timezonefinder.flatbuf.generated.{module_name}.PolygonList",
        fromlist=["PolygonList"],
    )
    shortcut_value_module = __import__(
        f"timezonefinder.flatbuf.generated.{module_name}.ShortcutValue",
        fromlist=["ShortcutValue"],
    )

    with open(file_path, "rb") as f:
        buf = f.read()

    collection = collection_module.HybridShortcutCollection.GetRootAs(buf, 0)

    hybrid_mapping = {}
    for i in range(collection.EntriesLength()):
        entry = collection.Entries(i)
        hex_id = entry.HexId()

        # Determine value type and extract data
        value_type = entry.ValueType()
        value = entry.Value()

        if value_type == shortcut_value_module.ShortcutValue.UniqueZone:
            unique_zone = unique_zone_module.UniqueZone()
            unique_zone.Init(value.Bytes, value.Pos)
            zone_id = unique_zone.ZoneId()  # Direct zone ID, no lookup needed
            hybrid_mapping[hex_id] = int(zone_id)

        elif value_type == shortcut_value_module.ShortcutValue.PolygonList:
            polygon_list = polygon_list_module.PolygonList()
            polygon_list.Init(value.Bytes, value.Pos)
            poly_ids = polygon_list.PolyIdsAsNumpy()
            hybrid_mapping[hex_id] = poly_ids

        else:
            raise ValueError(f"Unknown ShortcutValue type: {value_type}")

    return hybrid_mapping
