"""Which polygon owns a point lying exactly on a boundary, on every kernel.

The ray cast counts an edge when the edge spans the query's latitude half-open,
``(min, max]``, and lies at or east of the query, the query's own position included.
Together those make one rule, which these tests pin:

    a polygon owns a point on its boundary exactly when its interior lies immediately
    west of the point - or, where the boundary runs due east-west, immediately south.

Equivalently, every kernel answers for the point nudged an infinitesimal distance west
and then a far smaller one south, a point that never lies on an edge. So a rectangle
``[x0, x1] x [y0, y1]`` owns exactly ``(x0, x1] x (y0, y1]`` - its east and north edges
but neither end of them that touches the west or the south one - and two polygons
sharing a boundary never both own a point on it.

What rests on that, and fails silently rather than loudly if a kernel change moves
boundary points to the other polygon:

* **Answers on a shared border do not depend on candidate order.** The work optimizer in
  ``scripts/shortcut_ordering.py`` reorders zones whose candidates only touch - it
  refuses a positive-area overlap, never a shared edge - and that leaves every answer
  unchanged only because exactly one polygon owns each point of the edge they share.
* **A shortcut cell aligned with longitude and latitude can list exactly the polygons
  its points can belong to.** A half-open cell ``(x0, x1] x (y0, y1]`` contains only
  points whose owner's interior meets the cell's open interior, so a polygon touching
  the cell's west or south edge from outside never needs to be a candidate.
* **No polygon owns a point on the -180° meridian or the -90° parallel**, since nothing
  lies west or south of them. That is why a lookup reads -180° as +180° and -90° as the
  point one unit north before it tests a polygon (``utils.query2int``); without that,
  the shortcut index rather than geometry would decide what it answers there.

``tests/test_acceleration_paths.py`` holds the kernels to one another over the real
data; what it cannot show is which answer they agree on at a boundary, because real
queries almost never land on one.
"""

from collections.abc import Callable

import numpy as np
import pytest
from shapely import Point, Polygon

from timezonefinder import TimezoneFinder, utils, utils_clang, utils_numba
from timezonefinder._block_index import block_latitude_ranges
from timezonefinder.block_payload import (
    block_vertex_counts,
    encode_ring,
    ring_payload_offsets,
)
from timezonefinder.configs import (
    BLOCK_PAYLOAD_OFFSET_DTYPE,
    COORD2INT_FACTOR,
    MAX_LAT_VAL,
    MAX_LNG_VAL,
    SOURCE_COORD_STEP,
)

pytestmark = pytest.mark.unit

# Shapes are drawn on a lattice of whole units and queried at every lattice point, so
# that the queries land on vertices, on axis-aligned edges and - where a slope allows -
# on sloped edges. One unit is one source grid step, which the packed payload requires
# of every stored vertex.
UNIT = SOURCE_COORD_STEP

# The nudge the oracle applies, in units. West far more than south, so that a point on a
# sloped edge is decided by which side of the edge it is on and not by the edge's slope:
# SOUTH_NUDGE times the largest run per unit of rise among the sloped edges below stays
# well under WEST_NUDGE, and WEST_NUDGE well under 1 / (the largest rise of any edge
# below), the closest a lattice point that is *not* on an edge can come to one along its
# own latitude. Neither nudged coordinate is a
# fraction with a small denominator, so the nudged point is never on an edge either.
WEST_NUDGE = 1e-4
SOUTH_NUDGE = 1e-8

