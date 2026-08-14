"""Holes stored as a reference to an identical boundary polygon.

Most holes are enclaves whose ring the upstream builder also emits as the enclave
zone's own boundary polygon. Storing a reference instead of a second copy is only safe
if the resolved ring describes the same closed path, so that is what these tests pin
down - at the encoding, at the runtime resolution, and against the packaged data.
"""

from pathlib import Path

import numpy as np
import pytest

from scripts.data_integrity import (
    DataIntegrityError,
    validate_hole_dedup_ratio,
    validate_hole_references,
)
from scripts.utils import canonical_ring_key
from timezonefinder import TimezoneFinder, utils, utils_clang, utils_numba
from timezonefinder.configs import DEFAULT_DATA_DIR
from timezonefinder.flatbuf.io.polygons import (
    get_coordinate_path,
    write_polygon_collection_flatbuffer,
)
from timezonefinder.np_binary_helpers import (
    get_poly_ref_path,
    get_xmax_path,
    get_xmin_path,
    get_ymax_path,
    get_ymin_path,
    read_per_polygon_vector,
    store_per_polygon_vector,
)
from timezonefinder.polygon_array import HoleArray, PolygonArray
from timezonefinder.utils import get_boundaries_dir, get_holes_dir

RING = np.array([[0, 10, 10, 0], [0, 0, 10, 10]], dtype=np.int32)


def _rotate(ring: np.ndarray, by: int) -> np.ndarray:
    return np.ascontiguousarray(np.roll(ring, -by, axis=1))


# --------------------------------------------------------------------------------
# the canonical key, which decides what counts as "the same ring"
# --------------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize("by", range(4))
def test_canonical_key_ignores_starting_vertex(by):
    assert canonical_ring_key(_rotate(RING, by)) == canonical_ring_key(RING)


@pytest.mark.unit
def test_canonical_key_ignores_winding_direction():
    reversed_ring = np.ascontiguousarray(RING[:, ::-1])
    assert canonical_ring_key(reversed_ring) == canonical_ring_key(RING)


@pytest.mark.unit
def test_canonical_key_separates_different_rings():
    moved = RING.copy()
    moved[0, 2] += 1  # a single vertex one unit apart is a different ring
    assert canonical_ring_key(moved) != canonical_ring_key(RING)


@pytest.mark.unit
def test_canonical_key_handles_a_repeated_extreme_vertex():
    """A ring visiting its lexicographically smallest vertex twice has several equally
    valid rotations; the key must still be one deterministic value."""
    ring = np.array([[0, 5, 0, 5], [0, 1, 0, -1]], dtype=np.int32)
    assert canonical_ring_key(ring) == canonical_ring_key(_rotate(ring, 2))


# --------------------------------------------------------------------------------
# the packaged data
# --------------------------------------------------------------------------------


@pytest.mark.unit
def test_packaged_holes_are_deduplicated():
    """The shipped data must actually use the encoding, not just tolerate it."""
    tf = TimezoneFinder(in_memory=True)
    assert tf.holes.poly_ref is not None
    nr_referenced = int((tf.holes.poly_ref >= 0).sum())
    assert nr_referenced > 0
    # only the rings without a twin are stored
    assert len(tf.holes.coordinates) == len(tf.holes) - nr_referenced


@pytest.mark.unit
def test_packaged_data_passes_the_integrity_check():
    """The shipped data must satisfy the same check the converter runs over its output.

    This is the whole of the packaged-data verification: the reference vector, the
    coordinate file and the bounding boxes agreeing with one another, every reference
    resolving to the geometry its bounding box describes, and - separately, since it
    only means anything at dataset scale - the deduplication ratio clearing its floor.
    The checks live in ``scripts/data_integrity`` so that the
    converter and this test assert the same thing rather than two drifting
    approximations of it - and so that neither obligation falls on ``HoleArray``, where
    every user would re-derive it on every construction.
    """
    validate_hole_references(DEFAULT_DATA_DIR)
    validate_hole_dedup_ratio(DEFAULT_DATA_DIR)


