# -*- coding:utf-8 -*-
import json
from io import SEEK_CUR, BytesIO
from math import radians
from os.path import abspath, join, pardir
from struct import unpack

import numpy as np
from importlib_resources import open_binary
from numpy import array, dtype, empty, fromfile

from .global_settings import (
    DTYPE_FORMAT_B_NUMPY, DTYPE_FORMAT_F_NUMPY, DTYPE_FORMAT_H, DTYPE_FORMAT_H_NUMPY, DTYPE_FORMAT_I,
    DTYPE_FORMAT_SIGNED_I_NUMPY, MAX_HAVERSINE_DISTANCE, NR_BYTES_H, NR_BYTES_I, NR_LAT_SHORTCUTS, NR_SHORTCUTS_PER_LAT,
    NR_SHORTCUTS_PER_LNG, TIMEZONE_NAMES_FILE,
)

try:
    import numba
    from .helpers_numba import coord2int, distance_to_polygon_exact, distance_to_polygon, inside_polygon, \
        all_the_same, rectify_coordinates, coord2shortcut, convert2coord_pairs, convert2coords
except ImportError:
    numba = None
    from .helpers import coord2int, distance_to_polygon_exact, distance_to_polygon, inside_polygon, \
        all_the_same, rectify_coordinates, coord2shortcut, convert2coord_pairs, convert2coords

with open(abspath(join(__file__, pardir, TIMEZONE_NAMES_FILE)), 'r') as f:
    timezone_names = json.loads(f.read())


def fromfile_memory(file, **kwargs):
    # res = np.frombuffer(file.getbuffer(), offset=file.tell(), **kwargs)
    # faster:
    res = np.frombuffer(file.getbuffer(), offset=file.tell(), **kwargs)
    file.seek(dtype(kwargs['dtype']).itemsize * kwargs['count'], SEEK_CUR)
    return res


