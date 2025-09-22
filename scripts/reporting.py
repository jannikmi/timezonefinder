"""
Module for generating reports about timezone data statistics.
Contains functions for reporting various metrics about timezone polygons, holes, and boundaries.
"""

import argparse
import json
from collections import Counter
from contextlib import redirect_stdout
from pathlib import Path
from typing import Callable, Dict, List, Union

import numpy as np

from scripts.configs import DATA_REPORT_FILE
from scripts.utils import percent
from timezonefinder.configs import DEFAULT_DATA_DIR
from timezonefinder.flatbuf.io.polygons import get_coordinate_path
from timezonefinder.flatbuf.io.hybrid_shortcuts import (
    get_hybrid_shortcut_file_path,
    read_hybrid_shortcuts_binary,
)
from timezonefinder.np_binary_helpers import (
    get_zone_ids_path,
    read_per_polygon_vector,
)
from timezonefinder.utils import (
    get_holes_dir,
    get_boundaries_dir,
)
from timezonefinder.zone_names import read_zone_names


# decorator to reroute the output of a function to a file
def redirect_output_to_file(file_path: str) -> Callable:
    """Decorator to redirect the output of a function to a file."""

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # NOTE: append to the file, do not overwrite it
            with open(file_path, "a") as f:
                with redirect_stdout(f):
                    return func(*args, **kwargs)

        return wrapper

    return decorator


def load_binary_data(data_path: Path = DEFAULT_DATA_DIR) -> Dict:
    """
    Load all necessary data from binary files to generate reports.

    Args:
        data_path: Path to the directory containing binary data files

    Returns:
        Dictionary containing all loaded data
    """
    print(f"Loading binary data from: {data_path}")

    # Load shortcuts
    zone_ids = read_per_polygon_vector(get_zone_ids_path(data_path))
    zone_id_dtype = zone_ids.dtype
    shortcut_file = get_hybrid_shortcut_file_path(zone_id_dtype, data_path)
    shortcuts = read_hybrid_shortcuts_binary(shortcut_file)

    # Load timezone names
    all_tz_names = read_zone_names(data_path)
    nr_of_zones = len(all_tz_names)

    # Load boundary polygon data
    boundaries_dir = get_boundaries_dir(data_path)
    boundary_coord_path = get_coordinate_path(boundaries_dir)

    # Read boundary polygons using FlatBuffer
    from timezonefinder.flatbuf.io.polygons import (
        get_polygon_collection,
        read_polygon_array_from_binary,
    )

    with open(boundary_coord_path, "rb") as f:
        coord_buf = f.read()

    polygon_collection = get_polygon_collection(coord_buf)
    nr_of_polygons = polygon_collection.PolygonsLength()

    # Calculate polygon lengths from FlatBuffer data
    polygon_lengths = []
    for idx in range(nr_of_polygons):
        polygon_coords = read_polygon_array_from_binary(polygon_collection, idx)
        polygon_lengths.append(polygon_coords.shape[1])  # Number of coordinate pairs

    # Load hole data
    holes_dir = get_holes_dir(data_path)
    hole_coord_path = get_coordinate_path(holes_dir)

    # Load hole registry to get polynrs_of_holes
    hole_registry_path = data_path / "hole_registry.json"
    polynrs_of_holes = []
    all_hole_lengths = []

    if hole_registry_path.exists() and hole_coord_path.exists():
        with open(hole_registry_path) as f:
            hole_registry = json.load(f)

        # Read hole polygons using FlatBuffers
        with open(hole_coord_path, "rb") as f:
            hole_coord_buf = f.read()

        hole_polygon_collection = get_polygon_collection(hole_coord_buf)

        # Build polynrs_of_holes list from hole registry
        hole_index = 0
        for poly_id_str, hole_info in hole_registry.items():
            poly_id = int(poly_id_str)
            num_holes = hole_info[0]

            for _ in range(num_holes):
                polynrs_of_holes.append(poly_id)
                if hole_index < hole_polygon_collection.PolygonsLength():
                    hole_coords = read_polygon_array_from_binary(
                        hole_polygon_collection, hole_index
                    )
                    all_hole_lengths.append(
                        hole_coords.shape[1]
                    )  # Number of coordinate pairs
                    hole_index += 1

    return {
        "shortcuts": shortcuts,
        "nr_of_polygons": nr_of_polygons,
        "nr_of_zones": nr_of_zones,
        "polygon_lengths": polygon_lengths,
        "all_hole_lengths": all_hole_lengths,
        "polynrs_of_holes": polynrs_of_holes,
        "poly_zone_ids": zone_ids.tolist(),
        "all_tz_names": all_tz_names,
        "output_path": data_path,
    }


