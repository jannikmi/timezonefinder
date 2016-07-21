from __future__ import absolute_import, division, print_function, unicode_literals

from math import floor, radians
# from os import system
from os.path import dirname, join
from struct import unpack

from numpy import array, empty, fromfile

from .functional import kwargs_only
from .timezone_names import timezone_names

# later functions should be automatically compiled once on installation:
# try:
#     import compiled_numba_funcs
# except ImportError:
#     precompilation = None
#     try:
#         import numba
#     except ImportError:
#         numba = None
#
#     if numba is not None:
#         from .helpers_numba import coord2int, distance_to_polygon_exact, distance_to_polygon, inside_polygon, \
#             all_the_same
#     else:
#         from .helpers import coord2int, distance_to_polygon_exact, inside_polygon, all_the_same, distance_to_polygon

#
# try:
#     import numba
#
#     print('using numba version:', numba.__version__)
#
#     print('compiling the helpers ahead of time...')
#     # FIXME target architecture is wrong. because of old Numba version?
#     # TODO in this environment numba could not be available
#     system("python3 /Users/jannikmi/GitHub/timezonefinder/timezonefinder/helpers_numba.py")
#     try:
#         from compiled_helpers import coord2int, distance_to_polygon_exact, distance_to_polygon, inside_polygon, \
#             all_the_same
#
#         print('... worked!')
#
#     except ImportError:
#         from .helpers_numba import coord2int, distance_to_polygon_exact, distance_to_polygon, inside_polygon, \
#             all_the_same
#
#     print('... did not work!')
#
# except ImportError:
#     numba = None
#     from .helpers import coord2int, distance_to_polygon_exact, inside_polygon, all_the_same, distance_to_polygon
#

try:
    import numba
    from .helpers_numba import coord2int, distance_to_polygon_exact, distance_to_polygon, inside_polygon, all_the_same
except ImportError:
    numba = None
    from .helpers import coord2int, distance_to_polygon_exact, inside_polygon, all_the_same, distance_to_polygon


