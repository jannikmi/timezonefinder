"""Utilities for reading and writing FlatBuffer assets."""

from .polygons import (
    flatten_polygon_coords,
    reshape_to_polygon_coords,
    get_coordinate_path,
    write_polygon_collection_flatbuffer,
    get_polygon_collection,
    read_polygon_array_from_binary,
    derive_coord_offset_table,
    read_polygon_array_at,
)
from .hybrid_shortcuts import (
    get_hybrid_shortcut_file_path,
    write_hybrid_shortcuts_flatbuffers,
    read_hybrid_shortcuts_binary,
)

__all__ = [
    "flatten_polygon_coords",
    "reshape_to_polygon_coords",
    "get_coordinate_path",
    "write_polygon_collection_flatbuffer",
    "get_polygon_collection",
    "read_polygon_array_from_binary",
    "derive_coord_offset_table",
    "read_polygon_array_at",
    "get_hybrid_shortcut_file_path",
    "write_hybrid_shortcuts_flatbuffers",
    "read_hybrid_shortcuts_binary",
]
