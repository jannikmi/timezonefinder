from __future__ import absolute_import, division, print_function, unicode_literals

import re
from datetime import datetime
from math import ceil, floor
from struct import pack

from numpy import array, linalg

# # keep in mind: numba optimized fct. cannot be used here, because numpy classes are not being used at this stage yet!
from .helpers import coord2int, inside_polygon, int2coord
from .timezone_names import timezone_names

# import sys
# from os.path import dirname
# sys.path.insert(0, dirname(__file__))
# from helpers import coord2int, int2coord, inside_polygon
# from timezone_names import timezone_names

# ATTENTION: Don't change these settings or timezonefinder wont work!
# different setups of shortcuts are not supported, because then addresses in the .bin
# need to be calculated depending on how many shortcuts are being used.
# number of shortcuts per longitude
NR_SHORTCUTS_PER_LNG = 1
# shortcuts per latitude
NR_SHORTCUTS_PER_LAT = 2

nr_of_lines = -1
all_tz_names = []
ids = []
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
        yield range(start, end)


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


def line_segments_intersect(p1, p2, q1, q2, magn_delta_p):
    # solve equation line1 = line2
    # p1 + lambda * (p2-p1) = q1 + my * (q2-q1)
    # lambda * (p2-p1) - my * (q2-q1) = q1 - p1
    # normalize deltas to 1
    # lambda * (p2-p1)/|p1-p2| - my * (q2-q1)/|q1-q2| = q1 - p1
    # magn_delta_p = |p1-p2|  (magnitude)
    # magn_delta_q = euclidean_distance(q1[0], q1[1], q2[0], q2[1])
    if max(p1[0], p2[0]) < min(q1[0], q2[0]) or max(q1[0], q2[0]) < min(p1[0], p2[0]) or \
            max(p1[1], p2[1]) < min(q1[1], q2[1]) or max(q1[1], q2[1]) < min(p1[1], p2[1]):
        return False

    dif_p_x = p2[0] - p1[0]
    dif_p_y = p2[1] - p1[1]
    dif_q_x = q2[0] - q1[0]
    dif_q_y = q2[1] - q1[1]
    a = array([[dif_p_x, -dif_q_x], [dif_p_y, -dif_q_y]])
    # [[dif_p_x / magn_delta_p, -dif_q_x / magn_delta_q], [dif_p_y / magn_delta_p, -dif_q_y / magn_delta_q]])
    b = array([q1[0] - p1[0], q1[1] - p1[1]])
    try:
        x = linalg.solve(a, b)
    except linalg.linalg.LinAlgError:
        # Singular matrix (lines parallel, there is not intersection)
        return False

    if x[0] < 0 or x[0] > 1 or x[1] < 0 or x[1] > 1:
        # intersection of the two lines appears before or after actual line segments
        # in this use case it is important to include the points themselves when checking for intersections
        # that way a new edge that barely touches the old polygon is also legal
        return False

    return True


triangle_x = [0.0, 0.0, 0.0]
triangle_y = [0.0, 0.0, 0.0]


