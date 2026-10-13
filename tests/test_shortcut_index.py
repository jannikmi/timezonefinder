"""The shortcut index format: the addressing, the guards, and what it refuses.

The lookup divides a coordinate into a dense table, reads one ``int16``, and - if that is
negative - reads one more out of the block it names, then follows what it finds straight
into the payload: no bounds check, no key comparison, no dispatch beyond the sign. Every
assumption that makes that safe is established where the data is built
(``timezonefinder._data_integrity.validate_shortcut_index``) and asserted here over what is
committed, sharing one implementation so the two cannot drift.

What each group covers:

* the grid tiles the coordinate plane exactly, and the two levels address each other;
* the committed binary holds together, cell by cell;
* the build-time guards fail loudly, since a guard that cannot fail is not one;
* the layout markers reject data this version cannot read.
"""

from pathlib import Path

import numpy as np
import pytest

from scripts.configs import ZONE_ID_DTYPE
from timezonefinder import utils
from timezonefinder._data_integrity import (
    DataIntegrityError,
    validate_shortcut_index,
)
from tests.auxiliaries import (
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
    RANDOM_POINTS_FIXTURE,
    load_benchmark_points,
)
from timezonefinder.configs import (
    COORD2INT_FACTOR,
    DEFAULT_DATA_DIR,
    MAX_LAT_VAL_INT,
    MAX_LNG_VAL_INT,
    ZONE_ID_RESULT_DTYPE,
)
from timezonefinder.shortcut_index import (
    ABSENT,
    BLOCK_CELLS,
    BLOCK_SIDE,
    CHILD_COLUMNS,
    CHILD_ROWS,
    CHILD_WIDTH,
    ROOT_CELLS,
    ROOT_COLUMNS,
    ROOT_ROWS,
    ROOT_WIDTH,
    TABLE_DTYPE,
    _HEADER_SIZE,
    FILE_IDENTIFIER,
    SHORTCUT_LAYOUT_VERSION,
    ShortcutOverflowError,
    block_position_of,
    build_shortcut_index,
    cell_bounds,
    cell_bounds_of,
    child_cell_of,
    child_cells_of,
    get_last_change_idx,
    get_shortcut_file_path,
    is_root_cell,
    parent_cell_of,
    read_shortcuts_binary,
    root_cell_of,
    shifted,
    write_shortcuts_binary,
)

# Three root cells far enough apart to be distinct whatever the grid, derived rather than
# written as literals: a hard-coded cell id stops naming the same region the moment the
# grid shape moves.
CELL_A, CELL_B, CELL_C = (
    root_cell_of(*shifted(lng, lat))
    for lng, lat in ((13.4, 52.5), (2.35, 48.85), (139.0, 35.0))
)
# and three finest-level cells under *other* root cells, so that a mapping may hold a
# candidate list without the root cells above having to refine
CHILD_A, CHILD_B, CHILD_C = (
    child_cell_of(*shifted(lng, lat))
    for lng, lat in ((-58.4, -34.6), (151.2, -33.9), (-74.0, 40.7))
)

# zone id per boundary polygon, for the hand-built indices below
ZONE_IDS = np.array([0, 0, 1, 1, 2], dtype=np.uint16)


def build(mapping, zone_ids=ZONE_IDS):
    return build_shortcut_index(mapping, zone_ids)


def round_trip(index, tmp_path: Path):
    path = get_shortcut_file_path(tmp_path)
    write_shortcuts_binary(index, path)
    return read_shortcuts_binary(path)


def _level_bounds(
    count: int, width: int, half_span: int
) -> tuple[np.ndarray, np.ndarray]:
    """First and last integer coordinate of every division of one axis, as two arrays."""
    division = np.arange(count, dtype=np.int64)
    return (
        division * width - half_span + 1,
        (division + 1) * width - half_span,
    )


ROOT_X0, ROOT_X1 = _level_bounds(ROOT_COLUMNS, ROOT_WIDTH, MAX_LNG_VAL_INT)
ROOT_Y0, ROOT_Y1 = _level_bounds(ROOT_ROWS, ROOT_WIDTH, MAX_LAT_VAL_INT)
CHILD_X0, CHILD_X1 = _level_bounds(CHILD_COLUMNS, CHILD_WIDTH, MAX_LNG_VAL_INT)
CHILD_Y0, CHILD_Y1 = _level_bounds(CHILD_ROWS, CHILD_WIDTH, MAX_LAT_VAL_INT)