# vertex lists in units, counter-clockwise; none closes itself - every kernel adds the
# edge from the last vertex back to the first
SHAPES: dict[str, list[tuple[int, int]]] = {
    "rectangle": [(0, 0), (6, 0), (6, 4), (0, 4)],
    # a vertex in the middle of the east edge, the shape `utils_test.py` starts from
    "rectangle with a collinear vertex": [(0, 0), (6, 0), (6, 2), (6, 4), (0, 4)],
    # reflex corners on axis-aligned lines, and a notch whose sides face each other
    "u shape": [(0, 0), (8, 0), (8, 6), (6, 6), (6, 2), (2, 2), (2, 6), (0, 6)],
    # every edge sloped, every vertex a sharp turn
    "diamond": [(4, 0), (8, 4), (4, 8), (0, 4)],
    # sloped edges at several gradients, with east-west edges top and bottom
    "trapezoid": [(0, 0), (12, 0), (9, 6), (2, 6)],
    # steep and shallow edges alternating, and horizontal runs between them
    "zigzag": [
        (0, 0),
        (2, 6),
        (4, 0),
        (6, 0),
        (8, 6),
        (12, 6),
        (12, 8),
        (6, 10),
        (0, 8),
    ],
}

# Vertices per block for the packed kernels: small enough that every shape above is cut
# into several blocks, so blocks and the vertices bridging them are crossed too.
PACKED_BLOCK_SIZE = 3

# Where each shape is placed for the kernels, in stored units. The rule is the same
# everywhere because the kernels only ever form coordinate differences; the edges of the
# coordinate domain are included because that is where it decides that no polygon owns
# a point on the -180° meridian or the -90° parallel, and that one ending on +180° or
# +90° owns its points there.
_LNG_EDGE = int(MAX_LNG_VAL * COORD2INT_FACTOR)
_LAT_EDGE = int(MAX_LAT_VAL * COORD2INT_FACTOR)


def _origin(placement: str, vertices: list[tuple[int, int]]) -> tuple[int, int]:
    if placement == "at the origin":
        return 0, 0
    if placement == "west and south edges on -180 and -90":
        return (
            -_LNG_EDGE - min(x for x, _ in vertices) * UNIT,
            -_LAT_EDGE - min(y for _, y in vertices) * UNIT,
        )
    assert placement == "east and north edges on +180 and +90"
    return (
        _LNG_EDGE - max(x for x, _ in vertices) * UNIT,
        _LAT_EDGE - max(y for _, y in vertices) * UNIT,
    )


PLACEMENTS = [
    "at the origin",
    "west and south edges on -180 and -90",
    "east and north edges on +180 and +90",
]

# A kernel prepared for one ring: ``(x, y) -> owned``.
Prepared = Callable[[int, int], bool]


def _python(function: Callable) -> Callable:
    """The interpreted form of a ``utils_numba`` kernel, whether or not numba compiled it.

    It is the backend of an install with neither numba nor the C extension, and the one
    whose integer arithmetic numba does not cast - so it is tested in its own right. With
    numba installed the helpers it calls stay compiled; the test environments without
    numba run it wholly interpreted.
    """
    return getattr(function, "py_func", function)


def _plain(kernel: Callable) -> Callable[[np.ndarray], Prepared]:
    def prepare(ring: np.ndarray) -> Prepared:
        return lambda x, y: bool(kernel(x, y, ring))

    return prepare


def _packed(kernel: Callable, buffers: Callable) -> Callable[[np.ndarray], Prepared]:
    """Encode the ring as a one-ring collection, the way the converter encodes a stored
    one, and hand the kernel what a collection hands it."""

    def prepare(ring: np.ndarray) -> Prepared:
        nr_coords = ring.shape[1]
        ranges = block_latitude_ranges(ring[1], PACKED_BLOCK_SIZE)
        payload, bases, widths = encode_ring(ring, ranges, PACKED_BLOCK_SIZE)
        offsets = ring_payload_offsets(
            block_vertex_counts(nr_coords, PACKED_BLOCK_SIZE), widths
        ).astype(BLOCK_PAYLOAD_OFFSET_DTYPE)
        wrapped = buffers(payload, ranges, bases, widths, offsets)
        nr_blocks = len(ranges)
        return lambda x, y: bool(
            kernel(x, y, nr_coords, PACKED_BLOCK_SIZE, 0, nr_blocks, *wrapped)
        )

    return prepare


