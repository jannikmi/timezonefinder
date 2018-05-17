from __future__ import absolute_import, division, print_function, unicode_literals

import json
from datetime import datetime
from math import ceil, floor
from os.path import abspath, join, pardir
from struct import pack

from six.moves import range, zip

# keep in mind: the fater numba optimized helper fct. cannot be used here,
# because numpy classes are not being used at this stage yet!
from .helpers import TIMEZONE_NAMES_FILE, coord2int, inside_polygon, int2coord

# from helpers import coord2int, inside_polygon, int2coord, TIMEZONE_NAMES_FILE

# import sys
# from os.path import dirname
#
# sys.path.insert(0, dirname(__file__))
# from helpers import coord2int, int2coord, inside_polygon


"""
USE INSTRUCTIONS:

- download the latest timezones.geojson.zip file from github.com/evansiroky/timezone-boundary-builder
- unzip and place the combined.json inside this timezonefinder folder
- run this file_converter.py as a script until the compilation of the binary files is completed.


IMPORTANT: all coordinates (floats) are being converted to int32 (multiplied by 10^7). This makes computations faster
and it takes lot less space, without loosing too much accuracy (min accuracy (=at the equator) is still 1cm !)

B = unsigned char (1byte = 8bit Integer)
H = unsigned short (2 byte integer)
I = unsigned 4byte integer
i = signed 4byte integer


Binaries being written:

[POLYGONS:] there are approx. 1k Polygons (evansiroky/timezone-boundary-builder 2017a)
poly_zone_ids: the related zone_id for every polygon ('<H')
poly_coord_amount: the amount of coordinates in every polygon ('<I')
poly_adr2data: address in poly_data.bin where data for every polygon starts ('<I')
poly_max_values: boundaries for every polygon ('<iiii': xmax, xmin, ymax, ymin)
poly_data: coordinates for every polygon (multiple times '<i') (for every polygon first all x then all y values!)
poly_nr2zone_id: the polygon number of the first polygon from every zone('<H')

[HOLES:] number of holes (162 evansiroky/timezone-boundary-builder 2018d)
hole_poly_ids: the related polygon_nr (=id) for every hole ('<H')
hole_coord_amount: the amount of coordinates in every hole ('<H')
hole_adr2data: address in hole_data.bin where data for every hole starts ('<I')
hole_data: coordinates for every hole (multiple times '<i')

[SHORTCUTS:] the surface of the world is split up into a grid of shortcut rectangles.
-> there are a total of 360 * NR_SHORTCUTS_PER_LNG * 180 * NR_SHORTCUTS_PER_LAT shortcuts
shortcut here means storing for every cell in a grid of the world map which polygons are located in that cell
they can therefore be used to drastically reduce the amount of polygons which need to be checked in order to
decide which timezone a point is located in.

the list of polygon ids in each shortcut is sorted after freq. of appearance of their zone id
this is critical for ruling out zones faster (as soon as just polygons of one zone are left this zone can be returned)

shortcuts_entry_amount: the amount of polygons for every shortcut ('<H')
shortcuts_adr2data: address in shortcut_data.bin where data for every shortcut starts ('<I')
shortcuts_data: polygon numbers (ids) for every shortcut (multiple times '<H')
shortcuts_unique_id: the zone id if only polygons from one zone are present,
                     a high number (with no corresponding zone) if not ('<H').
                     the majority of zones either have no polygons at all (sea) or just one zone.
                     this zone then can be instantly returned without actually testing polygons.

also stored extra binary if only one zone (to directly return that zone without checking)



shortcut statistics: (data version 2018d)
highest entry amount is 30
frequencies of entry amounts (from 0 to max entries):
[89768, 32917, 6217, 617, 59, 11, 4, 1, 2, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1]
relative accumulated frequencies [%]:
[69.27, 94.66, 99.46, 99.94, 99.98, 99.99, 99.99, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0,
    100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0]
[30.73, 5.34, 0.54, 0.06, 0.02, 0.01, 0.01, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
69.27 % of all shortcuts are empty

highest amount of different zones in one shortcut is 7
frequencies of entry amounts (from 0 to max):
[89768, 33199, 5999, 593, 35, 4, 1, 1]
relative accumulated frequencies [%]:
[69.27, 94.88, 99.51, 99.97, 100.0, 100.0, 100.0, 100.0]
[30.73, 5.12, 0.49, 0.03, 0.0, 0.0, 0.0, 0.0]
--------------------------------

The number of filled shortcut zones are: 39832 (= 30.73 % of all shortcuts)
The number of polygons is: 1018
The number of floats in all the polygons is (2 per point): 10434626

the polygon data makes up 97.2 % of the data
the shortcuts make up 2.03 % of the data
holes make up 0.77 % of the data
"""

