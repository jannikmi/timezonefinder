import struct
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from h3.api import numpy_int as h3

from timezonefinder.configs import (
    DTYPE_FORMAT_I,
    DTYPE_FORMAT_Q,
    DTYPE_FORMAT_SIGNED_I,
    MAX_H3_RES,
    MIN_H3_RES,
    NR_BYTES_I,
    NR_BYTES_Q,
)


def export_shortcuts_binary(global_mapping: Dict[int, List[int]], path2shortcuts: Path):
    with open(path2shortcuts, "wb") as fp:
        for hex_id, poly_id in global_mapping.items():
            fp.write(struct.pack(DTYPE_FORMAT_Q, hex_id))
            if poly_id is None:
                poly_id = -1
            fp.write(struct.pack(DTYPE_FORMAT_SIGNED_I, poly_id))
            # TODO
            # for poly_id in poly_ids:
            #     fp.write(struct.pack(DTYPE_FORMAT_Q, hex_id))
            #     fp.write(struct.pack(DTYPE_FORMAT_I, poly_id))


def read_shortcuts_binary(path2shortcuts: Path) -> Dict[int, List[int]]:
    mapping: Dict[int, Optional[int]] = {}
    with open(path2shortcuts, "rb") as fp:
        while 1:
            try:
                hex_id: int = struct.unpack(DTYPE_FORMAT_Q, fp.read(NR_BYTES_Q))[0]
                poly_id: Optional[int] = struct.unpack(
                    DTYPE_FORMAT_SIGNED_I, fp.read(NR_BYTES_I)
                )[0]
            except struct.error:
                # EOF: buffer not long enough to unpack
                break

            if poly_id < 0:
                poly_id = None
            mapping[hex_id] = poly_id
            # poly_ids = mapping.setdefault(hex_id, [])
            # poly_ids.append(poly_id)

    return mapping


def get_shortcut_polys(
    mapping: Dict[int, List[int]], lng: float, lat: float
) -> List[int]:
    for res in range(MIN_H3_RES, MAX_H3_RES + 1):
        hex_id = h3.geo_to_h3(lat, lng, res)
        try:
            polys = mapping[hex_id]
        except KeyError:
            # check higher resolution mapping
            continue

        return polys

    raise ValueError(f"missing mapping for lng, lat {lng}, {lat}")


def get_zone_id(lng: float, lat: float, up_to: int = MAX_H3_RES) -> Optional[int]:
    for res in range(up_to + 1):
        hex_id = h3.geo_to_h3(lat, lng, res)
        try:
            zones, polys = mapping[hex_id]
        except KeyError:
            # check higher resolution mapping
            continue

        if len(zones) == 0:
            return None

        if len(zones) > 1:
            # TODO multiple zones
            print("found multiple:", zones)
        return zones[0]

    raise ValueError(f"missing mapping for lng, lat {lng}, {lat}")


def get_hex_cells_of_zone(zone_id: int, up_to: int = MAX_H3_RES) -> List[int]:
    ids: List[int] = []
    for res in range(up_to + 1):
        mapping = mappings[res]
        ids.extend(iter(hex_id for hex_id, zone in mapping.items() if zone == zone_id))

    # NOTE: do not include cells from the remaining mapping
    return ids


def get_zone(lng: float, lat: float, up_to: int = MAX_H3_RES) -> Optional[str]:
    zone_id = get_zone_id(lng, lat, up_to)
    if zone_id is None:
        return None
    return timezone_names[zone_id]


def get_polygons_of_zone(zone_id: int, up_to: int = MAX_H3_RES, **kwargs) -> List:
    cells = get_hex_cells_of_zone(zone_id, up_to)
    polygons = h3.h3_set_to_multi_polygon(cells, **kwargs)
    return polygons