def _kernels() -> dict[str, Callable[[np.ndarray], Prepared]]:
    """Every point-in-polygon implementation a lookup can be bound to, by name.

    The ``utils_numba`` pair appears once more as plain Python when numba compiled it:
    a compiled dispatcher and its interpreted source are two implementations here,
    though only one of them can be the bound backend of any one process. A missing C
    extension drops its pair, and ``utils_test.py`` is what fails loudly on that.
    """
    kernels = {
        "python": _plain(_python(utils_numba.pt_in_poly_python)),
        "python packed": _packed(
            _python(utils_numba.pt_in_poly_packed), utils_numba.packed_buffers_numba
        ),
    }
    if utils_numba.using_numba:
        kernels["numba"] = _plain(utils_numba.pt_in_poly_python)
        kernels["numba packed"] = _packed(
            utils_numba.pt_in_poly_packed, utils_numba.packed_buffers_numba
        )
    if utils.clang_extension_loaded:
        kernels["clang"] = _plain(utils_clang.pt_in_poly_clang)
        kernels["clang packed"] = _packed(
            utils_clang.pt_in_poly_clang_packed, utils_clang.packed_buffers_clang
        )
    return kernels


KERNELS = _kernels()


def _ring(vertices: list[tuple[int, int]], origin: tuple[int, int]) -> np.ndarray:
    """The ``(2, N)`` scaled ``int32`` ring the kernels read, placed at ``origin``."""
    ring = np.array(vertices, dtype=np.int64).T * UNIT
    ring[0] += origin[0]
    ring[1] += origin[1]
    return np.ascontiguousarray(ring, dtype=np.int32)


def _owns_by_the_rule(polygon: Polygon, x: int, y: int) -> bool:
    """The rule, independently of any kernel: is the nudged point inside?"""
    return polygon.contains(Point(x - WEST_NUDGE, y - SOUTH_NUDGE))