def accumulated_frequency(int_list):
    out = []
    total = sum(int_list)
    acc = 0
    for e in int_list:
        acc += e
        out.append(percent(acc, total))

    return out


def rst_title(title: str, level: int = 0) -> str:
    """Return a title in restructured text format"""
    separators = ["=", "-", "~", "^", "`"]
    level = min(level, len(separators) - 1)
    sep = separators[level]
    return f"\n\n{title}\n{sep * len(title)}\n"


def print_rst_table(headers: List[str], rows: List[List[str]]):
    """
    Print a table in restructured text (.rst) format using list-table directive

    :param headers: List of column headers
    :param rows: List of rows, each row is a list of values
    """
    # Calculate appropriate column widths based on content
    col_count = len(headers)
    default_width = 100 // col_count
    widths = [default_width] * col_count

    # Start the list-table directive
    print("\n.. list-table::")
    print("   :header-rows: 1")
    print(f"   :widths: {' '.join(str(w) for w in widths)}")
    print("")

    # Print headers
    print("   * - " + "\n     - ".join(str(h) for h in headers))

    # Print rows
    for row in rows:
        # Convert all cells to strings
        str_cells = [str(cell) for cell in row]
        print("   * - " + "\n     - ".join(str_cells))

    print("")


def print_frequencies(counts: List[int], label: str):
    max_val = max(*counts)
    frequencies = [counts.count(i) for i in range(max_val + 1)]

    total_count = sum(frequencies)
    acc = accumulated_frequency(frequencies)
    acc_inverse = [round(100 - x, 2) for x in acc]

    # Combined table with all frequency information
    combined_headers = [label, "Frequency", "Relative", "Accumulated", "Remaining"]
    combined_rows = []

    for i, amount in enumerate(frequencies):
        # Skip rows with an amount of 0
        if amount > 0 and i < len(acc):
            row = [
                i,  # Amount
                amount,  # Frequency
                f"{percent(amount, total_count)}%",  # Relative %
                f"{acc[i]}%",  # Accumulated %
                f"{acc_inverse[i]}%",  # Remaining %
            ]
            combined_rows.append(row)

    print_rst_table(combined_headers, combined_rows)


def get_file_size_in_mb(file_path: Path) -> float:
    """
    Returns the size of a file in megabytes.
    Args:
        file_path: Path to the file

    Returns:
        Size of the file in megabytes
    """
    size_in_bytes = file_path.stat().st_size
    size_in_mb = size_in_bytes / (1024**2)
    return size_in_mb