class TimezoneFinder:
    """
    This class lets you quickly find the timezone of a point on earth.
    It keeps the binary file with the timezonefinder open in reading mode to enable fast consequent access.
    In the file currently used there are two shortcuts stored per degree of latitude and one per degree of longitude
    (tests evaluated this to be the fastest setup when being used with numba)
    """

    def __init__(self):

        # open the file in binary reading mode
        self.binary_file = open(join(dirname(__file__), 'timezone_data.bin'), 'rb')

        # for more info on what is stored how in the .bin please read the comments in file_converter
        # read the first 2byte int (= number of polygons stored in the .bin)
        self.nr_of_entries = unpack(b'<H', self.binary_file.read(2))[0]

        # set addresses
        # the address where the shortcut section starts (after all the polygons) this is 34 433 054
        self.shortcuts_start = unpack(b'<I', self.binary_file.read(4))[0]

        self.amount_of_holes = unpack(b'<H', self.binary_file.read(2))[0]

        self.hole_area_start = unpack(b'<I', self.binary_file.read(4))[0]

        self.nr_val_start_address = 2 * self.nr_of_entries + 12
        self.adr_start_address = 4 * self.nr_of_entries + 12
        self.bound_start_address = 8 * self.nr_of_entries + 12
        # self.poly_start_address = 24 * self.nr_of_entries + 12
        self.first_shortcut_address = self.shortcuts_start + 259200

        self.nr_val_hole_address = self.hole_area_start + self.amount_of_holes * 2
        self.adr_hole_address = self.hole_area_start + self.amount_of_holes * 4
        # self.hole_data_start = self.hole_area_start + self.amount_of_holes * 8

        # for store for which polygons (how many) holes exits and the id of the first of those holes
        self.hole_registry = {}
        last_encountered_line_nr = 0
        first_hole_id = 0
        amount_of_holes = 0
        self.binary_file.seek(self.hole_area_start)
        for i in range(self.amount_of_holes):
            related_line = unpack(b'<H', self.binary_file.read(2))[0]
            # print(related_line)
            if related_line == last_encountered_line_nr:
                amount_of_holes += 1
            else:
                if i != 0:
                    # write an entry in the registry
                    self.hole_registry.update({
                        last_encountered_line_nr: (amount_of_holes, first_hole_id)
                    })

                last_encountered_line_nr = related_line
                first_hole_id = i
                amount_of_holes = 1

        # write the entry for the last hole(s) in the registry
        self.hole_registry.update({
            last_encountered_line_nr: (amount_of_holes, first_hole_id)
        })

    def __del__(self):
        self.binary_file.close()

    @staticmethod
    def using_numba():
        return (numba is not None)

    # TODO enable
    #  @staticmethod
    # def using_precompiled_funcs():
    #     return (precompilation is not None)

    def id_of(self, line=0):
        # ids start at address 6. per line one unsigned 2byte int is used
        self.binary_file.seek((12 + 2 * line))
        return unpack(b'<H', self.binary_file.read(2))[0]

    def ids_of(self, iterable):

        id_array = empty(shape=len(iterable), dtype='<i1')

        i = 0
        for line_nr in iterable:
            self.binary_file.seek((12 + 2 * line_nr))
            id_array[i] = unpack(b'<H', self.binary_file.read(2))[0]
            i += 1

        return id_array

    def shortcuts_of(self, lng=0.0, lat=0.0):
        # convert coords into shortcut
        x = int(floor((lng + 180)))
        y = int(floor((90 - lat) * 2))

        # get the address of the first entry in this shortcut
        # offset: 180 * number of shortcuts per lat degree * 2bytes = entries per column of x shortcuts
        # shortcuts are stored: (0,0) (0,1) (0,2)... (1,0)...
        self.binary_file.seek(self.shortcuts_start + 720 * x + 2 * y)

        nr_of_polygons = unpack(b'<H', self.binary_file.read(2))[0]

        self.binary_file.seek(self.first_shortcut_address + 1440 * x + 4 * y)
        self.binary_file.seek(unpack(b'<I', self.binary_file.read(4))[0])
        return fromfile(self.binary_file, dtype='<u2', count=nr_of_polygons)

    def polygons_of_shortcut(self, x=0, y=0):
        # get the address of the first entry in this shortcut
        # offset: 180 * number of shortcuts per lat degree * 2bytes = entries per column of x shortcuts
        # shortcuts are stored: (0,0) (0,1) (0,2)... (1,0)...
        self.binary_file.seek(self.shortcuts_start + 720 * x + 2 * y)

        nr_of_polygons = unpack(b'<H', self.binary_file.read(2))[0]

        self.binary_file.seek(self.first_shortcut_address + 1440 * x + 4 * y)
        self.binary_file.seek(unpack(b'<I', self.binary_file.read(4))[0])
        return fromfile(self.binary_file, dtype='<u2', count=nr_of_polygons)

    def coords_of(self, line=0):
        self.binary_file.seek((self.nr_val_start_address + 2 * line))
        nr_of_values = unpack(b'<H', self.binary_file.read(2))[0]

        self.binary_file.seek((self.adr_start_address + 4 * line))
        self.binary_file.seek(unpack(b'<I', self.binary_file.read(4))[0])

        # return array([fromfile(self.binary_file, dtype='<i8', count=nr_of_values),
        #               fromfile(self.binary_file, dtype='<i8', count=nr_of_values)])
        #
        return array([fromfile(self.binary_file, dtype='<i4', count=nr_of_values),
                      fromfile(self.binary_file, dtype='<i4', count=nr_of_values)])

    def _holes_of_line(self, line=0):
        try:
            amount_of_holes, hole_id = self.hole_registry[line]

            for i in range(amount_of_holes):
                self.binary_file.seek((self.nr_val_hole_address + 2 * hole_id))
                nr_of_values = unpack(b'<H', self.binary_file.read(2))[0]

                self.binary_file.seek((self.adr_hole_address + 4 * hole_id))
                self.binary_file.seek(unpack(b'<I', self.binary_file.read(4))[0])

                yield array([fromfile(self.binary_file, dtype='<i4', count=nr_of_values),
                             fromfile(self.binary_file, dtype='<i4', count=nr_of_values)])
                hole_id += 1

        except KeyError:
            return

    def compile_id_list(self, polygon_id_list, nr_of_polygons, dont_sort=False):
        """
        sorts the polygons_id list from least to most occurrences of the zone ids (->speed up)
        approx. 0.24% of all realistic points benefit from sorting (0.4% for random points)
        = percentage of sorting usage for 100k points
        in most of those cases there are only two types of zones (= entries in counted_zones) and one of them
        has only one entry. That means after checking one polygon timezone_at() already stops.
        Sorting only really makes sense for closest_timezone_at().
        :param polygon_id_list:
        :param nr_of_polygons: length of polygon_id_list
        :param dont_sort: if this is set to True, the sorting algorithms is skipped
        :return: sorted list of polygon_ids, sorted list of zone_ids, boolean: do all entries belong to the same zone
        """

        def all_equal(input_data):
            x = None
            for x in input_data:
                # first_val = x
                break
            for y in input_data:
                if x != y:
                    return False
            return True

        # print(polygon_id_list)
        # print(zone_id_list)
        zone_id_list = empty([nr_of_polygons], dtype='<u2', )
        if dont_sort:
            pointer_local = 0
            first_id = self.id_of(polygon_id_list[0])
            equal = True
            for polygon_id in polygon_id_list:
                zone_id = self.id_of(polygon_id)
                if zone_id != first_id:
                    equal = False
                zone_id_list[pointer_local] = zone_id
                pointer_local += 1

            return polygon_id_list, zone_id_list, equal

        counted_zones = {}
        pointer_local = 0
        for polygon_id in polygon_id_list:
            zone_id = self.id_of(polygon_id)
            zone_id_list[pointer_local] = zone_id
            pointer_local += 1
            try:
                counted_zones[zone_id] += 1
            except KeyError:
                counted_zones[zone_id] = 1
        # print(counted_zones)

        if len(counted_zones) == 1:
            return polygon_id_list, zone_id_list, True

        if all_equal(counted_zones.values()):
            return polygon_id_list, zone_id_list, False

        counted_zones_sorted = sorted(counted_zones.items(), key=lambda zone: zone[1])
        # print(counted_zones_sorted)

        sorted_polygon_id_list = empty([nr_of_polygons], dtype='<u2')
        sorted_zone_id_list = empty([nr_of_polygons], dtype='<u2')

        pointer_output = 0
        pointer_output2 = 0
        for zone_id, amount in counted_zones_sorted:
            # write all polygons from this zone in the new list
            pointer_local = 0
            detected_polygons = 0
            while detected_polygons < amount:
                if zone_id_list[pointer_local] == zone_id:
                    # the polygon at the pointer has the wanted zone_id
                    detected_polygons += 1
                    sorted_polygon_id_list[pointer_output] = polygon_id_list[pointer_local]
                    pointer_output += 1

                pointer_local += 1

            for pointer_local in range(amount):
                sorted_zone_id_list[pointer_output2] = zone_id
                pointer_output2 += 1

        # print(sorted_polygon_id_list)
        # print(sorted_zone_id_list)

        return sorted_polygon_id_list, sorted_zone_id_list, False

    @kwargs_only
    def closest_timezone_at(self, lng, lat, delta_degree=1, exact_computation=False, return_distances=False,
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
            empty_array = empty([2, nr_points], dtype='f8')
            return distance_to_polygon_exact(lng, lat, nr_points, coords, empty_array)

        def normal_routine(polygon_nr):
            coords = self.coords_of(polygon_nr)
            nr_points = len(coords[0])
            return distance_to_polygon(lng, lat, nr_points, coords)

        if lng > 180.0 or lng < -180.0 or lat > 90.0 or lat < -90.0:
            raise ValueError('The coordinates are out ouf bounds: (', lng, ',', lat, ')')

        if exact_computation:
            routine = exact_routine
        else:
            routine = normal_routine

        # the maximum possible distance is half the perimeter of earth pi * 12743km = 40,054.xxx km
        min_distance = 40100
        # transform point X into cartesian coordinates
        current_closest_id = None
        central_x_shortcut = int(floor((lng + 180)))
        central_y_shortcut = int(floor((90 - lat) * 2))

        lng = radians(lng)
        lat = radians(lat)

        possible_polygons = []

        # there are 2 shortcuts per 1 degree lat, so to cover 1 degree two shortcuts (rows) have to be checked
        # the highest shortcut is 0
        top = max(central_y_shortcut - 2 * delta_degree, 0)
        # the lowest shortcut is 360 (= 2 shortcuts per 1 degree lat)
        bottom = min(central_y_shortcut + 2 * delta_degree, 360)

        # the most left shortcut is 0
        left = max(central_x_shortcut - delta_degree, 0)
        # the most right shortcut is 360 (= 1 shortcuts per 1 degree lng)
        right = min(central_x_shortcut + delta_degree, 360)

        # select all the polygons from the surrounding shortcuts
        for x in range(left, right + 1, 1):
            for y in range(top, bottom + 1, 1):
                for p in self.polygons_of_shortcut(x, y):
                    if p not in possible_polygons:
                        possible_polygons.append(p)

        polygons_in_list = len(possible_polygons)

        if polygons_in_list == 0:
            return None

        # initialize the list of ids
        # TODO sorting doesn't give a bonus here?!
        possible_polygons, ids, zones_are_equal = self.compile_id_list(possible_polygons, polygons_in_list,
                                                                       dont_sort=True)

        # if all the polygons in this shortcut belong to the same zone return it
        if zones_are_equal:
            if not (return_distances or force_evaluation):
                return timezone_names[ids[0]]

        distances = [None for i in range(polygons_in_list)]
        pointer = 0
        if force_evaluation:
            for polygon_nr in possible_polygons:
                distance = routine(polygon_nr)
                distances[pointer] = distance
                if distance < min_distance:
                    min_distance = distance
                    current_closest_id = ids[pointer]
                pointer += 1

        else:
            # stores which polygons have been checked yet
            already_checked = [False for i in range(polygons_in_list)]
            polygons_checked = 0
            while polygons_checked < polygons_in_list:

                # only check a polygon when its id is not the closest a the moment!
                if already_checked[pointer] or ids[pointer] == current_closest_id:
                    # go to the next polygon
                    polygons_checked += 1

                else:
                    # this polygon has to be checked
                    distance = routine(possible_polygons[pointer])
                    distances[pointer] = distance

                    already_checked[pointer] = True
                    if distance < min_distance:
                        min_distance = distance
                        current_closest_id = ids[pointer]
                        # whole list has to be searched again!
                        polygons_checked = 1
                pointer = (pointer + 1) % polygons_in_list

        if return_distances:
            return timezone_names[current_closest_id], distances, [timezone_names[x] for x in ids]

        return timezone_names[current_closest_id]

    @kwargs_only
    def timezone_at(self, lng=0.0, lat=0.0):
        """
        this function looks up in which polygons the point could be included
        to speed things up there are shortcuts being used (stored in the binary file)
        especially for large polygons it is expensive to check if a point is really included,
        so certain simplifications are made and even when you get a hit the point might actually
        not be inside the polygon (for example when there is only one timezone nearby)
        if you want to make sure a point is really inside a timezone use 'certain_timezone_at'
        :param lng: longitude of the point in degree (-180 to 180)
        :param lat: latitude in degree (90 to -90)
        :return: the timezone name of the matching polygon or None
        """
        if lng > 180.0 or lng < -180.0 or lat > 90.0 or lat < -90.0:
            raise ValueError('The coordinates are out ouf bounds: ( %f, %f, )' % (lng, lat))

        possible_polygons = self.shortcuts_of(lng, lat)

        # x = longitude  y = latitude  both converted to 8byte int
        x = coord2int(lng)
        y = coord2int(lat)

        nr_possible_polygons = len(possible_polygons)

        if nr_possible_polygons == 0:
            return None

        if nr_possible_polygons == 1:
            return timezone_names[self.id_of(possible_polygons[0])]

        # initialize the list of ids
        # and sort possible_polygons from least to most occurrences of zone_id
        possible_polygons, ids, only_one_zone = self.compile_id_list(possible_polygons, nr_possible_polygons)
        if only_one_zone:
            return timezone_names[ids[0]]

        # otherwise check if the point is included for all the possible polygons
        for i in range(nr_possible_polygons):

            polygon_nr = possible_polygons[i]

            # get the boundaries of the polygon = (lng_max, lng_min, lat_max, lat_min)
            self.binary_file.seek((self.bound_start_address + 16 * polygon_nr), )
            boundaries = fromfile(self.binary_file, dtype='<i4', count=4)
            # only run the expensive algorithm if the point is withing the boundaries
            if not (x > boundaries[0] or x < boundaries[1] or y > boundaries[2] or y < boundaries[3]):

                outside_all_holes = True
                # when the point is within a hole of the polygon, this timezone doesn't need to be checked
                for hole_coordinates in self._holes_of_line(polygon_nr):
                    if inside_polygon(x, y, hole_coordinates):
                        outside_all_holes = False
                        break

                if outside_all_holes:
                    if inside_polygon(x, y, self.coords_of(line=polygon_nr)):
                        return timezone_names[ids[i]]

            # when after the current polygon only polygons from the same zone appear, return this zone
            same_element = all_the_same(pointer=i + 1, length=nr_possible_polygons, id_list=ids)
            if same_element != -1:
                return timezone_names[same_element]

        return None

    @kwargs_only
    def certain_timezone_at(self, lng=0.0, lat=0.0):
        """
        this function looks up in which polygon the point certainly is included
        this is much slower than 'timezone_at'!
        :param lng: longitude of the point in degree
        :param lat: latitude in degree
        :return: the timezone name of the polygon the point is included in or None
        """

        if lng > 180.0 or lng < -180.0 or lat > 90.0 or lat < -90.0:
            raise ValueError('The coordinates are out ouf bounds: (', lng, ',', lat, ')')

        possible_polygons = self.shortcuts_of(lng, lat)

        # x = longitude  y = latitude  both converted to 8byte int
        x = coord2int(lng)
        y = coord2int(lat)

        for polygon_nr in possible_polygons:

            # get boundaries
            self.binary_file.seek((self.bound_start_address + 16 * polygon_nr), )
            boundaries = fromfile(self.binary_file, dtype='<i4', count=4)
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

        return None
