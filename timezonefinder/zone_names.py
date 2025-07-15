import json
from pathlib import Path
from typing import Set
from timezonefinder.configs import DEFAULT_DATA_DIR, TIMEZONE_NAMES_FILE


def get_timezone_names_path(output_path: Path = DEFAULT_DATA_DIR) -> Path:
    """Get the path to the timezone names JSON file."""
    return output_path / TIMEZONE_NAMES_FILE


def write_json(obj, path: Path):
    print("writing json to ", path)
    with open(path, "w") as json_file:
        json.dump(obj, json_file, indent=2)
        # write a newline at the end of the file
        json_file.write("\n")


def write_zone_names(
    all_tz_names: Set[str], output_path: Path = DEFAULT_DATA_DIR
) -> None:
    file_path = get_timezone_names_path(output_path)
    print(f"updating the zone names in {file_path} now.")
    write_json(list(all_tz_names), file_path)