def calculate_shortcut_index_stats(
    mapping: Dict[int, Union[int, np.ndarray]], poly_zone_ids: List[int]
) -> Dict[str, Union[int, float]]:
    """
    Calculate comprehensive statistics about the hybrid shortcut index.

    Args:
        mapping: Hybrid shortcut mapping (hex_id -> zone_id | polygon_ids)
        poly_zone_ids: Zone IDs for each polygon

    Returns:
        Dictionary of statistical metrics
    """
    from scripts.configs import SHORTCUT_H3_RES

    # Basic counts
    total_entries = len(mapping)
    zone_entries = 0
    polygon_entries = 0
    polygon_id_count = 0
    empty_entries = 0

    # Data for frequency analysis
    nr_of_entries_in_shortcut = []
    amount_of_different_zones = []

    # Calculate per-entry statistics
    for v in mapping.values():
        if isinstance(v, int):
            # Direct zone ID - single zone, no polygons to enumerate
            zone_entries += 1
            nr_of_entries_in_shortcut.append(0)  # No polygons, direct zone
            amount_of_different_zones.append(1)  # Single zone
        else:
            # Polygon list - count polygons and distinct zones
            polygon_ids = v
            polygon_count = len(polygon_ids)

            if polygon_count == 0:
                empty_entries += 1
                nr_of_entries_in_shortcut.append(0)
                amount_of_different_zones.append(0)
            else:
                polygon_entries += 1
                polygon_id_count += polygon_count
                nr_of_entries_in_shortcut.append(polygon_count)

                # Count distinct zones for these polygons
                zone_ids = [poly_zone_ids[i] for i in polygon_ids]
                distinct_zones = set(zone_ids)
                amount_of_different_zones.append(len(distinct_zones))

    # Calculate H3 coverage statistics
    try:
        import h3.api.numpy_int as h3

        # Calculate theoretical maximum cells at this resolution
        if SHORTCUT_H3_RES == 0:
            possible_cells = len(h3.get_res0_cells())
        else:
            # For higher resolutions, calculate based on H3 formula
            # Each parent cell has 7 children (except res 0->1 which is different)
            # Approximately 2 + 240 * 7^(res-1) cells for res >= 1
            if SHORTCUT_H3_RES == 1:
                possible_cells = 842  # Known value for resolution 1
            elif SHORTCUT_H3_RES == 2:
                possible_cells = 5882  # Known value for resolution 2
            elif SHORTCUT_H3_RES == 3:
                possible_cells = 41162  # Known value for resolution 3 (current default)
            elif SHORTCUT_H3_RES == 4:
                possible_cells = 288122  # Known value for resolution 4
            else:
                # For other resolutions, use the stored cells as a conservative estimate
                possible_cells = total_entries

    except ImportError:
        # If h3 is not available, use stored cells as estimate
        possible_cells = total_entries

    stored_cells = total_entries
    missing_cells = max(possible_cells - stored_cells, 0)

    # Calculate derived metrics
    unique_entry_fraction = zone_entries / total_entries if total_entries else 0.0
    unique_surface_fraction = zone_entries / possible_cells if possible_cells else 0.0
    coverage_ratio = stored_cells / possible_cells if possible_cells else 0.0

    # Calculate average polygons per non-unique entry
    avg_polygons_per_entry = (
        polygon_id_count / polygon_entries if polygon_entries else 0.0
    )

    # Calculate zone distribution efficiency
    zone_distribution_efficiency = (
        sum(1 for zones in amount_of_different_zones if zones <= 1) / total_entries
        if total_entries
        else 0.0
    )

    # Calculate storage efficiency metrics
    # Estimate bytes per entry (key + value)
    ENTRY_KEY_SIZE_BYTES = 8  # int64 hex ID
    zone_storage_bytes = zone_entries * (
        ENTRY_KEY_SIZE_BYTES + 1
    )  # 1 byte for uint8 zone ID
    polygon_storage_bytes = (
        polygon_entries * ENTRY_KEY_SIZE_BYTES + polygon_id_count * 2
    )  # 2 bytes per uint16 polygon ID
    total_storage_bytes = zone_storage_bytes + polygon_storage_bytes

    # Calculate compression ratio vs naive storage
    naive_storage_bytes = total_entries * (
        ENTRY_KEY_SIZE_BYTES + polygon_id_count * 2 / total_entries
        if total_entries
        else 0
    )
    compression_ratio = (
        naive_storage_bytes / total_storage_bytes if total_storage_bytes else 1.0
    )

    return {
        # Basic counts
        "total_entries": total_entries,
        "zone_entries": zone_entries,
        "polygon_entries": polygon_entries,
        "empty_entries": empty_entries,
        "polygon_id_count": polygon_id_count,
        # H3 coverage
        "h3_resolution": SHORTCUT_H3_RES,
        "stored_cells": stored_cells,
        "possible_cells": possible_cells,
        "missing_cells": missing_cells,
        "coverage_ratio": coverage_ratio,
        # Efficiency metrics
        "unique_entry_fraction": unique_entry_fraction,
        "unique_surface_fraction": unique_surface_fraction,
        "zone_distribution_efficiency": zone_distribution_efficiency,
        "avg_polygons_per_entry": avg_polygons_per_entry,
        # Storage efficiency
        "zone_storage_bytes": zone_storage_bytes,
        "polygon_storage_bytes": polygon_storage_bytes,
        "total_storage_bytes": total_storage_bytes,
        "compression_ratio": compression_ratio,
        # Data for frequency analysis
        "polygons_per_shortcut": nr_of_entries_in_shortcut,
        "zones_per_shortcut": amount_of_different_zones,
    }


