"""
Module for generating reports about timezone data statistics.
Contains functions for reporting various metrics about timezone polygons, holes, and boundaries.
"""

from collections import Counter
from contextlib import redirect_stdout
from pathlib import Path
from typing import Callable, Dict, List


from scripts.configs import DATA_REPORT_FILE
from scripts.utils import percent
from timezonefinder.flatbuf.io.polygons import get_coordinate_path
from timezonefinder.flatbuf.io.shortcuts import get_shortcut_file_path
from timezonefinder.utils import (
    get_holes_dir,
    get_boundaries_dir,
)


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


@redirect_output_to_file(DATA_REPORT_FILE)
def print_shortcut_statistics(mapping: Dict[int, List[int]], poly_zone_ids: List[int]):
    print(rst_title("Shortcut Mapping Statistics", level=1))

    nr_of_entries_in_shortcut = [len(v) for v in mapping.values()]

    print_frequencies(nr_of_entries_in_shortcut, "polygons/shortcut")

    amount_of_different_zones = []
    for polygon_ids in mapping.values():
        # TODO count and evaluate the appearance of the different zones
        zone_ids = [poly_zone_ids[i] for i in polygon_ids]
        distinct_zones = set(zone_ids)
        amount_of_distinct_zones = len(distinct_zones)
        amount_of_different_zones.append(amount_of_distinct_zones)

    print_frequencies(amount_of_different_zones, "timezones/shortcut")


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
def report_file_sizes(output_path: Path) -> None:
    """
    Reports the sizes of the biggest generated binary files.

    NOTE: smaller .npy files are not reported here, since their size is negligible

    Args:
        output_path: Path to the output directory containing the binary files
    """
    print(rst_title("Binary File Sizes", level=1))
    holes_dir = get_holes_dir(output_path)
    boundaries_dir = get_boundaries_dir(output_path)

    boundary_polygon_file = get_coordinate_path(boundaries_dir)
    hole_polygon_file = get_coordinate_path(holes_dir)

    names_and_paths = {
        "boundary polygon data": boundary_polygon_file,
        "hole polygon data": hole_polygon_file,
        "shortcuts": get_shortcut_file_path(output_path),
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


def write_data_report(
    shortcuts: Dict[int, List[int]],
    output_path: Path,
    nr_of_polygons: int,
    nr_of_zones: int,
    polygon_lengths: List[int],
    all_hole_lengths: List[int],
    polynrs_of_holes: List[int],
    poly_zone_ids: List[int],
    all_tz_names: List[str],
) -> None:
    """
    Writes a complete data report to the report file.

    Args:
        shortcuts: Mapping of hexagon IDs to polygon IDs
        output_path: Path to the output directory
        nr_of_polygons: Number of boundary polygons
        nr_of_zones: Number of timezone zones
        polygon_lengths: List of coordinate lengths for each boundary polygon
        all_hole_lengths: List of coordinate lengths for each hole
        polynrs_of_holes: List mapping holes to their parent polygons
        poly_zone_ids: List mapping polygons to zone IDs
        all_tz_names: List of timezone names
    """
    if DATA_REPORT_FILE.exists():
        print(f"Removing old data report file: {DATA_REPORT_FILE}")
        DATA_REPORT_FILE.unlink()

    print("Writing data report to:", DATA_REPORT_FILE)
    report_data_statistics(
        nr_of_polygons,
        nr_of_zones,
        polygon_lengths,
        all_hole_lengths,
        polynrs_of_holes,
        poly_zone_ids,
        all_tz_names,
    )
    print_shortcut_statistics(shortcuts, poly_zone_ids)
    report_file_sizes(output_path)
