from __future__ import absolute_import, division, print_function, unicode_literals

import linecache
import math
import re
from datetime import datetime
from struct import pack

from timezone_names import timezone_names

# number of shortcuts per longitude
NR_SHORTCUTS_PER_LNG = 1
# shortcuts per latitude
NR_SHORTCUTS_PER_LAT = 2


# HELPERS:

def check_zone_names():
    '''
    scans for zone name in the original .csv which are not listed yet
    :return:
    '''
    omitted_zones = []
    for (zone_name, list_of_points) in _read_polygons_from_original_csv():

        if zone_name not in timezone_names:
            if zone_name not in omitted_zones:
                omitted_zones.append(zone_name)

    print(omitted_zones)
    return


def coordinate_to_longlong(double):
    return int(double * 10 ** 15)


def longlong_to_coordinate(longlong):
    return float(longlong / 10 ** 15)


def inside_polygon(x, y, x_coords, y_coords):
    def is_left_of(x, y, x1, x2, y1, y2):
        return (x2 - x1) * (y - y1) - (x - x1) * (y2 - y1)

    n = len(y_coords) - 1

    wn = 0
    for i in range(n):
        iplus = i + 1
        if y_coords[i] <= y:
            # print('Y1<=y')
            if y_coords[iplus] > y:
                # print('Y2>y')
                if is_left_of(x, y, x_coords[i], x_coords[iplus], y_coords[i], y_coords[iplus]) > 0:
                    wn += 1
                    # print('wn is:')
                    # print(wn)

        else:
            # print('Y1>y')
            if y_coords[iplus] <= y:
                # print('Y2<=y')
                if is_left_of(x, y, x_coords[i], x_coords[iplus], y_coords[i], y_coords[iplus]) < 0:
                    wn -= 1
                    # print('wn is:')
                    # print(wn)

    return wn is not 0


def _read_polygons_from_original_csv(path='tz_world.csv'):
    with open(path, 'r') as f:
        for row in f:
            row = row.split(',')
            yield (row[0], [[float(coordinate) for coordinate in point.split(' ')] for point in row[1:]])


def convert_csv(path='tz_world.csv'):
    '''
    create a new .csv with rearranged data
    converts the zone names into their ids (int instead of string, for later storing it in a .bin)
    additionally splits up the rows into:  id,xmax,xmin,ymax,ymin,y1 y2...,x1 x2 ...\n
    #those boundaries help do quickly decide wether to check the polygon at all (saves a lot of time)
    :param path:
    :return:
    '''
    output_file = open('tz_world_converted.csv', 'w')
    print('converting the old .csv now...')
    i = 0
    for (zone_name, list_of_points) in _read_polygons_from_original_csv(path):
        if i % 1000 == 0:
            print('line', i)
        i += 1
        xmax = -180
        xmin = 180
        ymax = -90
        ymin = 90
        string_of_x_coords = ''
        string_of_y_coords = ''
        # in the original .csv the earch polygon starts and ends with the same coordinate (=redundancy)
        # this is not needed, because the algorithms can do the job without this because value will be in the RAM anyway
        # 50+k floats and reading effort saved!
        for i in range(len(list_of_points) - 1):

            x = list_of_points[i][0]
            y = list_of_points[i][1]

            match = re.match(r'[-]?\d+\.?\d?', str(y))
            if match is None:
                raise ValueError('newline in y coord at value: ' + str(i - 1), y)

            match = re.match(r'[-]?\d+\.?\d?', str(x))
            if match is None:
                raise ValueError('newline in x coord at value: ' + str(i - 1), x)

            if x > xmax:
                xmax = x
            if x < xmin:
                xmin = x
            if y > ymax:
                ymax = y
            if y < ymin:
                ymin = y
            string_of_x_coords += str(x) + ' '
            string_of_y_coords += str(y) + ' '

        output_file.write(
            str(timezone_names.index(zone_name)) + ',' + str(xmax) + ',' + str(xmin) + ',' + str(ymax) + ',' + str(
                ymin) + ',' + string_of_x_coords.strip() + ',' + string_of_y_coords.strip() + '\n')


def _ids():
    with open('tz_world_converted.csv', 'r') as f:
        for row in f:
            row = row.split(',')
            # (id,xmax,xmin,ymax,ymin, [x1 x2 ...], [y1 y2...])
            # x = horizontal = longitude, y = vertical = latitude
            yield int(row[0])