@redirect_output_to_file(DATA_REPORT_FILE)
def print_shortcut_statistics(
    mapping: Dict[int, Union[int, np.ndarray]], poly_zone_ids: List[int]
):
    print(rst_title("Shortcut Mapping Statistics", level=1))

    # Calculate comprehensive statistics
    stats = calculate_shortcut_index_stats(mapping, poly_zone_ids)

    # Print detailed statistics table
    print(rst_title("Shortcut Index Overview", level=2))

    shortcut_headers = ["Shortcut Index Metric", "Value"]
    shortcut_rows = [
        ["H3 Resolution", f"{stats['h3_resolution']}"],
        ["Total shortcut entries", f"{stats['total_entries']:,}"],
        ["Zone entries (direct lookup)", f"{stats['zone_entries']:,}"],
        ["Polygon entries (require testing)", f"{stats['polygon_entries']:,}"],
        ["Empty entries", f"{stats['empty_entries']:,}"],
        ["Total polygon references", f"{stats['polygon_id_count']:,}"],
        ["", ""],  # Separator
        ["H3 cells stored", f"{stats['stored_cells']:,}"],
        ["H3 cells possible at resolution", f"{stats['possible_cells']:,}"],
        ["H3 cells missing", f"{stats['missing_cells']:,}"],
        ["H3 coverage ratio", f"{stats['coverage_ratio']:.3f}"],
        ["", ""],  # Separator
        ["Unique entry fraction", f"{stats['unique_entry_fraction']:.3f}"],
        ["Unique surface fraction", f"{stats['unique_surface_fraction']:.3f}"],
        [
            "Zone distribution efficiency",
            f"{stats['zone_distribution_efficiency']:.3f}",
        ],
        ["Avg polygons per polygon entry", f"{stats['avg_polygons_per_entry']:.2f}"],
        ["", ""],  # Separator
        ["Zone storage (KB)", f"{stats['zone_storage_bytes'] / 1024:.1f}"],
        ["Polygon storage (KB)", f"{stats['polygon_storage_bytes'] / 1024:.1f}"],
        ["Total estimated storage (KB)", f"{stats['total_storage_bytes'] / 1024:.1f}"],
        ["Storage compression ratio", f"{stats['compression_ratio']:.2f}x"],
    ]

    print_rst_table(shortcut_headers, shortcut_rows)

    # Print frequency distributions
    print(rst_title("Shortcut Entry Distributions", level=2))

    print_frequencies(stats["polygons_per_shortcut"], "polygons/shortcut")
    print_frequencies(stats["zones_per_shortcut"], "timezones/shortcut")


def generate_metrics_rows(metric_type: str, metrics_dict: Dict) -> List[List]:
    """
    Generate additional metric rows for tables based on a dictionary of metrics.

    Args:
        metric_type: Type of metrics (e.g., "boundary", "hole")
        metrics_dict: Dictionary of metric names and values

    Returns:
        List of rows for a table
    """
    rows = []
    for label, value in metrics_dict.items():
        # Format numbers with commas and add % to percentages
        if isinstance(value, (int, float)):
            if "percentage" in label.lower() or "%" in label:
                formatted_value = f"{value}%"
            else:
                formatted_value = f"{value:,}" if value == int(value) else f"{value}"
        else:
            formatted_value = str(value)

        rows.append([label, formatted_value])
    return rows