def minimize_polygon(x_coords, y_coords, own_id):
    # for computational simplification the polygon is simplified in xy (lng, lat) plane (not on a sphere)
    # after computation the polygon has no more indentations (only on borders to other zones)

    old_length = len(x_coords)
    if old_length <= 3:
        return (x_coords, y_coords), old_length

    refused_p1s = []
    remaining_points = [i for i in range(old_length)]

    # print(max(*x_coords), min(*x_coords), max(*y_coords), min(*y_coords))

    # all of the points are candidates at first
    # only points contained in this list should be tested. this is to prevent repeated computations
    candidate_points = [i for i in remaining_points if i not in refused_p1s]
    # maintain a list of all points (their indices) still in the polygon
    # = edge indices of simplified polygon
    # those two lists should never contain duplicate entries
    current_length = old_length
    lookahead_margin = min(250, int(current_length / 2)) + 1
    pointer1 = 0
    p1 = 0.0, 0.0
    p2 = 0.0, 0.0
    p3 = 0.0, 0.0

    def close_polygon_nrs():
        global triangle_x, triangle_y
        out = []
        # return out
        # atm using all the shortcuts in the min max rectangle spanned by the triangle
        x_min = min(triangle_x)
        x_max = max(triangle_x)
        y_min = min(triangle_y)
        y_max = max(triangle_y)
        # higher (=lng) means higher x shortcut!!! 0 (-180deg lng) -> 360 (180deg)
        x_shortcut_min = x_shortcut(x_min)
        x_shortcut_max = x_shortcut(x_max) + 1
        # ATTENTION: lower y (=lat) means higher y shortcut!!! 0 (90deg lat) -> 180 (-90deg)
        y_shortcut_min = y_shortcut(y_max)
        y_shortcut_max = y_shortcut(y_min) + 1

        # even though shortcuts stay the same for a couple of consequent queries,
        # it is not possible to reuse output because of the boundary optimisation down below
        for x_s in range(x_shortcut_min, x_shortcut_max):
            for y_s in range(y_shortcut_min, y_shortcut_max):
                for poly_nr in get_shortcuts(x_s, y_s):
                    # ignore polygons of own zone
                    if ids[poly_nr] != own_id:
                        b = all_boundaries[poly_nr]
                        if not (x_min > b[0] or x_max < b[1] or y_min > b[2] or y_max < b[3]):
                            out.append(poly_nr)
        return out

    def simplification_invalid():
        global triangle_x, triangle_y
        # simplification is valid if polygon gets bigger and no intersections with other polygons (of different zones)
        # are being introduced
        # print(remaining_points,pointer1)

        if contained((p1[0] + p2[0] + p3[0]) / 3.0, (p1[1] + p2[1] + p3[1]) / 3.0, x_coords, y_coords):
            # the median of the triangle lies inside the polygon
            # this new edge would run through the polygon itself and hence make it smaller!
            # this is not a valid simplification
            # later simplificatons could still be possible!
            return True

        triangle_x = [p1[0], p2[0], p3[0]]
        triangle_y = [p1[1], p2[1], p3[1]]

        # the new line runs outside the polygon, it could however still intersect with other polygons
        # there is no new intersection being introduced by a simplification iff
        # no points of other polygons are contained in the triangle
        # because this computation takes long if many polygons are nearby remember which points have been refused
        # (just the ones being refused out of that reason!)
        middle_point = point_between(p1, p3)
        close_polygon_nrs_list = close_polygon_nrs()
        for polygon in _polygons(close_polygon_nrs_list):
            # it is not allowed that the edge runs through polygon!
            if inside_polygon(middle_point[0], middle_point[1], polygon):
                refused_p1s.append(remaining_points[pointer1])
                return True

        n = 0
        for polygon in _polygons(close_polygon_nrs_list):
            for i in range(all_lengths[close_polygon_nrs_list[n]]):
                if contained(polygon[0][i], polygon[1][i], triangle_x, triangle_y):
                    # store that this point has been refused
                    # a point of a different zone lies in the polygon p1p2p3, no simplifications can be made here
                    refused_p1s.append(remaining_points[pointer1])
                    return True
            n += 1

        # also make sure the simplification does not introduce self intersection
        # this is the case if any other point of the polygon (except triangle points) lie inside the triangle
        # later simplifications could still be possible!
        # check this later, because its probability is quite low
        # (lower than intersection with other polygons <-> every border!)
        # NOTE: i has to start with 1! (otherwise p1 and p3 themselves are being checked... -> contained = True!)
        # for i in range(3, current_length):
        #     temp_pointer = (pointer1 + i) % current_length
        #     if contained(x_coords[temp_pointer], y_coords[temp_pointer], triangle_x, triangle_y):
        #         return True

        # NOTE: some polygons in tz_world have >10k points,
        # that means checking every point for inclusion takes very very long! -> heuristic lookahead
        # ERROR: this heuristic still leads to some errors in complicated polygons (e.g. Canada) even if
        # lookahead_margin is picked high
        for i in range(1, lookahead_margin):
            # check a few points after p3!
            temp_pointer = (pointer3 + i) % current_length
            if contained(x_coords[temp_pointer], y_coords[temp_pointer], triangle_x, triangle_y):
                return True

            # also check a few points before p1
            temp_pointer = (pointer1 - i)
            if contained(x_coords[temp_pointer], y_coords[temp_pointer], triangle_x, triangle_y):
                return True

        return False

    while not_empty(candidate_points):
        # look for the next point that has to be optimized
        # update first pointer (length has changed)
        # remove p1 from the candidate points
        # print(remaining_points)
        # print(candidate_points,'\n')
        pointer1 = remaining_points.index(candidate_points.pop(0))
        previous_point = remaining_points[pointer1 - 1]
        p1 = x_coords[pointer1], y_coords[pointer1]
        simplification_made = False
        # print(pointer1, pointer2, pointer3, current_length)
        while True:
            pointer2 = (pointer1 + 1) % current_length
            pointer3 = (pointer2 + 1) % current_length
            p2 = x_coords[pointer2], y_coords[pointer2]
            p3 = x_coords[pointer3], y_coords[pointer3]
            if simplification_invalid():
                # break if no simplification is possible
                break
            # simplification is valid, so remove p2
            x_coords.pop(pointer2)
            y_coords.pop(pointer2)
            try:
                # since point is not part of the poly any more, remove also from candidates
                # and the remaining points
                candidate_points.remove(remaining_points.pop(pointer2))
            except ValueError:
                pass
            current_length -= 1
            if current_length <= 3:
                return (x_coords, y_coords), current_length
            # since length >= 4: lookahead_margin >=2 (and lookahead_margin <=51)
            lookahead_margin = min(250, int(current_length / 2)) + 1
            simplification_made = True
            # since list is shorter now pointers don't have to be moved
            # but since the length is decreasing the modulo operator has to be applied again
            if pointer1 == current_length:
                # if the point that has been removed was in front of p1, pointer to p1 needs to be adjusted!
                pointer1 -= 1
                # print(pointer1, pointer2, pointer3, current_length)
                # print(p1, p2, p3)

        # when reaching this, the maximum amount of simplifications have been made for this particular point p1
        if simplification_made:
            if previous_point not in candidate_points and previous_point not in refused_p1s:
                # check the point before p1 again
                # (shape has changed now, so further simplifications could be possible!)
                # should only be added if not already a candidate
                # and hasn't been refused before
                candidate_points.append(previous_point)
            next_point = remaining_points[pointer2]
            if next_point not in candidate_points and next_point not in refused_p1s:
                # also check the point after p1 again
                # (since p2 couldn't be removed, this is the point where pointer2 is pointing now)
                candidate_points.append(next_point)

    return (x_coords, y_coords), current_length


