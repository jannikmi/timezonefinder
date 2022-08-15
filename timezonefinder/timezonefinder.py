# -*- coding:utf-8 -*-
import json
from abc import ABC, abstractmethod
from io import BytesIO
from pathlib import Path
from struct import unpack
from typing import List, Optional, Union

import numpy as np
from h3.api import numpy_int as h3

from timezonefinder import utils
from timezonefinder.configs import (
    BINARY_DATA_ATTRIBUTES,
    BINARY_FILE_ENDING,
    DATA_ATTRIBUTE_NAMES,
    DTYPE_FORMAT_H,
    DTYPE_FORMAT_H_NUMPY,
    DTYPE_FORMAT_I,
    DTYPE_FORMAT_SIGNED_I_NUMPY,
    HOLE_ADR2DATA,
    HOLE_COORD_AMOUNT,
    HOLE_DATA,
    HOLE_REGISTRY,
    HOLE_REGISTRY_FILE,
    NR_BYTES_H,
    NR_BYTES_I,
    POLY_ADR2DATA,
    POLY_COORD_AMOUNT,
    POLY_DATA,
    POLY_MAX_VALUES,
    POLY_NR2ZONE_ID,
    POLY_ZONE_IDS,
    SHORTCUT_FILE,
    SHORTCUT_H3_RES,
    TIMEZONE_NAMES_FILE,
    CoordLists,
    CoordPairs,
)
from timezonefinder.hex_helpers import read_shortcuts_binary
from timezonefinder.utils import inside_polygon