def _lattice(vertices: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Every lattice point of the shape's bounding box widened by one unit."""
    xs = [x for x, _ in vertices]
    ys = [y for _, y in vertices]
    return [
        (x, y)
        for x in range(min(xs) - 1, max(xs) + 2)
        for y in range(min(ys) - 1, max(ys) + 2)
    ]


@pytest.mark.parametrize("kernel_name", sorted(KERNELS))
@pytest.mark.parametrize(
    "point, owned",
    [
        # the four edges, at their midpoints
        ((6, 2), True),  # east
        ((3, 4), True),  # north
        ((0, 2), False),  # west
        ((3, 0), False),  # south
        # the four corners: only the one joining an owned pair of edges
        ((6, 4), True),  # north-east
        ((0, 4), False),  # north-west
        ((6, 0), False),  # south-east
        ((0, 0), False),  # south-west
    ],
)
@pytest.mark.parametrize("placement", PLACEMENTS)
def test_a_rectangle_owns_its_east_and_north_edges_only(
    kernel_name: str, point: tuple[int, int], owned: bool, placement: str
):
    """The rule where it reads most plainly, and where an aligned cell meets it."""
    vertices = SHAPES["rectangle"]
    origin = _origin(placement, vertices)
    owns = KERNELS[kernel_name](_ring(vertices, origin))
    assert owns(origin[0] + point[0] * UNIT, origin[1] + point[1] * UNIT) is owned


@pytest.mark.parametrize("kernel_name", sorted(KERNELS))
@pytest.mark.parametrize("shape_name", sorted(SHAPES))
@pytest.mark.parametrize("placement", PLACEMENTS)
@pytest.mark.usefixtures("strict_numpy_warnings")
def test_each_kernel_owns_exactly_the_points_the_rule_assigns(
    kernel_name: str, shape_name: str, placement: str
):
    """Every lattice point in and around each shape - vertices, axis-aligned edges,
    sloped edges, the interior and the outside - against an oracle that knows nothing
    of ray casting."""
    vertices = SHAPES[shape_name]
    origin = _origin(placement, vertices)
    owns = KERNELS[kernel_name](_ring(vertices, origin))
    polygon = Polygon(vertices)
    lattice = _lattice(vertices)
    # what makes this a test of the boundary at all: every vertex is a lattice point
    assert sum(polygon.boundary.covers(Point(p)) for p in lattice) >= len(vertices)
    wrong = [
        (x, y)
        for x, y in lattice
        if owns(origin[0] + x * UNIT, origin[1] + y * UNIT)
        != _owns_by_the_rule(polygon, x, y)
    ]
    assert not wrong, (
        f"{kernel_name} disagrees with the boundary rule on the {shape_name} placed "
        f"{placement} at {len(wrong)} lattice points (in units from the shape's "
        f"origin), first {wrong[:5]}"
    )


# Five tiles of one square, sharing every kind of boundary: vertical edges, horizontal
# ones, a point where four corners meet, and a diagonal.
TILES: dict[str, list[tuple[int, int]]] = {
    "south-west": [(0, 0), (4, 0), (4, 4), (0, 4)],
    "south-east": [(4, 0), (8, 0), (8, 4), (4, 4)],
    "north-west": [(0, 4), (4, 4), (4, 8), (0, 8)],
    # the north-east quarter, cut along its south-west to north-east diagonal
    "north-east lower": [(4, 4), (8, 4), (8, 8)],
    "north-east upper": [(4, 4), (8, 8), (4, 8)],
}


@pytest.mark.parametrize("kernel_name", sorted(KERNELS))
@pytest.mark.usefixtures("strict_numpy_warnings")
def test_polygons_sharing_a_boundary_never_both_own_a_point_on_it(kernel_name: str):
    """Each point of the tiled square has exactly one owner, except on the square's own
    west and south edges, where it has none - which is what lets two zones meeting along
    a border be tested in either order."""
    tiles = {
        name: KERNELS[kernel_name](_ring(vertices, (0, 0)))
        for name, vertices in TILES.items()
    }
    wrong = []
    for x in range(-1, 10):
        for y in range(-1, 10):
            owners = sorted(
                name for name, owns in tiles.items() if owns(x * UNIT, y * UNIT)
            )
            expected = 1 if 0 < x <= 8 and 0 < y <= 8 else 0
            if len(owners) != expected:
                wrong.append(((x, y), owners))
    assert not wrong, (
        f"{kernel_name}: lattice points of the tiled square owned by the wrong number "
        f"of tiles, first {wrong[:5]}"
    )


# The ocean zones are 15° sectors bordering each other along these meridians; at these
# latitudes two of them meet along a straight north-south line far from any land.
SECTOR_BORDERS = [-172.5, -97.5, -37.5, -7.5, 7.5, 82.5, 142.5, 172.5]
OPEN_OCEAN_LATITUDES = [-50.0, -40.0]
# far enough off a border to be in one zone, and well inside the coordinate grid
OFF_BORDER = 1e-6


@pytest.fixture(scope="module")
def finder() -> TimezoneFinder:
    return TimezoneFinder(in_memory=True)


@pytest.mark.parametrize("lat", OPEN_OCEAN_LATITUDES)
@pytest.mark.parametrize("lng", [*SECTOR_BORDERS, 180.0])
def test_a_lookup_gives_a_point_on_a_zone_border_to_the_zone_west_of_it(
    finder: TimezoneFinder, lng: float, lat: float
):
    """The rule through the whole lookup rather than one kernel: the shortcut index has to
    offer the western zone, the bounding-box filter keep it, and the kernel the lookup is
    bound to own the point - on borders the packaged data really has, and on +180°."""
    west = finder.certain_timezone_at(lng=lng - OFF_BORDER, lat=lat)
    assert west is not None
    assert finder.certain_timezone_at(lng=lng, lat=lat) == west
    assert finder.timezone_at(lng=lng, lat=lat) == west
    if lng < 180.0:
        # otherwise the meridian is no border here, and the assertions above say nothing
        assert finder.certain_timezone_at(lng=lng + OFF_BORDER, lat=lat) != west