def minimize_all(snapping_distance=1.0):
    # TODO partly included or close polygons of the same zone should be merged into one big polygon
    # TODO to merge close polygons (distance < snapping distance)
    # simply introduce edge between two closest points?!
    # (only of this edge itself is intersection free with other zones!
    # TODO in which direction should be appended? after merge minimize again
    # beide richtungen probieren und die variante nehmen die mehr vereinfacht werden konnte?!

    global all_coords
    global all_lengths
    global all_boundaries
    global ids
    global nr_of_lines
    global polynrs_of_holes

    print('now minimizing all polygons:\n')

    # minimize all polygons (of every zone), this also speeds up later steps
    zone_id = -1
    all_coords_new = []
    all_lengths_new = []
    all_boundaries_new = []
    ids_new = []
    current_new_polygon_nr = 0

    for poly_nrs in polys_of_one_zone():
        zone_id += 1
        # print(zone_id, poly_nrs)
        print('\ntz name:', timezone_names[zone_id], 'polygon nrs in this zone: from', poly_nrs[0], 'to', poly_nrs[-1])
        # if i == 2:
        #     break
        lengths = []
        for nr in poly_nrs:
            x_coords, y_coords = all_coords[nr]
            old_length = all_lengths[nr]
            # update polygon data (boundaries have not changed)
            all_coords[nr], new_length = minimize_polygon(x_coords, y_coords, own_id=zone_id)
            # update the lengths
            if new_length > 1000:
                print('still a big polygon: number:', nr, 'simplification:',
                      percent(old_length - new_length, old_length),
                      '%, old length:', old_length, 'new length:', new_length)
            # print('polygon number:', nr, 'simplification:', percent(length - new_length, length), '%, old length:',
            #       length, 'new length:', new_length)
            all_lengths[nr] = new_length
            lengths.append(new_length)

        poly_nrs, lengths = zip(*sorted(zip(poly_nrs, lengths), key=lambda k: -k[1]))
        poly_nrs = list(poly_nrs)
        # lengths = list(lengths)
        current_length = len(poly_nrs)
        pointer2big_poly = 0
        # then starting from the biggest zone, check if smaller zones are contained
        # print('trying to delete polygons...')
        if current_length == 1:
            # simply store the polygon, when there is just a single polygon in a zone
            # boundaries and lengths didnt change so just copy
            polygon_nr_big_poly = poly_nrs[pointer2big_poly]
            polynrs_of_holes = replace_entry(polynrs_of_holes, polygon_nr_big_poly, current_new_polygon_nr)
            all_coords_new.append(all_coords[polygon_nr_big_poly])
            all_lengths_new.append(lengths[pointer2big_poly])
            all_boundaries_new.append(all_boundaries[polygon_nr_big_poly])
            ids_new.append(zone_id)
            current_new_polygon_nr += 1

        while pointer2big_poly < current_length - 1:
            pointer2small_poly = pointer2big_poly + 1
            polygon_nr_big_poly = poly_nrs[pointer2big_poly]
            polygon = all_coords[polygon_nr_big_poly]
            # did_merge = False
            while True:
                polygon_nr_small_poly = poly_nrs[pointer2small_poly]
                x_coords, y_coords = all_coords[polygon_nr_small_poly]
                all_edges_contained = True
                delete_small_polygon = True
                contained_edges = []
                # distances = []
                n = 0
                for x in x_coords:
                    y = y_coords[n]
                    # (check for every edge inside_polygon(edge))
                    if inside_polygon(x, y, polygon):
                        contained_edges.append(n)
                    else:
                        all_edges_contained = False
                        # TODO remove break, when performing merges!
                        break
                    n += 1
                # when there is a hole in the big polygon, only delete the small one
                # if none of its points is included in the hole!
                if delete_small_polygon and polygon_nr_big_poly in polynrs_of_holes:
                    for hole in _holes_in_poly(polygon_nr_big_poly):
                        n = 0
                        for x in x_coords:
                            y = y_coords[n]
                            if inside_polygon(x, y, hole):
                                delete_small_polygon = False
                                break
                            n += 1

                if len(contained_edges) == 0:
                    # no_edge_contained

                    # # TODO if 'island' is close enough to the big one also include the edges and simplify
                    # i = 0
                    # min_distance = 2.0
                    # closest_point = 0
                    # for x in x_coords:
                    #     y = y_coords[i]
                    #     distance = min_distance_from_polygon(x, y, polygon)
                    #     if distance<min_distance:
                    #         min_distance = distance
                    #         closest_point = i
                    #     # distances.append(min_distance_from_polygon(x, y, polygon))
                    #     i += 1
                    #
                    # if min_distance < snapping_distance:
                    #     polygon = minimize_polygon(*insert_polygon(polygon, x_coords, y_coords, closest_point))
                    # else:
                    # check the next polygon and keep! this polygon
                    delete_small_polygon = False

                else:
                    # if all edges are contained simply delete the whole polygon
                    if all_edges_contained:
                        pass
                        # just removing is enough
                        # print('deleting polygon', polygon_nr_small_poly, '(completely contained in',
                        #       polygon_nr_big_poly, ')')
                    else:
                        delete_small_polygon = False
                        # print('polygon', polygon_nr_small_poly, ' is partly contained in',
                        #       polygon_nr_big_poly)
                        # # if at least one of the edges is contained, add edges of the "island" to big polygon
                        # # and simplify again
                        # polygon, delete_small_polygon = merge_polygons(polygon, x_coords, y_coords, contained_edges)
                        # if delete_small_polygon:
                        #     did_merge = True

                if delete_small_polygon:
                    # (delete the whole small polygon if one of the cases matched)
                    # this simply means not adding it to all_coords_new and deleting it from the poly_nrs list
                    poly_nrs.pop(pointer2small_poly)
                    current_length -= 1
                else:
                    pointer2small_poly += 1

                if pointer2small_poly == current_length:
                    # this was the last small polygon to check
                    break

            if pointer2big_poly == current_length - 2 and not delete_small_polygon:
                # the last big polygon has been checked and the last small polygon hasn't been deleted
                # add it otherwise it would get lost (only big polygons are added each iteration)
                all_coords_new.append((x_coords, y_coords))
                all_lengths_new.append(len(x_coords))
                all_boundaries_new.append((max(*x_coords), min(*x_coords), max(*y_coords), min(*y_coords)))
                ids_new.append(zone_id)
                current_new_polygon_nr += 1

            # minimize polygon once again (only after merging with polygons)
            # this is faster than minimizing after every merge, but also misses some possible simplifications
            # TODO this would also possibly introduces new intersections and so on...!
            # if did_merge:
            #     polygon = minimize_polygon(*polygon, own_id=zone_id)
            polynrs_of_holes = replace_entry(polynrs_of_holes, polygon_nr_big_poly, current_new_polygon_nr)
            # write minimized polygons back
            all_coords_new.append(polygon)
            all_lengths_new.append(lengths[pointer2big_poly])
            all_boundaries_new.append((max(*polygon[0]), min(*polygon[0]), max(*polygon[1]), min(*polygon[1])))
            ids_new.append(zone_id)
            current_new_polygon_nr += 1
            pointer2big_poly += 1

            # add all the remaining (not tested) polygons as is

    all_lengths = all_lengths_new
    all_coords = all_coords_new
    all_boundaries = all_boundaries_new
    ids = ids_new
    nr_of_lines = len(ids)
    print('\n\nDone with minimisation.')
    # print(all_lengths)
    # print(ids)
    # print(nr_of_lines)
    print(polynrs_of_holes)
    print('\n')