class AbstractTimezoneFinder(ABC):
    # TODO document attributes in all classes
    # prevent dynamic attribute assignment (-> safe memory)
    __slots__ = [
        "bin_file_location",
        "shortcut_mapping",
        "in_memory",
        "_fromfile",
        "timezone_names",
        POLY_ZONE_IDS,
    ]
    binary_data_attributes: List[str] = [POLY_ZONE_IDS]

    def __init__(
        self,
        bin_file_location: Optional[Union[str, Path]] = None,
        in_memory: bool = False,
    ):
        self.in_memory = in_memory

        if self.in_memory:
            self._fromfile = utils.fromfile_memory
        else:
            self._fromfile = np.fromfile

        # open all the files in binary reading mode
        # for more info on what is stored in which .bin file, please read the comments in file_converter.py
        if bin_file_location is None:
            bin_file_location = Path(__file__).parent
        else:
            bin_file_location = Path(bin_file_location)
        self.bin_file_location: Path = bin_file_location

        with open(self.bin_file_location / TIMEZONE_NAMES_FILE, "r") as json_file:
            self.timezone_names = json.loads(json_file.read())

        path2shortcut_bin = self.bin_file_location / SHORTCUT_FILE
        self.shortcut_mapping = read_shortcuts_binary(path2shortcut_bin)

        for attribute_name in self.binary_data_attributes:
            file_name = attribute_name + BINARY_FILE_ENDING
            path2file = self.bin_file_location / file_name
            if self.in_memory:
                with open(path2file, mode="rb") as bin_file:
                    bf_in_mem = BytesIO(bin_file.read())
                    bf_in_mem.seek(0)
                setattr(self, attribute_name, bf_in_mem)
            else:
                bin_file = open(path2file, mode="rb")
                setattr(self, attribute_name, bin_file)

    def __del__(self):
        for attribute_name in self.binary_data_attributes:
            getattr(self, attribute_name).close()

    @property
    def nr_of_zones(self):
        return len(self.timezone_names)

    @staticmethod
    def using_numba() -> bool:
        """
        :return: True if Numba is being used to JIT compile helper functions
        """
        return utils.using_numba

    @staticmethod
    def using_clang_pip() -> bool:
        """
        :return: True if the compiled C implementation of the point in polygon algorithm is being used
        """
        return utils.inside_polygon == utils.pt_in_poly_clang

    def zone_id_of(self, poly_id: int) -> int:
        poly_zone_ids = getattr(self, POLY_ZONE_IDS)
        poly_zone_ids.seek(NR_BYTES_H * poly_id)
        return unpack(DTYPE_FORMAT_H, poly_zone_ids.read(NR_BYTES_H))[0]

    def zone_ids_of(self, poly_ids: np.ndarray) -> np.ndarray:
        poly_zone_ids = getattr(self, POLY_ZONE_IDS)
        id_array = np.empty(shape=len(poly_ids), dtype=DTYPE_FORMAT_H_NUMPY)

        for i, poly_id in enumerate(poly_ids):
            poly_zone_ids.seek(NR_BYTES_H * poly_id)
            id_array[i] = unpack(DTYPE_FORMAT_H, poly_zone_ids.read(NR_BYTES_H))[0]

        return id_array

    def zone_name_from_id(self, zone_id: int) -> str:
        try:
            return self.timezone_names[zone_id]
        except IndexError:
            raise ValueError("timezone could not be found. index error.")

    def zone_name_from_poly_id(self, poly_id: int) -> str:
        zone_id = self.zone_id_of(poly_id)
        return self.zone_name_from_id(zone_id)

    def get_shortcut_polys(self, *, lng: float, lat: float) -> np.ndarray:
        hex_id = h3.geo_to_h3(lat, lng, SHORTCUT_H3_RES)
        shortcut_poly_ids = self.shortcut_mapping[hex_id]
        return shortcut_poly_ids

    def most_common_zone_id(self, *, lng: float, lat: float) -> Optional[int]:
        polys = self.get_shortcut_polys(lng=lng, lat=lat)
        if len(polys) == 0:
            return None
        # Note: polygons are sorted from small to big in the shortcuts (grouped by zone)
        # -> the polygons of the biggest zone come last
        poly_of_biggest_zone = polys[-1]
        return self.zone_id_of(poly_of_biggest_zone)

    def unique_zone_id(self, *, lng: float, lat: float) -> Optional[int]:
        """
        :return: the zone id at the coordinate if there is exactly one possible zone, else `None`
        """
        polys = self.get_shortcut_polys(lng=lng, lat=lat)
        if len(polys) == 0:
            return None
        if len(polys) == 1:
            return self.zone_id_of(polys[0])
        zones = self.zone_ids_of(polys)
        zones_unique = np.unique(zones)
        if len(zones_unique) == 1:
            return zones_unique[0]
        # more than one zone in this shortcut
        return None

    @abstractmethod
    def timezone_at(self, *, lng: float, lat: float) -> Optional[str]:
        """looks up in which timezone the given coordinate is included in

        :param lng: longitude of the point in degree (-180.0 to 180.0)
        :param lat: latitude in degree (90.0 to -90.0)
        :return: the timezone name of a matching polygon or None
        """
        ...

    def timezone_at_land(self, *, lng: float, lat: float) -> Optional[str]:
        """computes in which land timezone a point is included in

        Especially for large polygons it is expensive to check if a point is really included.
        To speed things up there are "shortcuts" being used (stored in a binary file),
        which have been precomputed and store which timezone polygons have to be checked.

        :param lng: longitude of the point in degree (-180.0 to 180.0)
        :param lat: latitude in degree (90.0 to -90.0)
        :return: the timezone name of a matching polygon or
            ``None`` when an ocean timezone ("Etc/GMT+-XX") has been matched.
        """
        tz_name = self.timezone_at(lng=lng, lat=lat)
        if tz_name is not None and utils.is_ocean_timezone(tz_name):
            return None
        return tz_name

    def unique_timezone_at(self, *, lng: float, lat: float) -> Optional[str]:
        """returns the name of a unique zone within the corresponding shortcut

        :param lng: longitude of the point in degree (-180.0 to 180.0)
        :param lat: latitude in degree (90.0 to -90.0)
        :return: the timezone name of the unique zone or ``None`` if there are no or multiple zones in this shortcut
        """
        lng, lat = utils.validate_coordinates(lng, lat)
        unique_id = self.unique_zone_id(lng=lng, lat=lat)
        if unique_id is None:
            return None
        return self.zone_name_from_id(unique_id)


