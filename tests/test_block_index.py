"""The latitude block index: that it is the same function, and that it skips.

The index is what the point-in-polygon kernels skip on, so every way it can be wrong is
a plausible wrong answer rather than an error - a range too narrow drops the block
holding a crossing edge, and an index keyed by the wrong id space filters a ring by
another ring's latitudes. Neither raises, and neither shows up in an answer that still
names a real timezone. What follows therefore checks equality against the unblocked
kernel over real geometry first, and only then that the filter is doing any work.
"""

import numpy as np
import pytest

from scripts.block_index import (
    best_rotation_offset,
    block_latitude_ranges,
    block_span_sum,
    build_block_index,
    nr_blocks_for,
    rotate_ring,
)
from scripts.data_integrity import DataIntegrityError, validate_block_index
from tests.auxiliaries import (
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
    ON_LAND_POINTS_FIXTURE,
    load_benchmark_points,
)
from timezonefinder import TimezoneFinder, utils, utils_clang, utils_numba
from timezonefinder.configs import (
    BLOCK_OFFSET_DTYPE,
    BLOCK_RANGE_DTYPE,
    DEFAULT_DATA_DIR,
    POLYGON_BLOCK_SIZE,
)
from timezonefinder.np_binary_helpers import (
    get_block_offsets_path,
    get_block_ranges_path,
    read_per_polygon_vector,
    store_per_polygon_vector,
)
from timezonefinder.utils import get_boundaries_dir, get_holes_dir

# How many query points to replay per fixture. The committed ``pip_inputs`` fixture is
# deliberately *not* used: it pairs a globally random point with a random polygon, so
# almost every one of its pairs is filtered out by the bounding latitudes alone and an
# equality assertion over it would pass without the kernel ever entering a block. What
# is needed here is the opposite - the tests a real lookup performs, where the point is
# near the polygon and blocks actually survive.
NR_QUERY_POINTS = 1_500

# What the block filter is for. Over the calls those queries produce it leaves ~2 % of
# the edges to be tested; the bound is loose because the exact figure moves with a data
# update, while losing the filter altogether would put it at 100 %.
MAX_EDGE_FRACTION = 0.10

KERNEL_PAIRS = [
    pytest.param(
        utils_numba.pt_in_poly_python, utils_numba.pt_in_poly_blocked, id="numba"
    ),
    pytest.param(
        utils_clang.pt_in_poly_clang, utils_clang.pt_in_poly_clang_blocked, id="clang"
    ),
]


@pytest.fixture(scope="module")
def finder() -> TimezoneFinder:
    # in_memory, so that the coordinate views recorded below stay valid for the whole
    # module instead of pinning a memory mapping
    return TimezoneFinder(in_memory=True)


@pytest.fixture(scope="module")
def real_pip_calls(finder) -> list[tuple[int, int, np.ndarray, np.ndarray]]:
    """Every ``(x, y, ring, block ranges)`` a real lookup reaches a kernel with.

    Recorded off the committed query fixtures rather than constructed, because which
    polygons a point is tested against - and with which of the two id spaces the index
    is addressed by - is decided by the lookup stack and not by this test.
    """
    calls: list[tuple[int, int, np.ndarray, np.ndarray]] = []
    original = utils.inside_polygon_blocked

    def recording(x, y, coords, block_ranges, block_size):
        calls.append((x, y, coords, block_ranges))
        return original(x, y, coords, block_ranges, block_size)

    utils.inside_polygon_blocked = recording
    try:
        for fixture in (AMBIGUOUS_SHORTCUT_POINTS_FIXTURE, ON_LAND_POINTS_FIXTURE):
            for lng, lat in load_benchmark_points(fixture)[:NR_QUERY_POINTS]:
                finder.timezone_at(lng=lng, lat=lat)
    finally:
        utils.inside_polygon_blocked = original

    assert calls, (
        "the query fixtures no longer reach the point-in-polygon stage, so everything "
        "below would pass over an empty workload"
    )
    return calls


def _edges_in_surviving_blocks(
    ranges: np.ndarray, nr_vertices: int, y: int, block_size: int
) -> int:
    """How many edges a blocked scan of this ring at latitude ``y`` would test."""
    total = 0
    for block in range(len(ranges)):
        if ranges[block, 0] <= y <= ranges[block, 1]:
            start = block * block_size
            total += min(start + block_size, nr_vertices) - start
    return total