def parse_polygons_from_json(path='tz_world.json'):
    global amount_of_holes
    global nr_of_lines

    max_length = 0

    f = open(path, 'r')
    print('Parsing data from .json\n')
    print('Encountered holes at: ')

    # file_line is the current line in the .json file being parsed. This is not equal to the id of the Polygon!
    file_line = 0
    for row in f:
        # print(row)
        tz_name_match = re.search(r'\"TZID\":\s\"(?P<name>.*)\"\s\}', row)
        # tz_name = re.search(r'(TZID)', row)
        # print(tz_name)
        if tz_name_match is not None:

            tz_name = tz_name_match.group('name').replace('\\', '')
            all_tz_names.append(tz_name)

            # if nr_of_lines == 200:
            #     # print(polynrs_of_holes)
            #     break

            nr_of_lines += 1
            # print(tz_name)

            actual_depth = 0
            counted_coordinate_pairs = 0
            encoutered_nr_of_coordinates = []
            for char in row:
                if char == '[':
                    actual_depth += 1

                elif char == ']':
                    actual_depth -= 1
                    if actual_depth == 2:
                        counted_coordinate_pairs += 1

                    if actual_depth == 1:
                        encoutered_nr_of_coordinates.append(counted_coordinate_pairs)
                        counted_coordinate_pairs = 0

            if actual_depth != 0:
                raise ValueError('uneven number of brackets detected. Something is wrong in line', file_line)

            coordinates = re.findall('[-]?\d+\.?\d+', row)

            if len(coordinates) != sum(encoutered_nr_of_coordinates) * 2:
                raise ValueError('There number of coordinates is counten wrong:', len(coordinates),
                                 sum(encoutered_nr_of_coordinates) * 2)

            # nr_floats = len(coordinates)
            x_coords = []
            y_coords = []
            xmax = -180.0
            xmin = 180.0
            ymax = -90.0
            ymin = 90.0

            pointer = 0
            # the coordiate pairs within the first brackets [ [x,y], ..., [xn, yn] ] are the polygon coordinates
            # The last coordinate pair should be left out (is equal to the first one)
            # the edge from last to first coordinate is still being tested in the algorithms,
            # even without this redundancy
            for n in range(2 * (encoutered_nr_of_coordinates[0] - 1)):
                if n % 2 == 0:
                    x = float(coordinates[pointer])
                    x_coords.append(x)
                    if x > xmax:
                        xmax = x
                    if x < xmin:
                        xmin = x

                else:
                    y = float(coordinates[pointer])
                    y_coords.append(y)
                    if y > ymax:
                        ymax = y
                    if y < ymin:
                        ymin = y

                pointer += 1

            all_coords.append((x_coords, y_coords))
            all_lengths.append(len(x_coords))
            max_length = max(len(x_coords), max_length)
            if max_length > 2 ** 16:
                # 34621 in tz_world 2016d
                raise ValueError('amount of coords cannot be represented by short (int16) in poly_coord_amount.bin:',
                                 len(x_coords))

            # print(x_coords)
            # print(y_coords)

            all_boundaries.append((xmax, xmin, ymax, ymin))

            amount_holes_this_line = len(encoutered_nr_of_coordinates) - 1
            if amount_holes_this_line > 0:
                # store how many holes there are in this line
                # store what the id of the first hole for this line is (for calculating the address to jump)
                # first_hole_id_in_line.append(amount_of_holes)
                # keep track of how many holes there are
                amount_of_holes += amount_holes_this_line
                print(tz_name)

                for i in range(amount_holes_this_line):
                    polynrs_of_holes.append(nr_of_lines)
                    print(nr_of_lines)
                    # print(amount_holes_this_line)

            # for every encountered hole
            for i in range(1, amount_holes_this_line + 1):
                x_coords = []
                y_coords = []

                # since the last coordinate was being left out,
                # we have to move the pointer 2 floats further to be in the hole data again
                pointer += 2

                # The last coordinate pair should be left out (is equal to the first one)
                for n in range(2 * (encoutered_nr_of_coordinates[i] - 1)):
                    if n % 2 == 0:
                        x_coords.append(float(coordinates[pointer]))
                    else:
                        y_coords.append(float(coordinates[pointer]))

                    pointer += 1

                all_holes.append((x_coords, y_coords))
                all_hole_lengths.append(len(x_coords))

        file_line += 1

    # so far the nr_of_lines used to point to the current polygon but there is actually 1 more polygons in total
    nr_of_lines += 1

    print('\nmaximal amount of coordinates in one polygon:', max_length)
    print('amount_of_holes:', amount_of_holes)
    print('amount of polygons:', nr_of_lines)
    print('Done with parsing .json\n')


