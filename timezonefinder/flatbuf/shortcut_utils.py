"""
Utility functions for working with shortcut data in FlatBuffers.
"""

from pathlib import Path
from typing import Dict, List
import flatbuffers
import numpy as np
from timezonefinder.configs import DEFAULT_DATA_DIR
from timezonefinder.flatbuf.ShortcutEntry import (
    ShortcutEntryStart,
    ShortcutEntryEnd,
    ShortcutEntryAddHexId,
    ShortcutEntryAddPolyIds,
    ShortcutEntryStartPolyIdsVector,
)
from timezonefinder.flatbuf.ShortcutCollection import (
    ShortcutCollection,
    ShortcutCollectionStart,
    ShortcutCollectionEnd,
    ShortcutCollectionAddEntries,
    ShortcutCollectionStartEntriesVector,
)


def get_shortcut_file_path(output_path: Path = DEFAULT_DATA_DIR) -> Path:
    """Get the path to the shortcuts flatbuffer binary file."""
    return output_path / "shortcuts.fbs"


def write_shortcuts_flatbuffers(
    shortcut_mapping: Dict[int, List[int]],
    output_path: Path = DEFAULT_DATA_DIR,
) -> int:
    """
    Write H3 shortcuts to a FlatBuffer binary file.

    Args:
        shortcut_mapping: Dictionary mapping H3 hexagon IDs to lists of polygon IDs
        output_path: Directory where the output file will be written

    Returns:
        The size of the written file in bytes
    """
    print(f"writing {len(shortcut_mapping)} shortcuts to binary file {output_path}")
    builder = flatbuffers.Builder(0)
    entry_offsets = []

    for hex_id, poly_ids in shortcut_mapping.items():
        # Create poly_ids vector
        ShortcutEntryStartPolyIdsVector(builder, len(poly_ids))
        for i in range(len(poly_ids) - 1, -1, -1):
            builder.PrependUint16(poly_ids[i])
        poly_ids_vector = builder.EndVector()

        # Start building shortcut entry
        ShortcutEntryStart(builder)
        ShortcutEntryAddHexId(builder, hex_id)
        ShortcutEntryAddPolyIds(builder, poly_ids_vector)
        entry_offsets.append(ShortcutEntryEnd(builder))

    # Create vector of shortcut entries
    ShortcutCollectionStartEntriesVector(builder, len(entry_offsets))
    for offset in reversed(entry_offsets):
        builder.PrependUOffsetTRelative(offset)
    entries_vector = builder.EndVector()

    # Create ShortcutCollection
    ShortcutCollectionStart(builder)
    ShortcutCollectionAddEntries(builder, entries_vector)
    collection = ShortcutCollectionEnd(builder)

    builder.Finish(collection)
    buf = builder.Output()

    # Write to file
    # Ensure the output directory exists
    output_path.mkdir(parents=True, exist_ok=True)
    output_file = get_shortcut_file_path(output_path)
    with open(output_file, "wb") as f:
        f.write(buf)

    size_in_bytes = output_file.stat().st_size
    size_in_mb = size_in_bytes / (1024**2)
    print(f"the binary file takes up {size_in_mb:.2f} MB")
    return size_in_bytes


def read_shortcuts_binary(
    file_path: Path,
) -> Dict[int, np.ndarray]:
    """
    Read shortcut mapping from a FlatBuffer binary file.

    Args:
        file_path: Path to the shortcut FlatBuffer file.

    Returns:
        Dictionary mapping H3 hexagon IDs to numpy arrays of polygon IDs
    """
    with open(file_path, "rb") as f:
        buf = f.read()

    collection = ShortcutCollection.GetRootAsShortcutCollection(buf, 0)

    shortcut_mapping = {}
    for i in range(collection.EntriesLength()):
        entry = collection.Entries(i)
        hex_id = entry.HexId()
        poly_ids = entry.PolyIdsAsNumpy()
        shortcut_mapping[hex_id] = poly_ids

    return shortcut_mapping
