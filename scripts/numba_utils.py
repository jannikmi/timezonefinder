import numba
import numpy as np


@numba.njit(cache=True)
def inside_polygon(x: float, y: float, coordinates: np.ndarray) -> bool:
    """
    TODO put in utils and test
    Implementing the ray casting point in polygon test algorithm
    cf. https://en.wikipedia.org/wiki/Point_in_polygon#Ray_casting_algorithm
    :param x:
    :param y:
    :param coordinates: a polygon represented by a list containing two lists (x and y coordinates):
        [ [x1,x2,x3...], [y1,y2,y3...]]
        those lists are actually numpy arrays which are bei
        ng read directly from a binary file
    :return: true if the point (x,y) lies within the polygon

    Some overflow considerations for the critical part of comparing the line segment slopes:

        (y2 - y) * (x2 - x1) <= delta_y_max * delta_x_max
        (y2 - y1) * (x2 - x) <= delta_y_max * delta_x_max
        delta_y_max * delta_x_max = 180 * 360 < 65 x10^3

    Instead of calculating with float I decided using just ints (by multiplying with 10^7). That gives us:

        delta_y_max * delta_x_max = 180x10^7 * 360x10^7
        delta_y_max * delta_x_max <= 65x10^17

    So these numbers need up to log_2(65 x10^17) ~ 63 bits to be represented! Even though values this big should never
     occur in practice (timezone polygons do not span the whole lng lat coordinate space),
     32bit accuracy hence is not safe to use here!
     Python 2.2 automatically uses the appropriate int data type preventing overflow
     (cf. https://www.python.org/dev/peps/pep-0237/),
     but here the data types are numpy internal static data types. The data is stored as int32
     -> use int64 when comparing slopes!

    ATTENTION: `continue` must not be used here
        in order to not skip variable replacement for considering the next point!
    """
    contained = False
    # the edge from the last to the first point is checked first
    i = -1
    y1 = coordinates[1, -1]
    y_gt_y1 = y > y1
    for y2 in coordinates[1]:
        y_gt_y2 = y > y2
        if y_gt_y1 ^ y_gt_y2:  # XOR
            # [p1-p2] crosses horizontal line in p
            x1 = coordinates[0, i]
            x2 = coordinates[0, i + 1]
            # only count crossings "right" of the point ( >= x)
            x_le_x1 = x <= x1
            x_le_x2 = x <= x2
            if x_le_x1 or x_le_x2:
                if x_le_x1 and x_le_x2:
                    # p1 and p2 are both to the right -> valid crossing
                    contained = not contained
                else:
                    # compare the slope of the line [p1-p2] and [p-p2]
                    # depending on the position of p2 this determines whether
                    # the polygon edge is right or left of the point
                    # to avoid expensive division the divisors (of the slope dy/dx) are brought to the other side
                    # ( dy/dx > a  ==  dy > a * dx )
                    # only one of the points is to the right
                    slope1 = (y2 - y) * (x2 - x1)
                    slope2 = (y2 - y1) * (x2 - x)
                    # NOTE: accept slope equality to also detect if p lies directly on an edge
                    if y_gt_y1:
                        if slope1 <= slope2:
                            contained = not contained
                    elif slope1 >= slope2:  # NOT y_gt_y1
                        contained = not contained

        # next point
        y1 = y2
        y_gt_y1 = y_gt_y2
        i += 1

    return contained


@numba.njit(cache=True)
def any_pt_in_poly(coords1, coords2):
    # pt = points[:, i]
    for pt in coords1.T:
        if inside_polygon(pt[0], pt[1], coords2):
            return True
    return False


@numba.njit(cache=True)
def polygons_overlap(poly1: np.ndarray, poly2: np.ndarray) -> bool:
    # if any point lies within the other polygon (both ways have to be checked!
    return any_pt_in_poly(poly2, poly1) or any_pt_in_poly(poly1, poly2)


@numba.njit(cache=True)
def fully_contained_in_hole(poly: np.ndarray, hole: np.ndarray) -> bool:
    for pt in poly.T:
        if not inside_polygon(pt[0], pt[1], hole):
            return False
    return True