def update_zone_names(path='timezone_names.py'):
    global ids
    global list_of_pointers
    global all_boundaries
    global all_coords
    global all_lengths
    global polynrs_of_holes
    print('updating the zone names now')
    unique_zones = []
    for zone_name in all_tz_names:
        if zone_name not in unique_zones:
            unique_zones.append(zone_name)
    unique_zones.sort()

    for zone_name in all_tz_names:
        # the ids of the polygons have to be set correctly
        ids.append(unique_zones.index(zone_name))

    # write all unique zones into the file at path with the syntax of a python array
    file = open(path, 'w')
    file.write(
        'from __future__ import absolute_import, division, print_function, unicode_literals\n\ntimezone_names = [\n')
    for zone_name in unique_zones:
        file.write('    "' + zone_name + '"' + ',\n')

    file.write(']\n')
    print('Done updating the ids and zone names\n')
    print('Sorting the polygons now after the id of their zone')
    list_of_pointers = range(nr_of_lines)
    ids, list_of_pointers = zip(*sorted(zip(ids, list_of_pointers), key=lambda id: id[0]))
    # index of poly_nr in list of pointers indicates new position of that polygon
    sorted_coords = []
    sorted_lengths = []
    sorted_boundaries = []
    for p in list_of_pointers:
        sorted_coords.append(all_coords[p])
        sorted_lengths.append(all_lengths[p])
        sorted_boundaries.append(all_boundaries[p])

    all_coords = sorted_coords
    all_boundaries = sorted_boundaries
    all_lengths = sorted_lengths

    new_polynrs = []
    # replace the corresponding poly nrs for every hole
    for nr in polynrs_of_holes:
        new_polynrs.append(list_of_pointers.index(nr))
    # the order of holes does not matter
    polynrs_of_holes = new_polynrs
    print('Done\n')

    print('computing where zones start and end')
    i = 0
    last_id = -1
    for zone_id in ids:
        if zone_id != last_id:
            poly_nr2zone_id.append(i)
            last_id = zone_id
        i += 1
    poly_nr2zone_id.append(i)
    print('Done\n')