# --------------------------------------------------------------------------------
# both point-in-polygon backends must agree on a resolved ring
# --------------------------------------------------------------------------------


@pytest.mark.unit
def test_both_pip_backends_agree_on_resolved_hole_rings():
    """The backend is bound at import time, so a resolved ring has to satisfy both.

    A referenced ring is handed over as the boundary's array; if that ever stopped
    being a C-contiguous (2, N) view, the C extension would reject it outright while
    the Numba kernel kept working, and only one CI environment would notice.
    """
    tf = TimezoneFinder(in_memory=True)
    rng = np.random.default_rng(3)
    referenced = [i for i in range(len(tf.holes)) if int(tf.holes.poly_ref[i]) >= 0]
    assert referenced, "expected the packaged data to contain referenced holes"

    for hole_id in referenced[:40]:
        ring = tf.holes.coords_of(hole_id)
        assert ring.shape[0] == 2
        assert ring[0].flags["C_CONTIGUOUS"] and ring[1].flags["C_CONTIGUOUS"]
        xmin, xmax = int(tf.holes.xmin[hole_id]), int(tf.holes.xmax[hole_id])
        ymin, ymax = int(tf.holes.ymin[hole_id]), int(tf.holes.ymax[hole_id])
        points = [(int(ring[0][0]), int(ring[1][0]))]  # a vertex, the awkward case
        points += [
            (int(rng.integers(xmin, xmax + 1)), int(rng.integers(ymin, ymax + 1)))
            for _ in range(20)
        ]
        for x, y in points:
            from_numba = utils_numba.pt_in_poly_python(x, y, ring)
            from_clang = utils_clang.pt_in_poly_clang(x, y, ring)
            assert from_numba == from_clang
            assert utils.inside_polygon(x, y, ring) == from_numba


# --------------------------------------------------------------------------------
# HoleArray, on synthetic data directories
# --------------------------------------------------------------------------------


def _write_hole_dir(path, *, rings, poly_ref, bboxes):
    path.mkdir(parents=True, exist_ok=True)
    write_polygon_collection_flatbuffer(get_coordinate_path(path), rings)
    xmin, xmax, ymin, ymax = zip(*bboxes)
    store_per_polygon_vector(get_xmin_path(path), np.array(xmin, dtype=np.int32))
    store_per_polygon_vector(get_xmax_path(path), np.array(xmax, dtype=np.int32))
    store_per_polygon_vector(get_ymin_path(path), np.array(ymin, dtype=np.int32))
    store_per_polygon_vector(get_ymax_path(path), np.array(ymax, dtype=np.int32))
    if poly_ref is not None:
        store_per_polygon_vector(
            get_poly_ref_path(path), np.array(poly_ref, dtype=np.int32)
        )


@pytest.fixture
def boundaries() -> PolygonArray:
    return PolygonArray(data_location=get_boundaries_dir(DEFAULT_DATA_DIR))


def _synthetic_data_dir(tmp_path, *, rings, poly_ref, bboxes) -> Path:
    """A whole data directory: the packaged boundaries, plus the given hole files.

    ``validate_hole_references`` takes a data directory rather than a hole directory,
    since resolving a reference needs the boundaries too.
    """
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    get_boundaries_dir(data_dir).symlink_to(
        get_boundaries_dir(DEFAULT_DATA_DIR), target_is_directory=True
    )
    _write_hole_dir(
        get_holes_dir(data_dir), rings=rings, poly_ref=poly_ref, bboxes=bboxes
    )
    return data_dir


def _bbox_of(ring) -> tuple[int, int, int, int]:
    return (
        int(ring[0].min()),
        int(ring[0].max()),
        int(ring[1].min()),
        int(ring[1].max()),
    )


