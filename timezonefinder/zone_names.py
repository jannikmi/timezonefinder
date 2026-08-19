"""
Timezone names file I/O operations.

This module handles reading and writing timezone names from/to persistent storage.
Timezone names are used to map numeric zone IDs to human-readable timezone identifiers.
"""

from pathlib import Path

from timezonefinder.configs import DEFAULT_DATA_DIR

__all__ = [
    "get_zone_names_path",
    "write_zone_names",
    "read_zone_names",
]


def get_zone_names_path(output_path: Path = DEFAULT_DATA_DIR) -> Path:
    """
    Get the absolute path to the timezone names file.

    :param output_path: Directory containing the timezone names file (default: package data dir)
    :return: Path to timezone_names.txt
    """
    return output_path / "timezone_names.txt"


def write_zone_names(zone_names: list[str], output_path: Path) -> None:
    """
    Write timezone names to a persistent text file.

    The file format is one timezone name per line. This is used during data generation to
    store the list of all timezone identifiers in the dataset.

    :param zone_names: List of timezone names to write
    :param output_path: Directory where output file will be written. Required, unlike
        the read side above: ``DEFAULT_DATA_DIR`` resolves to wherever the
        ``timezonefinder-data`` distribution is installed, so defaulting to it would
        make an omitted argument rewrite the installed dataset in site-packages.
        Generators pass ``scripts.configs.SOURCE_DATA_DIR``.
    :raises OSError: If file cannot be written
    """
    path = get_zone_names_path(output_path)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(zone_names))
        f.write("\n")  # write a newline at the end of the file


def read_zone_names(path: Path) -> list[str]:
    """
    Read timezone names from the persistent text file.

    The file should contain one timezone name per line. Empty lines are skipped.

    :param path: Directory containing the timezone names file
    :return: List of timezone names, in zone id order
    :raises FileNotFoundError: If the directory holds no timezone names file
    :raises OSError: For any other read failure (``FileNotFoundError`` is a subclass of it,
        listed separately because it is the one a caller realistically handles)

    Example:
        >>> names = read_zone_names(Path("./data"))
        >>> "Europe/Berlin" in names
        True
    """
    file_path = get_zone_names_path(path)
    with open(file_path, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]
