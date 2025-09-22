"""Utilities for working with unique shortcut FlatBuffer data."""

from pathlib import Path
from typing import Any, Dict

import flatbuffers
import numpy as np

from timezonefinder.configs import DEFAULT_DATA_DIR
from timezonefinder.flatbuf.generated.unique.UniqueShortcutCollection import (
    UniqueShortcutCollection,
    UniqueShortcutCollectionAddEntries,
    UniqueShortcutCollectionAddWidth,
    UniqueShortcutCollectionAddZoneIds,
    UniqueShortcutCollectionEnd,
    UniqueShortcutCollectionStart,
    UniqueShortcutCollectionStartEntriesVector,
)
from timezonefinder.flatbuf.generated.unique.UniqueShortcutEntry import (
    UniqueShortcutEntryAddHexId,
    UniqueShortcutEntryAddZoneIndex,
    UniqueShortcutEntryEnd,
    UniqueShortcutEntryStart,
)
from timezonefinder.flatbuf.generated.unique.ZoneIdWidth import ZoneIdWidth


_ZONE_ID_WIDTH_TO_DTYPE = {
    ZoneIdWidth.UINT8: np.dtype("<u1"),
    ZoneIdWidth.UINT16: np.dtype("<u2"),
}
_DTYPE_TO_ZONE_ID_WIDTH = {
    np.dtype("<u1"): ZoneIdWidth.UINT8,
    np.dtype("<u2"): ZoneIdWidth.UINT16,
}


def get_unique_shortcut_file_path(output_path: Path = DEFAULT_DATA_DIR) -> Path:
    """Return the path to the unique shortcut FlatBuffer binary file."""

    return output_path / "unique_shortcuts.fbs"


def _normalise_zone_id_dtype(dtype: np.dtype) -> np.dtype:
    dtype = np.dtype(dtype)
    if dtype.kind != "u":
        raise ValueError(f"Zone id dtype must be unsigned integer, got {dtype}")
    if dtype.itemsize == 1:
        return np.dtype("<u1")
    if dtype.itemsize == 2:
        return np.dtype("<u2")
    if dtype.itemsize == 4:
        raise ValueError(
            "Zone id dtype wider than 16 bit is not supported; use uint8 or uint16."
        )
    return dtype.newbyteorder("<")


def _zone_width_from_dtype(dtype: np.dtype) -> int:
    normalised = _normalise_zone_id_dtype(dtype)
    try:
        return _DTYPE_TO_ZONE_ID_WIDTH[normalised]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported zone id dtype '{dtype}'. Use one of uint8 or uint16."
        ) from exc


def _dtype_from_zone_width(width: int) -> "np.dtype[Any]":
    try:
        return _ZONE_ID_WIDTH_TO_DTYPE[width]
    except KeyError as exc:
        raise ValueError(f"Unsupported ZoneIdWidth value: {width}") from exc


def write_unique_shortcuts_flatbuffers(
    unique_mapping: Dict[int, int],
    zone_id_dtype: np.dtype,
    output_file: Path,
) -> None:
    """Write the unique shortcut mapping to a FlatBuffer binary file."""

    builder = flatbuffers.Builder(0)
    width = _zone_width_from_dtype(zone_id_dtype)

    # Build the zone ids byte array in the same order as entries
    sorted_items = sorted(unique_mapping.items())
    zone_ids_bytes = bytearray(len(sorted_items) * width)

    for index, (_, zone_id) in enumerate(sorted_items):
        offset = index * width
        zone_ids_bytes[offset : offset + width] = int(zone_id).to_bytes(
            width, byteorder="little", signed=False
        )

    zone_ids_vector = builder.CreateByteVector(zone_ids_bytes)

    entry_offsets: list[int] = []
    for index, (hex_id, _) in enumerate(sorted_items):
        UniqueShortcutEntryStart(builder)
        UniqueShortcutEntryAddHexId(builder, hex_id)
        UniqueShortcutEntryAddZoneIndex(builder, index)
        entry_offsets.append(UniqueShortcutEntryEnd(builder))

    entries_vector = 0
    if entry_offsets:
        UniqueShortcutCollectionStartEntriesVector(builder, len(sorted_items))
        for offset in reversed(entry_offsets):
            builder.PrependUOffsetTRelative(offset)
        entries_vector = builder.EndVector()

    UniqueShortcutCollectionStart(builder)
    UniqueShortcutCollectionAddWidth(builder, width)
    UniqueShortcutCollectionAddZoneIds(builder, zone_ids_vector)
    if entry_offsets:
        UniqueShortcutCollectionAddEntries(builder, entries_vector)
    collection = UniqueShortcutCollectionEnd(builder)

    builder.Finish(collection)
    with open(output_file, "wb") as f:
        f.write(builder.Output())


def read_unique_shortcuts_binary(file_path: Path) -> Dict[int, int]:
    """Read the unique shortcut mapping from a FlatBuffer binary file."""

    with open(file_path, "rb") as f:
        buf = f.read()

    collection = UniqueShortcutCollection.GetRootAs(buf, 0)
    width = collection.Width()
    dtype = _dtype_from_zone_width(width)

    raw_zone_ids = collection.ZoneIdsAsNumpy()
    if isinstance(raw_zone_ids, int):  # pragma: no cover - defensive
        zone_ids = np.empty(0, dtype=dtype)
    else:
        # view the raw uint8 buffer as the appropriate dtype
        zone_ids = raw_zone_ids.view(dtype)

    result: Dict[int, int] = {}
    entries_length = collection.EntriesLength()
    if entries_length != len(zone_ids):
        raise ValueError(
            "Unique shortcut FlatBuffer is inconsistent: number of entries "
            "does not match zone id count."
        )

    for index in range(entries_length):
        entry = collection.Entries(index)
        hex_id = entry.HexId()
        zone_index = entry.ZoneIndex()
        zone_id = int(zone_ids[zone_index])
        result[hex_id] = zone_id

    return result
