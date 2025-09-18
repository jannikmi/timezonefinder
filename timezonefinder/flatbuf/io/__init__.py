"""Utilities for reading and writing FlatBuffer assets."""

from .polygons import (
    flatten_polygon_coords,
    reshape_to_polygon_coords,
    get_coordinate_path,
    write_polygon_collection_flatbuffer,
    get_polygon_collection,
    read_polygon_array_from_binary,
)
from .shortcuts import (
    get_shortcut_file_path,
    write_shortcuts_flatbuffers,
    read_shortcuts_binary,
)
from .unique_shortcuts import (
    get_unique_shortcut_file_path,
    write_unique_shortcuts_flatbuffers,
    read_unique_shortcuts_binary,
)

__all__ = [
    "flatten_polygon_coords",
    "reshape_to_polygon_coords",
    "get_coordinate_path",
    "write_polygon_collection_flatbuffer",
    "get_polygon_collection",
    "read_polygon_array_from_binary",
    "get_shortcut_file_path",
    "write_shortcuts_flatbuffers",
    "read_shortcuts_binary",
    "get_unique_shortcut_file_path",
    "write_unique_shortcuts_flatbuffers",
    "read_unique_shortcuts_binary",
]
