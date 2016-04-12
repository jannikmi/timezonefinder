from math import radians, cos, sin, asin, sqrt, degrees, ceil, atan2


def inside_polygon(x, y, coords):
    wn = 0
    i = 0
    y1 = coords[1][0]
    for y2 in coords[1]:
        if y1 < y:
            if y2 >= y:
                x1 = coords[0][i - 1]
                x2 = coords[0][i]
                """tests if a point is Left|On|Right of an infinite line from p1 to p2
                //    Return: >0 for xy left of the line from! p1 to! p2
                //            =0 for xy on the line
                            <0 for xy  right of the line
                everything has to be divided by 1000 because otherwise there would be overflow with int8
                """
                if ((x2 - x1) / 1000) * ((y - y1) / 1000) - ((x - x1) / 1000) * ((y2 - y1) / 1000) > 0:
                    wn += 1

        else:
            if y2 < y:
                x1 = coords[0][i - 1]
                x2 = coords[0][i]
                if ((x2 - x1) / 1000) * ((y - y1) / 1000) - ((x - x1) / 1000) * ((y2 - y1) / 1000) < 0:
                    wn -= 1

        y1 = y2
        i += 1

    y1 = coords[1][-1]
    y2 = coords[1][0]
    if y1 < y:
        if y2 >= y:
            x1 = coords[0][-1]
            x2 = coords[0][0]
            if ((x2 - x1) / 1000) * ((y - y1) / 1000) - ((x - x1) / 1000) * ((y2 - y1) / 1000) > 0:
                wn += 1
    else:
        if y2 < y:
            x1 = coords[0][-1]
            x2 = coords[0][0]
            if ((x2 - x1) / 1000) * ((y - y1) / 1000) - ((x - x1) / 1000) * ((y2 - y1) / 1000) < 0:
                wn -= 1
    return wn != 0


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


def y_rotate(degree, point):
    # y stays the same
    degree = radians(-degree)
    sin_rad = sin(degree)
    cos_rad = cos(degree)
    return point[0] * cos_rad - point[2] * sin_rad, point[1], point[0] * sin_rad + point[2] * cos_rad


def coords2cartesian(lng, lat):
    lng = radians(lng)
    lat = radians(lat)
    return cos(lng) * cos(lat), sin(lng) * cos(lat), sin(lat)


def distance_to_point_on_equator(lng_rad, lat_rad, lng_rad_p1):
    """
    uses the simplified haversine formula for this special case
    :param lng_rad: the longitude of the point in radians
    :param lat_rad: the latitude of the point
    :param lng_rad_p1: the latitude of the point1 on the equator (lat=0)
    :return: distance between the point and p1 (lng_rad_p1,0) in radians
    """
    return 2 * asin(sqrt((sin(lat_rad) / 2) ** 2 + cos(lat_rad) * sin((lng_rad - lng_rad_p1) / 2) ** 2))


def haversine(lng_p1, lat_p1, lng_p2, lat_p2):
    """
    :param lng_p1: the longitude of point 1 in radians
    :param lat_p1: the latitude of point 1 in radians
    :param lng_p2: the longitude of point 1 in radians
    :param lat_p2: the latitude of point 1 in radians
    :return: distance between p1 and p2 in radians
    """
    return 2 * asin(sqrt(sin((lat_p1 - lat_p2) / 2) ** 2 + cos(lat_p2) * cos(lat_p1) * sin((lng_p1 - lng_p2) / 2) ** 2))


def compute_min_distance(lng, lat, p0_lng, p0_lat, pm1_lng, pm1_lat, p1_lng, p1_lat):
    """
    :param lng: lng of px in degree
    :param lat: lat of px in degree
    :param p0_lng: lng of p0 in degree
    :param p0_lat: lat of p0 in degree
    :param pm1_lng: lng of pm1 in degree
    :param pm1_lat: lat of pm1 in degree
    :param p1_lng: lng of p1 in degree
    :param p1_lat: lat of p1 in degree
    :return: shortest distance between pX and the polygon section (pm1---p0---p1) in radians
    """
    # rotate coordinate system (= all the points) so that p0 would have lat=lng=0 (=origin)
    # z rotation is simply substracting the lng
    # convert the points to the cartesian coorinate system
    px_cartesian = coords2cartesian(lng - p0_lng, lat)
    p1_cartesian = coords2cartesian(p1_lng - p0_lng, p1_lat)
    pm1_cartesian = coords2cartesian(pm1_lng - p0_lng, pm1_lat)

    px_cartesian = y_rotate(p0_lat, px_cartesian)
    p1_cartesian = y_rotate(p0_lat, p1_cartesian)
    pm1_cartesian = y_rotate(p0_lat, pm1_cartesian)

    # for both p1 and pm1 separately do:

    # rotate coordinate system so that this point also has lat=0 (p0 does not change!)
    rotation_rad = atan2(p1_cartesian[2], p1_cartesian[1])
    p1_cartesian = x_rotate(rotation_rad, p1_cartesian)
    lng_p1_rad = atan2(p1_cartesian[1], p1_cartesian[0])
    px_retrans_rad = cartesian2rad(*x_rotate(rotation_rad, px_cartesian))

    # if lng of px is between 0 (<-point1) and lng of point 2:
    # the distance between point x and the 'equator' is the shortest
    # if the point is not between p0 and p1 the distance to the closest of the two points should be used
    # so clamp/clip the lng of px to the interval of [0; lng p1] and compute the distance with it
    temp_distance = distance_to_point_on_equator(px_retrans_rad[0], px_retrans_rad[1],
                                                 max(min(px_retrans_rad[0], lng_p1_rad), 0))

    # ATTENTION: vars are being reused. p1 is actually pm1 here!
    rotation_rad = atan2(pm1_cartesian[2], pm1_cartesian[1])
    p1_cartesian = x_rotate(rotation_rad, pm1_cartesian)
    lng_p1_rad = atan2(p1_cartesian[1], p1_cartesian[0])
    px_retrans_rad = cartesian2rad(*x_rotate(rotation_rad, px_cartesian))

    return min(temp_distance,
               distance_to_point_on_equator(px_retrans_rad[0], px_retrans_rad[1],
                                            max(min(px_retrans_rad[0], lng_p1_rad), 0)))


def long2coord(longlong):
    return float(longlong / 10 ** 15)


def coord2long(double):
    return int(double * 10 ** 15)


def distance_to_polygon(lng, lat, nr_points, points, trans_points):
    # transform all points (long long) to coords
    for i in range(nr_points):
        trans_points[0][i] = long2coord(points[0][i])
        trans_points[1][i] = long2coord(points[1][i])

    # check points -2, -1, 0 first
    pm1_lng = trans_points[0][0]
    pm1_lat = trans_points[1][0]

    p1_lng = trans_points[0][-2]
    p1_lat = trans_points[1][-2]
    min_distance = compute_min_distance(lng, lat, trans_points[0][-1], trans_points[1][-1], pm1_lng, pm1_lat, p1_lng,
                                        p1_lat)

    index_p0 = 1
    index_p1 = 2
    for i in range(int(ceil((nr_points / 2) - 1))):
        p1_lng = trans_points[0][index_p1]
        p1_lat = trans_points[1][index_p1]

        distance = compute_min_distance(lng, lat, trans_points[0][index_p0], trans_points[1][index_p0], pm1_lng,
                                        pm1_lat, p1_lng, p1_lat)
        if distance < min_distance:
            min_distance = distance

        index_p0 += 2
        index_p1 += 2
        pm1_lng = p1_lng
        pm1_lat = p1_lat

    return min_distance