# --------------------------------------------------------------------------------
# the same function, over the packaged geometry
# --------------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize("unblocked, blocked", KERNEL_PAIRS)
def test_the_blocked_kernel_answers_what_the_unblocked_one_does(
    real_pip_calls, unblocked, blocked
):
    """Skipping blocks may not change a single answer, on either acceleration path.

    Over every point-in-polygon test the committed query fixtures actually produce, so
    the rings and the ranges are paired the way the lookup stack pairs them - holes
    resolved through their references included.
    """
    disagreements = []
    for x, y, ring, ranges in real_pip_calls:
        expected = unblocked(x, y, ring)
        got = blocked(x, y, ring, ranges, POLYGON_BLOCK_SIZE)
        if expected != got:
            disagreements.append((x, y, ring.shape[1], expected, got))
    assert not disagreements, (
        f"{len(disagreements)} of {len(real_pip_calls)} point-in-polygon tests disagree "
        f"between the blocked and unblocked kernels, first: {disagreements[0]}"
    )


@pytest.mark.unit
def test_a_vertex_of_every_ring_is_answered_alike(finder):
    """The awkward input: a query landing exactly on a stored vertex.

    It sits on the boundary of the block that owns it *and* of the block bridging into
    it, so it is the case a range computed one vertex short would get wrong.
    """
    boundaries = finder.boundaries
    for poly_id in range(len(boundaries)):
        ring = boundaries.coords_of(poly_id)
        ranges = boundaries.block_ranges_of(poly_id)
        for vertex in (0, ring.shape[1] // 2, ring.shape[1] - 1):
            x, y = int(ring[0][vertex]), int(ring[1][vertex])
            assert utils_numba.pt_in_poly_blocked(
                x, y, ring, ranges, POLYGON_BLOCK_SIZE
            ) == utils_numba.pt_in_poly_python(x, y, ring), (
                f"polygon {poly_id} answers its own vertex {vertex} differently "
                f"with the block filter"
            )


@pytest.mark.unit
def test_the_filter_actually_skips(real_pip_calls):
    """An index that never skips is correct and worthless - that is the failure this
    catches, since every equality assertion above would still pass."""
    scanned = 0
    total = 0
    for _, y, ring, ranges in real_pip_calls:
        nr_vertices = ring.shape[1]
        scanned += _edges_in_surviving_blocks(
            ranges, nr_vertices, y, POLYGON_BLOCK_SIZE
        )
        total += nr_vertices
    fraction = scanned / total
    assert fraction < MAX_EDGE_FRACTION, (
        f"the block index leaves {fraction:.1%} of the edges to be tested, against the "
        f"{MAX_EDGE_FRACTION:.0%} this data is expected to stay under. The index is "
        f"still correct - it is no longer paying for itself."
    )


# --------------------------------------------------------------------------------
# which index belongs to which ring
# --------------------------------------------------------------------------------


@pytest.mark.unit
def test_every_hole_is_indexed_by_the_ring_it_resolves_to(finder):
    """Hole ids and boundary polygon ids are two dense spaces starting at 0.

    ``HoleArray`` resolves most holes to a boundary polygon, so its block index has to
    follow the same reference - and a collection keyed by the other space still answers,
    with some other ring's latitudes. That skips blocks holding real crossings for the
    handful of points that fall in them, which reads as noise rather than as a failure.
    """
    holes = finder.holes
    assert len(holes), "expected the packaged data to hold holes"
    referenced = 0
    for hole_id in range(len(holes)):
        ring = holes.coords_of(hole_id)
        stored = holes.block_ranges_of(hole_id)
        expected = block_latitude_ranges(ring[1], POLYGON_BLOCK_SIZE)
        assert np.array_equal(stored, expected), (
            f"hole {hole_id} is indexed by a ring that is not the one it resolves to"
        )
        referenced += int(holes.poly_ref[hole_id]) >= 0
    assert referenced, "expected some holes to be stored as references"


@pytest.mark.unit
def test_every_boundary_is_indexed_by_its_own_ring(finder):
    boundaries = finder.boundaries
    for poly_id in range(len(boundaries)):
        ring = boundaries.coords_of(poly_id)
        assert np.array_equal(
            boundaries.block_ranges_of(poly_id),
            block_latitude_ranges(ring[1], POLYGON_BLOCK_SIZE),
        ), f"boundary polygon {poly_id} is indexed by another ring"


# --------------------------------------------------------------------------------
# the stored files
# --------------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize("polygon_dir_of", [get_boundaries_dir, get_holes_dir])
def test_the_packaged_index_is_stored_in_the_declared_dtypes(polygon_dir_of):
    """Both columns are read by position without being checked at lookup time."""
    polygon_dir = polygon_dir_of(DEFAULT_DATA_DIR)
    ranges = read_per_polygon_vector(get_block_ranges_path(polygon_dir))
    offsets = read_per_polygon_vector(get_block_offsets_path(polygon_dir))
    assert ranges.dtype == BLOCK_RANGE_DTYPE
    assert ranges.ndim == 2 and ranges.shape[1] == 2
    assert offsets.dtype == BLOCK_OFFSET_DTYPE
    assert int(offsets[0]) == 0
    assert int(offsets[-1]) == len(ranges)
    assert np.all(np.diff(offsets.astype(np.int64)) > 0)


@pytest.mark.unit
def test_the_packaged_data_passes_the_integrity_check():
    """The same check the converter runs over what it wrote, over what is committed."""
    validate_block_index(DEFAULT_DATA_DIR)


def _writable_boundaries_dir(tmp_path):
    """A data directory whose boundary index files can be rewritten.

    Symlinked from the packaged one so the multi-megabyte coordinate file is not
    copied; the two small index files are replaced with real ones.
    """
    data_dir = tmp_path / "data"
    for source in (get_boundaries_dir, get_holes_dir):
        target = source(data_dir)
        target.mkdir(parents=True)
        for item in source(DEFAULT_DATA_DIR).iterdir():
            (target / item.name).symlink_to(item)
    boundaries_dir = get_boundaries_dir(data_dir)
    for path_of in (get_block_ranges_path, get_block_offsets_path):
        path = path_of(boundaries_dir)
        content = read_per_polygon_vector(path).copy()
        path.unlink()
        store_per_polygon_vector(path, content)
    return data_dir


@pytest.mark.unit
def test_the_integrity_check_rejects_a_narrowed_range(tmp_path):
    """It has to be able to fail, or it says nothing about the packaged data.

    A range one unit too narrow is exactly the defect that does not announce itself:
    the file still parses, the block count is right, and only the points whose latitude
    falls in the dropped sliver are answered wrongly.
    """
    data_dir = _writable_boundaries_dir(tmp_path)
    path = get_block_ranges_path(get_boundaries_dir(data_dir))
    ranges = read_per_polygon_vector(path).copy()
    ranges[0, 0] += 1
    path.unlink()
    store_per_polygon_vector(path, ranges)

    with pytest.raises(DataIntegrityError, match="does not cover its own edges"):
        validate_block_index(data_dir)


@pytest.mark.unit
def test_the_integrity_check_rejects_another_block_size(tmp_path):
    """A directory blocked at a different POLYGON_BLOCK_SIZE parses perfectly.

    Nothing in the files says which size they were built at, so this is what pins it -
    the block *counts* only fit one, and the layout marker keeps such a directory from
    reaching a released reader in the first place.
    """
    data_dir = _writable_boundaries_dir(tmp_path)
    boundaries_dir = get_boundaries_dir(data_dir)
    finder = TimezoneFinder(in_memory=True)
    rings = [finder.boundaries.coords_of(i) for i in range(len(finder.boundaries))]
    ranges, offsets = build_block_index(rings, POLYGON_BLOCK_SIZE // 2)
    for path_of, content in (
        (get_block_ranges_path, ranges),
        (get_block_offsets_path, offsets),
    ):
        path = path_of(boundaries_dir)
        path.unlink()
        store_per_polygon_vector(path, content)

    with pytest.raises(DataIntegrityError, match="blocked at a different size"):
        validate_block_index(data_dir)


# --------------------------------------------------------------------------------
# the block partition and the ring rotation
# --------------------------------------------------------------------------------

# A ring whose latitudes are deliberately uneven, so that where it starts changes how
# tightly the blocks bound it.
_RING = np.ascontiguousarray(
    np.vstack(
        [
            (np.cos(np.linspace(0, 2 * np.pi, 40, endpoint=False)) * 1_000_000),
            (np.sin(np.linspace(0, 2 * np.pi, 40, endpoint=False)) ** 3 * 1_000_000),
        ]
    ).astype(np.int32)
)


@pytest.mark.unit
@pytest.mark.parametrize(
    "nr_vertices, block_size, expected",
    [(1, 4, 1), (4, 4, 1), (5, 4, 2), (128, 128, 1), (129, 128, 2)],
)
def test_block_counts(nr_vertices, block_size, expected):
    assert nr_blocks_for(nr_vertices, block_size) == expected


@pytest.mark.unit
@pytest.mark.parametrize("block_size", [3, 7, 40, 64])
def test_every_edge_lies_inside_its_own_block_range(block_size):
    """The property the whole filter rests on, checked edge by edge.

    A block owns the edges *leaving* its vertices, so its range must also cover the
    first vertex of the next block - and on the last block, vertex 0.
    """
    y = _RING[1]
    ranges = block_latitude_ranges(y, block_size)
    nr_vertices = y.shape[0]
    for i in range(nr_vertices):
        j = (i + 1) % nr_vertices
        block = i // block_size
        low, high = int(ranges[block, 0]), int(ranges[block, 1])
        for endpoint in (int(y[i]), int(y[j])):
            assert low <= endpoint <= high, (
                f"edge {i} spans latitude {endpoint}, outside block {block}'s "
                f"recorded range [{low}, {high}] at block size {block_size}"
            )


@pytest.mark.unit
def test_best_rotation_offset_attains_the_minimum():
    block_size = 7
    offset = best_rotation_offset(_RING[1], block_size)
    sums = [
        block_span_sum(np.roll(_RING[1], -candidate), block_size)
        for candidate in range(block_size)
    ]
    assert sums[offset] == min(sums)


@pytest.mark.unit
def test_a_single_block_ring_is_not_rotated():
    """Nothing to choose: one block covers the whole ring at every offset."""
    assert best_rotation_offset(_RING[1], _RING.shape[1]) == 0


@pytest.mark.unit
@pytest.mark.parametrize("by", [1, 5, 17])
def test_rotating_a_ring_does_not_change_an_answer(finder, by):
    """Why the converter is free to choose where a ring starts.

    Rotation is not a stored property and no reader can detect it, so the only thing
    that makes it safe is that the answers do not move - over a real ring and the real
    query points that reach it.
    """
    boundaries = finder.boundaries
    poly_id = int(np.argmax([boundaries.coords_of(i).shape[1] for i in range(200)]))
    ring = boundaries.coords_of(poly_id)
    rotated = rotate_ring(ring, by)
    rotated_ranges = block_latitude_ranges(rotated[1], POLYGON_BLOCK_SIZE)
    ranges = boundaries.block_ranges_of(poly_id)

    rng = np.random.default_rng(0)
    xs = rng.integers(int(ring[0].min()), int(ring[0].max()) + 1, 200)
    ys = rng.integers(int(ring[1].min()), int(ring[1].max()) + 1, 200)
    for x, y in zip(xs.tolist(), ys.tolist()):
        assert utils_numba.pt_in_poly_blocked(
            x, y, rotated, rotated_ranges, POLYGON_BLOCK_SIZE
        ) == utils_numba.pt_in_poly_blocked(x, y, ring, ranges, POLYGON_BLOCK_SIZE)


@pytest.mark.unit
def test_build_block_index_refuses_a_collection_it_cannot_address(monkeypatch):
    """The offset column is chosen by fit, so its ceiling has to be loud.

    Silently wrapping would leave a ring reading another ring's block ranges, which is
    a wrong answer rather than an error.
    """
    monkeypatch.setattr(
        "scripts.block_index.BLOCK_OFFSET_DTYPE", np.dtype("<u1"), raising=True
    )
    rings = [_RING] * 100
    with pytest.raises(ValueError, match="Widen BLOCK_OFFSET_DTYPE"):
        build_block_index(rings, 4)