INPUT_JSON_FILE_NAME = 'combined.json'

# in debugging mode parse only some polygons
DEBUG = False
DEBUG_POLY_STOP = 20

# ATTENTION: Don't change these settings or timezonefinder wont work!
# different setups of shortcuts are not supported, because then addresses in the .bin
# need to be calculated depending on how many shortcuts are being used.
# number of shortcuts per longitude
NR_SHORTCUTS_PER_LNG = 1
# shortcuts per latitude
NR_SHORTCUTS_PER_LAT = 2

INVALID_ZONE_ID = 65535  # highest possible with H (2 byte integer)

nr_of_lines = -1
all_tz_names = []
poly_zone_ids = []
all_boundaries = []
all_coords = []
all_lengths = []
amount_of_holes = 0
polynrs_of_holes = []
all_holes = []
all_hole_lengths = []
list_of_pointers = []
poly_nr2zone_id = []
shortcuts = {}


def x_shortcut(lng):
    # higher (=lng) means higher x shortcut!!! 0 (-180deg lng) -> 360 (180deg)
    # if lng < -180 or lng >= 180:
    # raise ValueError('longitude out of bounds', lng)
    return floor((lng + 180) * NR_SHORTCUTS_PER_LNG)


def y_shortcut(lat):
    # lower y (=lat) means higher y shortcut!!! 0 (90deg lat) -> 180 (-90deg)
    # if lat < -90 or lat >= 90:
    # raise ValueError('this latitude is out of bounds', lat)
    return floor((90 - lat) * NR_SHORTCUTS_PER_LAT)


def big_zone(xmax, xmin, ymax, ymin):
    # returns True if a zone with those boundaries could have more than 4 shortcuts
    return xmax - xmin > 2 / NR_SHORTCUTS_PER_LNG and ymax - ymin > 2 / NR_SHORTCUTS_PER_LAT


def percent(numerator, denominator):
    return round((numerator / denominator) * 100, 2)


def accumulated_frequency(int_list):
    out = []
    total = sum(int_list)
    acc = 0
    for e in int_list:
        acc += e
        out.append(percent(acc, total))

    return out


def ints_of(line=0):
    x_coords, y_coords = all_coords[line]
    return [coord2int(x) for x in x_coords], [coord2int(x) for x in y_coords]


def contained(x, y, x_coords, y_coords):
    return inside_polygon(x, y, [x_coords, y_coords])


def unique(iterable):
    out = []
    for i in iterable:
        if i not in out:
            out.append(i)
    return out


def point_between(p1, p2):
    return p1[0] + (p2[0] - p1[0]) / 2, p1[1] + (p2[1] - p1[1]) / 2


def get_shortcuts(x, y):
    result = shortcuts.get((x, y))
    if result is None:
        return []
    else:
        return result


def _polygons(id_list):
    for i in id_list:
        yield all_coords[i]


def not_empty(iterable):
    for i in iterable:
        return True
    return False


def polys_of_one_zone():
    for i in range(len(timezone_names)):
        start = poly_nr2zone_id[i]
        end = poly_nr2zone_id[i + 1]
        yield list(range(start, end))


def replace_entry(iterable, entry, substitute):
    for i in range(len(iterable)):
        if iterable[i] == entry:
            iterable[i] = substitute
    return iterable


def _holes_in_poly(poly_nr):
    i = 0
    for nr in polynrs_of_holes:
        if nr == poly_nr:
            yield all_holes[i]
        i += 1