def generate_polygon_statistics_table(
    polygon_type: str, count: int, length_list: List[int], additional_rows: List = None
) -> None:
    """
    Generate and print a table with statistics for a polygon collection.

    Args:
        polygon_type: Type of polygon ("Boundary" or "Hole")
        count: Number of polygons
        length_list: List of coordinate lengths for each polygon
        additional_rows: Optional additional rows to add to the table
    """
    # Safe handling for empty or missing data
    length_list = length_list or []
    polygon_type_lower = polygon_type.lower()

    if count == 0 or not length_list:
        print(f"No {polygon_type_lower} polygons found.")
        # Still print a table with zeros for consistency
        headers = [f"{polygon_type} Metric", "Value"]
        rows = [
            [f"Total {polygon_type_lower} polygons", "0"],
            [f"Total {polygon_type_lower} coordinates", "0"],
            [f"Total {polygon_type_lower} coordinate values (2 per point)", "0"],
        ]
        if additional_rows:
            rows.extend(additional_rows)
        print_rst_table(headers, rows)
        return

    # Calculate statistics
    total_coord_pairs = sum(length_list)
    total_coords = 2 * total_coord_pairs
    avg_length = round(sum(length_list) / len(length_list), 2)
    max_length = max(length_list)
    min_length = min(length_list)

    # Create table
    headers = [f"{polygon_type} Metric", "Value"]
    rows = [
        [f"Total {polygon_type_lower} polygons", f"{count:,}"],
        [f"Total {polygon_type_lower} coordinates", f"{total_coord_pairs:,}"],
        [
            f"Total {polygon_type_lower} coordinate values (2 per point)",
            f"{total_coords:,}",
        ],
        [f"Average coordinates per {polygon_type_lower} polygon", f"{avg_length:,}"],
        [f"Maximum coordinates in one {polygon_type_lower} polygon", f"{max_length:,}"],
        [f"Minimum coordinates in one {polygon_type_lower} polygon", f"{min_length:,}"],
    ]

    # Add any additional rows
    if additional_rows:
        rows.extend(additional_rows)

    print_rst_table(headers, rows)


def calculate_general_statistics(
    polygon_lengths: List[int], all_hole_lengths: List[int]
) -> Dict:
    """
    Calculate general statistics about the dataset.

    Args:
        polygon_lengths: List of coordinate lengths for each boundary polygon
        all_hole_lengths: List of coordinate lengths for each hole

    Returns:
        Dictionary of general metrics
    """
    total_floats_boundaries = 2 * sum(polygon_lengths) if polygon_lengths else 0
    total_floats_holes = 2 * sum(all_hole_lengths) if all_hole_lengths else 0
    total_floats = total_floats_boundaries + total_floats_holes

    return {"Total coordinate values (2 per point)": total_floats}


def calculate_hole_metrics(
    nr_of_polygons: int, all_hole_lengths: List[int], polynrs_of_holes: List[int]
) -> Dict:
    """
    Calculate statistics about holes in the dataset.

    Args:
        nr_of_polygons: Number of boundary polygons
        all_hole_lengths: List of coordinate lengths for each hole
        polynrs_of_holes: List mapping holes to their parent polygons

    Returns:
        Dictionary of hole metrics
    """
    nr_of_holes = len(all_hole_lengths) if all_hole_lengths else 0
    polygons_with_holes = len(set(polynrs_of_holes)) if polynrs_of_holes else 0

    return {
        "Number of boundary polygons with holes": polygons_with_holes,
        "Percentage of boundary polygons with holes": round(
            (polygons_with_holes / nr_of_polygons) * 100, 2
        )
        if nr_of_polygons > 0 and polygons_with_holes > 0
        else 0,
        "Average holes per boundary polygon (with holes)": round(
            nr_of_holes / polygons_with_holes, 2
        )
        if polygons_with_holes > 0
        else 0,
    }


def calculate_timezone_metrics(
    nr_of_zones: int,
    nr_of_polygons: int,
    polygons_per_timezone: Counter,
) -> Dict:
    """
    Calculate statistics about timezones in the dataset.

    Args:
        nr_of_zones: Number of timezone zones
        nr_of_polygons: Number of boundary polygons
        polygons_per_timezone: Counter mapping zone IDs to polygon counts
        all_tz_names: List of timezone names

    Returns:
        Dictionary of timezone metrics
    """
    return {
        "Total timezones": nr_of_zones,
        "Average boundary polygons per timezone": round(nr_of_polygons / nr_of_zones, 2)
        if nr_of_zones > 0
        else 0,
        "Maximum polygons in one timezone": max(polygons_per_timezone.values())
        if polygons_per_timezone
        else 0,
        "Minimum polygons in one timezone": min(polygons_per_timezone.values())
        if polygons_per_timezone
        else 0,
        "Median polygons per timezone": sorted(list(polygons_per_timezone.values()))[
            len(polygons_per_timezone) // 2
        ]
        if polygons_per_timezone
        else 0,
    }