def compile_binaries(simplify=True):
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
                id = ids[polygon_nr]
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
        print('currently in line:')
        line = 0
        for xmax, xmin, ymax, ymin in all_boundaries:
            # xmax, xmin, ymax, ymin = boundaries_of(line=line)
            if line % 1000 == 0:
                print('line ' + str(line))
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

    if simplify:
        old_sum_coords = sum(all_lengths)
        nr_of_polygons_old = len(all_lengths)
        minimize_all()
        new_sum_coords = sum(all_lengths)
        nr_of_floats = 2 * new_sum_coords
        nr_of_polygons_new = len(all_lengths)
        print('Done.\nthere originally were', old_sum_coords, 'coordinates in all polygons')
        print('now there are', new_sum_coords, '. this is a reduction of',
              percent(old_sum_coords - new_sum_coords, old_sum_coords), '%')
        print('of', nr_of_polygons_old, 'polygons', nr_of_polygons_new, '(',
              percent(nr_of_polygons_new, nr_of_polygons_old), '%) remain\n')

        print('recomputing shortcuts now:')
        shortcuts = {}
        start_time = datetime.now()
        construct_shortcuts()
        end_time = datetime.now()
        print('calculating the shortcuts took:', end_time - start_time, '\n')
    else:
        nr_of_floats = 2 * sum(all_lengths)

    # write number of entries in shortcut field (x,y)
    nr_of_entries_in_shortcut = []
    shortcut_entries = []
    amount_filled_shortcuts = 0

    # count how many shortcut addresses will be written:
    for x in range(360 * NR_SHORTCUTS_PER_LNG):
        for y in range(180 * NR_SHORTCUTS_PER_LAT):
            try:
                this_lines_shortcuts = shortcuts[(x, y)]
                shortcut_entries.append(this_lines_shortcuts)
                amount_filled_shortcuts += 1
                nr_of_entries_in_shortcut.append(len(this_lines_shortcuts))
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
    i = 0
    last_id = -1
    for zone_id in ids:
        if zone_id != last_id:
            output_file.write(pack(b'<H', i))
            poly_nr2zone_id.append(i)
            last_id = zone_id

        i += 1

    # write one more value to have an end address for the last zone_id
    output_file.write(pack(b'<H', i))
    poly_nr2zone_id.append(i)
    output_file.close()

    print('Done\n')
    # write zone_ids
    path = 'poly_zone_ids.bin'
    print('writing file "', path, '"')
    output_file = open(path, 'wb')
    for zone_id in ids:
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
    amounts = []
    for x_coords, y_coords in all_coords:
        addresses.append(output_file.tell())
        amounts.append(len(x_coords))
        for x in x_coords:
            output_file.write(pack(b'<i', coord2int(x)))
        for y in y_coords:
            output_file.write(pack(b'<i', coord2int(y)))
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
    for a in amounts:
        output_file.write(pack(b'<H', a))
    output_file.close()

    # [SHORTCUT AREA]
    # write all nr of entries
    path = 'shortcuts_entry_amount.bin'
    print('writing file "', path, '"')
    output_file = open(path, 'wb')
    for nr in nr_of_entries_in_shortcut:
        if nr > 300:
            raise ValueError("There are too many polygons in this shortcuts:", nr)
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
    for x in range(360 * NR_SHORTCUTS_PER_LNG):
        for y in range(180 * NR_SHORTCUTS_PER_LAT):
            try:
                this_lines_shortcuts = shortcuts[(x, y)]
                unique_id = ids[this_lines_shortcuts[0]]
                for nr in this_lines_shortcuts:
                    if ids[nr] != unique_id:
                        unique_id = 9999
                        break
                output_file.write(pack(b'<H', unique_id))
            except KeyError:
                output_file.write(pack(b'<H', 9999))

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


