from __future__ import absolute_import, division, print_function, unicode_literals

from math import asin, atan2, ceil, cos, degrees, radians, sin, sqrt


def position_to_line(x, y, x1, x2, y1, y2):
    """tests if a point pX(x,y) is Left|On|Right of an infinite line from p1 to p2
            Return: -1 for pX left of the line from! p1 to! p2
                    0 for pX on the line [is not needed]
                    1 for pX  right of the line
                    this approach is only valid because we already know that y lies within ]y1;y2]
        """

    if x1 < x2:
        # p2 is further right than p1
        if x > x2:
            # pX is further right than p2,
            if y1 > y2:
                return -1
            else:
                return 1

        if x < x1:
            # pX is further left than p1
            if y1 > y2:
                # so it has to be right of the line p1-p2
                return 1
            else:
                return -1

        x1gtx2 = False

    else:
        # p1 is further right than p2
        if x > x1:
            # pX is further right than p1,
            if y1 > y2:
                # so it has to be left of the line p1-p2
                return -1
            else:
                return 1

        if x < x2:
            # pX is further left than p2,
            if y1 > y2:
                # so it has to be right of the line p1-p2
                return 1
            else:
                return -1

        # TODO is no return also accepted
        if x1 == x2 and x == x1:
            # could also be equal
            return 0

        # x1 greater than x2
        x1gtx2 = True

    # x is between [x1;x2]
    # compute the x-intersection of the point with the line p1-p2
    # delta_y cannot be 0 here because of the condition 'y lies within ]y1;y2]'
    # NOTE: bracket placement is important here (we are dealing with 64-bit ints!). first divide then multiply!
    delta_x = ((y - y1) * ((x2 - x1) / (y2 - y1))) + x1 - x

    if delta_x > 0:
        if x1gtx2:
            if y1 > y2:
                return 1
            else:
                return -1

        else:
            if y1 > y2:
                return 1
            else:
                return -1

    elif delta_x == 0:
        return 0

    else:
        if x1gtx2:
            if y1 > y2:
                return -1
            else:
                return 1

        else:
            if y1 > y2:
                return -1
            else:
                return 1


def inside_polygon(x, y, coords):
    wn = 0
    i = 0
    y1 = coords[1][0]
    # TODO why start with both y1=y2= y[0]?
    for y2 in coords[1]:
        if y1 < y:
            if y2 >= y:
                x1 = coords[0][i - 1]
                x2 = coords[0][i]
                # print(long2coord(x), long2coord(y), long2coord(x1), long2coord(x2), long2coord(y1), long2coord(y2),
                #       position_to_line(x, y, x1, x2, y1, y2))
                if position_to_line(x, y, x1, x2, y1, y2) == -1:
                    # point is left of line
                    # return true when its on the line?! this is very unlikely to happen!
                    # and would need to be checked every time!
                    wn += 1

        else:
            if y2 < y:
                x1 = coords[0][i - 1]
                x2 = coords[0][i]
                if position_to_line(x, y, x1, x2, y1, y2) == 1:
                    # point is right of line
                    wn -= 1

        y1 = y2
        i += 1

    y1 = coords[1][-1]
    y2 = coords[1][0]
    if y1 < y:
        if y2 >= y:
            x1 = coords[0][-1]
            x2 = coords[0][0]
            if position_to_line(x, y, x1, x2, y1, y2) == -1:
                # point is left of line
                wn += 1
    else:
        if y2 < y:
            x1 = coords[0][-1]
            x2 = coords[0][0]
            if position_to_line(x, y, x1, x2, y1, y2) == 1:
                # point is right of line
                wn -= 1
    return wn != 0


def all_the_same(pointer, length, id_list):
    # List mustn't be empty or Null
    # There is at least one

    element = id_list[pointer]
    pointer += 1

    while pointer < length:
        if element != id_list[pointer]:
            return -1
        pointer += 1

    return element


def cartesian2rad(x, y, z):
    return atan2(y, x), asin(z)


def cartesian2coords(x, y, z):
    return degrees(atan2(y, x)), degrees(asin(z))


def x_rotate(rad, point):
    # Attention: this rotation uses radians!
    # x stays the same
    sin_rad = sin(rad)
    cos_rad = cos(rad)
    return point[0], point[1] * cos_rad + point[2] * sin_rad, point[2] * cos_rad - point[1] * sin_rad


def y_rotate(rad, point):
    # y stays the same
    # this is actually a rotation with -rad (use symmetry of sin/cos)
    sin_rad = sin(rad)
    cos_rad = cos(rad)
    return point[0] * cos_rad + point[2] * sin_rad, point[1], point[2] * cos_rad - point[0] * sin_rad


def coords2cartesian(lng_rad, lat_rad):
    return cos(lng_rad) * cos(lat_rad), sin(lng_rad) * cos(lat_rad), sin(lat_rad)


def distance_to_point_on_equator(lng_rad, lat_rad, lng_rad_p1):
    """
    uses the simplified haversine formula for this special case (lat_p1 = 0)
    :param lng_rad: the longitude of the point in radians
    :param lat_rad: the latitude of the point
    :param lng_rad_p1: the latitude of the point1 on the equator (lat=0)
    :return: distance between the point and p1 (lng_rad_p1,0) in km
    this is only an approximation since the earth is not a real sphere
    """
    # 2* for the distance in rad and * 12742 (mean diameter of earth) for the distance in km
    return 12742 * asin(sqrt(((sin(lat_rad / 2)) ** 2 + cos(lat_rad) * (sin((lng_rad - lng_rad_p1) / 2)) ** 2)))


