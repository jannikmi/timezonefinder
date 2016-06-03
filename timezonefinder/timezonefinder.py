from __future__ import absolute_import, division, print_function, unicode_literals

from math import floor
from os.path import dirname, join
from struct import unpack

from numpy import array, empty, fromfile

from .timezone_names import timezone_names

try:
    import numba
except ImportError:
    numba = None

if numba is not None:
    from .helpers_numba import coord2int, distance_to_polygon, inside_polygon, all_the_same
else:
    from .helpers import coord2int, distance_to_polygon, inside_polygon, all_the_same


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
        self.nr_of_entries = unpack(b'!H', self.binary_file.read(2))[0]

        # set addresses
        # the address where the shortcut section starts (after all the polygons) this is 34 433 054
        self.shortcuts_start = unpack(b'!I', self.binary_file.read(4))[0]

        self.amount_of_holes = unpack(b'!H', self.binary_file.read(2))[0]

        self.hole_area_start = unpack(b'!I', self.binary_file.read(4))[0]

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
            related_line = unpack(b'!H', self.binary_file.read(2))[0]
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

    def id_of(self, line=0):
        # ids start at address 6. per line one unsigned 2byte int is used
        self.binary_file.seek((12 + 2 * line))
        return unpack(b'!H', self.binary_file.read(2))[0]

    def ids_of(self, iterable):

        id_array = empty(shape=len(iterable), dtype='>i1')

        i = 0
        for line_nr in iterable:
            self.binary_file.seek((12 + 2 * line_nr))
            id_array[i] = unpack(b'!H', self.binary_file.read(2))[0]
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

        nr_of_polygons = unpack(b'!H', self.binary_file.read(2))[0]

        self.binary_file.seek(self.first_shortcut_address + 1440 * x + 4 * y)
        self.binary_file.seek(unpack(b'!I', self.binary_file.read(4))[0])
        return fromfile(self.binary_file, dtype='>u2', count=nr_of_polygons)

    def polygons_of_shortcut(self, x=0, y=0):
        # get the address of the first entry in this shortcut
        # offset: 180 * number of shortcuts per lat degree * 2bytes = entries per column of x shortcuts
        # shortcuts are stored: (0,0) (0,1) (0,2)... (1,0)...
        self.binary_file.seek(self.shortcuts_start + 720 * x + 2 * y)

        nr_of_polygons = unpack(b'!H', self.binary_file.read(2))[0]

        self.binary_file.seek(self.first_shortcut_address + 1440 * x + 4 * y)
        self.binary_file.seek(unpack(b'!I', self.binary_file.read(4))[0])
        return fromfile(self.binary_file, dtype='>u2', count=nr_of_polygons)

    def coords_of(self, line=0):
        self.binary_file.seek((self.nr_val_start_address + 2 * line))
        nr_of_values = unpack(b'!H', self.binary_file.read(2))[0]

        self.binary_file.seek((self.adr_start_address + 4 * line))
        self.binary_file.seek(unpack(b'!I', self.binary_file.read(4))[0])

        # return array([fromfile(self.binary_file, dtype='>i8', count=nr_of_values),
        #               fromfile(self.binary_file, dtype='>i8', count=nr_of_values)])
        #
        return array([fromfile(self.binary_file, dtype='>i4', count=nr_of_values),
                      fromfile(self.binary_file, dtype='>i4', count=nr_of_values)])

    def _holes_of_line(self, line=0):
        try:
            amount_of_holes, hole_id = self.hole_registry[line]

            for i in range(amount_of_holes):
                self.binary_file.seek((self.nr_val_hole_address + 2 * hole_id))
                nr_of_values = unpack(b'!H', self.binary_file.read(2))[0]

                self.binary_file.seek((self.adr_hole_address + 4 * hole_id))
                self.binary_file.seek(unpack(b'!I', self.binary_file.read(4))[0])

                yield array([fromfile(self.binary_file, dtype='>i4', count=nr_of_values),
                             fromfile(self.binary_file, dtype='>i4', count=nr_of_values)])
                hole_id += 1

        except KeyError:
            return

    def closest_timezone_at(self, lng, lat, delta_degree=1):
        """
        This function searches for the closest polygon in the surrounding shortcuts.
        Make sure that the point does not lie within a polygon (for that case the algorithm is simply wrong!)
        Note that the algorithm won't find the closest polygon when it's on the 'other end of earth'
        (it can't search beyond the 180 deg lng border yet)
        this checks all the polygons within [delta_degree] degree lng and lat
        Keep in mind that x degrees lat are not the same distance apart than x degree lng!
        :param lng: longitude of the point in degree
        :param lat: latitude in degree
        :param delta_degree: the 'search radius' in degree
        :return: the timezone name of the closest found polygon or None
        """

        if lng > 180.0 or lng < -180.0 or lat > 90.0 or lat < -90.0:
            raise ValueError('The coordinates are out ouf bounds: (', lng, ',', lat, ')')

        # the maximum possible distance is pi = 3.14...
        min_distance = 4
        # transform point X into cartesian coordinates
        current_closest_id = None
        central_x_shortcut = int(floor((lng + 180)))
        central_y_shortcut = int(floor((90 - lat) * 2))

        polygon_nrs = []

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
                    if p not in polygon_nrs:
                        polygon_nrs.append(p)

        polygons_in_list = len(polygon_nrs)

        if polygons_in_list == 0:
            return None

        # initialize the list of ids
        ids = [self.id_of(x) for x in polygon_nrs]

        # if all the polygons in this shortcut belong to the same zone return it
        first_entry = ids[0]
        if ids.count(first_entry) == polygons_in_list:
            return timezone_names[first_entry]

        # stores which polygons have been checked yet
        already_checked = [False for i in range(polygons_in_list)]

        pointer = 0
        polygons_checked = 0

        while polygons_checked < polygons_in_list:

            # only check a polygon when its id is not the closest a the moment!
            if already_checked[pointer] or ids[pointer] == current_closest_id:
                # go to the next polygon
                polygons_checked += 1

            else:
                # this polygon has to be checked
                coords = self.coords_of(polygon_nrs[pointer])
                nr_points = len(coords[0])
                empty_array = empty([2, nr_points], dtype='f8')
                distance = distance_to_polygon(lng, lat, nr_points, coords, empty_array)

                already_checked[pointer] = True
                if distance < min_distance:
                    min_distance = distance
                    current_closest_id = ids[pointer]
                    # whole list has to be searched again!
                    polygons_checked = 1
            pointer = (pointer + 1) % polygons_in_list

        # the the whole list has been searched
        return timezone_names[current_closest_id]

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
        # TODO sort from least to most occurrences
        ids = [self.id_of(p) for p in possible_polygons]

        # otherwise check if the point is included for all the possible polygons
        for i in range(nr_possible_polygons):

            same_element = all_the_same(pointer=i, length=nr_possible_polygons, id_list=ids)
            if same_element != -1:
                return timezone_names[same_element]

            polygon_nr = possible_polygons[i]

            # get the boundaries of the polygon = (lng_max, lng_min, lat_max, lat_min)
            # self.binary_file.seek((self.bound_start_address + 32 * polygon_nr), )
            self.binary_file.seek((self.bound_start_address + 16 * polygon_nr), )
            boundaries = fromfile(self.binary_file, dtype='>i4', count=4)
            # only run the algorithm if it the point is withing the boundaries
            if not (x > boundaries[0] or x < boundaries[1] or y > boundaries[2] or y < boundaries[3]):

                outside_all_holes = True
                # when the point is within a hole of the polygon this timezone doesn't need to be checked
                for hole_coordinates in self._holes_of_line(polygon_nr):
                    if inside_polygon(x, y, hole_coordinates):
                        outside_all_holes = False
                        break

                if outside_all_holes:
                    if inside_polygon(x, y, self.coords_of(line=polygon_nr)):
                        return timezone_names[ids[i]]

        return None

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
            boundaries = fromfile(self.binary_file, dtype='>i4', count=4)
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