def _division_containing(value: int, first: np.ndarray, last: np.ndarray) -> int:
    """Which division of an axis owns an integer coordinate, found by search.

    Deliberately a search over ``cell_bounds``'s own numbers rather than the lookup's
    floor division: the contract is "the cell whose bounds contain the point", and
    re-deriving it with the same arithmetic the lookup uses would assert nothing.
    """
    found = np.flatnonzero((first <= value) & (value <= last))
    assert len(found) == 1, f"{value} belongs to {len(found)} divisions of this axis"
    return int(found[0])


def reference_cell(index, lng: float, lat: float) -> int:
    """The cell a coordinate's answer is stored in, derived independently of the lookup.

    The scaling and the two rewritten lines come from ``utils.query2int`` - the function
    the *geometry* side uses - so this also holds the index's prologue to it: a tree that
    clamped -180 to the first column instead of wrapping it to the last would disagree
    here, and ``tests/test_minus_180_meridian_and_minus_90_parallel.py`` says why that is
    a wrong answer rather than a different one.
    """
    x, y = utils.query2int(lng, lat)
    root = _division_containing(
        y, ROOT_Y0, ROOT_Y1
    ) * ROOT_COLUMNS + _division_containing(x, ROOT_X0, ROOT_X1)
    if int(index.table[root]) >= ABSENT:
        return root
    return (
        ROOT_CELLS
        + _division_containing(y, CHILD_Y0, CHILD_Y1) * CHILD_COLUMNS
        + _division_containing(x, CHILD_X0, CHILD_X1)
    )


# --- the grid --------------------------------------------------------------------


@pytest.mark.unit
def test_every_axis_is_a_whole_number_of_units_at_both_levels():
    """What makes a cell one floor division instead of a float multiply and a round."""
    assert ROOT_WIDTH * ROOT_COLUMNS == 2 * MAX_LNG_VAL_INT
    assert ROOT_WIDTH * ROOT_ROWS == 2 * MAX_LAT_VAL_INT
    assert CHILD_WIDTH * CHILD_COLUMNS == 2 * MAX_LNG_VAL_INT
    assert CHILD_WIDTH * CHILD_ROWS == 2 * MAX_LAT_VAL_INT
    assert ROOT_WIDTH == CHILD_WIDTH * BLOCK_SIDE


@pytest.mark.unit
@pytest.mark.parametrize(
    "count, width, half_span",
    [
        (ROOT_COLUMNS, ROOT_WIDTH, MAX_LNG_VAL_INT),
        (ROOT_ROWS, ROOT_WIDTH, MAX_LAT_VAL_INT),
        (CHILD_COLUMNS, CHILD_WIDTH, MAX_LNG_VAL_INT),
        (CHILD_ROWS, CHILD_WIDTH, MAX_LAT_VAL_INT),
    ],
)
def test_the_divisions_of_an_axis_tile_it_without_gap_or_overlap(
    count, width, half_span
):
    """Every integer coordinate belongs to exactly one division, and the ends are the
    ends: a gap is a cell nothing answers, an overlap a cell two answers disagree in."""
    first, last = _level_bounds(count, width, half_span)
    assert np.array_equal(first[1:], last[:-1] + 1)
    assert int(first[0]) == -half_span + 1
    assert int(last[-1]) == half_span


@pytest.mark.unit
def test_the_two_levels_address_each_other_both_ways():
    """``child_cells_of`` and ``parent_cell_of`` are inverses, and the block position is
    where the descent reads - so a disagreement between them is a child answering with
    its neighbour's value."""
    rng = np.random.default_rng(0)
    for root in rng.integers(0, ROOT_CELLS, 500).tolist():
        children = child_cells_of(root).tolist()
        assert len(set(children)) == BLOCK_CELLS
        assert [parent_cell_of(child) for child in children] == [root] * BLOCK_CELLS
        assert [block_position_of(child) for child in children] == list(
            range(BLOCK_CELLS)
        )
        assert all(not is_root_cell(child) for child in children)
        # the block covers exactly its parent's region
        x0, y0, x1, y1 = cell_bounds(root)
        boxes = [cell_bounds(child) for child in children]
        assert min(b[0] for b in boxes) == x0
        assert min(b[1] for b in boxes) == y0
        assert max(b[2] for b in boxes) == x1
        assert max(b[3] for b in boxes) == y1


@pytest.mark.unit
def test_a_cell_id_names_one_level_and_the_two_ranges_do_not_meet():
    """The levels are numbered one after the other, so no cell id means two things."""
    assert is_root_cell(0) and is_root_cell(ROOT_CELLS - 1)
    assert not is_root_cell(ROOT_CELLS)
    assert child_cells_of(0).min() == ROOT_CELLS
    assert (
        child_cells_of(ROOT_CELLS - 1).max()
        == ROOT_CELLS + CHILD_COLUMNS * CHILD_ROWS - 1
    )