@pytest.mark.unit
def test_reference_and_inline_rings_resolve(tmp_path, boundaries):
    """A negative entry addresses the inline ring at ``-(v + 1)``, a non-negative one a
    boundary polygon. Inline ring 0 and boundary polygon 0 must not collide."""
    inline = np.array([[1, 2, 3], [4, 5, 6]], dtype=np.int32)
    _write_hole_dir(
        tmp_path,
        rings=[inline],
        poly_ref=[-1, 0],  # inline ring 0, then boundary polygon 0
        bboxes=[(1, 3, 4, 6), (0, 0, 0, 0)],
    )
    holes = HoleArray(data_location=tmp_path, boundaries=boundaries)
    assert np.array_equal(holes.coords_of(0), inline)
    assert np.array_equal(holes.coords_of(1), boundaries.coords_of(0))


@pytest.mark.unit
def test_missing_reference_vector_is_not_readable(tmp_path, boundaries):
    """``poly_ref.npy`` is required, not optional.

    The layout it belongs to has never been released, so a hole directory without it
    is not an older format to stay compatible with - it is one that cannot be
    interpreted, since the coordinate file holds only the inline rings and hole ids do
    not index it. Failing on the missing file beats guessing at an interpretation.
    """
    rings = [
        np.array([[1, 2, 3], [4, 5, 6]], dtype=np.int32),
        np.array([[7, 8, 9], [1, 2, 3]], dtype=np.int32),
    ]
    _write_hole_dir(
        tmp_path, rings=rings, poly_ref=None, bboxes=[(1, 3, 4, 6), (7, 9, 1, 3)]
    )
    with pytest.raises(FileNotFoundError, match="poly_ref"):
        HoleArray(data_location=tmp_path, boundaries=boundaries)


@pytest.mark.unit
def test_hole_array_does_not_validate_on_construction(tmp_path, boundaries):
    """Constructing a ``HoleArray`` must not re-check the data directory.

    Whether the binaries are coherent is settled by the build; paying for that again in
    every user's process is what this guards against. A directory the integrity check
    rejects therefore still constructs - catching it is the converter's job and the
    test suite's, not the runtime's.
    """
    data_dir = _synthetic_data_dir(
        tmp_path,
        rings=[],  # the reference claims an inline ring the file does not contain
        poly_ref=[-1],
        bboxes=[(1, 3, 4, 6)],
    )
    HoleArray(data_location=get_holes_dir(data_dir), boundaries=boundaries)  # no raise

    with pytest.raises(DataIntegrityError):
        validate_hole_references(data_dir)


# --------------------------------------------------------------------------------
# the integrity check, which the converter and the test suite share
# --------------------------------------------------------------------------------


@pytest.mark.unit
def test_integrity_check_accepts_a_consistent_directory(tmp_path, boundaries):
    inline = np.array([[1, 2, 3], [4, 5, 6]], dtype=np.int32)
    data_dir = _synthetic_data_dir(
        tmp_path,
        rings=[inline],
        poly_ref=[-1, 0],
        bboxes=[_bbox_of(inline), _bbox_of(boundaries.coords_of(0))],
    )
    validate_hole_references(data_dir)


@pytest.mark.unit
def test_integrity_check_rejects_a_reference_vector_of_the_wrong_length(
    tmp_path, boundaries
):
    data_dir = _synthetic_data_dir(
        tmp_path,
        rings=[np.array([[1, 2, 3], [4, 5, 6]], dtype=np.int32)],
        poly_ref=[-1],
        bboxes=[(1, 3, 4, 6), (0, 0, 0, 0)],  # two holes, one reference entry
    )
    with pytest.raises(DataIntegrityError, match="entries but there are 2 holes"):
        validate_hole_references(data_dir)


