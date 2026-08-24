"""The shortcut index format: the addressing, the guards, and what it refuses.

The lookup reads one ``int16`` out of a table it addressed by slicing bits out of an H3
cell id, and follows what it finds there straight into the payload - no bounds check, no
key comparison, no dispatch beyond the sign. Every assumption that makes that safe is
established where the data is built (``scripts.data_integrity.validate_shortcut_index``)
and asserted here over what is committed, sharing one implementation so the two cannot
drift.

What each group covers:

* the slot map is a bijection, and agrees with h3's public accessors;
* the committed binary holds together, cell by cell;
* the build-time guards fail loudly, since a guard that cannot fail is not one;
* the layout markers reject data this version cannot read.
"""

from pathlib import Path

import numpy as np
import pytest
from h3.api import numpy_int as h3

from scripts.configs import ZONE_ID_DTYPE
from scripts.data_integrity import (
    DataIntegrityError,
    all_cells_at_shortcut_res,
    validate_shortcut_index,
)
from tests.auxiliaries import (
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
    load_benchmark_points,
)
from timezonefinder.configs import (
    DEFAULT_DATA_DIR,
    SHORTCUT_H3_RES,
    ZONE_ID_RESULT_DTYPE,
)
from timezonefinder.shortcut_index import (
    ABSENT,
    COMPACT_TABLE_SIZE,
    TABLE_DTYPE,
    _HEADER_SIZE,
    FILE_IDENTIFIER,
    SHORTCUT_LAYOUT_VERSION,
    SLOT_BASE_CELL_MASK,
    SLOT_BASE_CELL_SHIFT,
    SLOT_DIGITS_MASK,
    SLOT_DIGITS_SHIFT,
    SLOT_STRIDE,
    SLOT_TABLE_SIZE,
    ShortcutOverflowError,
    build_shortcut_index,
    cell_of_slot,
    compact_of_expanded,
    compact_slots_of,
    expand_compact,
    get_last_change_idx,
    get_shortcut_file_path,
    read_shortcuts_binary,
    slot_of,
    slots_of,
    write_shortcuts_binary,
)

# Three distinct cells at whatever resolution is in force, derived rather than written as
# literals: a hard-coded cell id is a resolution-3 id and stops addressing anything the
# moment SHORTCUT_H3_RES moves.
CELL_A, CELL_B, CELL_C = (
    int(h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES))
    for lat, lng in ((52.5, 13.4), (48.85, 2.35), (35.0, 139.0))
)

# zone id per boundary polygon, for the hand-built indices below
ZONE_IDS = np.array([0, 0, 1, 1, 2], dtype=np.uint16)


def build(mapping, zone_ids=ZONE_IDS):
    return build_shortcut_index(mapping, zone_ids)


def round_trip(index, tmp_path: Path):
    path = get_shortcut_file_path(tmp_path)
    write_shortcuts_binary(index, path)
    return read_shortcuts_binary(path)


# --- the addressing --------------------------------------------------------------


@pytest.mark.unit
def test_the_slot_map_is_a_bijection_over_every_cell_at_this_resolution():
    """Not over the packaged keys - over the whole domain, which is the stronger claim.

    Custom data can cover cells the packaged dataset does not, and the padding the reader
    fills has to be padding for *all* of them.
    """
    cells = all_cells_at_shortcut_res()
    slots = slots_of(cells)
    assert len(np.unique(slots)) == len(cells)
    assert int(slots.max()) < SLOT_TABLE_SIZE
    assert [cell_of_slot(int(s)) for s in slots[:1000]] == [
        int(c) for c in cells[:1000]
    ]


@pytest.mark.unit
def test_nothing_outside_the_slot_bits_distinguishes_two_cells():
    """Why the map is a bijection and not a hash: at a fixed resolution every other bit
    of a cell id is the same constant, so the slot bits carry the whole identity."""
    cells = all_cells_at_shortcut_res()
    slot_bits = np.int64(
        (SLOT_BASE_CELL_MASK << SLOT_BASE_CELL_SHIFT)
        | (SLOT_DIGITS_MASK << SLOT_DIGITS_SHIFT)
    )
    assert len(np.unique(cells & ~slot_bits)) == 1