class TimezoneFinder:
    """
    This class lets you quickly find the timezone of a point on earth.
    It keeps the binary files open in reading mode to enable fast consequent access.
    currently per half degree of latitude and per degree of longitude a set of candidate polygons are stored
        this gives a SHORTCUT to which of the 27k+ polygons should be tested
        (tests evaluated this to be the fastest setup when being used with numba)
    """

    def __init__(self, in_memory=False):
        self.in_memory = in_memory

        if self.in_memory:
            self.fromfile = fromfile_memory
        else:
            self.fromfile = fromfile

        # open all the files in binary reading mode
        # for more info on what is stored in which .bin file, please read the comments in file_converter.py
        self.poly_zone_ids = self.open_binary('timezonefinder', 'poly_zone_ids.bin')
        self.poly_coord_amount = self.open_binary('timezonefinder', 'poly_coord_amount.bin')
        self.poly_adr2data = self.open_binary('timezonefinder', 'poly_adr2data.bin')
        self.poly_data = self.open_binary('timezonefinder', 'poly_data.bin')
        self.poly_max_values = self.open_binary('timezonefinder', 'poly_max_values.bin')
        self.poly_nr2zone_id = self.open_binary('timezonefinder', 'poly_nr2zone_id.bin')

        self.hole_poly_ids = self.open_binary('timezonefinder', 'hole_poly_ids.bin')
        self.hole_coord_amount = self.open_binary('timezonefinder', 'hole_coord_amount.bin')
        self.hole_adr2data = self.open_binary('timezonefinder', 'hole_adr2data.bin')
        self.hole_data = self.open_binary('timezonefinder', 'hole_data.bin')

        self.shortcuts_entry_amount = self.open_binary('timezonefinder', 'shortcuts_entry_amount.bin')
        self.shortcuts_adr2data = self.open_binary('timezonefinder', 'shortcuts_adr2data.bin')
        self.shortcuts_data = self.open_binary('timezonefinder', 'shortcuts_data.bin')
        self.shortcuts_unique_id = self.open_binary('timezonefinder', 'shortcuts_unique_id.bin')

        # store for which polygons (how many) holes exits and the id of the first of those holes
        # since there are very few (+-22) it is feasible to keep them in the memory
        self.hole_registry = {}
        # read the polygon ids for all the holes
        for i, block in enumerate(iter(lambda: self.hole_poly_ids.read(NR_BYTES_H), b'')):
            poly_id = unpack(DTYPE_FORMAT_H, block)[0]
            try:
                amount_of_holes, hole_id = self.hole_registry[poly_id]
                self.hole_registry.update({
                    poly_id: (amount_of_holes + 1, hole_id),
                })
            except KeyError:
                self.hole_registry.update({
                    poly_id: (1, i),
                })

    def open_binary(self, *args):
        bin_fd = open_binary(*args)
        if self.in_memory:
            mem_bin_fd = BytesIO(bin_fd.read())
            mem_bin_fd.seek(0)
            bin_fd.close()
            return mem_bin_fd
        else:
            return bin_fd

    def __del__(self):
        self.poly_zone_ids.close()
        self.poly_coord_amount.close()
        self.poly_adr2data.close()
        self.poly_data.close()
        self.poly_max_values.close()
        self.poly_nr2zone_id.close()
        self.hole_poly_ids.close()
        self.hole_coord_amount.close()
        self.hole_adr2data.close()
        self.hole_data.close()
        self.shortcuts_entry_amount.close()
        self.shortcuts_adr2data.close()
        self.shortcuts_data.close()
        self.shortcuts_unique_id.close()

    @staticmethod
    def using_numba():
        return numba is not None

    # TODO enable
    #  @staticmethod
    # def using_precompiled_funcs():
    #     return (precompilation is not None)

    def id_of(self, line=0):
        self.poly_zone_ids.seek(NR_BYTES_H * line)
        return unpack(DTYPE_FORMAT_H, self.poly_zone_ids.read(NR_BYTES_H))[0]

    def ids_of(self, iterable):
        id_array = empty(shape=len(iterable), dtype=DTYPE_FORMAT_B_NUMPY)

        for i, line_nr in enumerate(iterable):
            self.poly_zone_ids.seek((NR_BYTES_H * line_nr))
            id_array[i] = unpack(DTYPE_FORMAT_H, self.poly_zone_ids.read(NR_BYTES_H))[0]

        return id_array

    def polygon_ids_of_shortcut(self, x=0, y=0):
        # get the address of the first entry in this shortcut
        # offset: 180 * number of shortcuts per lat degree * 2bytes = entries per column of x shortcuts
        # shortcuts are stored: (0,0) (0,1) (0,2)... (1,0)...
        self.shortcuts_entry_amount.seek(NR_LAT_SHORTCUTS * NR_BYTES_H * x + NR_BYTES_H * y)
        nr_of_entries = unpack(DTYPE_FORMAT_H, self.shortcuts_entry_amount.read(NR_BYTES_H))[0]

        self.shortcuts_adr2data.seek(NR_LAT_SHORTCUTS * NR_BYTES_I * x + NR_BYTES_I * y)
        self.shortcuts_data.seek(unpack(DTYPE_FORMAT_I, self.shortcuts_adr2data.read(NR_BYTES_I))[0])
        return self.fromfile(self.shortcuts_data, dtype=DTYPE_FORMAT_H_NUMPY, count=nr_of_entries)

    def coords_of(self, line=0):
        # how many coordinates are stored in this polygon
        self.poly_coord_amount.seek(NR_BYTES_I * line)
        nr_of_values = unpack(DTYPE_FORMAT_I, self.poly_coord_amount.read(NR_BYTES_I))[0]
        if nr_of_values == 0:
            raise ValueError

        self.poly_adr2data.seek(NR_BYTES_I * line)
        self.poly_data.seek(unpack(DTYPE_FORMAT_I, self.poly_adr2data.read(NR_BYTES_I))[0])

        return array([self.fromfile(self.poly_data, dtype=DTYPE_FORMAT_SIGNED_I_NUMPY, count=nr_of_values),
                      self.fromfile(self.poly_data, dtype=DTYPE_FORMAT_SIGNED_I_NUMPY, count=nr_of_values)])

    def _holes_of_line(self, line=0):
        try:
            amount_of_holes, hole_id = self.hole_registry[line]

            for i in range(amount_of_holes):
                self.hole_coord_amount.seek(NR_BYTES_H * hole_id)
                nr_of_values = unpack(DTYPE_FORMAT_H, self.hole_coord_amount.read(NR_BYTES_H))[0]

                self.hole_adr2data.seek(NR_BYTES_I * hole_id)
                self.hole_data.seek(unpack(DTYPE_FORMAT_I, self.hole_adr2data.read(NR_BYTES_I))[0])

                yield array([self.fromfile(self.hole_data, dtype=DTYPE_FORMAT_SIGNED_I_NUMPY, count=nr_of_values),
                             self.fromfile(self.hole_data, dtype=DTYPE_FORMAT_SIGNED_I_NUMPY, count=nr_of_values)])
                hole_id += 1

        except KeyError:
            return

    def get_polygon(self, polygon_nr, coords_as_pairs=False):
        list_of_converted_polygons = []
        if coords_as_pairs:
            conversion_method = convert2coord_pairs
        else:
            conversion_method = convert2coords
        list_of_converted_polygons.append(conversion_method(self.coords_of(line=polygon_nr)))

        for hole in self._holes_of_line(polygon_nr):
            list_of_converted_polygons.append(conversion_method(hole))

        return list_of_converted_polygons

    def get_geometry(self, tz_name='', tz_id=0, use_id=False, coords_as_pairs=False):
        '''
        :param tz_name: one of the names in timezone_names
        :param tz_id: the id of the timezone (=index in timezone_names)
        :param use_id: determines whether id or name should be used
        :param coords_as_pairs: determines the structure of the polygon representation
        :return: a data structure representing the multipolygon of this timezone
        output format: [ [polygon1, hole1, hole2...], [polygon2, ...], ...]
         and each polygon and hole is itself formated like: ([longitudes], [latitudes])
         or [(lng1,lat1), (lng2,lat2),...] if ``coords_as_pairs=True``.
        '''

        if use_id:
            zone_id = tz_id
        else:
            try:
                zone_id = timezone_names.index(tz_name)
            except ValueError:
                raise ValueError("The timezone '", tz_name, "' does not exist.")

        self.poly_nr2zone_id.seek(NR_BYTES_H * zone_id)
        # read poly_nr of the first polygon of that zone
        first_polygon_nr = unpack(DTYPE_FORMAT_H, self.poly_nr2zone_id.read(NR_BYTES_H))[0]
        # read poly_nr of the first polygon of the next zone
        last_polygon_nr = unpack(DTYPE_FORMAT_H, self.poly_nr2zone_id.read(NR_BYTES_H))[0]
        poly_nrs = list(range(first_polygon_nr, last_polygon_nr))
        return [self.get_polygon(poly_nr, coords_as_pairs) for poly_nr in poly_nrs]

    def id_list(self, polygon_id_list, nr_of_polygons):
        """
        :param polygon_id_list:
        :param nr_of_polygons: length of polygon_id_list
        :return: (list of zone_ids, boolean: do all entries belong to the same zone)
        """
        zone_id_list = empty([nr_of_polygons], dtype=DTYPE_FORMAT_H_NUMPY)
        for pointer_local, polygon_id in enumerate(polygon_id_list):
            zone_id = self.id_of(polygon_id)
            zone_id_list[pointer_local] = zone_id

        return zone_id_list

    def compile_id_list(self, polygon_id_list, nr_of_polygons):
        """
        sorts the polygons_id list from least to most occurrences of the zone ids (->speed up)
        only 4.8% of all shortcuts include polygons from more than one zone
        but only for about 0.4% sorting would be beneficial (zones have different frequencies)
        in most of those cases there are only two types of zones (= entries in counted_zones) and one of them
         has only one entry.
         the polygon lists of all single shortcut are already sorted (during compilation of the binary files)
        sorting should be used for closest_timezone_at(), because only in
         that use case the polygon lists are quite long (multiple shortcuts are being checked simultaneously).
        :param polygon_id_list:
        :param nr_of_polygons: length of polygon_id_list
        :return: sorted list of polygon_ids, sorted list of zone_ids, boolean: do all entries belong to the same zone
        """

        # TODO functional
        def all_equal(iterable):
            x = None
            for x in iterable:
                # first_val = x
                break
            for y in iterable:
                if x != y:
                    return False
            return True

        zone_id_list = empty([nr_of_polygons], dtype=DTYPE_FORMAT_H_NUMPY)
        counted_zones = {}
        for pointer_local, polygon_id in enumerate(polygon_id_list):
            zone_id = self.id_of(polygon_id)
            zone_id_list[pointer_local] = zone_id
            try:
                counted_zones[zone_id] += 1
            except KeyError:
                counted_zones[zone_id] = 1

        if len(counted_zones) == 1:
            # there is only one zone. no sorting needed.
            return polygon_id_list, zone_id_list, True

        if all_equal(list(counted_zones.values())):
            # all the zones have the same amount of polygons. no sorting needed.
            return polygon_id_list, zone_id_list, False

        counted_zones_sorted = sorted(list(counted_zones.items()), key=lambda zone: zone[1])
        sorted_polygon_id_list = empty([nr_of_polygons], dtype=DTYPE_FORMAT_H_NUMPY)
        sorted_zone_id_list = empty([nr_of_polygons], dtype=DTYPE_FORMAT_H_NUMPY)

        pointer_output = 0
        for zone_id, amount in counted_zones_sorted:
            # write all polygons from this zone in the new list
            pointer_local = 0
            detected_polygons = 0
            while detected_polygons < amount:
                if zone_id_list[pointer_local] == zone_id:
                    # the polygon at the pointer has the wanted zone_id
                    detected_polygons += 1
                    sorted_polygon_id_list[pointer_output] = polygon_id_list[pointer_local]
                    sorted_zone_id_list[pointer_output] = zone_id
                    pointer_output += 1

                pointer_local += 1

        return sorted_polygon_id_list, sorted_zone_id_list, False

    def closest_timezone_at(self, *, lat, lng, delta_degree=1, exact_computation=False, return_distances=False,
                            force_evaluation=False):
        """
        This function searches for the closest polygon in the surrounding shortcuts.
        Make sure that the point does not lie within a polygon (for that case the algorithm is simply wrong!)
        Note that the algorithm won't find the closest polygon when it's on the 'other end of earth'
        (it can't search beyond the 180 deg lng border yet)
        This checks all the polygons within [delta_degree] degree lng and lat/
        Keep in mind that x degrees lat are not the same distance apart than x degree lng!
        This is also the reason why there could still be a closer polygon even though you got a result already.
        In order to make sure to get the closest polygon, you should increase the search radius
        until you get a result and then increase it once more (and take that result).
        This should only make a difference in really rare cases however.
        :param lng: longitude of the point in degree
        :param lat: latitude in degree
        :param delta_degree: the 'search radius' in degree
        :param exact_computation: when enabled the distance to every polygon edge is computed (way more complicated),
        instead of only evaluating the distances to all the vertices (=default).
        This only makes a real difference when polygons are very close.
        :param return_distances: when enabled the output looks like this:
        ( 'tz_name_of_the_closest_polygon',[ distances to all polygons in km], [tz_names of all polygons])
        :param force_evaluation:
        :return: the timezone name of the closest found polygon, the list of distances or None
        """

        def exact_routine(polygon_nr):
            coords = self.coords_of(polygon_nr)
            nr_points = len(coords[0])
            empty_array = empty([2, nr_points], dtype=DTYPE_FORMAT_F_NUMPY)
            return distance_to_polygon_exact(lng, lat, nr_points, coords, empty_array)

        def normal_routine(polygon_nr):
            coords = self.coords_of(polygon_nr)
            nr_points = len(coords[0])
            return distance_to_polygon(lng, lat, nr_points, coords)

        lng, lat = rectify_coordinates(lng, lat)

        # transform point X into cartesian coordinates
        current_closest_id = None
        central_x_shortcut, central_y_shortcut = coord2shortcut(lng, lat)

        lng = radians(lng)
        lat = radians(lat)

        possible_polygons = []

        # there are 2 shortcuts per 1 degree lat, so to cover 1 degree two shortcuts (rows) have to be checked
        # the highest shortcut is 0
        top = max(central_y_shortcut - NR_SHORTCUTS_PER_LAT * delta_degree, 0)
        # the lowest shortcut is 359 (= 2 shortcuts per 1 degree lat)
        bottom = min(central_y_shortcut + NR_SHORTCUTS_PER_LAT * delta_degree, 359)

        # the most left shortcut is 0
        left = max(central_x_shortcut - NR_SHORTCUTS_PER_LNG * delta_degree, 0)
        # the most right shortcut is 359 (= 1 shortcuts per 1 degree lng)
        right = min(central_x_shortcut + NR_SHORTCUTS_PER_LAT * delta_degree, 359)

        # select all the polygons from the surrounding shortcuts
        for x in range(left, right + 1, 1):
            for y in range(top, bottom + 1, 1):
                for p in self.polygon_ids_of_shortcut(x, y):
                    if p not in possible_polygons:
                        possible_polygons.append(p)

        polygons_in_list = len(possible_polygons)

        if polygons_in_list == 0:
            return None

        # initialize the list of ids
        # this list is sorted (see documentation of compile_id_list() )
        possible_polygons, ids, zones_are_equal = self.compile_id_list(possible_polygons, polygons_in_list)

        # if all the polygons in this shortcut belong to the same zone return it
        if zones_are_equal:
            if not (return_distances or force_evaluation):
                return timezone_names[ids[0]]

        if exact_computation:
            routine = exact_routine
        else:
            routine = normal_routine

        min_distance = MAX_HAVERSINE_DISTANCE
        distances = empty(polygons_in_list, dtype=DTYPE_FORMAT_F_NUMPY)
        # [None for i in range(polygons_in_list)]

        if force_evaluation:
            for pointer, polygon_nr in enumerate(possible_polygons):
                distance = routine(polygon_nr)
                distances[pointer] = distance
                if distance < min_distance:
                    min_distance = distance
                    current_closest_id = ids[pointer]

        else:
            pointer = 0
            # stores which polygons have been checked yet
            already_checked = [False] * polygons_in_list  # initialize array with False
            while pointer < polygons_in_list:
                # only check a polygon when its id is not the closest a the moment and it has not been checked already!
                if already_checked[pointer] or ids[pointer] == current_closest_id:
                    # go to the next polygon
                    pointer += 1

                else:
                    # this polygon has to be checked
                    distance = routine(possible_polygons[pointer])
                    distances[pointer] = distance
                    already_checked[pointer] = True
                    if distance < min_distance:
                        min_distance = distance
                        current_closest_id = ids[pointer]
                        # list of polygons has to be searched again, because closest zone has changed
                        # set pointer to the beginning of the list
                        # having a sorted list of polygon is beneficial here (less common zones come first)
                        pointer = 1

        if return_distances:
            return timezone_names[current_closest_id], distances, [timezone_names[x] for x in ids]
        return timezone_names[current_closest_id]

    def timezone_at(self, *, lng, lat):
        """
        this function looks up in which polygons the point could be included in
        to speed things up there are shortcuts being used (stored in a binary file)
        especially for large polygons it is expensive to check if a point is really included,
        so certain simplifications are made and even when you get a hit the point might actually
        not be inside the polygon (for example when there is only one timezone nearby)
        if you want to make sure a point is really inside a timezone use 'certain_timezone_at'
        :param lng: longitude of the point in degree (-180 to 180)
        :param lat: latitude in degree (90 to -90)
        :return: the timezone name of a matching polygon or None
        """
        lng, lat = rectify_coordinates(lng, lat)

        shortcut_id_x, shortcut_id_y = coord2shortcut(lng, lat)
        self.shortcuts_unique_id.seek(
            (180 * NR_SHORTCUTS_PER_LAT * NR_BYTES_H * shortcut_id_x + NR_BYTES_H * shortcut_id_y))
        try:
            # if there is just one possible zone in this shortcut instantly return its name
            return timezone_names[unpack(DTYPE_FORMAT_H, self.shortcuts_unique_id.read(NR_BYTES_H))[0]]
        except IndexError:
            possible_polygons = self.polygon_ids_of_shortcut(shortcut_id_x, shortcut_id_y)
            nr_possible_polygons = len(possible_polygons)
            if nr_possible_polygons == 0:
                return None
            if nr_possible_polygons == 1:
                # there is only one polygon in that area. return its timezone name without further checks
                return timezone_names[self.id_of(possible_polygons[0])]

            # create a list of all the timezone ids of all possible polygons
            ids = self.id_list(possible_polygons, nr_possible_polygons)
            # x = longitude  y = latitude  both converted to 8byte int
            x = coord2int(lng)
            y = coord2int(lat)

            # check until the point is included in one of the possible polygons
            for i in range(nr_possible_polygons):

                # when including the current polygon only polygons from the same zone remain,
                same_element = all_the_same(pointer=i, length=nr_possible_polygons, id_list=ids)
                if same_element != -1:
                    # return the name of that zone
                    return timezone_names[same_element]

                polygon_nr = possible_polygons[i]

                # get the boundaries of the polygon = (lng_max, lng_min, lat_max, lat_min)
                self.poly_max_values.seek(4 * NR_BYTES_I * polygon_nr)
                boundaries = self.fromfile(self.poly_max_values, dtype=DTYPE_FORMAT_SIGNED_I_NUMPY, count=4)
                # only run the expensive algorithm if the point is withing the boundaries
                if not (x > boundaries[0] or x < boundaries[1] or y > boundaries[2] or y < boundaries[3]):

                    outside_all_holes = True
                    # when the point is within a hole of the polygon, this timezone must not be returned
                    for hole_coordinates in self._holes_of_line(polygon_nr):
                        if inside_polygon(x, y, hole_coordinates):
                            outside_all_holes = False
                            break

                    if outside_all_holes:
                        if inside_polygon(x, y, self.coords_of(line=polygon_nr)):
                            # the point is included in this polygon. return its timezone name without further checks
                            return timezone_names[ids[i]]

            # the timezone name of the last polygon should always be returned
            # if no other polygon has been matched beforehand.
            raise ValueError('BUG: this statement should never be reached. Please open up an issue on Github!')

    def certain_timezone_at(self, *, lng, lat):
        """
        this function looks up in which polygon the point certainly is included
        this is much slower than 'timezone_at'!
        :param lng: longitude of the point in degree
        :param lat: latitude in degree
        :return: the timezone name of the polygon the point is included in or None
        """

        lng, lat = rectify_coordinates(lng, lat)
        shortcut_id_x, shortcut_id_y = coord2shortcut(lng, lat)
        possible_polygons = self.polygon_ids_of_shortcut(shortcut_id_x, shortcut_id_y)

        # x = longitude  y = latitude  both converted to 8byte int
        x = coord2int(lng)
        y = coord2int(lat)

        # check if the point is actually included in one of the polygons
        for polygon_nr in possible_polygons:

            # get boundaries
            self.poly_max_values.seek(4 * NR_BYTES_I * polygon_nr)
            boundaries = self.fromfile(self.poly_max_values, dtype=DTYPE_FORMAT_SIGNED_I_NUMPY, count=4)
            if not (x > boundaries[0] or x < boundaries[1] or y > boundaries[2] or y < boundaries[3]):

                outside_all_holes = True
                # when the point is within a hole of the polygon this timezone doesn't need to be checked
                for hole_coordinates in self._holes_of_line(polygon_nr):
                    if inside_polygon(x, y, hole_coordinates):
                        outside_all_holes = False
                        break

                if outside_all_holes:
                    if inside_polygon(x, y, self.coords_of(line=polygon_nr)):
                        return timezone_names[self.id_of(polygon_nr)]

        # no polygon has been matched
        return None


if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser(description='parse training parameters')
    parser.add_argument('lng', type=float, help='longitude to be queried')
    parser.add_argument('lat', type=float, help='latitude to be queried')
    parser.add_argument('-v', action='store_true', help='verbosity flag')
    parser.add_argument('-f', '--function', type=int, choices=[0, 1], default=0,
                        help='function to be called. 0: timezone_at(...) 1: certain_timezone_at(...)')

    # takes input from sys.argv
    parsed_args = parser.parse_args()
    tf = TimezoneFinder()
    functions = [tf.timezone_at, tf.certain_timezone_at]
    tz = functions[parsed_args.function](lng=parsed_args.lng, lat=parsed_args.lat)
    if parsed_args.v:
        print('Looking for TZ at lat=', parsed_args.lat, ' lng=', parsed_args.lng)
        print('Function:', ['timezone_at()', 'certain_timezone_at()'][parsed_args.function])
        print('Timezone=', tz)
    else:
        print(tz)