class TimezoneFinderL(AbstractTimezoneFinder):
    """a 'light' version of the TimezoneFinder class for quickly suggesting a timezone for a point on earth

    Instead of using timezone polygon data like ``TimezoneFinder``,
    this class only uses a precomputed 'shortcut' to suggest a probable result:
    the most common zone in a rectangle of a half degree of latitude and one degree of longitude
    """

    def timezone_at(self, *, lng: float, lat: float) -> Optional[str]:
        """instantly returns the name of the most common zone within the corresponding shortcut

        Note: 'most common' in this context means that the polygons with the most coordinates in sum
            occurring in the corresponding shortcut belong to this zone.

        :param lng: longitude of the point in degree (-180.0 to 180.0)
        :param lat: latitude in degree (90.0 to -90.0)
        :return: the timezone name of the most common zone or None if there are no timezone polygons in this shortcut
        """
        lng, lat = utils.validate_coordinates(lng, lat)
        most_common_id = self.most_common_zone_id(lng=lng, lat=lat)
        if most_common_id is None:
            return None
        return self.zone_name_from_id(most_common_id)


class TimezoneFinder(AbstractTimezoneFinder):
    """Class for quickly finding the timezone of a point on earth offline.

    Because of indexing ("shortcuts"), not all timezone polygons have to be tested during a query.

    Opens the required timezone polygon data in binary files to enable fast access.
    For a detailed documentation of data management please refer to the code documentation of
    `file_converter.py <https://github.com/jannikmi/timezonefinder/blob/master/scripts/file_converter.py>`__

    :ivar binary_data_attributes: the names of all attributes which store the opened binary data files

    :param bin_file_location: path to the binary data files to use, None if native package data should be used
    :param in_memory: whether to completely read and keep the binary files in memory
    """

    # __slots__ declared in parents are available in child classes. However, child subclasses will get a __dict__
    # and __weakref__ unless they also define __slots__ (which should only contain names of any additional slots).
    __slots__ = DATA_ATTRIBUTE_NAMES

    binary_data_attributes = BINARY_DATA_ATTRIBUTES

    def __init__(self, bin_file_location: Optional[str] = None, in_memory: bool = False):
        super(TimezoneFinder, self).__init__(bin_file_location, in_memory)

        # stores for which polygons (how many) holes exits and the id of the first of those holes
        # since there are very few it is feasible to keep them in the memory
        with open(self.bin_file_location / HOLE_REGISTRY_FILE, "r") as json_file:
            hole_registry_tmp = json.loads(json_file.read())

        # convert the json string keys to int
        hole_registry = {int(k): v for k, v in hole_registry_tmp.items()}
        setattr(self, HOLE_REGISTRY, hole_registry)

    @property
    def nr_of_polygons(self) -> int:
        poly_zone_ids = getattr(self, POLY_ZONE_IDS)
        return utils.get_file_size_byte(poly_zone_ids) // NR_BYTES_H

    def coords_of(self, polygon_nr: int = 0) -> np.ndarray:
        poly_coord_amount = getattr(self, POLY_COORD_AMOUNT)
        poly_adr2data = getattr(self, POLY_ADR2DATA)
        poly_data = getattr(self, POLY_DATA)

        # how many coordinates are stored in this polygon
        poly_coord_amount.seek(NR_BYTES_I * polygon_nr)
        nr_of_values = unpack(DTYPE_FORMAT_I, poly_coord_amount.read(NR_BYTES_I))[0]

        poly_adr2data.seek(NR_BYTES_I * polygon_nr)
        poly_data.seek(unpack(DTYPE_FORMAT_I, poly_adr2data.read(NR_BYTES_I))[0])
        return np.stack(
            (
                self._fromfile(poly_data, dtype=DTYPE_FORMAT_SIGNED_I_NUMPY, count=nr_of_values),
                self._fromfile(poly_data, dtype=DTYPE_FORMAT_SIGNED_I_NUMPY, count=nr_of_values),
            )
        )

    def _holes_of_poly(self, polygon_nr: int):
        hole_coord_amount = getattr(self, HOLE_COORD_AMOUNT)
        hole_adr2data = getattr(self, HOLE_ADR2DATA)
        hole_data = getattr(self, HOLE_DATA)
        hole_registry = getattr(self, HOLE_REGISTRY)

        try:
            amount_of_holes, first_hole_id = hole_registry[polygon_nr]
        except KeyError:
            return

        hole_coord_amount.seek(NR_BYTES_H * first_hole_id)
        hole_adr2data.seek(NR_BYTES_I * first_hole_id)

        for _ in range(amount_of_holes):
            nr_of_values = unpack(DTYPE_FORMAT_H, hole_coord_amount.read(NR_BYTES_H))[0]
            hole_data.seek(unpack(DTYPE_FORMAT_I, hole_adr2data.read(NR_BYTES_I))[0])

            x_coords = self._fromfile(hole_data, dtype=DTYPE_FORMAT_SIGNED_I_NUMPY, count=nr_of_values)
            y_coords = self._fromfile(hole_data, dtype=DTYPE_FORMAT_SIGNED_I_NUMPY, count=nr_of_values)
            yield np.array(
                [
                    x_coords,
                    y_coords,
                ]
            )

    def get_polygon(self, polygon_nr: int, coords_as_pairs: bool = False) -> List[Union[CoordPairs, CoordLists]]:
        list_of_converted_polygons = []
        if coords_as_pairs:
            conversion_method = utils.convert2coord_pairs
        else:
            conversion_method = utils.convert2coords
        list_of_converted_polygons.append(conversion_method(self.coords_of(polygon_nr=polygon_nr)))

        for hole in self._holes_of_poly(polygon_nr):
            list_of_converted_polygons.append(conversion_method(hole))

        return list_of_converted_polygons

    def get_geometry(
        self,
        tz_name: Optional[str] = "",
        tz_id: Optional[int] = 0,
        use_id: bool = False,
        coords_as_pairs: bool = False,
    ):
        """retrieves the geometry of a timezone polygon

        :param tz_name: one of the names in ``timezone_names.json`` or ``self.timezone_names``
        :param tz_id: the id of the timezone (=index in ``self.timezone_names``)
        :param use_id: if ``True`` uses ``tz_id`` instead of ``tz_name``
        :param coords_as_pairs: determines the structure of the polygon representation
        :return: a data structure representing the multipolygon of this timezone
            output format: ``[ [polygon1, hole1, hole2...], [polygon2, ...], ...]``
            and each polygon and hole is itself formatted like: ``([longitudes], [latitudes])``
            or ``[(lng1,lat1), (lng2,lat2),...]`` if ``coords_as_pairs=True``.
        """

        if use_id:
            if not isinstance(tz_id, int):
                raise TypeError("the zone id must be given as int.")
            if tz_id < 0 or tz_id >= self.nr_of_zones:
                raise ValueError(f"the given zone id {tz_id} is invalid (value range: 0 - {self.nr_of_zones - 1}.")
        else:
            try:
                tz_id = self.timezone_names.index(tz_name)
            except ValueError:
                raise ValueError("The timezone '", tz_name, "' does not exist.")
        if tz_id is None:
            raise ValueError("no timezone id given.")
        poly_id2zone_id = getattr(self, POLY_NR2ZONE_ID)
        poly_id2zone_id.seek(NR_BYTES_H * tz_id)
        # read poly_id of the first polygon of that zone
        this_zone_poly_id = unpack(DTYPE_FORMAT_H, poly_id2zone_id.read(NR_BYTES_H))[0]
        # read poly_id of the first polygon of the consequent zone
        # (also exists for the last zone, cf. file_converter.py)
        next_zone_poly_id = unpack(DTYPE_FORMAT_H, poly_id2zone_id.read(NR_BYTES_H))[0]
        # read and return all polygons from this zone:
        return [self.get_polygon(poly_id, coords_as_pairs) for poly_id in range(this_zone_poly_id, next_zone_poly_id)]

    def outside_the_boundaries_of(self, poly_id: int, x: int, y: int) -> bool:
        # get the boundaries of the polygon = (lng_max, lng_min, lat_max, lat_min) converted to int32
        poly_max_values = getattr(self, POLY_MAX_VALUES)
        poly_max_values.seek(4 * NR_BYTES_I * poly_id)
        xmax, xmin, ymax, ymin = self._fromfile(
            poly_max_values,
            dtype=DTYPE_FORMAT_SIGNED_I_NUMPY,
            count=4,
        )
        return x > xmax or x < xmin or y > ymax or y < ymin

    def inside_of_polygon(self, poly_id: int, x: int, y: int) -> bool:
        # only read polygon (hole) data on demand
        # only run the expensive algorithm if the point is withing the boundaries
        if self.outside_the_boundaries_of(poly_id, x, y):
            return False

        if not inside_polygon(x, y, self.coords_of(polygon_nr=poly_id)):
            return False

        # when the point is within a hole of the polygon, this timezone must not be returned
        if any(iter(inside_polygon(x, y, hole) for hole in self._holes_of_poly(poly_id))):
            return False

        # the query point is included in this polygon, but not any hole
        return True

    def timezone_at(self, *, lng: float, lat: float) -> Optional[str]:
        """computes in which ocean OR land timezone a point is included in

        Especially for large polygons it is expensive to check if a point is really included.
        In case there is only one possible zone (left), this zone will instantly be returned without actually checking
        if the query point is included in this polygon.

        To speed things up there are "shortcuts" being used
            which have been precomputed and store which timezone polygons have to be checked.

        .. note:: Since ocean timezones span the whole globe, some timezone will always be matched!
            `None` can only be returned when you have compiled timezone data without such "full coverage".

        :param lng: longitude of the point in degree (-180.0 to 180.0)
        :param lat: latitude in degree (90.0 to -90.0)
        :return: the timezone name of the matched timezone polygon. possibly "Etc/GMT+-XX" in case of an ocean timezone.
        """
        lng, lat = utils.validate_coordinates(lng, lat)
        possible_polygons = self.get_shortcut_polys(lng=lng, lat=lat)
        nr_possible_polygons = len(possible_polygons)
        if nr_possible_polygons == 0:
            # Note: hypothetical case, with ocean data every shortcut maps to at least one polygon
            return None
        if nr_possible_polygons == 1:
            # there is only one polygon in that area. return its timezone name without further checks
            polygon_id = possible_polygons[0]
            return self.zone_name_from_poly_id(polygon_id)

        # create a list of all the timezone ids of all possible polygons
        zone_ids = self.zone_ids_of(possible_polygons)

        last_zone_change_idx = utils.get_last_change_idx(zone_ids)
        if last_zone_change_idx == 0:
            return self.zone_name_from_id(zone_ids[0])

        # ATTENTION: the polygons are stored converted to 32-bit ints,
        # convert the query coordinates in the same fashion in order to make the data formats match
        # x = longitude  y = latitude  both converted to 8byte int
        x = utils.coord2int(lng)
        y = utils.coord2int(lat)

        # check until the point is included in one of the possible polygons
        for i, poly_id in enumerate(possible_polygons):

            if i >= last_zone_change_idx:
                break

            if self.inside_of_polygon(poly_id, x, y):
                zone_id = zone_ids[i]
                return self.zone_name_from_id(zone_id)

        # since it is the last possible option,
        # the polygons of the last possible zone don't actually have to be checked
        zone_id = zone_ids[-1]
        return self.zone_name_from_id(zone_id)

    def certain_timezone_at(self, *, lng: float, lat: float) -> Optional[str]:
        """checks in which timezone polygon the point is certainly included in

        .. note:: this is only meaningful when you have compiled your own timezone data
            where there are areas without timezone polygon coverage.
            Otherwise some timezone will always be matched and the functionality is equal to using `.timezone_at()`
            -> useless to actually test all polygons.

        .. note:: using this function is less performant than `.timezone_at()`

        :param lng: longitude of the point in degree
        :param lat: latitude in degree
        :return: the timezone name of the polygon the point is included in or `None`
        """
        lng, lat = utils.validate_coordinates(lng, lat)
        possible_polygons = self.get_shortcut_polys(lng=lng, lat=lat)
        nr_possible_polygons = len(possible_polygons)

        if nr_possible_polygons == 0:
            # Note: hypothetical case, with ocean data every shortcut maps to at least one polygon
            return None

        # ATTENTION: the polygons are stored converted to 32-bit ints,
        # convert the query coordinates in the same fashion in order to make the data formats match
        # x = longitude  y = latitude  both converted to 8byte int
        x = utils.coord2int(lng)
        y = utils.coord2int(lat)

        # check if the query point is found to be truly included in one of the possible polygons
        for poly_id in possible_polygons:
            if self.inside_of_polygon(poly_id, x, y):
                zone_id = self.zone_id_of(poly_id)
                return self.zone_name_from_id(zone_id)

        # none of the polygon candidates truly matched
        return None