@pytest.mark.unit
def test_integrity_check_rejects_an_inline_ring_count_mismatch(tmp_path, boundaries):
    """Coordinates from one build beside references from another must be caught here.

    Every index would still resolve to some ring, so this cannot be left to fail on its
    own - it would surface as a wrong timezone, not as an error.
    """
    data_dir = _synthetic_data_dir(
        tmp_path, rings=[], poly_ref=[-1], bboxes=[(1, 3, 4, 6)]
    )
    with pytest.raises(DataIntegrityError, match="exactly once"):
        validate_hole_references(data_dir)


@pytest.mark.unit
def test_integrity_check_rejects_an_out_of_range_boundary_reference(
    tmp_path, boundaries
):
    data_dir = _synthetic_data_dir(
        tmp_path, rings=[], poly_ref=[len(boundaries)], bboxes=[(0, 0, 0, 0)]
    )
    with pytest.raises(DataIntegrityError, match="references boundary polygon"):
        validate_hole_references(data_dir)


@pytest.mark.unit
def test_integrity_check_rejects_a_reference_to_the_wrong_polygon(tmp_path, boundaries):
    """The check with evidence independent of the references themselves.

    An off-by-one in the converter's matching produces exactly this: a reference that
    resolves to a real, valid ring which is not the one the hole's bounding box was
    computed from. Nothing else in the data would notice.
    """
    data_dir = _synthetic_data_dir(
        tmp_path,
        rings=[],
        poly_ref=[1],  # the bbox below describes polygon 0
        bboxes=[_bbox_of(boundaries.coords_of(0))],
    )
    with pytest.raises(DataIntegrityError, match="points at the wrong geometry"):
        validate_hole_references(data_dir)


@pytest.mark.unit
def test_integrity_check_rejects_a_directory_without_references(tmp_path, boundaries):
    """A hole directory missing ``poly_ref.npy`` is rejected rather than guessed at."""
    data_dir = _synthetic_data_dir(
        tmp_path,
        rings=[np.array([[1, 2, 3], [4, 5, 6]], dtype=np.int32)],
        poly_ref=None,
        bboxes=[(1, 3, 4, 6), (0, 0, 0, 0)],
    )
    with pytest.raises(FileNotFoundError, match="poly_ref"):
        validate_hole_references(data_dir)


@pytest.mark.unit
def test_teardown_drops_the_boundaries_reference(tmp_path, boundaries):
    """``HoleArray`` outlives nothing it resolves against: after teardown it must not
    read through a boundaries array that may already be half gone."""
    _write_hole_dir(tmp_path, rings=[], poly_ref=[0], bboxes=[(0, 0, 0, 0)])
    holes = HoleArray(data_location=tmp_path, boundaries=boundaries)
    assert np.array_equal(holes.coords_of(0), boundaries.coords_of(0))
    holes.__del__()
    with pytest.raises(AttributeError):
        holes.coords_of(0)


@pytest.mark.unit
def test_poly_ref_is_stored_as_int32():
    """Signed, and wide enough for every boundary polygon id."""
    vector = read_per_polygon_vector(get_poly_ref_path(get_holes_dir(DEFAULT_DATA_DIR)))
    assert vector.dtype == np.dtype("int32")


# --------------------------------------------------------------------------------
# equivalence with an all-inline dataset
# --------------------------------------------------------------------------------


def _inline_data_dir(destination) -> None:
    """Build a data directory equivalent to the packaged one but with every hole ring
    stored inline, i.e. what the converter produced before this encoding existed.

    Reconstructed from the packaged data rather than shipped as a second fixture: it
    stays in step with whatever data is packaged, and needs no second copy of a
    multi-megabyte binary in the repository.
    """
    source = DEFAULT_DATA_DIR
    for item in sorted(source.rglob("*")):
        target = destination / item.relative_to(source)
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(item)

    tf = TimezoneFinder(in_memory=True)
    rings = [tf.holes.coords_of(i) for i in range(len(tf.holes))]

    holes_dir = destination / get_holes_dir(source).relative_to(source)
    coord_path = get_coordinate_path(holes_dir)
    coord_path.unlink()  # drop the symlink, do not write through it
    write_polygon_collection_flatbuffer(coord_path, rings)

    # every hole addressed as its own inline ring: a valid directory in the same
    # layout, just one where nothing was deduplicated
    ref_path = get_poly_ref_path(holes_dir)
    ref_path.unlink()
    store_per_polygon_vector(
        ref_path, np.array([-(i + 1) for i in range(len(rings))], dtype=np.int32)
    )


