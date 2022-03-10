from pathlib import Path
from typing import Dict, List, Optional

import h3.api.numpy_int as h3

from scripts.configs import MAX_RES
from scripts.utils import load_json, load_pickle
from timezonefinder.global_settings import TIMEZONE_NAMES_FILE

PARENT_FOLDER = Path(__file__).parent
PATH2DATA = PARENT_FOLDER / "10_full_separate_last"

FILES = {res: PATH2DATA / f"mapping_res{res}.pickle" for res in range(MAX_RES + 1)}

mappings: Dict[int, Dict] = {res: load_pickle(path) for res, path in FILES.items()}
mapping_remaining: Dict[int, List] = load_pickle(
    PATH2DATA / f"mapping_remaining_res{MAX_RES}.pickle"
)

timezone_names = load_json(PARENT_FOLDER / TIMEZONE_NAMES_FILE)


def get_zone_id(lng: float, lat: float, up_to: int = MAX_RES) -> int:
    for res in range(up_to + 1):
        mapping = mappings[res]
        hex_id = h3.geo_to_h3(lat, lng, res)
        try:
            return mapping[hex_id]
        except KeyError:
            pass

    hex_id = h3.geo_to_h3(lat, lng, up_to)
    return mapping_remaining.get(hex_id, [None])[0]


def get_zone(lng: float, lat: float, up_to: int = MAX_RES) -> Optional[str]:
    zone_id = get_zone_id(lng, lat, up_to)
    if zone_id is None:
        return None
    return timezone_names[zone_id]


def get_hex_cells_of_zone(zone_id: int, up_to: int = MAX_RES) -> List[int]:
    ids: List[int] = []
    for res in range(up_to + 1):
        mapping = mappings[res]
        ids.extend(iter(hex_id for hex_id, zone in mapping.items() if zone == zone_id))

    # NOTE: do not include cells from the remaining mapping
    return ids


def get_polygons_of_zone(zone_id: int, up_to: int = MAX_RES, **kwargs) -> List:
    cells = get_hex_cells_of_zone(zone_id, up_to)
    polygons = h3.h3_set_to_multi_polygon(cells, **kwargs)
    return polygons


print(get_zone_id(40.5, 26.6))
print(get_zone(40.5, 26.6))
cells = get_hex_cells_of_zone(12, up_to=3)
print(cells)
print(get_polygons_of_zone(12, 3))