@pytest.mark.unit
def test_cell_bounds_vectorises_to_the_same_numbers_with_the_levels_mixed():
    """The converter builds boxes in bulk through the array form, so it has to agree."""
    ids = np.array(
        [0, 17, ROOT_CELLS - 1, ROOT_CELLS, ROOT_CELLS + 5000], dtype=np.int64
    )
    x0, y0, x1, y1 = cell_bounds_of(ids)
    assert [
        (int(a), int(b), int(c), int(d))
        for a, b, c, d in zip(x0, y0, x1, y1, strict=True)
    ] == [cell_bounds(int(i)) for i in ids]


@pytest.mark.unit
def test_the_prologue_rewrites_the_two_unowned_lines_and_nothing_else():
    """-180 degrees reads as +180 - the *last* column, not the first - and -90 as the
    point one unit north. Only those two spellings can go negative after the shift, which
    is what lets the rewrite be two branches rather than a range check."""
    last_column_x = ROOT_WIDTH * ROOT_COLUMNS - 1
    assert shifted(-180.0, 0.0)[0] == last_column_x
    assert shifted(180.0, 0.0)[0] == last_column_x
    assert root_cell_of(*shifted(-180.0, 0.0)) == root_cell_of(*shifted(180.0, 0.0))

    assert shifted(0.0, -90.0)[1] == 0
    assert root_cell_of(*shifted(0.0, -90.0)) == root_cell_of(
        *shifted(0.0, -90.0 + 1 / COORD2INT_FACTOR)
    )

    # every other coordinate is the plain shift, with nothing to rewrite
    rng = np.random.default_rng(1)
    for lng, lat in zip(
        rng.uniform(-179.999, 180.0, 400), rng.uniform(-89.999, 90.0, 400), strict=True
    ):
        x, y = shifted(float(lng), float(lat))
        assert x == int(lng * COORD2INT_FACTOR) + MAX_LNG_VAL_INT - 1
        assert y == int(lat * COORD2INT_FACTOR) + MAX_LAT_VAL_INT - 1


# --- what is committed -----------------------------------------------------------


@pytest.mark.unit
def test_the_packaged_index_holds_together():
    """The same check the converter runs over what it wrote, over what is committed."""
    validate_shortcut_index(DEFAULT_DATA_DIR)