def print_polygon_distribution_table(
    polygons_per_timezone: Counter,
    all_tz_names: List[str],
) -> List[List[str]]:
    """
    Create a table showing the distribution of polygon counts across timezones.

    Args:
        polygons_per_timezone: Counter mapping zone IDs to polygon counts
        all_tz_names: List of timezone names

    Returns:
        List of rows for the distribution table
    """
    print(rst_title("Polygons per Timezone Distribution", level=3))

    # Create distribution of polygon counts
    distribution = Counter(polygons_per_timezone.values())
    distribution_items = sorted(distribution.items())

    # Group timezone IDs by polygon count for examples
    polygon_count_to_timezone = {}
    for zone_id, poly_count in polygons_per_timezone.items():
        if poly_count not in polygon_count_to_timezone:
            polygon_count_to_timezone[poly_count] = zone_id

    # Convert to more readable format
    distribution_items = [
        (f"{k} polygon" + ("s" if k > 1 else ""), v) for k, v in distribution_items
    ]

    # Create rows for distribution table
    distribution_rows = []
    total_zones = sum(distribution.values())

    for category, count in distribution_items:
        polygon_count = int(category.split()[0])  # Extract number from category
        example = ""
        if polygon_count in polygon_count_to_timezone:
            example_zone_id = polygon_count_to_timezone[polygon_count]
            if 0 <= example_zone_id < len(all_tz_names):
                example = all_tz_names[example_zone_id]

        percentage = round((count / total_zones) * 100, 2) if total_zones > 0 else 0
        distribution_rows.append([category, str(count), f"{percentage}%", example])

    cols = [
        "Number of Polygons",
        "Number of Timezones",
        "Percentage",
        "Example Timezone",
    ]
    print_rst_table(cols, distribution_rows)


@redirect_output_to_file(DATA_REPORT_FILE)
def report_data_statistics(
    nr_of_polygons: int,
    nr_of_zones: int,
    polygon_lengths: List[int],
    all_hole_lengths: List[int],
    polynrs_of_holes: List[int],
    poly_zone_ids: List[int],
    all_tz_names: List[str],
) -> None:
    """
    Prints a report of the statistics of the timezone data.

    Args:
        nr_of_polygons: Number of boundary polygons
        nr_of_zones: Number of timezone zones
        polygon_lengths: List of coordinate lengths for each boundary polygon
        all_hole_lengths: List of coordinate lengths for each hole
        polynrs_of_holes: List mapping holes to their parent polygons
        poly_zone_ids: List mapping polygons to zone IDs
        all_tz_names: List of timezone names
    """
    print(".. _data_report:\n")
    print(rst_title("Data Report", level=0))
    print(rst_title("Data Statistics", level=1))

    # General statistics section
    general_metrics = calculate_general_statistics(polygon_lengths, all_hole_lengths)
    print_rst_table(
        ["General Metric", "Value"], generate_metrics_rows("general", general_metrics)
    )

    # Boundary polygon statistics section
    print(rst_title("Boundary Polygon Statistics", level=2))
    boundary_metrics = {}  # Could add more boundary-specific metrics here if needed
    boundary_rows = generate_metrics_rows("boundary", boundary_metrics)
    generate_polygon_statistics_table(
        "Boundary", nr_of_polygons, polygon_lengths, boundary_rows
    )

    # Hole polygon statistics section
    print(rst_title("Hole Polygon Statistics", level=2))
    hole_metrics = calculate_hole_metrics(
        nr_of_polygons, all_hole_lengths, polynrs_of_holes
    )
    hole_rows = generate_metrics_rows("hole", hole_metrics)
    nr_of_holes = len(all_hole_lengths) if all_hole_lengths else 0
    generate_polygon_statistics_table("Hole", nr_of_holes, all_hole_lengths, hole_rows)

    # Timezone statistics section
    print(rst_title("Timezone Statistics", level=2))
    polygons_per_timezone = Counter(poly_zone_ids)
    timezone_metrics = calculate_timezone_metrics(
        nr_of_zones, nr_of_polygons, polygons_per_timezone
    )
    timezone_rows = generate_metrics_rows("timezone", timezone_metrics)
    print_rst_table(["Timezone Metric", "Value"], timezone_rows)

    # Polygon distribution section
    print_polygon_distribution_table(polygons_per_timezone, all_tz_names)