"""
IMPORTANT: all coordinates (floats) are being converted to int32 (multiplied by 10^7). This makes computations faster
and it takes lot less space, without loosing too much accuracy (min accuracy (=at the equator) is still 1cm !)

H = unsigned short (2 byte integer)
I = unsigned 4byte integer
i = signed 4byte integer


Binaries being written:

[POLYGONS:] there are approx. 27k Polygons (tz_world 2016d)
poly_zone_ids: the related zone_id for every polygon ('<H')
poly_coord_amount: the amount of coordinates in every polygon ('<H')
poly_adr2data: address in poly_data.bin where data for every polygon starts ('<I')
poly_max_values: boundaries for every polygon ('<iiii': xmax, xmin, ymax, ymin)
poly_data: coordinates for every polygon (multiple times '<i')
poly_nr2zone_id: the polygon number of the first polygon from every zone('<H')

[HOLES:] number of holes (very few: around 22)
hole_poly_ids: the related polygon_nr (=id) for every hole ('<H')
hole_coord_amount: the amount of coordinates in every hole ('<H')
hole_adr2data: address in hole_data.bin where data for every hole starts ('<I')
hole_data: coordinates for every hole (multiple times '<i')

[SHORTCUTS:] there are a total of 360 * NR_SHORTCUTS_PER_LNG * 180 * NR_SHORTCUTS_PER_LAT shortcuts
shortcut here means storing for every cell in a grid of the world map which polygons are located in that cell
they can therefore be used to drastically reduce the amount of polygons which need to be checked in order to
decide which timezone a point is located in

shortcuts_entry_amount: the amount of polygons for every shortcut ('<H')
shortcuts_adr2data: address in shortcut_data.bin where data for every shortcut starts ('<I')
shortcuts_data: polygon numbers (ids) for every shortcut (multiple times '<H')
shortcuts_unique_id: the zone id if only polygons from one zone are present,
                     a high number (with no corresponding zone) if not ('<H')
"""

if __name__ == '__main__':
    # reading the data from the .json converted from the tz_world shapefile .shp
    parse_polygons_from_json(path='tz_world.json')
    # update all the zone names and set the right ids to be written in the poly_zone_ids.bin
    # sort data according to zone_id
    update_zone_names(path='timezone_names.py')
    # compute shortcuts
    # write everything into the binaries
    compile_binaries(simplify=False)
