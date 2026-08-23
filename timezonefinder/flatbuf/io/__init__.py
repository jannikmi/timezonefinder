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

__all__ = [
    "flatten_polygon_coords",
    "reshape_to_polygon_coords",
    "get_coordinate_path",
    "write_polygon_collection_flatbuffer",
    "get_polygon_collection",
    "read_polygon_array_from_binary",
    "derive_coord_offset_table",
    "read_polygon_array_at",
]