def parse_polygons_from_json(path=INPUT_JSON_FILE_NAME):
    global amount_of_holes
    global nr_of_lines
    global poly_zone_ids

    print('Parsing data from {}\nthis could take a while...\n'.format(path))
    tz_list = json.loads(open(path).read()).get('features')
    # this counter just counts polygons, not holes!
    polygon_counter = 0
    current_zone_id = 0
    print('holes found at: (poly_nr zone_name)')
    for tz_dict in tz_list:
        if DEBUG and polygon_counter > DEBUG_POLY_STOP:
            break

        tz_name = tz_dict.get('properties').get("tzid")
        # print(tz_name)
        all_tz_names.append(tz_name)
        geometry = tz_dict.get("geometry")
        if geometry.get('type') == 'MultiPolygon':
            # depth is 4
            multipolygon = geometry.get("coordinates")
        else:
            # depth is 3 (only one polygon, possibly with holes!)
            multipolygon = [geometry.get("coordinates")]
        # multipolygon has depth 4
        # assert depth_of_array(multipolygon) == 4
        for poly_with_hole in multipolygon:
            # assert len(poly_with_hole) > 0
            # the first entry is polygon
            x_coords, y_coords = list(zip(*poly_with_hole.pop(0)))
            # IMPORTANT: do not use the last value (is equal to the first)!
            x_coords = list(x_coords)
            y_coords = list(y_coords)
            x_coords.pop(-1)
            y_coords.pop(-1)
            all_coords.append((x_coords, y_coords))
            # assert len(x_coords) > 0
            all_lengths.append(len(x_coords))
            all_boundaries.append((max(x_coords), min(x_coords), max(y_coords), min(y_coords)))
            poly_zone_ids.append(current_zone_id)

            # everything else is interpreted as a hole!
            for hole in poly_with_hole:
                print(polygon_counter, tz_name)
                # keep track of how many holes there are
                amount_of_holes += 1
                polynrs_of_holes.append(polygon_counter)
                x_coords, y_coords = list(zip(*hole))
                # IMPORTANT: do not use the last value (is equal to the first)!
                x_coords = list(x_coords)
                y_coords = list(y_coords)
                x_coords.pop(-1)
                y_coords.pop(-1)
                all_holes.append((x_coords, y_coords))
                all_hole_lengths.append(len(x_coords))

            polygon_counter += 1

        current_zone_id += 1

    if max(all_lengths) >= 2 ** 32:
        # 34621 in tz_world 2016d (small enough for int16)
        # 137592 in evansiroky/timezone-boundary-builder 2017a (now int32 is needed!)
        raise ValueError('amount of coords cannot be represented by int32 in poly_coord_amount.bin:',
                         max(all_lengths))

    if max(all_hole_lengths) >= 2 ** 16:
        # 21071 in evansiroky/timezone-boundary-builder 2017a (int16 still enough)
        raise ValueError('amount of coords cannot be represented by short (int16) in hole_coord_amount.bin:',
                         max(all_hole_lengths))

    nr_of_lines = len(all_lengths)
    if polygon_counter != nr_of_lines:
        raise ValueError('polygon counter and entry number in all_length is different:', polygon_counter, nr_of_lines)

    if nr_of_lines >= 2 ** 16:
        # 24k in tz_world 2016d
        # 1022 in evansiroky/timezone-boundary-builder 2017a
        raise ValueError('polygon id cannot be encoded as short (int16) in hole_coord_amount.bin! there are',
                         nr_of_lines, 'polygons')

    if poly_zone_ids[-1] > 2 ** 16:
        # 420 different zones in evansiroky/timezone-boundary-builder 2017a
        # used in shortcuts_unique_id and poly_zone_ids
        raise ValueError('zone id cannot be encoded as char (int8). the last id is',
                         poly_zone_ids[-1])

    if 0 in all_lengths:
        raise ValueError()

    print('... parsing done.')
    print('maximal amount of coordinates in one polygon:', max(all_lengths))
    print('amount_of_holes:', amount_of_holes)
    print('amount of polygons:', nr_of_lines)
    print('\n')


def update_zone_names(path=TIMEZONE_NAMES_FILE):
    global poly_zone_ids
    global list_of_pointers
    global all_boundaries
    global all_coords
    global all_lengths
    global polynrs_of_holes
    print('updating the zone names in {} now...'.format(path))
    # pickle the zone names (python array)
    with open(abspath(path), 'w') as f:
        f.write(json.dumps(all_tz_names))
    print('...Done.\n\nComputing where zones start and end...')
    i = 0
    last_id = -1
    for zone_id in poly_zone_ids:
        if zone_id != last_id:
            poly_nr2zone_id.append(i)
            if zone_id < last_id:
                raise ValueError()
            last_id = zone_id
        i += 1
    poly_nr2zone_id.append(i)
    print('...Done.\n')


