"""utility functions

JIT compiled for efficiency in case `numba` is installed

"""

import numpy as np

from timezonefinder.utils_numba import (
    CoordType,
    is_valid_lat,
    is_valid_lng,
    pt_in_poly_python,
)

try:
    from numba import njit, boolean, f8
    from numba.types import Array

    using_numba = True
except ImportError:
    using_numba = False
    # replace Numba functionality with "transparent" implementations
    from timezonefinder._numba_replacements import njit, boolean, Array, f8

FloatCoordType1D = Array(f8, 1, "A")


@njit(boolean(CoordType, CoordType), cache=True)
def any_pt_in_poly(coords1: np.ndarray, coords2: np.ndarray) -> bool:
    # pt = points[:, i]
    for pt in coords1.T:
        if pt_in_poly_python(pt[0], pt[1], coords2):
            return True
    return False


@njit(boolean(CoordType, CoordType), cache=True)
def any_edge_crossing(ring1: np.ndarray, ring2: np.ndarray) -> bool:
    """True if an edge of closed ring ``ring1`` properly crosses an edge of ``ring2``.

    Two rings can overlap with no vertex of either inside the other - an edge passing
    clean through - which is the case vertex inclusion alone cannot see. It is not
    hypothetical: at H3 resolution 4 a cell in the Strait of Malacca lies inside an ocean
    polygon whose boundary crosses it without either shape's vertices being enclosed, and
    the cell was recorded as not covered.

    Only *proper* crossings are reported. An edge that merely touches a vertex of the
    other ring is a measure-zero case that the vertex tests already answer, and treating
    it here would mean handling collinear overlap for no gain.

    Coordinates are translated by ``ring1``'s first vertex before the orientation tests.
    They are scaled by 10^7, so a raw difference reaches ~3.6e9 and the cross products
    would overflow ``int64``; after translation everything that survives the bounding-box
    rejection is within a cell's extent of the origin, which keeps the products small
    enough to stay exact.
    """
    n1 = ring1.shape[1]
    n2 = ring2.shape[1]
    if n1 < 2 or n2 < 2:
        return False

    ox = np.int64(ring1[0, 0])
    oy = np.int64(ring1[1, 0])

    # ring1 is a hexagon: six edges, so its bounding box is worth computing once and
    # testing every edge of the much longer ring2 against
    xmin = np.int64(ring1[0, 0])
    xmax = xmin
    ymin = np.int64(ring1[1, 0])
    ymax = ymin
    for i in range(1, n1):
        x = np.int64(ring1[0, i])
        y = np.int64(ring1[1, i])
        if x < xmin:
            xmin = x
        if x > xmax:
            xmax = x
        if y < ymin:
            ymin = y
        if y > ymax:
            ymax = y

    for j in range(n2):
        k = j + 1 if j + 1 < n2 else 0
        qx1 = np.int64(ring2[0, j])
        qy1 = np.int64(ring2[1, j])
        qx2 = np.int64(ring2[0, k])
        qy2 = np.int64(ring2[1, k])
        # reject the overwhelming majority of edges before any arithmetic that matters
        if qx1 < xmin and qx2 < xmin:
            continue
        if qx1 > xmax and qx2 > xmax:
            continue
        if qy1 < ymin and qy2 < ymin:
            continue
        if qy1 > ymax and qy2 > ymax:
            continue
        qx1 -= ox
        qy1 -= oy
        qx2 -= ox
        qy2 -= oy
        rqx = qx2 - qx1
        rqy = qy2 - qy1
        for i in range(n1):
            m = i + 1 if i + 1 < n1 else 0
            px1 = np.int64(ring1[0, i]) - ox
            py1 = np.int64(ring1[1, i]) - oy
            px2 = np.int64(ring1[0, m]) - ox
            py2 = np.int64(ring1[1, m]) - oy
            d1 = rqx * (py1 - qy1) - rqy * (px1 - qx1)
            d2 = rqx * (py2 - qy1) - rqy * (px2 - qx1)
            if (d1 > 0) == (d2 > 0):
                continue
            rpx = px2 - px1
            rpy = py2 - py1
            d3 = rpx * (qy1 - py1) - rpy * (qx1 - px1)
            d4 = rpx * (qy2 - py1) - rpy * (qx2 - px1)
            if (d3 > 0) != (d4 > 0):
                return True
    return False


@njit(boolean(CoordType, CoordType), cache=True)
def fully_contained_in_hole(poly: np.ndarray, hole: np.ndarray) -> bool:
    for pt in poly.T:
        if not pt_in_poly_python(pt[0], pt[1], hole):
            return False
    return True


@njit(boolean(FloatCoordType1D), cache=True)
def is_valid_lat_vec(lats: np.ndarray) -> bool:
    for lat in lats:
        if not is_valid_lat(lat):
            return False
    return True


@njit(boolean(FloatCoordType1D), cache=True)
def is_valid_lng_vec(lngs: np.ndarray) -> bool:
    for lng in lngs:
        if not is_valid_lng(lng):
            return False
    return True
