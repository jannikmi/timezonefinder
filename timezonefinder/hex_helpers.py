# TODO remove

from h3.api import numpy_int as h3


def lies_in_h3_cell(h: int, lng: float, lat: float) -> bool:
    res = h3.get_resolution(h)
    return h3.latlng_to_cell(lat, lng, res) == h