@pytest.mark.unit
def test_the_packaged_index_answers_every_cell_it_covers(tf):
    """Every stored cell resolves through the query path to what the index holds.

    Probed at the cell's own centre, computed from its bounds: the cells are rectangles,
    so their centre is exact and needs no library to state it.
    """
    index = read_shortcuts_binary(get_shortcut_file_path(DEFAULT_DATA_DIR))
    for cell_id, value in index.items():
        x0, y0, x1, y1 = cell_bounds(cell_id)
        lng = ((x0 + x1) // 2) / COORD2INT_FACTOR
        lat = ((y0 + y1) // 2) / COORD2INT_FACTOR
        if isinstance(value, int):
            assert tf.unique_timezone_at(lng=lng, lat=lat) == tf.zone_name_from_id(
                value
            )
        else:
            assert len(value) >= 2
            assert tf.unique_timezone_at(lng=lng, lat=lat) is None


# --- the round trip --------------------------------------------------------------


@pytest.mark.unit
def test_zone_ids_and_candidate_lists_round_trip(tmp_path):
    index = round_trip(build({CELL_A: 3, CHILD_B: [0, 2, 4], CELL_C: 1}), tmp_path)
    assert index.value_of(CELL_A) == 3
    assert list(index.value_of(CHILD_B)) == [0, 2, 4]
    assert index.value_of(CELL_C) == 1
    assert index.nr_of_entries == 1
    assert index.nr_of_blocks == 1


@pytest.mark.unit
def test_an_uncovered_cell_answers_none(tmp_path):
    index = round_trip(build({CELL_A: 3}), tmp_path)
    assert index.value_of(CELL_B) is None
    assert index.nr_of_blocks == 0
    assert len(index.blocks) == 0


@pytest.mark.unit
def test_an_empty_candidate_list_is_stored_as_absent(tmp_path):
    """Both answer ``None`` everywhere, and storing nothing does not need an index."""
    index = round_trip(build({CHILD_A: [], CELL_B: 3}), tmp_path)
    assert index.value_of(CHILD_A) is None
    assert index.nr_of_entries == 0


@pytest.mark.unit
def test_identical_candidate_lists_are_stored_once_and_share_no_indirection(tmp_path):
    """Duplicates carry *equal offsets*, which is what makes sharing free at lookup."""
    index = round_trip(
        build({CHILD_A: [0, 2], CHILD_B: [0, 2], CHILD_C: [2, 4]}), tmp_path
    )
    assert index.nr_of_entries == 2
    assert len(index.payload) == 4
    assert list(index.value_of(CHILD_A)) == list(index.value_of(CHILD_B)) == [0, 2]
    assert index.entry_of(CHILD_A) == index.entry_of(CHILD_B)


@pytest.mark.unit
def test_the_stop_index_is_what_the_query_would_have_computed(tmp_path):
    """``[0, 2, 4]`` has zones ``[0, 1, 2]``, so no test may be skipped; ``[2, 3]``
    shares zone 1 throughout, which a unique cell would have caught, and ``[0, 1, 2]``
    may stop at 2."""
    index = round_trip(build({CHILD_A: [0, 2, 4], CHILD_B: [0, 1, 2]}), tmp_path)
    stop = {
        tuple(int(p) for p in index.polygons_of_entry(i)): int(index.last_change[i])
        for i in range(index.nr_of_entries)
    }
    assert stop == {(0, 2, 4): 2, (0, 1, 2): 2}


@pytest.mark.unit
def test_an_index_without_any_candidate_list_round_trips(tmp_path):
    """A dataset every cell of which is unambiguous stores no payload at all."""
    index = round_trip(build({CELL_A: 1, CELL_B: 2}), tmp_path)
    assert index.nr_of_entries == 0
    assert len(index.payload) == 0
    assert index.value_of(CELL_A) == 1


@pytest.mark.unit
def test_replacing_one_cell_shares_every_array_it_did_not_touch(tmp_path):
    """The operation the tests reaching ``ABSENT`` use. A copy rather than a write,
    because loaded index arrays are the dataset and are frozen."""
    index = round_trip(build({CELL_A: 1, CHILD_B: [0, 2]}), tmp_path)
    blanked = index.replacing(CELL_A, ABSENT)
    assert blanked.value_of(CELL_A) is None
    assert index.value_of(CELL_A) == 1, "the original must not have moved"
    assert blanked.blocks is index.blocks
    assert blanked.payload is index.payload

    blanked_child = index.replacing(CHILD_B, ABSENT)
    assert blanked_child.value_of(CHILD_B) is None
    assert blanked_child.table is index.table


# --- the guards ------------------------------------------------------------------


@pytest.mark.unit
def test_a_single_candidate_is_refused_because_the_encoding_needs_it_impossible():
    """It is what leaves a table value free to mean "no cell here", so it cannot be
    stored - and it never has to be, a lone candidate being unambiguous."""
    with pytest.raises(ValueError, match="single candidate"):
        build({CHILD_A: [3]})


@pytest.mark.unit
def test_a_root_cell_cannot_both_answer_and_refine():
    """The lookup reads one value per root cell and the sign says which it is, so a cell
    claiming both would answer one of them and silently drop the other."""
    with pytest.raises(ValueError, match="also has finest-level cells"):
        build({parent_cell_of(CHILD_A): 1, CHILD_A: [0, 2]})


@pytest.mark.unit
def test_a_root_cell_may_not_carry_a_candidate_list():
    """A negative root value is the index of a child block, not of a candidate list -
    the two are the same number and only the level tells them apart."""
    with pytest.raises(ValueError, match="stores a candidate list"):
        build({CELL_A: [0, 2]})


@pytest.mark.unit
@pytest.mark.parametrize("cell", [CELL_A, CHILD_A], ids=["root", "finest"])
def test_a_zone_id_the_level_cannot_hold_names_the_width_to_move_to(cell):
    """The message is the deliverable: whoever hits this is regenerating the data years
    from now and needs the ceiling, the remedy and the release ordering. Both levels
    store zone ids in the same ``int16``, so both have to refuse one that does not fit."""
    with pytest.raises(ShortcutOverflowError) as excinfo:
        build({cell: 40_000})
    message = str(excinfo.value)
    assert "40,000" in message
    assert "32,767" in message
    assert "int32" in message
    assert "SHORTCUT_LAYOUT_VERSION" in message
    assert "DATA_FORMAT_VERSION" in message


@pytest.mark.unit
def test_more_child_blocks_than_the_root_table_can_name_is_refused():
    """The overflow the tree adds, and the one no current dataset comes near: 10,538 root
    cells refine against a ceiling of 32,766. A block index past it would wrap into a
    zone id and answer a plausible wrong timezone, so it is refused where the data is
    built. The remedy names making the root grid finer first, because that is the cheap
    half of the fix - a narrower root cell refines less often.
    """
    ceiling = int(np.iinfo(TABLE_DTYPE).max) - 1
    mapping = {
        # one child per refined root is enough to make the root refine, and far cheaper
        # than sixteen: what is being overflowed is the number of blocks
        int(child_cells_of(root)[0]): 1
        for root in range(ceiling + 1)
    }
    with pytest.raises(ShortcutOverflowError) as excinfo:
        build(mapping)
    message = str(excinfo.value)
    assert "child block index" in message
    assert "root grid finer" in message


def _data_dir_with_shortcut_file(tmp_path: Path, buffer: bytes) -> Path:
    """A minimal compiled data directory holding ``buffer`` as its shortcut index."""
    data_dir = tmp_path / "data"
    data_dir.mkdir(exist_ok=True)
    for name in ("zone_ids.npy", "timezone_names.txt"):
        (data_dir / name).write_bytes((DEFAULT_DATA_DIR / name).read_bytes())
    get_shortcut_file_path(data_dir).write_bytes(buffer)
    return data_dir


def _packaged_header() -> tuple[int, ...]:
    source = get_shortcut_file_path(DEFAULT_DATA_DIR).read_bytes()
    return tuple(
        int(v) for v in np.frombuffer(source, dtype=np.int64, count=6, offset=8)
    )


def _bounds_offset(nr_blocks: int) -> int:
    return _HEADER_SIZE + (ROOT_CELLS + nr_blocks * BLOCK_CELLS) * TABLE_DTYPE.itemsize


@pytest.mark.unit
def test_a_padded_offset_column_is_caught_over_the_committed_data(tmp_path):
    """The widths are chosen by fit, and this is the only direction a reader can check.

    A width that is too *narrow* wrapped what it wrote, and the wrapped value comes back
    off disk fitting that width perfectly - so it is caught by the lengths it makes
    negative, not by re-measuring the column. A width that is too *wide* leaves no trace
    at all beyond the bytes it costs, which is what this is for.
    """
    source = get_shortcut_file_path(DEFAULT_DATA_DIR).read_bytes()
    columns, side, nr_blocks, nr_entries, offset_width, length_width = (
        _packaged_header()
    )
    bounds_at = _bounds_offset(nr_blocks)
    bounds = np.frombuffer(
        source,
        dtype=np.dtype(f"uint{offset_width * 8}"),
        count=nr_entries + 1,
        offset=bounds_at,
    )
    wider = offset_width * 2
    padded = (
        source[:8]
        + np.array(
            [columns, side, nr_blocks, nr_entries, wider, length_width], dtype=np.int64
        ).tobytes()
        + source[_HEADER_SIZE:bounds_at]
        + bounds.astype(np.dtype(f"uint{wider * 8}")).tobytes()
        + source[bounds_at + (nr_entries + 1) * offset_width :]
    )

    with pytest.raises(DataIntegrityError, match="bits wide"):
        validate_shortcut_index(_data_dir_with_shortcut_file(tmp_path, padded))


@pytest.mark.unit
def test_an_offset_column_too_narrow_for_its_payload_is_caught(tmp_path):
    """The other direction, and the reason re-measuring the column cannot find it.

    An offset that overflowed its column wrapped to a small value, and reading it back
    through that same width returns the wrapped value - in range, indistinguishable from
    an intended one. What gives it away is the candidate list it truncates: the offsets
    ascend, so a wrapped one leaves the entry before it with a negative length.
    """
    source = bytearray(get_shortcut_file_path(DEFAULT_DATA_DIR).read_bytes())
    _, _, nr_blocks, _, offset_width, _ = _packaged_header()
    bounds_at = _bounds_offset(nr_blocks)
    # wrap the second offset back to 0, as too narrow a column would have stored it
    source[bounds_at + offset_width : bounds_at + 2 * offset_width] = bytes(
        offset_width
    )

    with pytest.raises(DataIntegrityError, match="wrapped"):
        validate_shortcut_index(_data_dir_with_shortcut_file(tmp_path, bytes(source)))


@pytest.mark.unit
def test_a_root_cell_naming_a_block_that_is_not_stored_is_caught(tmp_path):
    """The tree's own structural guard. The descent multiplies a block index by the block
    size and reads, so an index past the last block reads whatever follows the array -
    and the file is otherwise perfectly well-formed."""
    source = bytearray(get_shortcut_file_path(DEFAULT_DATA_DIR).read_bytes())
    _, _, nr_blocks, _, _, _ = _packaged_header()
    table = np.frombuffer(
        bytes(source), dtype=TABLE_DTYPE, count=ROOT_CELLS, offset=_HEADER_SIZE
    )
    refined = int(np.flatnonzero(table < ABSENT)[0])
    at = _HEADER_SIZE + refined * TABLE_DTYPE.itemsize
    source[at : at + TABLE_DTYPE.itemsize] = np.array(
        [-(nr_blocks + 2)], dtype=TABLE_DTYPE
    ).tobytes()

    with pytest.raises(DataIntegrityError, match="names child block"):
        validate_shortcut_index(_data_dir_with_shortcut_file(tmp_path, bytes(source)))


@pytest.mark.unit
def test_two_root_cells_naming_one_block_is_caught(tmp_path):
    """One of them would answer the other's region, and nothing about the bytes says so.

    Also what catches a block nothing points at, which is dead weight in a file whose
    whole purpose is to be small.
    """
    source = bytearray(get_shortcut_file_path(DEFAULT_DATA_DIR).read_bytes())
    table = np.frombuffer(
        bytes(source), dtype=TABLE_DTYPE, count=ROOT_CELLS, offset=_HEADER_SIZE
    )
    first, second = (int(i) for i in np.flatnonzero(table < ABSENT)[:2])
    at = _HEADER_SIZE + second * TABLE_DTYPE.itemsize
    source[at : at + TABLE_DTYPE.itemsize] = table[first : first + 1].tobytes()

    with pytest.raises(DataIntegrityError, match="same child block"):
        validate_shortcut_index(_data_dir_with_shortcut_file(tmp_path, bytes(source)))


@pytest.mark.unit
def test_a_block_naming_a_candidate_list_that_is_not_stored_is_caught(tmp_path):
    """The block level's half of the same guard, and the deeper of the two reads.

    A negative value means a child block on the root level and a candidate list on the
    block level; nothing in the number says which, so each level has to be checked
    against the array it addresses. This is the one the query follows furthest: the entry
    index goes straight into the CSR bounds, so an index past the last entry reads two
    offsets from beyond the array and slices the payload with them.
    """
    source = bytearray(get_shortcut_file_path(DEFAULT_DATA_DIR).read_bytes())
    _, _, nr_blocks, nr_entries, _, _ = _packaged_header()
    blocks_at = _HEADER_SIZE + ROOT_CELLS * TABLE_DTYPE.itemsize
    blocks = np.frombuffer(
        bytes(source),
        dtype=TABLE_DTYPE,
        count=nr_blocks * BLOCK_CELLS,
        offset=blocks_at,
    )
    listed = int(np.flatnonzero(blocks < ABSENT)[0])
    at = blocks_at + listed * TABLE_DTYPE.itemsize
    source[at : at + TABLE_DTYPE.itemsize] = np.array(
        [-(nr_entries + 2)], dtype=TABLE_DTYPE
    ).tobytes()

    with pytest.raises(DataIntegrityError, match="points at candidate list"):
        validate_shortcut_index(_data_dir_with_shortcut_file(tmp_path, bytes(source)))


@pytest.mark.unit
def test_a_zone_count_past_the_id_width_is_caught(tmp_path):
    """Two widths carry a zone id - the shortcut levels and a batch lookup's answer
    array - and both are ``int16`` because that is what the dataset fits, not because
    of headroom. Nothing at lookup time re-checks the fit, so a dataset that outgrew it
    has to be refused where the data is produced; past the ceiling the id would wrap and
    a query would answer with a different zone's name."""
    data_dir = _data_dir_with_shortcut_file(
        tmp_path, get_shortcut_file_path(DEFAULT_DATA_DIR).read_bytes()
    )
    too_many = int(np.iinfo(ZONE_ID_RESULT_DTYPE).max) + 2
    (data_dir / "timezone_names.txt").write_text(
        "\n".join(f"Zone/{i}" for i in range(too_many)), encoding="utf-8"
    )

    with pytest.raises(DataIntegrityError, match="the widest a zone id may be"):
        validate_shortcut_index(data_dir)


@pytest.mark.unit
def test_a_corrupted_stop_index_is_caught_over_the_committed_data(tmp_path):
    """A guard that cannot fail is not one. A stop index one too small ends the
    candidate loop early and attributes the point to the wrong zone - which nothing
    about the file announces."""
    corrupted = bytearray(get_shortcut_file_path(DEFAULT_DATA_DIR).read_bytes())
    corrupted[-1] = (corrupted[-1] + 1) % 256

    with pytest.raises(DataIntegrityError, match="no other zone can be matched"):
        validate_shortcut_index(
            _data_dir_with_shortcut_file(tmp_path, bytes(corrupted))
        )


# --- the layout markers ----------------------------------------------------------


@pytest.mark.unit
def test_the_written_file_carries_the_identifier_and_the_layout_version(tmp_path):
    path = get_shortcut_file_path(tmp_path)
    write_shortcuts_binary(build({CELL_A: 1}), path)
    buffer = path.read_bytes()
    assert buffer[:4] == FILE_IDENTIFIER
    assert (
        int(np.frombuffer(buffer, dtype=np.uint32, count=1, offset=4)[0])
        == SHORTCUT_LAYOUT_VERSION
    )


@pytest.mark.unit
def test_a_file_without_the_identifier_is_reported_as_layout_version_zero(tmp_path):
    """Which is what a data directory written before this format actually is, for
    everyone who will ever hit it - not a corrupt file."""
    path = get_shortcut_file_path(tmp_path)
    path.write_bytes(b"\x00" * 64)
    with pytest.raises(ValueError, match="layout version 0"):
        read_shortcuts_binary(path)


@pytest.mark.unit
def test_a_newer_layout_version_is_rejected_rather_than_read(tmp_path):
    path = get_shortcut_file_path(tmp_path)
    write_shortcuts_binary(build({CELL_A: 1}), path)
    buffer = bytearray(path.read_bytes())
    buffer[4:8] = np.array([SHORTCUT_LAYOUT_VERSION + 1], dtype=np.uint32).tobytes()
    path.write_bytes(bytes(buffer))
    with pytest.raises(
        ValueError, match=f"layout version {SHORTCUT_LAYOUT_VERSION + 1}"
    ):
        read_shortcuts_binary(path)


@pytest.mark.unit
@pytest.mark.parametrize("field", [0, 1], ids=["root columns", "block side"])
def test_a_file_built_for_another_grid_is_rejected(tmp_path, field):
    """The one marker the layout version cannot stand in for.

    The layout is byte-for-byte identical at every grid shape, so a file built for
    another one parses perfectly and every cell in it addresses a different region - the
    reader would answer with another cell's timezone rather than fail. The grid is
    recorded in the header for that reason alone, which makes this the only thing that
    exercises it: nothing else in the suite reads those fields.
    """
    path = get_shortcut_file_path(tmp_path)
    write_shortcuts_binary(build({CELL_A: 1}), path)
    buffer = bytearray(path.read_bytes())
    at = 8 + field * 8
    stated = (ROOT_COLUMNS, BLOCK_SIDE)[field]
    buffer[at : at + 8] = np.array([stated * 2], dtype=np.int64).tobytes()
    path.write_bytes(bytes(buffer))

    with pytest.raises(ValueError) as excinfo:
        read_shortcuts_binary(path)

    message = str(excinfo.value)
    assert str(stated * 2) in message, "must name the file's own"
    assert str(stated) in message, "must name what this version reads"
    assert "file_converter.py" in message, "must name the way to regenerate"


@pytest.mark.unit
def test_the_packaged_file_carries_the_markers_its_own_writer_stamps():
    buffer = get_shortcut_file_path(DEFAULT_DATA_DIR).read_bytes()
    assert buffer[:4] == FILE_IDENTIFIER
    assert (
        int(np.frombuffer(buffer, dtype=np.uint32, count=1, offset=4)[0])
        == SHORTCUT_LAYOUT_VERSION
    )
    columns, side, *_ = _packaged_header()
    assert (columns, side) == (ROOT_COLUMNS, BLOCK_SIDE)


@pytest.mark.unit
def test_entry_at_answers_what_entry_of_answers_for_the_points_cell(tf):
    """The point forms are the cell forms behind one cell computation, scalar and batch.

    Every lookup method reaches the index through ``entry_at`` / ``entries_at``, so a
    swapped coordinate order or a mis-zipped batch there would move answers everywhere
    while ``entry_of`` - what the format tests check - stayed right. The expectation is
    computed independently, from ``cell_bounds`` by search and ``utils.query2int``, over
    the random and ambiguous fixtures plus the corners and edges of the coordinate plane.
    """
    points = [
        *load_benchmark_points(RANDOM_POINTS_FIXTURE)[:1000],
        *load_benchmark_points(AMBIGUOUS_SHORTCUT_POINTS_FIXTURE)[:1000],
        *((lng, lat) for lng in (-180.0, 0.0, 180.0) for lat in (-90.0, 0.0, 90.0)),
    ]
    lngs = np.array([lng for lng, _ in points], dtype=np.float64)
    lats = np.array([lat for _, lat in points], dtype=np.float64)
    expected = [
        tf.shortcuts.entry_of(reference_cell(tf.shortcuts, lng, lat))
        for lng, lat in points
    ]
    assert any(e < ABSENT for e in expected) and any(e >= 0 for e in expected), (
        "the sample must reach both a unique and an ambiguous cell"
    )

    assert [tf.shortcuts.entry_at(lng, lat) for lng, lat in points] == expected
    assert [tf.shortcuts.cell_at(lng, lat) for lng, lat in points] == [
        reference_cell(tf.shortcuts, lng, lat) for lng, lat in points
    ]
    batch = tf.shortcuts.entries_at(lngs, lats)
    assert batch.dtype == tf.shortcuts.table.dtype
    assert batch.tolist() == expected
    assert tf.shortcuts.entries_at(lngs[:0], lats[:0]).shape == (0,)


@pytest.mark.unit
def test_entries_of_answers_what_entry_of_answers_for_every_cell(tf):
    """The batch sibling has to be the same lookup, not merely a lookup that agrees on
    the fixtures. It recovers each finest-level cell's parent with vectorised divmod
    rather than one at a time, so a divergence between the two - a wrong block stride, an
    index dtype that truncated - would surface only as a wrong timezone several layers
    away from its cause.

    Every cell the tree has, so the uncovered ones are in it too.
    """
    index = tf.shortcuts
    roots = np.arange(ROOT_CELLS, dtype=np.int64)
    refined = np.flatnonzero(index.table < ABSENT)
    cells = np.concatenate(
        [roots, np.concatenate([child_cells_of(int(r)) for r in refined])]
    )
    batch = index.entries_of(cells)

    assert batch.dtype == index.table.dtype
    expected = np.fromiter(
        (index.entry_of(cell) for cell in cells.tolist()),
        dtype=batch.dtype,
        count=cells.shape[0],
    )
    assert np.array_equal(batch, expected)


@pytest.mark.unit
def test_a_finest_level_cell_whose_root_answers_has_no_value_to_read(tf):
    """Asking for one is a caller error rather than a number: the block it would be read
    out of belongs to a different root cell, so the answer would be another region's."""
    index = tf.shortcuts
    answering_root = int(np.flatnonzero(index.table >= 0)[0])
    orphan = int(child_cells_of(answering_root)[0])
    with pytest.raises(ValueError, match="stores an answer of its own"):
        index.entry_of(orphan)
    with pytest.raises(ValueError, match="stores an answer of its own"):
        index.entries_of(np.array([orphan], dtype=np.int64))


@pytest.mark.unit
def test_the_query_reads_the_stored_stop_index_and_it_agrees_with_computing_it(tf):
    """``timezone_at`` reads ``last_change`` rather than calling ``get_last_change_idx``.

    ``validate_shortcut_index`` checks the *stored* values are right. Nothing checked that
    the query uses them, which is the other half: reading the wrong entry's stop index
    ends the candidate loop early and attributes the point to the wrong zone, while the
    file stays perfectly valid - so no build-time check can see it. Here the one line is
    reverted to a live computation and the answers must not move.
    """

    class LiveStopIndex(type(tf)):
        __slots__ = ()

        def timezone_at(self, *, lng, lat):
            lng, lat = utils.validate_coordinates(lng, lat)
            entry = self.shortcuts.entry_at(lng, lat)
            if entry >= 0:
                return self.zone_name_from_id(entry)
            if entry == ABSENT:
                return None
            cand = self.shortcuts.candidates_of(entry)
            zone_ids = self.zone_ids_of(cand)
            stop = get_last_change_idx(zone_ids)  # what the query no longer does
            x, y = utils.query2int(lng, lat)
            for j, boundary_id in enumerate(cand):
                if j >= stop:
                    break
                if self.inside_of_polygon(boundary_id, x, y):
                    return self.zone_name_from_id(int(zone_ids[j]))
            return self.zone_name_from_id(int(zone_ids[-1]))

    points = load_benchmark_points(AMBIGUOUS_SHORTCUT_POINTS_FIXTURE)[:2000]
    with LiveStopIndex() as live:
        reached = sum(
            1 for lng, lat in points if tf.shortcuts.entry_at(lng, lat) < ABSENT
        )
        assert reached > 100, (
            f"only {reached} of {len(points)} points reach the candidate loop - the "
            "assertion below would be close to vacuous"
        )
        mismatches = [
            (lng, lat)
            for lng, lat in points
            if tf.timezone_at(lng=lng, lat=lat) != live.timezone_at(lng=lng, lat=lat)
        ]
    assert not mismatches, (
        f"{len(mismatches)} points answer differently when the stop index is computed "
        f"instead of read, e.g. {mismatches[:3]}"
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "entry_list, expected",
    [
        ([], 0),
        ([1], 0),
        ([2], 0),
        ([1, 1], 0),
        ([1, 2], 1),
        ([1, 3], 1),
        ([1, 3, 3], 1),
        ([1, 3, 3, 0], 3),
        ([1, 3, 3, 0, 0, 0, 0], 3),
    ],
)
def test_get_last_change_idx(entry_list, expected):
    array = np.array(entry_list, dtype=ZONE_ID_DTYPE)
    assert get_last_change_idx(array) == expected