@pytest.mark.unit
def test_the_slot_is_one_contiguous_bit_field():
    """The lookup is a shift and a mask; this is what makes that the same arithmetic.

    H3 puts the base cell immediately above the digits, so ``base * stride + digits`` is
    the contiguous field at ``SLOT_DIGITS_SHIFT``. Asserted over arbitrary integers as
    well as over real cells, because it is an identity rather than a property of the cells
    that happen to exist - and because the tempting "fix" to the mask would still pass on
    real cells alone.
    """

    def the_long_way(values):
        return (
            (values >> SLOT_BASE_CELL_SHIFT) & SLOT_BASE_CELL_MASK
        ) * SLOT_STRIDE + ((values >> SLOT_DIGITS_SHIFT) & SLOT_DIGITS_MASK)

    cells = all_cells_at_shortcut_res()
    assert np.array_equal(slots_of(cells), the_long_way(cells))
    arbitrary = np.random.default_rng(0).integers(
        0, 2**62, size=200_000, dtype=np.int64
    )
    assert np.array_equal(slots_of(arbitrary), the_long_way(arbitrary))


@pytest.mark.unit
def test_the_compact_form_survives_expansion():
    compact = np.arange(COMPACT_TABLE_SIZE, dtype=np.int16)
    expanded = expand_compact(compact, fill=ABSENT)
    assert len(expanded) == SLOT_TABLE_SIZE
    assert np.array_equal(compact_of_expanded(expanded), compact)
    cells = all_cells_at_shortcut_res()
    # the two addressings must name the same entry for every cell that exists
    assert np.array_equal(expanded[slots_of(cells)], compact[compact_slots_of(cells)])


@pytest.mark.unit
def test_unreachable_slots_read_as_absent_rather_than_as_zone_zero():
    """A table whose padding reads as zone id 0 is one nobody can assert over.

    Two kinds of slot are unreachable and both have to end up absent: the base-8 digits
    the file never stores, which :func:`expand_compact` fills, and the pentagon deleted
    subsequences *inside* the stored block, which only the builder can set. So this is
    asserted over a built table rather than over an arbitrary expansion.
    """
    index = build({CELL_A: 1, CELL_B: [0, 2]})
    reachable = np.zeros(SLOT_TABLE_SIZE, dtype=bool)
    reachable[slots_of(all_cells_at_shortcut_res())] = True
    assert np.all(index.table[~reachable] == ABSENT)


# --- what is committed -----------------------------------------------------------


@pytest.mark.unit
def test_the_packaged_index_holds_together():
    """The same check the converter runs over what it wrote, over what is committed."""
    validate_shortcut_index(DEFAULT_DATA_DIR)


@pytest.mark.unit
def test_the_packaged_index_answers_every_cell_it_covers(tf):
    """Every stored cell resolves through the query path to what the index holds."""
    index = read_shortcuts_binary(get_shortcut_file_path(DEFAULT_DATA_DIR))
    for hex_id, value in index.items():
        lat, lng = h3.cell_to_latlng(hex_id)
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
    index = round_trip(build({CELL_A: 3, CELL_B: [0, 2, 4], CELL_C: 1}), tmp_path)
    assert index.value_of(CELL_A) == 3
    assert list(index.value_of(CELL_B)) == [0, 2, 4]
    assert index.value_of(CELL_C) == 1
    assert index.nr_of_entries == 1


@pytest.mark.unit
def test_an_uncovered_cell_answers_none(tmp_path):
    index = round_trip(build({CELL_A: 3}), tmp_path)
    assert index.value_of(CELL_B) is None


@pytest.mark.unit
def test_an_empty_candidate_list_is_stored_as_absent(tmp_path):
    """Both answer ``None`` everywhere, and storing nothing does not need an index."""
    index = round_trip(build({CELL_A: [], CELL_B: 3}), tmp_path)
    assert index.value_of(CELL_A) is None
    assert index.nr_of_entries == 0


@pytest.mark.unit
def test_identical_candidate_lists_are_stored_once_and_share_no_indirection(tmp_path):
    """Duplicates carry *equal offsets*, which is what makes sharing free at lookup."""
    index = round_trip(
        build({CELL_A: [0, 2], CELL_B: [0, 2], CELL_C: [2, 4]}), tmp_path
    )
    assert index.nr_of_entries == 2
    assert len(index.payload) == 4
    assert list(index.value_of(CELL_A)) == list(index.value_of(CELL_B)) == [0, 2]
    assert index.table[slot_of(CELL_A)] == index.table[slot_of(CELL_B)]