def haversine(lng_p1, lat_p1, lng_p2, lat_p2):
    """
    :param lng_p1: the longitude of point 1 in radians
    :param lat_p1: the latitude of point 1 in radians
    :param lng_p2: the longitude of point 1 in radians
    :param lat_p2: the latitude of point 1 in radians
    :return: distance between p1 and p2 in km
    this is only an approximation since the earth is not a real sphere
    """
    # 2* for the distance in rad and * 12742(mean diameter of earth) for the distance in km
    return 12742 * asin(
        sqrt(((sin((lat_p1 - lat_p2) / 2)) ** 2 + cos(lat_p2) * cos(lat_p1) * (sin((lng_p1 - lng_p2) / 2)) ** 2)))


def compute_min_distance(lng_rad, lat_rad, p0_lng, p0_lat, pm1_lng, pm1_lat, p1_lng, p1_lat):
    """
    :param lng_rad: lng of px in radians
    :param lat_rad: lat of px in radians
    :param p0_lng: lng of p0 in radians
    :param p0_lat: lat of p0 in radians
    :param pm1_lng: lng of pm1 in radians
    :param pm1_lat: lat of pm1 in radians
    :param p1_lng: lng of p1 in radians
    :param p1_lat: lat of p1 in radians
    :return: shortest distance between pX and the polygon section (pm1---p0---p1) in radians
    """

    # rotate coordinate system (= all the points) so that p0 would have lat_rad=lng_rad=0 (=origin)
    # z rotation is simply subtracting the lng_rad
    # convert the points to the cartesian coordinate system
    px_cartesian = coords2cartesian(lng_rad - p0_lng, lat_rad)
    p1_cartesian = coords2cartesian(p1_lng - p0_lng, p1_lat)
    pm1_cartesian = coords2cartesian(pm1_lng - p0_lng, pm1_lat)

    px_cartesian = y_rotate(p0_lat, px_cartesian)
    p1_cartesian = y_rotate(p0_lat, p1_cartesian)
    pm1_cartesian = y_rotate(p0_lat, pm1_cartesian)

    # for both p1 and pm1 separately do:

    # rotate coordinate system so that this point also has lat_p1_rad=0 and lng_p1_rad>0 (p0 does not change!)
    rotation_rad = atan2(p1_cartesian[2], p1_cartesian[1])
    p1_cartesian = x_rotate(rotation_rad, p1_cartesian)
    lng_p1_rad = atan2(p1_cartesian[1], p1_cartesian[0])
    px_retrans_rad = cartesian2rad(*x_rotate(rotation_rad, px_cartesian))

    # if lng_rad of px is between 0 (<-point1) and lng_rad of point 2:
    # the distance between point x and the 'equator' is the shortest
    # if the point is not between p0 and p1 the distance to the closest of the two points should be used
    # so clamp/clip the lng_rad of px to the interval of [0; lng_rad p1] and compute the distance with it
    temp_distance = distance_to_point_on_equator(px_retrans_rad[0], px_retrans_rad[1],
                                                 max(min(px_retrans_rad[0], lng_p1_rad), 0))

    # ATTENTION: vars are being reused. p1 is actually pm1 here!
    rotation_rad = atan2(pm1_cartesian[2], pm1_cartesian[1])
    p1_cartesian = x_rotate(rotation_rad, pm1_cartesian)
    lng_p1_rad = atan2(p1_cartesian[1], p1_cartesian[0])
    px_retrans_rad = cartesian2rad(*x_rotate(rotation_rad, px_cartesian))

    return min(temp_distance, distance_to_point_on_equator(px_retrans_rad[0], px_retrans_rad[1],
                                                           max(min(px_retrans_rad[0], lng_p1_rad), 0)))


def int2coord(int32):
    return float(int32 / 10 ** 7)


def coord2int(double):
    return int(double * 10 ** 7)


def distance_to_polygon_exact(lng_rad, lat_rad, nr_points, points, trans_points):
    # transform all points (long long) to coords
    for i in range(nr_points):
        trans_points[0][i] = radians(int2coord(points[0][i]))
        trans_points[1][i] = radians(int2coord(points[1][i]))

    # check points -2, -1, 0 first
    pm1_lng = trans_points[0][0]
    pm1_lat = trans_points[1][0]

    p1_lng = trans_points[0][-2]
    p1_lat = trans_points[1][-2]
    min_distance = compute_min_distance(lng_rad, lat_rad, trans_points[0][-1], trans_points[1][-1], pm1_lng, pm1_lat,
                                        p1_lng, p1_lat)

    index_p0 = 1
    index_p1 = 2
    for i in range(int(ceil((nr_points / 2) - 1))):
        p1_lng = trans_points[0][index_p1]
        p1_lat = trans_points[1][index_p1]
        min_distance = min(min_distance,
                           compute_min_distance(lng_rad, lat_rad, trans_points[0][index_p0], trans_points[1][index_p0],
                                                pm1_lng, pm1_lat, p1_lng, p1_lat))

        index_p0 += 2
        index_p1 += 2
        pm1_lng = p1_lng
        pm1_lat = p1_lat

    return min_distance


def distance_to_polygon(lng_rad, lat_rad, nr_points, points):
    min_distance = 40100000

    for i in range(nr_points):
        min_distance = min(min_distance, haversine(lng_rad, lat_rad, radians(int2coord(points[0][i])),
                                                   radians(int2coord(points[1][i]))))

    return min_distance
