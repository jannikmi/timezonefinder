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
    block_edge_counts,
    block_latitude_ranges,
    block_scan_cost,
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
from timezonefinder import TimezoneFinder, utils, utils_numba
from timezonefinder.block_payload import encode_ring
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
from timezonefinder.polygon_array import PolygonArray
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


@pytest.fixture(scope="module")
def finder() -> TimezoneFinder:
    # in_memory, so that the coordinate views recorded below stay valid for the whole
    # module instead of pinning a memory mapping
    return TimezoneFinder(in_memory=True)


@pytest.fixture(scope="module")
def real_pip_calls(finder) -> list[tuple]:
    """Every ``(collection, poly_id, x, y, ring, block ranges)`` a real lookup makes.

    Recorded off the committed query fixtures rather than constructed, because which
    polygons a point is tested against - and with which of the two id spaces the index
    is addressed by - is decided by the lookup stack and not by this test.
    """
    calls: list[tuple] = []
    original = PolygonArray.pip

    def recording(self, poly_id, x, y):
        # The collection and the id, so a test can re-run the *shipped* path; and the
        # ring and its ranges, which since polygon layout 3 only exist as such above the
        # kernel - it is handed the whole collection and a block offset - and which the
        # unblocked reference below has to be given at this level.
        calls.append(
            (
                self,
                poly_id,
                x,
                y,
                self.coords_of(poly_id),
                self.block_ranges_of(poly_id),
            )
        )
        return original(self, poly_id, x, y)

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(PolygonArray, "pip", recording)
        for fixture in (AMBIGUOUS_SHORTCUT_POINTS_FIXTURE, ON_LAND_POINTS_FIXTURE):
            for lng, lat in load_benchmark_points(fixture)[:NR_QUERY_POINTS]:
                finder.timezone_at(lng=lng, lat=lat)

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
def test_the_shipped_kernel_answers_what_the_naive_one_does(real_pip_calls):
    """Neither skipping blocks nor unpacking residuals may change a single answer.

    The reference is ``utils.inside_polygon``: the plain ray cast over an absolute
    coordinate array, which is what every other kernel here is a faster spelling of.
    Run over every point-in-polygon test the committed query fixtures actually produce,
    so the rings are paired the way the lookup stack pairs them - holes resolved
    through their references included.

    Only one backend is exercised, whichever is bound; ``tests/test_acceleration_paths``
    is what holds the two to each other, and it does so over this same shipped path.
    """
    disagreements = []
    for collection, poly_id, x, y, ring, _ in real_pip_calls:
        expected = utils.inside_polygon(x, y, ring)
        got = collection.pip(poly_id, x, y)
        if expected != got:
            disagreements.append((x, y, ring.shape[1], expected, got))
    assert not disagreements, (
        f"{len(disagreements)} of {len(real_pip_calls)} point-in-polygon tests disagree "
        f"between the shipped kernel and the naive one, first: {disagreements[0]}"
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
        for vertex in (0, ring.shape[1] // 2, ring.shape[1] - 1):
            x, y = int(ring[0][vertex]), int(ring[1][vertex])
            assert boundaries.pip(poly_id, x, y) == utils_numba.pt_in_poly_python(
                x, y, ring
            ), (
                f"polygon {poly_id} answers its own vertex {vertex} differently "
                f"through the block filter and the packed payload"
            )


@pytest.mark.unit
def test_the_filter_actually_skips(real_pip_calls):
    """An index that never skips is correct and worthless - that is the failure this
    catches, since every equality assertion above would still pass."""
    scanned = 0
    total = 0
    for _, _, _, y, ring, ranges in real_pip_calls:
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

    The *upper* bound is what this can catch by re-derivation, and the reason is worth
    knowing: since polygon layout 3 the lower bound is also the block's y frame origin,
    so a decode performed with a shifted one produces latitudes shifted by exactly the
    same amount and re-deriving the range reproduces the corrupted file. Nothing
    internal can witness a number that is stored once -
    ``test_the_encoder_rejects_a_range_that_does_not_describe_the_ring`` is where that
    half is guarded instead, at build time, where it cannot be written in the first
    place.
    """
    data_dir = _writable_boundaries_dir(tmp_path)
    path = get_block_ranges_path(get_boundaries_dir(data_dir))
    ranges = read_per_polygon_vector(path).copy()
    ranges[0, 1] -= 1
    path.unlink()
    store_per_polygon_vector(path, ranges)

    with pytest.raises(DataIntegrityError, match="does not cover its own edges"):
        validate_block_index(data_dir)


@pytest.mark.unit
def test_the_encoder_rejects_a_range_that_does_not_describe_the_ring():
    """The build-time half of the check above, and what lets the y frame be stored once.

    The encoder frames each block's latitudes against the index rather than against a
    second copy of the same minima, so the two cannot disagree in a written file - but
    only because it refuses to write one where they would. Without this a mis-built
    index would silently produce residuals relative to the wrong origin.
    """
    boundaries = PolygonArray(
        data_location=get_boundaries_dir(DEFAULT_DATA_DIR), in_memory=True
    )
    ring = np.ascontiguousarray(boundaries.coords_of(0))
    ranges = np.array(boundaries.block_ranges_of(0), copy=True)

    encode_ring(ring, ranges, POLYGON_BLOCK_SIZE)  # the honest index is accepted

    ranges[0, 0] += 1
    with pytest.raises(ValueError, match="the index records"):
        encode_ring(ring, ranges, POLYGON_BLOCK_SIZE)


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
@pytest.mark.parametrize("block_size", [3, 7, 16, 39])
def test_best_rotation_offset_attains_the_global_minimum(block_size):
    """Every rotation is searched, not one block of them.

    The bounded search this replaced was not a smaller way of finding the same answer:
    rotating by a whole block moves the ragged final block whenever the block size does
    not divide the vertex count, so it repartitions the ring rather than relabelling it.
    """
    y = _RING[1]
    offset = best_rotation_offset(y, block_size)
    costs = [block_scan_cost(np.roll(y, -r), block_size) for r in range(len(y))]
    assert costs[offset] == min(costs)


@pytest.mark.unit
def test_block_scan_cost_weights_each_block_by_the_edges_it_holds():
    """The ragged block holds fewer edges and must count for less.

    Summing the spans unweighted lets a one-edge block outvote a full one, which is what
    made the objective disagree with the thing it stands for.
    """
    block_size = 4
    # 5 vertices: a full block of 4 edges, then a ragged block holding 1
    ring_y = np.array([0, 10, 20, 30, 1_000], dtype=np.int32)
    counts = block_edge_counts(len(ring_y), block_size)
    assert counts.tolist() == [4, 1]

    ranges = block_latitude_ranges(ring_y, block_size)
    spans = (ranges[:, 1].astype(np.int64) - ranges[:, 0]).tolist()
    assert block_scan_cost(ring_y, block_size) == 4 * spans[0] + 1 * spans[1]
    assert block_scan_cost(ring_y, block_size) != sum(spans)


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

    rng = np.random.default_rng(0)
    xs = rng.integers(int(ring[0].min()), int(ring[0].max()) + 1, 200)
    ys = rng.integers(int(ring[1].min()), int(ring[1].max()) + 1, 200)
    # the rotated ring through the naive kernel against the stored one through the
    # shipped path: if where a ring starts were observable, these would part company
    for x, y in zip(xs.tolist(), ys.tolist()):
        assert utils.inside_polygon(x, y, rotated) == boundaries.pip(poly_id, x, y)


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