@pytest.mark.unit
def test_the_stop_index_is_what_the_query_would_have_computed(tmp_path):
    """``[0, 2, 4]`` has zones ``[0, 1, 2]``, so no test may be skipped; ``[2, 3]``
    shares zone 1 throughout, which a unique cell would have caught, and ``[0, 1, 2]``
    may stop at 2."""
    index = round_trip(build({CELL_A: [0, 2, 4], CELL_B: [0, 1, 2]}), tmp_path)
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


# --- the guards ------------------------------------------------------------------


@pytest.mark.unit
def test_a_single_candidate_is_refused_because_the_encoding_needs_it_impossible():
    """It is what leaves a table value free to mean "no cell here", so it cannot be
    stored - and it never has to be, a lone candidate being unambiguous."""
    with pytest.raises(ValueError, match="single candidate"):
        build({CELL_A: [3]})


@pytest.mark.unit
def test_a_zone_id_the_table_cannot_hold_names_the_width_to_move_to():
    """The message is the deliverable: whoever hits this is regenerating the data years
    from now and needs the ceiling, the remedy and the release ordering."""
    with pytest.raises(ShortcutOverflowError) as excinfo:
        build({CELL_A: 40_000})
    message = str(excinfo.value)
    assert "40,000" in message
    assert "32,767" in message
    assert "int32" in message
    assert "SHORTCUT_LAYOUT_VERSION" in message
    assert "DATA_FORMAT_VERSION" in message


def _data_dir_with_shortcut_file(tmp_path: Path, buffer: bytes) -> Path:
    """A minimal compiled data directory holding ``buffer`` as its shortcut index."""
    data_dir = tmp_path / "data"
    data_dir.mkdir(exist_ok=True)
    for name in ("zone_ids.npy", "timezone_names.txt"):
        (data_dir / name).write_bytes((DEFAULT_DATA_DIR / name).read_bytes())
    get_shortcut_file_path(data_dir).write_bytes(buffer)
    return data_dir


@pytest.mark.unit
def test_a_padded_offset_column_is_caught_over_the_committed_data(tmp_path):
    """The widths are chosen by fit, and this is the only direction a reader can check.

    A width that is too *narrow* wrapped what it wrote, and the wrapped value comes back
    off disk fitting that width perfectly - so it is caught by the lengths it makes
    negative, not by re-measuring the column. A width that is too *wide* leaves no trace
    at all beyond the bytes it costs, which is what this is for.
    """
    source = get_shortcut_file_path(DEFAULT_DATA_DIR).read_bytes()
    resolution, nr_entries, offset_width, length_width = (
        int(v) for v in np.frombuffer(source, dtype=np.int64, count=4, offset=8)
    )
    bounds_at = _HEADER_SIZE + COMPACT_TABLE_SIZE * TABLE_DTYPE.itemsize
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
            [resolution, nr_entries, wider, length_width], dtype=np.int64
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
    header = np.frombuffer(bytes(source), dtype=np.int64, count=4, offset=8)
    offset_width = int(header[2])
    bounds_at = _HEADER_SIZE + COMPACT_TABLE_SIZE * TABLE_DTYPE.itemsize
    # wrap the second offset back to 0, as too narrow a column would have stored it
    source[bounds_at + offset_width : bounds_at + 2 * offset_width] = bytes(
        offset_width
    )

    with pytest.raises(DataIntegrityError, match="wrapped"):
        validate_shortcut_index(_data_dir_with_shortcut_file(tmp_path, bytes(source)))