@pytest.mark.integration
def test_deduplicated_data_answers_exactly_like_inline_data(tmp_path):
    """The packaged data must return what it would with every hole ring stored inline.

    Covers the points that actually exercise the hole path - interior points of every
    hole - rather than relying on a uniform sample to hit them.
    """
    inline_dir = tmp_path / "inline"
    inline_dir.mkdir()
    _inline_data_dir(inline_dir)

    packaged = TimezoneFinder(in_memory=True)
    inline = TimezoneFinder(bin_file_location=inline_dir, in_memory=True)
    assert (inline.holes.poly_ref < 0).all(), "the reference data must be all-inline"
    assert len(inline.holes.coordinates) == len(inline.holes)

    rng = np.random.default_rng(11)
    points: list[tuple[float, float]] = []
    for hole_id in range(len(packaged.holes)):
        ring = packaged.holes.coords_of(hole_id)
        assert np.array_equal(ring, inline.holes.coords_of(hole_id))
        xmin, xmax = (
            int(packaged.holes.xmin[hole_id]),
            int(packaged.holes.xmax[hole_id]),
        )
        ymin, ymax = (
            int(packaged.holes.ymin[hole_id]),
            int(packaged.holes.ymax[hole_id]),
        )
        found = 0
        for _ in range(2000):
            if found >= 2:
                break
            x = int(rng.integers(xmin, xmax + 1))
            y = int(rng.integers(ymin, ymax + 1))
            if utils.inside_polygon(x, y, ring):
                points.append((utils.int2coord(x), utils.int2coord(y)))
                found += 1

    points += [
        (float(rng.uniform(-180, 180)), float(rng.uniform(-90, 90)))
        for _ in range(2000)
    ]
    assert len(points) > 2000

    for lng, lat in points:
        assert packaged.timezone_at(lng=lng, lat=lat) == inline.timezone_at(
            lng=lng, lat=lat
        )
        assert packaged.timezone_at_land(lng=lng, lat=lat) == inline.timezone_at_land(
            lng=lng, lat=lat
        )


# --------------------------------------------------------------------------------
# compiling custom data whose holes are not enclaves
# --------------------------------------------------------------------------------


@pytest.mark.unit
def test_low_dedup_ratio_does_not_block_the_converter(capsys):
    """Custom data whose holes are not enclaves must still compile.

    ``scripts/file_converter.py`` is documented for "any other data in this format"
    (``docs/2_use_cases.rst``), and a dataset whose holes are ordinary interior rings
    rather than enclaves is perfectly valid - those rings are stored inline and answer
    correctly, the output is merely larger. The deduplication floor is a statement
    about the *packaged* dataset, so it is reported here and enforced only against that
    (``validate_hole_dedup_ratio``).
    """
    from scripts.timezone_data import HoleCollection, PolygonCollection

    boundary = np.array([[0, 100, 100, 0], [0, 0, 100, 100]], dtype=np.int32)
    # an interior ring that is nothing like the boundary: 0% deduplication
    hole = np.array([[10, 20, 20, 10], [10, 10, 20, 20]], dtype=np.int32)

    polygons = PolygonCollection(polygons=[boundary], lengths=[4])
    holes = HoleCollection(holes=[hole], lengths=[4], polynrs_of_holes=[0])

    holes.deduplicate(polygons, np.array([0], dtype=np.uint16))

    assert holes.poly_refs == [-1], "the unmatched ring must be stored inline"
    assert len(holes.inline_holes) == 1
    assert "WARNING" in capsys.readouterr().out
