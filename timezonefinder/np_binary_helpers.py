"""
Utility functions for handling .npy numpy binary files related to timezone data.
"""

from pathlib import Path

import numpy as np


def get_zone_ids_path(path: Path) -> Path:
    """Return the path to the zone_ids.npy file in the given directory."""
    return path / "zone_ids.npy"


def get_zone_positions_path(path: Path) -> Path:
    """Return the path to the zone_positions.npy file in the given directory."""
    return path / "zone_positions.npy"


def get_xmax_path(path: Path) -> Path:
    """Return the path to the xmax.npy file in the given directory."""
    return path / "xmax.npy"


def get_xmin_path(path: Path) -> Path:
    """Return the path to the xmin.npy file in the given directory."""
    return path / "xmin.npy"


def get_ymax_path(path: Path) -> Path:
    """Return the path to the ymax.npy file in the given directory."""
    return path / "ymax.npy"


def get_ymin_path(path: Path) -> Path:
    """Return the path to the ymin.npy file in the given directory."""
    return path / "ymin.npy"


def get_poly_ref_path(path: Path) -> Path:
    """Return the path to the poly_ref.npy file in the given directory."""
    return path / "poly_ref.npy"


def get_block_ranges_path(path: Path) -> Path:
    """Return the path to the block_ranges.npy file in the given directory."""
    return path / "block_ranges.npy"


def get_block_offsets_path(path: Path) -> Path:
    """Return the path to the block_offsets.npy file in the given directory."""
    return path / "block_offsets.npy"


def get_block_bases_path(path: Path) -> Path:
    """Return the path to the block_bases.npy file in the given directory."""
    return path / "block_bases.npy"


def get_block_widths_path(path: Path) -> Path:
    """Return the path to the block_widths.npy file in the given directory."""
    return path / "block_widths.npy"


def get_nr_vertices_path(path: Path) -> Path:
    """Return the path to the nr_vertices.npy file in the given directory."""
    return path / "nr_vertices.npy"


def store_per_polygon_vector(file_path: Path, vector: np.ndarray) -> None:
    """Store a vector as a .npy file in the specified file path."""
    print(f"Storing vector to {file_path}")
    np.save(file_path, vector)


def read_per_polygon_vector(file_path: Path) -> np.ndarray:
    """Read an immutable runtime vector from a ``.npy`` file.

    These vectors describe the loaded dataset rather than caller-owned working state.
    Every runtime consumer only reads them, and several are publicly reachable through
    a finder, so making that contract explicit prevents an accidental assignment from
    silently changing later lookup answers.
    """
    vector = np.load(file_path)
    vector.flags.writeable = False
    return vector
