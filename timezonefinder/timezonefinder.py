import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Union
import numpy as np
from h3.api import numpy_int as h3

from timezonefinder.np_binary_helpers import (
    get_zone_ids_path,
    get_zone_positions_path,
    read_per_polygon_vector,
)
from timezonefinder.polygon_array import PolygonArray
from timezonefinder import utils, utils_clang
from timezonefinder.configs import (
    DEFAULT_DATA_DIR,
    SHORTCUT_H3_RES,
    CoordLists,
    CoordPairs,
)

from timezonefinder.flatbuf.shortcut_utils import (
    get_shortcut_file_path,
    read_shortcuts_binary,
)
from timezonefinder.zone_names import read_zone_names


class AbstractTimezoneFinder(ABC):
    # prevent dynamic attribute assignment (-> safe memory)
    """
    Abstract base class for TimezoneFinder instances
    """

    __slots__ = [
        "data_location",
        "shortcut_mapping",
        "in_memory",
        "_fromfile",
        "timezone_names",
        "zone_ids",
        "holes_dir",
        "boundaries_dir",
        "boundaries",
        "holes",
    ]

    zone_ids: np.ndarray
    """
    List of attribute names that store opened binary data files.
    """

    def __init__(
        self,
        bin_file_location: Optional[Union[str, Path]] = None,
        in_memory: bool = False,
    ):
        """
        Initialize the AbstractTimezoneFinder.
        :param bin_file_location: The path to the binary data files to use. If None, uses native package data.
        :param in_memory: ignored. The binary files will be read into memory (few MB)
        """
        if bin_file_location is None:
            bin_file_location = DEFAULT_DATA_DIR
        self.data_location: Path = Path(bin_file_location)

        self.timezone_names = read_zone_names(self.data_location)

        path2shortcut_bin = get_shortcut_file_path(self.data_location)
        self.shortcut_mapping = read_shortcuts_binary(path2shortcut_bin)

        zone_ids_path = get_zone_ids_path(self.data_location)
        self.zone_ids = read_per_polygon_vector(zone_ids_path)

    @property
    def nr_of_zones(self):
        """
        Get the number of timezones.

        :rtype: int
        """
        return len(self.timezone_names)

    @staticmethod
    def using_numba() -> bool:
        """
        Check if Numba is being used.

        :rtype: bool
        :return: True if Numba is being used to JIT compile helper functions
        """
        return utils.using_numba

    @staticmethod
    def using_clang_pip() -> bool:
        """
        :return: True if the compiled C implementation of the point in polygon algorithm is being used
        """
        return utils.inside_polygon == utils_clang.pt_in_poly_clang

    def zone_id_of(self, poly_id: int) -> int:
        """
        Get the zone ID of a polygon.

        :param poly_id: The ID of the polygon.
        :type poly_id: int
        :rtype: int
        """
        try:
            return self.zone_ids[poly_id]
        except TypeError:
            raise ValueError(f"zone_ids is not set in directory {self.data_location}.")

    def zone_ids_of(self, poly_ids: np.ndarray) -> np.ndarray:
        """
        Get the zone IDs of multiple polygons.

        :param poly_ids: An array of polygon IDs.
        :return: array of zone IDs corresponding to the polygon IDs.
        """
        return self.zone_ids[poly_ids]

    def zone_name_from_id(self, zone_id: int) -> str:
        """
        Get the zone name from a zone ID.

        :param zone_id: The ID of the zone.
        :return: The name of the zone.
        :raises ValueError: If the timezone could not be found.
        """
        try:
            return self.timezone_names[zone_id]
        except IndexError:
            raise ValueError("timezone could not be found. index error.")

    def zone_name_from_poly_id(self, poly_id: int) -> str:
        """
        Get the zone name from a polygon ID.

        :param poly_id: The ID of the polygon.
        :return: The name of the zone.
        """
        zone_id = self.zone_id_of(poly_id)
        return self.zone_name_from_id(zone_id)

    def get_shortcut_polys(self, *, lng: float, lat: float) -> np.ndarray:
        """
        Get the polygon IDs in the shortcut corresponding to the given coordinates.

        :param lng: The longitude of the point in degrees (-180.0 to 180.0).
        :param lat: The latitude of the point in degrees (90.0 to -90.0).
        :return: An array of polygon IDs.
        """
        hex_id = h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES)
        shortcut_poly_ids = self.shortcut_mapping[hex_id]
        return shortcut_poly_ids

    def most_common_zone_id(self, *, lng: float, lat: float) -> Optional[int]:
        """
        Get the most common zone ID in the shortcut corresponding to the given coordinates.

        :param lng: The longitude of the point in degrees (-180.0 to 180.0).
        :param lat: The latitude of the point in degrees (90.0 to -90.0).
        :return: The most common zone ID or None if no polygons exist in the shortcut.
        """
        polys = self.get_shortcut_polys(lng=lng, lat=lat)
        if len(polys) == 0:
            return None
        # Note: polygons are sorted from small to big in the shortcuts (grouped by zone)
        # -> the polygons of the biggest zone come last
        poly_of_biggest_zone = polys[-1]
        return self.zone_id_of(poly_of_biggest_zone)

    def unique_zone_id(self, *, lng: float, lat: float) -> Optional[int]:
        """
        Get the unique zone ID in the shortcut corresponding to the given coordinates.

        :param lng: The longitude of the point in degrees (-180.0 to 180.0).
        :param lat: The latitude of the point in degrees (90.0 to -90.0).
        :return: The unique zone ID or None if no polygons exist in the shortcut.
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
    :param in_memory: whether to completely read and keep the timezone polygon binary files in memory
    """

    # __slots__ declared in parents are available in child classes. However, child subclasses will get a __dict__
    # and __weakref__ unless they also define __slots__ (which should only contain names of any additional slots).
    __slots__ = [
        "hole_registry",
        "_boundaries_file",
        "_holes_file",
    ]

    def __init__(
        self, bin_file_location: Optional[str] = None, in_memory: bool = False
    ):
        super().__init__(bin_file_location, in_memory)
        self.holes_dir = utils.get_holes_dir(self.data_location)
        self.boundaries_dir = utils.get_boundaries_dir(self.data_location)
        self.boundaries = PolygonArray(
            data_location=self.boundaries_dir, in_memory=in_memory
        )
        self.holes = PolygonArray(data_location=self.holes_dir, in_memory=in_memory)

        # stores for which polygons (how many) holes exits and the id of the first of those holes
        # since there are very few entries it is feasible to keep them in the memory
        self.hole_registry = self._load_hole_registry()

    def _load_hole_registry(self) -> Dict[int, Tuple[int, int]]:
        """
        Load and convert the hole registry from JSON file, converting keys to int.
        """
        path = utils.get_hole_registry_path(self.data_location)
        with open(path, encoding="utf-8") as json_file:
            hole_registry_tmp = json.loads(json_file.read())
        # convert the json string keys to int
        return {int(k): v for k, v in hole_registry_tmp.items()}

    @property
    def nr_of_polygons(self):
        return len(self.boundaries)

    @property
    def nr_of_holes(self):
        return len(self.holes)

    def coords_of(self, polygon_nr: int = 0) -> np.ndarray:
        """
        Get the coordinates of a polygon from the FlatBuffers collection.

        :param polygon_nr: The index of the polygon.
        :return: Array of coordinates.
        """
        return self.boundaries.coords_of(polygon_nr)

    def _iter_hole_ids_of(self, polygon_nr: int) -> Iterable[int]:
        """
        Yield the hole IDs for a given polygon number.

        :param polygon_nr: Number of the polygon
        :yield: Hole IDs
        """
        try:
            amount_of_holes, first_hole_id = self.hole_registry[polygon_nr]
        except KeyError:
            return
        for i in range(amount_of_holes):
            yield first_hole_id + i

    def _holes_of_poly(self, polygon_nr: int):
        """
        Get the holes of a polygon from the FlatBuffers collection.

        :param polygon_nr: Number of the polygon
        :yield: Generator of hole coordinates
        """
        for hole_id in self._iter_hole_ids_of(polygon_nr):
            yield self.holes.coords_of(hole_id)

    def get_polygon(
        self, polygon_nr: int, coords_as_pairs: bool = False
    ) -> List[Union[CoordPairs, CoordLists]]:
        """
        Get the polygon coordinates of a given polygon number.

        :param polygon_nr: Polygon number
        :param coords_as_pairs: Determines the structure of the polygon representation
        :return: List of polygon coordinates
        """
        list_of_converted_polygons = []
        if coords_as_pairs:
            conversion_method = utils.convert2coord_pairs
        else:
            conversion_method = utils.convert2coords
        list_of_converted_polygons.append(
            conversion_method(self.coords_of(polygon_nr=polygon_nr))
        )

        for hole in self._holes_of_poly(polygon_nr):
            list_of_converted_polygons.append(conversion_method(hole))

        return list_of_converted_polygons

    def _iter_poly_ids_of_zone(self, zone_id: int) -> Iterable[int]:
        """
        Yield the polygon IDs for a given zone ID.

        :param zone_id: ID of the zone
        :yield: Polygon IDs
        """
        # load only on demand. used only in get_geometry() which is a non performance critical utility function
        zone_positions_path = get_zone_positions_path(self.data_location)
        zone_positions = np.load(zone_positions_path, mmap_mode="r")
        first_poly_id_zone = zone_positions[zone_id]
        # read the poly_id of the first polygon of the consequent zone
        # NOTE: this has also been added for the last zone
        first_poly_id_next = zone_positions[zone_id + 1]
        yield from range(first_poly_id_zone, first_poly_id_next)

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
                raise ValueError(
                    f"the given zone id {tz_id} is invalid (value range: 0 - {self.nr_of_zones - 1}."
                )
        else:
            if tz_name is None:
                raise ValueError("no timezone name given.")
            try:
                tz_id = self.timezone_names.index(tz_name)
            except ValueError:
                raise ValueError("The timezone '", tz_name, "' does not exist.")
        if tz_id is None:
            raise ValueError("no timezone id given.")

        return [
            self.get_polygon(poly_id, coords_as_pairs)
            for poly_id in self._iter_poly_ids_of_zone(tz_id)
        ]

    def get_polygon_boundaries(self, poly_id: int) -> Tuple[int, int, int, int]:
        """returns the bounding box of the polygon = (lng_max, lng_min, lat_max, lat_min) converted to int32"""
        xmax = self.boundaries.xmax[poly_id]
        xmin = self.boundaries.xmin[poly_id]
        ymax = self.boundaries.ymax[poly_id]
        ymin = self.boundaries.ymin[poly_id]
        return xmax, xmin, ymax, ymin

    def inside_of_polygon(self, poly_id: int, x: int, y: int) -> bool:
        """
        Check if a point is inside a polygon.

        :param poly_id: Polygon ID # TODO rename to boundary_id
        :param x: X-coordinate of the point
        :param y: Y-coordinate of the point
        :return: True if the point is inside the polygon, False otherwise
        """
        # avoid running the expensive PIP algorithm at any cost
        # -> check bboxes first
        if self.boundaries.outside_bbox(poly_id, x, y):
            return False

        # NOTE: holes are much smaller -> less expensive to check
        # -> check holes before the polygon
        hole_id_iter = self._iter_hole_ids_of(poly_id)
        if self.holes.in_any_polygon(hole_id_iter, x, y):
            # the point is within a hole of the polygon
            # it is excluded fromn the this boundary polygon
            return False

        return self.boundaries.pip(poly_id, x, y)

    def timezone_at(self, *, lng: float, lat: float) -> Optional[str]:
        """
        Find the timezone for a given point, considering both land and ocean timezones.

        Uses precomputed shortcuts to reduce the number of polygons checked. Returns the timezone name
        of the matched polygon, which may be an ocean timezone ("Etc/GMT+-XX") if applicable.

        Since ocean timezones span the whole globe, some timezone will always be matched!
        `None` can only be returned when using custom timezone data without such ocean timezones.


        :param lng: longitude of the point in degrees (-180.0 to 180.0)
        :param lat: latitude of the point in degrees (90.0 to -90.0)
        :return: the timezone name of the matched polygon, or None if no match is found.
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
        # -> instantly return the last zone
        zone_id = zone_ids[-1]
        return self.zone_name_from_id(zone_id)

    def certain_timezone_at(self, *, lng: float, lat: float) -> Optional[str]:
        """checks in which timezone polygon the point is certainly included in

        .. note:: this is only meaningful when you have compiled your own timezone data
            where there are areas without timezone polygon coverage.
            Otherwise, some timezone will always be matched and the functionality is equal to using `.timezone_at()`
            -> useless to actually test all polygons.

        .. note:: using this function is less performant than `.timezone_at()`

        :param lng: longitude of the point in degree
        :param lat: latitude of the point in degree
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