def compile_binaries():
    global nr_of_lines
    global shortcuts

    def print_shortcut_statistics():
        frequencies = []
        max_val = max(*nr_of_entries_in_shortcut)
        print('shortcut statistics:')
        print('highest entry amount is', max_val)
        while max_val >= 0:
            frequencies.append(nr_of_entries_in_shortcut.count(max_val))
            max_val -= 1

        frequencies.reverse()
        print('frequencies of entry amounts (from 0 to max entries):')
        print(frequencies)
        empty_shortcuts = frequencies[0]
        print('relative accumulated frequencies [%]:')
        acc = accumulated_frequency(frequencies)
        print(acc)
        print([round(100 - x, 2) for x in acc])
        print(percent(empty_shortcuts, amount_of_shortcuts), '% of all shortcuts are empty\n')

        amount_of_different_zones = []
        for entry in shortcut_entries:
            registered_zone_ids = []
            for polygon_nr in entry:
                id = poly_zone_ids[polygon_nr]
                if id not in registered_zone_ids:
                    registered_zone_ids.append(id)

            amount_of_different_zones.append(len(registered_zone_ids))

        frequencies = []
        max_val = max(*amount_of_different_zones)
        print('highest amount of different zones in one shortcut is', max_val)
        while max_val >= 1:
            frequencies.append(amount_of_different_zones.count(max_val))
            max_val -= 1
        # show the proper amount of shortcuts with 0 zones (=nr of empty shortcuts)
        frequencies.append(empty_shortcuts)
        frequencies.reverse()
        print('frequencies of entry amounts (from 0 to max):')
        print(frequencies)
        print('relative accumulated frequencies [%]:')
        acc = accumulated_frequency(frequencies)
        print(acc)
        print([round(100 - x, 2) for x in acc])
        print('--------------------------------\n')

    def included_shortcut_row_nrs(max_lat, min_lat):
        return list(range(y_shortcut(max_lat), y_shortcut(min_lat) + 1))

    def included_shortcut_column_nrs(max_lng, min_lng):
        return list(range(x_shortcut(min_lng), x_shortcut(max_lng) + 1))

    def longitudes_to_check(max_lng, min_lng):
        output_list = []
        step = 1 / NR_SHORTCUTS_PER_LNG
        current = ceil(min_lng * NR_SHORTCUTS_PER_LNG) / NR_SHORTCUTS_PER_LNG
        end = floor(max_lng * NR_SHORTCUTS_PER_LNG) / NR_SHORTCUTS_PER_LNG
        while current < end:
            output_list.append(current)
            current += step

        output_list.append(end)
        return output_list

    def latitudes_to_check(max_lat, min_lat):
        output_list = []
        step = 1 / NR_SHORTCUTS_PER_LAT
        current = ceil(min_lat * NR_SHORTCUTS_PER_LAT) / NR_SHORTCUTS_PER_LAT
        end = floor(max_lat * NR_SHORTCUTS_PER_LAT) / NR_SHORTCUTS_PER_LAT
        while current < end:
            output_list.append(current)
            current += step

        output_list.append(end)
        return output_list

    def compute_x_intersection(y, x1, x2, y1, y2):
        """returns the x intersection from a horizontal line in y with the line from x1,y1 to x1,y2
        """
        delta_y = y2 - y1
        if delta_y == 0:
            return x1
        return ((y - y1) * (x2 - x1) / delta_y) + x1

    def compute_y_intersection(x, x1, x2, y1, y2):
        """returns the y intersection from a vertical line in x with the line from x1,y1 to x1,y2
        """
        delta_x = x2 - x1
        if delta_x == 0:
            return x1
        return ((x - x1) * (y2 - y1) / delta_x) + y1

    def x_intersections(y, x_coords, y_coords):
        intersects = []
        for i in range(len(y_coords) - 1):
            iplus1 = i + 1
            if y_coords[i] <= y:
                # print('Y1<=y')
                if y_coords[iplus1] > y:
                    # this was a crossing. compute the intersect
                    # print('Y2>y')
                    intersects.append(
                        compute_x_intersection(y, x_coords[i], x_coords[iplus1], y_coords[i], y_coords[iplus1]))
            else:
                # print('Y1>y')
                if y_coords[iplus1] <= y:
                    # this was a crossing. compute the intersect
                    # print('Y2<=y')
                    intersects.append(compute_x_intersection(y, x_coords[i], x_coords[iplus1], y_coords[i],
                                                             y_coords[iplus1]))
        return intersects

    def y_intersections(x, x_coords, y_coords):

        intersects = []
        for i in range(len(y_coords) - 1):
            iplus1 = i + 1
            if x_coords[i] <= x:
                if x_coords[iplus1] > x:
                    # this was a crossing. compute the intersect
                    intersects.append(
                        compute_y_intersection(x, x_coords[i], x_coords[iplus1], y_coords[i], y_coords[iplus1]))
            else:
                if x_coords[iplus1] <= x:
                    # this was a crossing. compute the intersect
                    intersects.append(compute_y_intersection(x, x_coords[i], x_coords[iplus1], y_coords[i],
                                                             y_coords[iplus1]))
        return intersects

    def compute_exact_shortcuts(xmax, xmin, ymax, ymin, line):
        shortcuts_for_line = set()

        # x_longs = binary_reader.x_coords_of(line)
        x_longs, y_longs = ints_of(line)

        # y_longs = binary_reader.y_coords_of(line)
        y_longs.append(y_longs[0])
        x_longs.append(x_longs[0])

        step = 1 / NR_SHORTCUTS_PER_LAT
        # print('checking the latitudes')
        for lat in latitudes_to_check(ymax, ymin):
            # print(lat)
            # print(coordinate_to_longlong(lat))
            # print(y_longs)
            # print(x_intersections(coordinate_to_longlong(lat), x_longs, y_longs))
            # raise ValueError
            intersects = sorted([int2coord(x) for x in
                                 x_intersections(coord2int(lat), x_longs, y_longs)])
            # print(intersects)

            nr_of_intersects = len(intersects)
            if nr_of_intersects % 2 != 0:
                raise ValueError('an uneven number of intersections has been accounted')

            for i in range(0, nr_of_intersects, 2):
                possible_longitudes = []
                # collect all the zones between two intersections [in,out,in,out,...]
                iplus = i + 1
                intersection_in = intersects[i]
                intersection_out = intersects[iplus]
                if intersection_in == intersection_out:
                    # the polygon has a point exactly on the border of a shortcut zone here!
                    # only select the top shortcut if it is actually inside the polygon (point a little up is inside)
                    if contained(coord2int(intersection_in), coord2int(lat) + 1, x_longs,
                                 y_longs):
                        shortcuts_for_line.add((x_shortcut(intersection_in), y_shortcut(lat) - 1))
                    # the bottom shortcut is always selected
                    shortcuts_for_line.add((x_shortcut(intersection_in), y_shortcut(lat)))

                else:
                    # add all the shortcuts for the whole found area of intersection
                    possible_y_shortcut = y_shortcut(lat)

                    # both shortcuts should only be selected when the polygon doesnt stays on the border
                    middle = intersection_in + (intersection_out - intersection_in) / 2
                    if contained(coord2int(middle), coord2int(lat) + 1, x_longs,
                                 y_longs):
                        while intersection_in < intersection_out:
                            possible_longitudes.append(intersection_in)
                            intersection_in += step

                        possible_longitudes.append(intersection_out)

                        # the shortcut above and below of the intersection should be selected!
                        possible_y_shortcut_min1 = possible_y_shortcut - 1
                        for possible_x_coord in possible_longitudes:
                            shortcuts_for_line.add((x_shortcut(possible_x_coord), possible_y_shortcut))
                            shortcuts_for_line.add((x_shortcut(possible_x_coord), possible_y_shortcut_min1))
                    else:
                        # polygon does not cross the border!
                        while intersection_in < intersection_out:
                            possible_longitudes.append(intersection_in)
                            intersection_in += step

                        possible_longitudes.append(intersection_out)

                        # only the shortcut above of the intersection should be selected!
                        for possible_x_coord in possible_longitudes:
                            shortcuts_for_line.add((x_shortcut(possible_x_coord), possible_y_shortcut))

        # print('now all the longitudes to check')
        # same procedure horizontally
        step = 1 / NR_SHORTCUTS_PER_LAT
        for lng in longitudes_to_check(xmax, xmin):
            # print(lng)
            # print(coordinate_to_longlong(lng))
            # print(x_longs)
            # print(x_intersections(coordinate_to_longlong(lng), x_longs, y_longs))
            intersects = sorted([int2coord(y) for y in
                                 y_intersections(coord2int(lng), x_longs, y_longs)])
            # print(intersects)

            nr_of_intersects = len(intersects)
            if nr_of_intersects % 2 != 0:
                raise ValueError('an uneven number of intersections has been accounted')

            possible_latitudes = []
            for i in range(0, nr_of_intersects, 2):
                # collect all the zones between two intersections [in,out,in,out,...]
                iplus = i + 1
                intersection_in = intersects[i]
                intersection_out = intersects[iplus]
                if intersection_in == intersection_out:
                    # the polygon has a point exactly on the border of a shortcut here!
                    # only select the left shortcut if it is actually inside the polygon (point a little left is inside)
                    if contained(coord2int(lng) - 1, coord2int(intersection_in), x_longs,
                                 y_longs):
                        shortcuts_for_line.add((x_shortcut(lng) - 1, y_shortcut(intersection_in)))
                    # the right shortcut is always selected
                    shortcuts_for_line.add((x_shortcut(lng), y_shortcut(intersection_in)))

                else:
                    # add all the shortcuts for the whole found area of intersection
                    possible_x_shortcut = x_shortcut(lng)

                    # both shortcuts should only be selected when the polygon doesnt stays on the border
                    middle = intersection_in + (intersection_out - intersection_in) / 2
                    if contained(coord2int(lng) - 1, coord2int(middle), x_longs,
                                 y_longs):
                        while intersection_in < intersection_out:
                            possible_latitudes.append(intersection_in)
                            intersection_in += step

                        possible_latitudes.append(intersection_out)

                        # both shortcuts right and left of the intersection should be selected!
                        possible_x_shortcut_min1 = possible_x_shortcut - 1
                        for possible_latitude in possible_latitudes:
                            shortcuts_for_line.add((possible_x_shortcut, y_shortcut(possible_latitude)))
                            shortcuts_for_line.add((possible_x_shortcut_min1, y_shortcut(possible_latitude)))

                    else:
                        while intersection_in < intersection_out:
                            possible_latitudes.append(intersection_in)
                            intersection_in += step
                        # only the shortcut right of the intersection should be selected!
                        possible_latitudes.append(intersection_out)

                        for possible_latitude in possible_latitudes:
                            shortcuts_for_line.add((possible_x_shortcut, y_shortcut(possible_latitude)))

        return shortcuts_for_line

    def construct_shortcuts():
        print('building shortucts...')
        print('currently at polygon nr:')
        line = 0
        for xmax, xmin, ymax, ymin in all_boundaries:
            # xmax, xmin, ymax, ymin = boundaries_of(line=line)
            if line % 100 == 0:
                print(line)
                # print([xmax, xmin, ymax, ymin])

            column_nrs = included_shortcut_column_nrs(xmax, xmin)
            row_nrs = included_shortcut_row_nrs(ymax, ymin)

            if big_zone(xmax, xmin, ymax, ymin):

                # print('line ' + str(line))
                # print('This is a big zone! computing exact shortcuts')
                # print('Nr of entries before')
                # print(len(column_nrs) * len(row_nrs))
                # print('columns and rows before optimisation:')
                # print(column_nrs)
                # print(row_nrs)
                # print(ints_of(line))

                # This is a big zone! compute exact shortcuts with the whole polygon points
                shortcuts_for_line = compute_exact_shortcuts(xmax, xmin, ymax, ymin, line)
                # n += len(shortcuts_for_line)

                min_x_shortcut = column_nrs[0]
                max_x_shortcut = column_nrs[-1]
                min_y_shortcut = row_nrs[0]
                max_y_shortcut = row_nrs[-1]
                shortcuts_to_remove = []

                # remove shortcuts from outside the possible/valid area
                for x, y in shortcuts_for_line:
                    if x < min_x_shortcut or x > max_x_shortcut or y < min_y_shortcut or y > max_y_shortcut:
                        shortcuts_to_remove.append((x, y))

                for s in shortcuts_to_remove:
                    shortcuts_for_line.remove(s)

                # print('and after:')
                # print(len(shortcuts_for_line))
                # print(shortcuts_for_line)
                # column_nrs_after = set()
                # row_nrs_after = set()
                # for x, y in shortcuts_for_line:
                #     column_nrs_after.add(x)
                #     row_nrs_after.add(y)
                # print(column_nrs_after)
                # print(row_nrs_after)
                # print(shortcuts_for_line)

                if len(shortcuts_for_line) > len(column_nrs) * len(row_nrs):
                    raise ValueError(
                        'there are more shortcuts than before now. there is something wrong with the algorithm!')
                if len(shortcuts_for_line) < 3:
                    raise ValueError('algorithm not valid! less than 3 zones detected (should be at least 3)')

            else:
                shortcuts_for_line = []
                for column_nr in column_nrs:
                    for row_nr in row_nrs:
                        shortcuts_for_line.append((column_nr, row_nr))
                        # print(shortcuts_for_line)

            for shortcut in shortcuts_for_line:
                shortcuts[shortcut] = shortcuts.get(shortcut, []) + [line]

            line += 1
            # print('collected entries:')
            # print(n)

    start_time = datetime.now()
    construct_shortcuts()
    end_time = datetime.now()
    print('calculating the shortcuts took:', end_time - start_time, '\n')

    nr_of_floats = 2 * sum(all_lengths)

    # write number of entries in shortcut field (x,y)
    nr_of_entries_in_shortcut = []
    shortcut_entries = []
    amount_filled_shortcuts = 0

    def sort_poly_shortcut(poly_nrs):
        # TODO write test
        # the list of polygon ids in each shortcut is sorted after freq. of appearance of their zone id
        # this is critical for ruling out zones faster
        # (as soon as just polygons of one zone are left this zone can be returned)
        # only around 5% of all shortcuts include polygons from more than one zone
        # in most of those cases there are only two types of zones (= entries in counted_zones) and one of them
        # has only one entry (important to check the zone with one entry first!).
        polygon_ids = [poly_zone_ids[poly_nr] for poly_nr in poly_nrs]
        id_freq = [polygon_ids.count(id) for id in polygon_ids]
        zipped = list(zip(poly_nrs, polygon_ids, id_freq))
        # also make sure polygons with the same zone freq. are ordered after their zone id
        # (polygons from different zones should not get mixed up)
        sort = sorted((sorted(zipped, key=lambda x: x[1])), key=lambda x: x[2])
        return [x[0] for x in sort]  # take only the polygon nrs

    # count how many shortcut addresses will be written:
    # flatten out the shortcuts in one list in the order they are going to be written inside the polygon file
    for x in range(360 * NR_SHORTCUTS_PER_LNG):
        for y in range(180 * NR_SHORTCUTS_PER_LAT):
            try:
                shortcuts_this_entry = shortcuts[(x, y)]
                shortcut_entries.append(sort_poly_shortcut(shortcuts_this_entry))
                amount_filled_shortcuts += 1
                nr_of_entries_in_shortcut.append(len(shortcuts_this_entry))
                # print((x,y,this_lines_shortcuts))
            except KeyError:
                nr_of_entries_in_shortcut.append(0)

    amount_of_shortcuts = len(nr_of_entries_in_shortcut)
    print_shortcut_statistics()

    if amount_of_shortcuts != 64800 * NR_SHORTCUTS_PER_LNG * NR_SHORTCUTS_PER_LAT:
        print(amount_of_shortcuts)
        raise ValueError('this number of shortcut zones is wrong')

    print('The number of filled shortcut zones are:', amount_filled_shortcuts, '(=',
          round((amount_filled_shortcuts / amount_of_shortcuts) * 100, 2), '% of all shortcuts)')

    # for every shortcut <H and <I is written (nr of entries and address)
    shortcut_space = 360 * NR_SHORTCUTS_PER_LNG * 180 * NR_SHORTCUTS_PER_LAT * 6
    for nr in nr_of_entries_in_shortcut:
        # every line in every shortcut takes up 2bytes
        shortcut_space += 2 * nr

    print('The number of polygons is:', nr_of_lines)
    print('The number of floats in all the polygons is (2 per point):', nr_of_floats)

    path = 'poly_nr2zone_id.bin'
    print('writing file "', path, '"')
    output_file = open(path, 'wb')
    for zone_id in poly_nr2zone_id:
        output_file.write(pack(b'<H', zone_id))
    output_file.close()

    print('Done\n')
    # write zone_ids
    path = 'poly_zone_ids.bin'
    print('writing file "', path, '"')
    output_file = open(path, 'wb')
    for zone_id in poly_zone_ids:
        output_file.write(pack(b'<H', zone_id))
    output_file.close()

    # write boundary_data
    path = 'poly_max_values.bin'
    print('writing file "', path, '"')
    output_file = open(path, 'wb')
    for xmax, xmin, ymax, ymin in all_boundaries:
        output_file.write(pack(b'<iiii', coord2int(xmax), coord2int(xmin), coord2int(ymax), coord2int(ymin)))
    output_file.close()

    # write polygon_data, addresses and number of values
    path = 'poly_data.bin'
    print('writing file "', path, '"')
    output_file = open(path, 'wb')
    addresses = []
    i = 0
    for x_coords, y_coords in all_coords:
        addresses.append(output_file.tell())
        if all_lengths[i] != len(x_coords):
            raise ValueError('x_coords do not have the expected length!', all_lengths[i], len(x_coords))
        for x in x_coords:
            output_file.write(pack(b'<i', coord2int(x)))
        for y in y_coords:
            output_file.write(pack(b'<i', coord2int(y)))
        i += 1
    output_file.close()

    path = 'poly_adr2data.bin'
    print('writing file "', path, '"')
    output_file = open(path, 'wb')
    for adr in addresses:
        output_file.write(pack(b'<I', adr))
    output_file.close()

    path = 'poly_coord_amount.bin'
    print('writing file "', path, '"')
    output_file = open(path, 'wb')
    for length in all_lengths:
        output_file.write(pack(b'<I', length))
    output_file.close()

    # [SHORTCUT AREA]
    # write all nr of entries
    path = 'shortcuts_entry_amount.bin'
    print('writing file "', path, '"')
    output_file = open(path, 'wb')
    for nr in nr_of_entries_in_shortcut:
        if nr > 300:
            raise ValueError("There are too many polygons in this shortcut:", nr)
        output_file.write(pack(b'<H', nr))
    output_file.close()

    # write  Address of first Polygon_nr  in shortcut field (x,y)
    # Attention: 0 is written when no entries are in this shortcut
    adr = 0
    path = 'shortcuts_adr2data.bin'
    print('writing file "', path, '"')
    output_file = open(path, 'wb')
    for nr in nr_of_entries_in_shortcut:
        if nr == 0:
            output_file.write(pack(b'<I', 0))
        else:
            output_file.write(pack(b'<I', adr))
            # each line_nr takes up 2 bytes of space
            adr += 2 * nr
    output_file.close()

    # write Line_Nrs for every shortcut
    path = 'shortcuts_data.bin'
    print('writing file "', path, '"')
    output_file = open(path, 'wb')
    for entries in shortcut_entries:
        for entry in entries:
            if entry > nr_of_lines:
                raise ValueError(entry)
            output_file.write(pack(b'<H', entry))
    output_file.close()

    # write corresponding zone id for every shortcut (iff unique)
    path = 'shortcuts_unique_id.bin'
    print('writing file "', path, '"')
    output_file = open(path, 'wb')
    if poly_zone_ids[-1] >= INVALID_ZONE_ID:
        raise ValueError(
            'There are too many zones for this data type (H). The shortcuts_unique_id file need a Invalid Id!')
    for x in range(360 * NR_SHORTCUTS_PER_LNG):
        for y in range(180 * NR_SHORTCUTS_PER_LAT):
            try:
                shortcuts_this_entry = shortcuts[(x, y)]
                unique_id = poly_zone_ids[shortcuts_this_entry[0]]
                for nr in shortcuts_this_entry:
                    if poly_zone_ids[nr] != unique_id:
                        # there is a polygon from a different zone (hence an invalid id should be written)
                        unique_id = INVALID_ZONE_ID
                        break
                output_file.write(pack(b'<H', unique_id))
            except KeyError:
                # also write an Invalid Id when there is no polygon at all
                output_file.write(pack(b'<H', INVALID_ZONE_ID))

    output_file.close()
    # [HOLE AREA, Y = number of holes (very few: around 22)]
    hole_space = 0

    # '<H' for every hole store the related line
    path = 'hole_poly_ids.bin'
    print('writing file "', path, '"')
    output_file = open(path, 'wb')
    i = 0
    for line in polynrs_of_holes:
        if line > nr_of_lines:
            raise ValueError(line, nr_of_lines)
        output_file.write(pack(b'<H', line))
        i += 1
    hole_space += output_file.tell()
    output_file.close()

    if i > amount_of_holes:
        raise ValueError('There are more related lines than holes.')

    # '<H'  Y times [H unsigned short: nr of values (coordinate PAIRS! x,y in int32 int32) in this hole]
    path = 'hole_coord_amount.bin'
    print('writing file "', path, '"')
    output_file = open(path, 'wb')
    for length in all_hole_lengths:
        output_file.write(pack(b'<H', length))
    hole_space += output_file.tell()
    output_file.close()

    # '<I' Y times [ I unsigned int: absolute address of the byte where the data of that hole starts]
    adr = 0
    path = 'hole_adr2data.bin'
    print('writing file "', path, '"')
    output_file = open(path, 'wb')
    for length in all_hole_lengths:
        output_file.write(pack(b'<I', adr))
        # each pair of points takes up 8 bytes of space
        adr += 8 * length
    hole_space += output_file.tell()
    output_file.close()

    # Y times [ 2x i signed ints for every hole: x coords, y coords ]
    # write hole polygon_data
    path = 'hole_data.bin'
    print('writing file "', path, '"')
    output_file = open(path, 'wb')
    for x_coords, y_coords in all_holes:
        for x in x_coords:
            output_file.write(pack(b'<i', coord2int(x)))
        for y in y_coords:
            output_file.write(pack(b'<i', coord2int(y)))
    hole_space += output_file.tell()
    output_file.close()

    polygon_space = nr_of_floats * 4
    total_space = polygon_space + hole_space + shortcut_space

    print('the polygon data makes up', percent(polygon_space, total_space), '% of the data')
    print('the shortcuts make up', percent(shortcut_space, total_space), '% of the data')
    print('holes make up', percent(hole_space, total_space), '% of the data')
    print('Success!')
    return


if __name__ == '__main__':
    # parsing the data from the .json into RAM
    parse_polygons_from_json(path=INPUT_JSON_FILE_NAME)
    # update all the zone names and set the right ids to be written in the poly_zone_ids.bin
    # sort data according to zone_id
    update_zone_names(path=TIMEZONE_NAMES_FILE)

    # IMPORTANT: import the newly compiled timezone_names pickle!
    # the compilation process needs the new version of the timezone names
    with open(abspath(join(__file__, pardir, TIMEZONE_NAMES_FILE)), 'r') as f:
        timezone_names = json.loads(f.read())

    # compute shortcuts and write everything into the binaries
    compile_binaries()