@pytest.mark.unit
def test_a_zone_count_past_the_id_width_is_caught(tmp_path):
    """Two widths carry a zone id - the shortcut table and a batch lookup's answer
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
def test_a_file_built_for_another_h3_resolution_is_rejected(tmp_path):
    """The one marker the layout version cannot stand in for.

    The layout is byte-for-byte identical at every resolution, so a file built at another
    one parses perfectly and every slot in it addresses a different cell - the reader
    would answer with a neighbour's timezone rather than fail. The resolution is recorded
    in the header for that reason alone, which makes this the only thing that exercises
    it: nothing else in the suite reads that field.
    """
    path = get_shortcut_file_path(tmp_path)
    write_shortcuts_binary(build({CELL_A: 1}), path)
    buffer = bytearray(path.read_bytes())
    # the resolution is the first of the four int64 following the 4-byte identifier and
    # the uint32 layout version
    buffer[8:16] = np.array([SHORTCUT_H3_RES + 1], dtype=np.int64).tobytes()
    path.write_bytes(bytes(buffer))

    with pytest.raises(ValueError) as excinfo:
        read_shortcuts_binary(path)

    message = str(excinfo.value)
    assert f"resolution {SHORTCUT_H3_RES + 1}" in message, "must name the file's own"
    assert f"resolution {SHORTCUT_H3_RES}" in message, (
        "must name what this version reads"
    )
    assert "file_converter.py" in message, "must name the way to regenerate"


@pytest.mark.unit
def test_the_packaged_file_carries_the_markers_its_own_writer_stamps():
    buffer = get_shortcut_file_path(DEFAULT_DATA_DIR).read_bytes()
    assert buffer[:4] == FILE_IDENTIFIER
    assert (
        int(np.frombuffer(buffer, dtype=np.uint32, count=1, offset=4)[0])
        == SHORTCUT_LAYOUT_VERSION
    )


@pytest.mark.unit
def test_entries_of_answers_what_entry_of_answers_for_every_cell(tf):
    """The batch sibling has to be the same lookup, not merely a lookup that agrees on
    the fixtures. It reaches the table through ``slots_of`` rather than ``slot_of`` and
    indexes with a ``uint64`` array rather than a scalar, so a divergence between the
    two - a shift applied to the wrong width, an index dtype that truncated - would
    surface only as a wrong timezone several layers away from its cause.

    Every cell at this resolution, so the padding and the uncovered cells are in it too.
    """
    cells = all_cells_at_shortcut_res().astype(np.uint64)
    batch = tf.shortcuts.entries_of(cells)

    assert batch.dtype == tf.shortcuts.table.dtype
    expected = np.fromiter(
        (tf.shortcuts.entry_of(cell) for cell in cells.tolist()),
        dtype=batch.dtype,
        count=cells.shape[0],
    )
    assert np.array_equal(batch, expected)


@pytest.mark.unit
def test_the_query_reads_the_stored_stop_index_and_it_agrees_with_computing_it(tf):
    """``timezone_at`` reads ``last_change`` rather than calling ``get_last_change_idx``.

    ``validate_shortcut_index`` checks the *stored* values are right. Nothing checked that
    the query uses them, which is the other half: reading the wrong entry's stop index
    ends the candidate loop early and attributes the point to the wrong zone, while the
    file stays perfectly valid - so no build-time check can see it. Here the one line is
    reverted to a live computation and the answers must not move.
    """
    from timezonefinder import utils
    from timezonefinder.shortcut_index import ABSENT

    class LiveStopIndex(type(tf)):
        __slots__ = ()

        def timezone_at(self, *, lng, lat):
            lng, lat = utils.validate_coordinates(lng, lat)
            hex_id = h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES)
            entry = self.shortcuts.entry_of(hex_id)
            if entry >= 0:
                return self.zone_name_from_id(entry)
            if entry == ABSENT:
                return None
            cand = self.shortcuts.candidates_of(entry)
            zone_ids = self.zone_ids_of(cand)
            stop = get_last_change_idx(zone_ids)  # what the query no longer does
            x, y = utils.coord2int(lng), utils.coord2int(lat)
            for j, boundary_id in enumerate(cand):
                if j >= stop:
                    break
                if self.inside_of_polygon(boundary_id, x, y):
                    return self.zone_name_from_id(int(zone_ids[j]))
            return self.zone_name_from_id(int(zone_ids[-1]))

    points = load_benchmark_points(AMBIGUOUS_SHORTCUT_POINTS_FIXTURE)[:2000]
    with LiveStopIndex() as live:
        reached = sum(
            1
            for lng, lat in points
            if tf.shortcuts.entry_of(h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES))
            < ABSENT
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