@redirect_output_to_file(DATA_REPORT_FILE)
def report_file_sizes(output_path: Path, zone_id_dtype=None) -> None:
    """
    Reports the sizes of the biggest generated binary files.

    NOTE: smaller .npy files are not reported here, since their size is negligible

    Args:
        output_path: Path to the output directory containing the binary files
        zone_id_dtype: Data type for zone IDs (needed for hybrid shortcut file path)
    """
    print(rst_title("Binary File Sizes", level=1))
    holes_dir = get_holes_dir(output_path)
    boundaries_dir = get_boundaries_dir(output_path)

    boundary_polygon_file = get_coordinate_path(boundaries_dir)
    hole_polygon_file = get_coordinate_path(holes_dir)

    # Get hybrid shortcut file path - if zone_id_dtype not provided, try to infer it
    if zone_id_dtype is None:
        from timezonefinder.np_binary_helpers import (
            get_zone_ids_path,
            read_per_polygon_vector,
        )

        zone_ids_path = get_zone_ids_path(output_path)
        zone_ids_temp = read_per_polygon_vector(zone_ids_path)
        zone_id_dtype = zone_ids_temp.dtype

    names_and_paths = {
        "boundary polygon data": boundary_polygon_file,
        "hole polygon data": hole_polygon_file,
        "hybrid shortcut index": get_hybrid_shortcut_file_path(
            zone_id_dtype, output_path
        ),
    }
    names_and_sizes = {
        name: get_file_size_in_mb(path) for name, path in names_and_paths.items()
    }
    total_space = sum(names_and_sizes.values())

    # Create table for file sizes
    headers = ["File Type", "Size (MB)", "Percentage"]
    rows = [
        [name, f"{size:.2f}", f"{size / total_space:.2%}"]
        for name, size in names_and_sizes.items()
    ]

    # Add total row
    rows.append(["Total", f"{total_space:.2f}", "100.00%"])

    # Print the table
    print_rst_table(headers, rows)


def write_data_report_from_binary(data_path: Path = DEFAULT_DATA_DIR) -> None:
    """
    Writes a complete data report to the report file by loading data from binary files.

    Args:
        data_path: Path to binary data files directory
    """
    data = load_binary_data(data_path)

    if DATA_REPORT_FILE.exists():
        print(f"Removing old data report file: {DATA_REPORT_FILE}")
        DATA_REPORT_FILE.unlink()

    print("Writing data report to:", DATA_REPORT_FILE)
    report_data_statistics(
        data["nr_of_polygons"],
        data["nr_of_zones"],
        data["polygon_lengths"],
        data["all_hole_lengths"],
        data["polynrs_of_holes"],
        data["poly_zone_ids"],
        data["all_tz_names"],
    )
    print_shortcut_statistics(data["shortcuts"], data["poly_zone_ids"])
    # Derive zone_id_dtype from the zone IDs data
    zone_ids_array = np.array(data["poly_zone_ids"])
    # Convert int64 to appropriate dtype based on range
    if zone_ids_array.max() < 256:
        zone_id_dtype = np.dtype(np.uint8)
    elif zone_ids_array.max() < 65536:
        zone_id_dtype = np.dtype(np.uint16)
    else:
        raise ValueError(f"Zone ID range too large: {zone_ids_array.max()}")

    report_file_sizes(data["output_path"], zone_id_dtype)


def main() -> None:
    """
    Main function for standalone execution.
    Generate data report from binary files.
    """
    parser = argparse.ArgumentParser(
        description="Generate timezone data report from binary files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate report using default data directory
  python -m scripts.reporting

  # Generate report using custom data directory
  python -m scripts.reporting --data-path /path/to/data

  # Generate report using current package data
  python -m scripts.reporting --data-path timezonefinder/data
        """.strip(),
    )

    parser.add_argument(
        "--data-path",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"Path to directory containing binary data files (default: {DEFAULT_DATA_DIR})",
    )

    args = parser.parse_args()

    # Validate data path exists
    if not args.data_path.exists():
        print(f"Error: Data path does not exist: {args.data_path}")
        return 1

    if not args.data_path.is_dir():
        print(f"Error: Data path is not a directory: {args.data_path}")
        return 1

    try:
        print(f"Generating data report from: {args.data_path}")
        write_data_report_from_binary(args.data_path)
        print(f"Data report successfully generated at: {DATA_REPORT_FILE}")
        return 0
    except Exception as e:
        print(f"Error generating data report: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