def _boundaries():
    with open('tz_world_converted.csv', 'r') as f:
        for row in f:
            row = row.split(',')
            # (id,xmax,xmin,ymax,ymin, [x1 x2 ...], [y1 y2...])
            # x = horizontal = longitude, y = vertical = latitude
            yield (float(row[1]), float(row[2]), float(row[3]), float(row[4]),)


def _coordinates():
    with open('tz_world_converted.csv', 'r') as f:
        for row in f:
            row = row.split(',')
            # (id,xmax,xmin,ymax,ymin, [x1 x2 ...], [y1 y2...])
            # x = horizontal = longitude, y = vertical = latitude
            yield ([float(x) for x in row[5].split(' ')], [float(x) for x in row[6].strip().split(' ')])


def longs_in(line=0):
    row = linecache.getline('tz_world_converted.csv', lineno=line)
    row = row.split(',')
    return (
        [int(float(x) * 10 ** 15) for x in row[5].split(' ')],
        [int(float(x) * 10 ** 15) for x in row[6].strip().split(' ')])


def _length_of_rows():
    with open('tz_world_converted.csv', 'r') as f:
        for row in f:
            yield len(row.split(',')[5].split(' '))


def compile_into_binary(path='tz_binary.bin'):
    nr_of_floats = 0
    nr_of_lines = 0
    zone_ids = []
    shortcuts = {}

    def x_shortcut(lng):
        # if lng < -180 or lng >= 180:
        # print(lng)
        # raise ValueError('longitude out of bounds')
        return math.floor((lng + 180) * NR_SHORTCUTS_PER_LNG)

    def y_shortcut(lat):
        # if lat < -90 or lat >= 90:
        # print(lat)
        # raise ValueError('this latitude is out of bounds')
        return math.floor((90 - lat) * NR_SHORTCUTS_PER_LAT)

    def big_zone(xmax, xmin, ymax, ymin):
        # returns True if a zone with those boundaries could have more than 4 shortcuts
        return xmax - xmin > 2 / NR_SHORTCUTS_PER_LNG and ymax - ymin > 2 / NR_SHORTCUTS_PER_LAT

    def included_shortcut_row_nrs(max_lat, min_lat):
        return list(range(y_shortcut(max_lat), y_shortcut(min_lat) + 1))

    def included_shortcut_column_nrs(max_lng, min_lng):
        return list(range(x_shortcut(min_lng), x_shortcut(max_lng) + 1))

    def longitudes_to_check(max_lng, min_lng):
        output_list = []
        step = 1 / NR_SHORTCUTS_PER_LNG
        current = math.ceil(min_lng * NR_SHORTCUTS_PER_LNG) / NR_SHORTCUTS_PER_LNG
        end = math.floor(max_lng * NR_SHORTCUTS_PER_LNG) / NR_SHORTCUTS_PER_LNG
        while current < end:
            output_list.append(current)
            current += step

        output_list.append(end)
        return output_list

    def latitudes_to_check(max_lat, min_lat):
        output_list = []
        step = 1 / NR_SHORTCUTS_PER_LAT
        current = math.ceil(min_lat * NR_SHORTCUTS_PER_LAT) / NR_SHORTCUTS_PER_LAT
        end = math.floor(max_lat * NR_SHORTCUTS_PER_LAT) / NR_SHORTCUTS_PER_LAT
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

        # print(x_coords)
        # print(y)
        # print(y_coords)

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
        longs = longs_in(line + 1)
        x_longs = longs[0]
        y_longs = longs[1]

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
            intersects = sorted([longlong_to_coordinate(x) for x in
                                 x_intersections(coordinate_to_longlong(lat), x_longs, y_longs)])
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
                    if inside_polygon(coordinate_to_longlong(intersection_in), coordinate_to_longlong(lat) + 1, x_longs,
                                      y_longs):
                        shortcuts_for_line.add((x_shortcut(intersection_in), y_shortcut(lat) - 1))
                    # the bottom shortcut is always selected
                    shortcuts_for_line.add((x_shortcut(intersection_in), y_shortcut(lat)))

                else:
                    # add all the shortcuts for the whole found area of intersection
                    possible_y_shortcut = y_shortcut(lat)

                    # both shortcuts should only be selected when the polygon doesnt stays on the border
                    middle = intersection_in + (intersection_out - intersection_in) / 2
                    if inside_polygon(coordinate_to_longlong(middle), coordinate_to_longlong(lat) + 1, x_longs,
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
            intersects = sorted([longlong_to_coordinate(y) for y in
                                 y_intersections(coordinate_to_longlong(lng), x_longs, y_longs)])
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
                    if inside_polygon(coordinate_to_longlong(lng) - 1, coordinate_to_longlong(intersection_in), x_longs,
                                      y_longs):
                        shortcuts_for_line.add((x_shortcut(lng) - 1, y_shortcut(intersection_in)))
                    # the right shortcut is always selected
                    shortcuts_for_line.add((x_shortcut(lng), y_shortcut(intersection_in)))

                else:
                    # add all the shortcuts for the whole found area of intersection
                    possible_x_shortcut = x_shortcut(lng)

                    # both shortcuts should only be selected when the polygon doesnt stays on the border
                    middle = intersection_in + (intersection_out - intersection_in) / 2
                    if inside_polygon(coordinate_to_longlong(lng) - 1, coordinate_to_longlong(middle), x_longs,
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
        line = 0
        for xmax, xmin, ymax, ymin in _boundaries():
            # xmax, xmin, ymax, ymin = boundaries_of(line=line)
            if line % 1000 == 0:
                print('line ' + str(line))
                # print([xmax, xmin, ymax, ymin])

            column_nrs = included_shortcut_column_nrs(xmax, xmin)
            row_nrs = included_shortcut_row_nrs(ymax, ymin)

            if big_zone(xmax, xmin, ymax, ymin):
                '''
                print('line ' + str(line))
                print('This is a big zone! computing exact shortcuts')
                print('Nr of entries before')
                print(len(column_nrs) * len(row_nrs))

                print('columns and rows before optimisation:')

                print(column_nrs)
                print(row_nrs)
                '''

                # This is a big zone! compute exact shortcuts with the whole polygon points
                shortcuts_for_line = compute_exact_shortcuts(xmax, xmin, ymax, ymin, line)
                # n += len(shortcuts_for_line)

                '''
                accurracy = 1000000000000
                while len(shortcuts_for_line) < 3 and accurracy > 10000000000:
                    shortcuts_for_line = compute_exact_shortcuts(line=i,accurracy)
                    accurracy = int(accurracy/10)
                '''
                min_x_shortcut = column_nrs[0]
                max_x_shortcut = column_nrs[-1]
                min_y_shortcut = row_nrs[0]
                max_y_shortcut = row_nrs[-1]
                shortcuts_to_remove = []
                for x, y in shortcuts_for_line:
                    if x < min_x_shortcut:
                        shortcuts_to_remove.append((x, y))
                    if x > max_x_shortcut:
                        shortcuts_to_remove.append((x, y))
                    if y < min_y_shortcut:
                        shortcuts_to_remove.append((x, y))
                    if y > max_y_shortcut:
                        shortcuts_to_remove.append((x, y))

                for s in shortcuts_to_remove:
                    shortcuts_for_line.remove(s)

                '''
                print('and after:')
                print(len(shortcuts_for_line))

                column_nrs_after = set()
                row_nrs_after = set()
                for x, y in shortcuts_for_line:
                    column_nrs_after.add(x)
                    row_nrs_after.add(y)
                print(column_nrs_after)
                print(row_nrs_after)
                print(shortcuts_for_line)
                '''
                if len(shortcuts_for_line) > len(column_nrs) * len(row_nrs):
                    raise ValueError(
                        'there are more shortcuts than before now. there is something wrong with the algorithm!')
                if len(shortcuts_for_line) < 3:
                    raise ValueError('algorithm not accurate enough. less than 3 zones detected')

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

    print('reading the converted .csv file')
    for ID in _ids():
        nr_of_lines += 1
        zone_ids.append(ID)

    for length in _length_of_rows():
        nr_of_floats += 2 * length

    start_time = datetime.now()
    construct_shortcuts()
    end_time = datetime.now()

    print('calculating the shortcus took:', end_time - start_time)

    polygon_address = (40 * nr_of_lines + 6)
    shortcut_start_address = polygon_address + 8 * nr_of_floats
    nr_of_floats += nr_of_lines * 4
    print('The number of polygons is:', nr_of_lines)
    print('The number of floats in all the polygons is:', nr_of_floats)
    print('now writing file "', path, '"')
    output_file = open(path, 'wb')
    # write nr_of_lines
    output_file.write(pack(b'!H', nr_of_lines))
    # write start address of shortcut_data:
    output_file.write(pack(b'!I', shortcut_start_address))
    # write zone_ids
    for zone_id in zone_ids:
        output_file.write(pack(b'!H', zone_id))
    # write number of values
    for length in _length_of_rows():
        output_file.write(pack(b'!H', length))

    # write polygon_addresses
    for length in _length_of_rows():
        output_file.write(pack(b'!I', polygon_address))
        polygon_address += 16 * length

    if shortcut_start_address != polygon_address:
        # both should be the same!
        raise ValueError('shortcut_start_address and polygon_address should now be the same!')

    # write boundary_data
    for xmax, xmin, ymax, ymin in _boundaries():
        output_file.write(pack(b'!qqqq',
                               coordinate_to_longlong(xmax), coordinate_to_longlong(xmin), coordinate_to_longlong(ymax),
                               coordinate_to_longlong(ymin)))

    # write polygon_data
    for x_coords, y_coords in _coordinates():
        for x in x_coords:
            output_file.write(pack(b'!q', coordinate_to_longlong(x)))
        for y in y_coords:
            output_file.write(pack(b'!q', coordinate_to_longlong(y)))

    print('position after writing all polygon data (=start of shortcut section):', output_file.tell())
    # write number of entries in shortcut field (x,y)
    nr_of_entries_in_shortcut = []
    shortcut_entries = []
    total_entries_in_shortcuts = 0

    # count how many shortcut addresses will be written:
    for x in range(360 * NR_SHORTCUTS_PER_LNG):
        for y in range(180 * NR_SHORTCUTS_PER_LAT):
            try:
                this_lines_shortcuts = shortcuts[(x, y)]
                shortcut_entries.append(this_lines_shortcuts)
                total_entries_in_shortcuts += 1
                nr_of_entries_in_shortcut.append(len(this_lines_shortcuts))
                # print((x,y,this_lines_shortcuts))
            except KeyError:
                nr_of_entries_in_shortcut.append(0)

    print('The number of filled shortcut zones are:', total_entries_in_shortcuts)

    if len(nr_of_entries_in_shortcut) != 64800 * NR_SHORTCUTS_PER_LNG * NR_SHORTCUTS_PER_LAT:
        print(len(nr_of_entries_in_shortcut))
        raise ValueError('this number of shortcut zones is wrong')

    # write all nr of entries
    for nr in nr_of_entries_in_shortcut:
        if nr > 300:
            raise ValueError(nr)
        output_file.write(pack(b'!H', nr))

    # write  Address of first Polygon_nr  in shortcut field (x,y)
    # Attention: 0 is written when no entries are in this shortcut
    shortcut_address = output_file.tell() + 259200 * NR_SHORTCUTS_PER_LNG * NR_SHORTCUTS_PER_LAT
    for nr in nr_of_entries_in_shortcut:
        if nr == 0:
            output_file.write(pack(b'!I', 0))
        else:
            output_file.write(pack(b'!I', shortcut_address))
            # each polygon takes up 2 bytes of space
            shortcut_address += 2 * nr

    # write Line_Nrs for every shortcut
    for entries in shortcut_entries:
        for entry in entries:
            if entry > nr_of_lines:
                raise ValueError(entry)
            output_file.write(pack(b'!H', entry))

    print('Success!')
    return


"""
Data format in the .bin:
IMPORTANT: all coordinates multiplied by 10**15 (to store them as longs/ints not floats, because floats arithmetic
are slower)

no of rows (= no of polygons = no of boundaries)
approx. 28k -> use 2byte unsigned short (has range until 65k)
'!H' = n


I Address of Shortcut area (end of polygons+1) @ 2

'!H'  n times [H unsigned short: zone number=ID in this line, @ 6 + 2* lineNr]

'!H'  n times [H unsigned short: nr of values (coordinate PAIRS! x,y in long long) in this line, @ 6 + 4* lineNr]

'!I'n times [ I unsigned int: absolute address of the byte where the polygon-data of that line starts,
@ 6 + 4 * n +  4*lineNr]



n times 4 long longs: xmax, xmin, ymax, ymin  @ 6 + 8n
'!qqqq'



(for all lines: x coords, y coords:)   @ Address see above
'!q'


56700 times H   number of entries in shortcut field (x,y)  @ Pointer see above


X times I   Address of first Polygon_nr  in shortcut field (x,y)  @ 56700 + Pointer see above


X times H  Polygon_Nr     @Pointer see one above

"""

if __name__ == '__main__':
    convert_csv()

    # Don't change this setup or timezonefinder wont work!
    # different setups of shortcuts are not supported, because then addresses in the .bin
    # would need to be calculated depending on how many shortcuts are being used.

    # set the number of shortcuts created per longitude
    NR_SHORTCUTS_PER_LNG = 1
    # shortcuts per latitude
    NR_SHORTCUTS_PER_LAT = 2
    compile_into_binary(path='timezone_data.bin')
