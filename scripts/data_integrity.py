"""Integrity checks over a *compiled* binary data directory.

These run where the data is produced and where it is reviewed - the converter checks
what it just wrote, and the test suite checks what the repository ships. They are
deliberately **not** run when a ``TimezoneFinder`` is constructed: whether a data
directory is coherent is settled once, by the build, and re-deriving it in every user's
process would spend startup time re-answering a question that already has an answer.

What that buys is the freedom to check properly. Nothing here is written to be cheap:
the reference check resolves every hole ring and compares its extent against the stored
bounding box, which is O(all hole vertices) and would be indefensible on an
initialisation path.
"""

import mmap
from pathlib import Path

import numpy as np
from h3.api import numpy_int as h3

from scripts.configs import MIN_HOLE_DEDUP_RATIO
from timezonefinder.flatbuf.schemas import (
    SCHEMA_SUFFIX,
    get_schemas_dir,
    iter_schema_files,
)
from timezonefinder.flatbuf.io.polygons import (
    derive_coord_offset_table,
    get_coordinate_path,
    get_polygon_collection,
    read_polygon_array_at,
    read_polygon_array_from_binary,
)
from timezonefinder.configs import SHORTCUT_H3_RES
from timezonefinder.np_binary_helpers import (
    get_poly_ref_path,
    get_zone_ids_path,
    read_per_polygon_vector,
)
from timezonefinder.polygon_array import HoleArray, PolygonArray
from timezonefinder.shortcut_index import (
    ABSENT,
    SLOT_BASE_CELL_MASK,
    SLOT_BASE_CELL_SHIFT,
    SLOT_TABLE_SIZE,
    check_fits,
    get_shortcut_file_path,
    read_shortcuts_binary,
    slots_of,
)
from timezonefinder.utils import (
    get_boundaries_dir,
    get_holes_dir,
    get_last_change_idx,
)
from timezonefinder.zone_names import read_zone_names


class DataIntegrityError(ValueError):
    """A compiled data directory is internally inconsistent."""


def validate_hole_references(data_dir: Path) -> None:
    """Check that the hole reference encoding in ``data_dir`` addresses real geometry.

    A hole is stored either as its own ring or as a reference to the identical boundary
    polygon (see ``docs/data_format.rst``). The reference vector, the hole coordinate
    file and the hole bounding box vectors are three separate files, so they can only be
    trusted together if something checks that they agree. Nothing about a disagreement
    is self-announcing: every hole id still resolves to *some* valid ring, so the
    symptom is a plausible wrong timezone rather than an error.

    :param data_dir: A compiled data directory, as written by ``scripts/file_converter.py``
    :raises DataIntegrityError: if the hole files do not agree with each other
    """
    boundaries = PolygonArray(data_location=get_boundaries_dir(data_dir))
    holes_dir = get_holes_dir(data_dir)
    holes = HoleArray(data_location=holes_dir, boundaries=boundaries)

    nr_holes = len(holes)
    nr_stored = len(holes.coordinates)
    poly_ref = holes.poly_ref
    ref_path = get_poly_ref_path(holes_dir)

    if len(poly_ref) != nr_holes:
        raise DataIntegrityError(
            f"{ref_path} has {len(poly_ref)} entries but there are {nr_holes} holes."
        )

    inline_positions = sorted(-(int(v) + 1) for v in poly_ref if v < 0)
    if inline_positions != list(range(nr_stored)):
        raise DataIntegrityError(
            f"{ref_path} does not address each of the {nr_stored} inline rings in "
            f"{holes_dir} exactly once."
        )

    if nr_holes:
        max_ref = int(poly_ref.max())
        if max_ref >= len(boundaries):
            raise DataIntegrityError(
                f"a hole in {holes_dir} references boundary polygon {max_ref}, but only "
                f"{len(boundaries)} boundary polygons exist."
            )

    # The strongest check available, and the only one with evidence independent of the
    # references themselves: the bounding boxes are computed from the original hole
    # rings before deduplication and never rewritten, so a reference pointing at the
    # wrong polygon resolves to a ring whose extent disagrees with them.
    for hole_id in range(nr_holes):
        ring = holes.coords_of(hole_id)
        expected = (
            int(holes.xmin[hole_id]),
            int(holes.xmax[hole_id]),
            int(holes.ymin[hole_id]),
            int(holes.ymax[hole_id]),
        )
        actual = (
            int(ring[0].min()),
            int(ring[0].max()),
            int(ring[1].min()),
            int(ring[1].max()),
        )
        if expected != actual:
            ref = int(poly_ref[hole_id])
            target = (
                f"boundary polygon {ref}" if ref >= 0 else f"inline ring {-(ref + 1)}"
            )
            raise DataIntegrityError(
                f"hole {hole_id} in {holes_dir} resolves to {target}, whose extent "
                f"{actual} does not match the bounding box {expected} stored for it. "
                f"The reference points at the wrong geometry."
            )


def validate_hole_dedup_ratio(data_dir: Path) -> None:
    """Check that deduplication is still paying off for a full timezone dataset.

    Kept separate from :func:`validate_hole_references`, which is about whether the
    files agree with each other and holds for *any* data directory. This one is an
    expectation about the upstream data - that the boundary builder still emits
    enclaves as shared rings - and it is only meaningful at dataset scale. A small
    custom region legitimately has few enclaves and would fail it while being perfectly
    well formed.

    The converter only reports the ratio - compiling custom data whose holes are not
    enclaves is a supported use case. This is where it is actually enforced, and it is
    applied to the packaged dataset alone.

    :param data_dir: A compiled data directory
    :raises DataIntegrityError: if too few holes are stored as references
    """
    boundaries = PolygonArray(data_location=get_boundaries_dir(data_dir))
    holes_dir = get_holes_dir(data_dir)
    holes = HoleArray(data_location=holes_dir, boundaries=boundaries)
    if not len(holes):
        return

    ratio = int((holes.poly_ref >= 0).sum()) / len(holes)
    if ratio < MIN_HOLE_DEDUP_RATIO:
        raise DataIntegrityError(
            f"only {ratio:.1%} of the holes in {holes_dir} are stored as a reference "
            f"to an identical boundary polygon, below the expected minimum of "
            f"{MIN_HOLE_DEDUP_RATIO:.0%}. Either the upstream dataset stopped emitting "
            f"enclaves as shared rings - in which case the packaged data is quietly "
            f"re-inflated - or the matching pass is broken. Re-check with "
            f"prototypes/hole_boundary_redundancy.py."
        )


def validate_shipped_schemas(data_dir: Path) -> None:
    """Check that the schemas in ``data_dir`` are the ones its binaries were written by.

    A compiled data directory carries a copy of the FlatBuffers schemas describing it,
    so that it says what its own format is - which matters for a hand-built
    ``bin_file_location`` and for anyone debugging one, and puts the format's definition
    in the distribution whose major version *is* the format version.

    Being a copy, it can go stale: the schemas change under ``make flatbuf`` while the
    binaries are not regenerated, and nothing about the resulting directory announces
    that the description no longer matches the thing described. Hence one check, run
    both by the converter over what it just wrote and by the test suite over what is
    committed.

    :param data_dir: A compiled data directory, as written by ``scripts/file_converter.py``
    :raises DataIntegrityError: if the shipped schemas are missing or differ
    """
    shipped_dir = get_schemas_dir(data_dir)
    expected = {path.name: path.read_bytes() for path in iter_schema_files()}
    if not expected:
        raise DataIntegrityError(
            "no schema definitions found to compare against - the canonical schemas "
            "have moved, and the shipped copies are now checked against nothing."
        )

    shipped = {
        path.name: path.read_bytes()
        for path in sorted(shipped_dir.glob(f"*{SCHEMA_SUFFIX}"))
    }
    if shipped.keys() != expected.keys():
        missing = sorted(expected.keys() - shipped.keys())
        extra = sorted(shipped.keys() - expected.keys())
        raise DataIntegrityError(
            f"{shipped_dir} does not hold the schemas describing this data: "
            f"missing {missing}, unexpected {extra}. Regenerate the data directory."
        )

    differing = sorted(name for name, body in expected.items() if shipped[name] != body)
    if differing:
        raise DataIntegrityError(
            f"the schema copies in {shipped_dir} differ from the canonical ones: "
            f"{differing}. They are generated, so fix this by regenerating the data "
            "rather than by editing the copy - and check whether the binaries next to "
            "it still match the schema that changed."
        )


def validate_coordinate_offset_table(data_dir: Path) -> None:
    """Check that the offset table addresses the same bytes the FlatBuffers reader does.

    The lookup path does not walk the FlatBuffers structure. It resolves every polygon's
    ``(byte offset, length)`` once, with whole-array arithmetic over the vtables
    (``timezonefinder.flatbuf.io.polygons.derive_coord_offset_table``), and afterwards
    slices coordinates straight out of the buffer. That is what makes a candidate
    polygon cheap to fetch on the memory-mapped path, and it means the reader's
    guarantees - that a table is where its reference says, that a vtable is aligned, that
    the coords field is present - are assumed there rather than checked.

    Nothing about a violated assumption announces itself: an offset landing one word
    early still yields plausible ``int32`` coordinates and therefore a plausible wrong
    timezone. So it is established here, over every polygon in both coordinate files, by
    comparing against ``read_polygon_array_from_binary`` - the same bytes read the slow,
    structural way. Exhaustive on purpose, which is affordable because this runs where
    the data is produced and in the test suite, never when a ``TimezoneFinder`` is built.

    :param data_dir: A compiled data directory, as written by ``scripts/file_converter.py``
    :raises DataIntegrityError: if the table disagrees with the reader for any polygon
    """
    for polygon_dir in (get_boundaries_dir(data_dir), get_holes_dir(data_dir)):
        coordinate_path = get_coordinate_path(polygon_dir)
        with open(coordinate_path, "rb") as coord_file:
            with mmap.mmap(
                coord_file.fileno(), 0, access=mmap.ACCESS_READ
            ) as coord_buf:
                collection = get_polygon_collection(coord_buf, coordinate_path)
                offsets, lengths = derive_coord_offset_table(collection)

                nr_polygons = collection.PolygonsLength()
                if len(offsets) != nr_polygons:
                    raise DataIntegrityError(
                        f"the offset table derived from {coordinate_path} has "
                        f"{len(offsets)} entries but the file holds {nr_polygons} "
                        f"polygons."
                    )

                # Both readers hand out zero-copy views, and a mapping refuses to
                # close while an export of it is alive - so the comparison happens
                # inside a scope the views do not outlive, on the raising path too.
                def compare(idx: int) -> tuple[bool, tuple[int, ...], tuple[int, ...]]:
                    expected = read_polygon_array_from_binary(collection, idx)
                    actual = read_polygon_array_at(
                        coord_buf, offsets[idx], lengths[idx]
                    )
                    agree = actual.shape == expected.shape and np.array_equal(
                        actual, expected
                    )
                    return agree, actual.shape, expected.shape

                for idx in range(nr_polygons):
                    agree, actual_shape, expected_shape = compare(idx)
                    if not agree:
                        raise DataIntegrityError(
                            f"polygon {idx} of {coordinate_path} reads as "
                            f"{actual_shape} coordinates at byte offset "
                            f"{int(offsets[idx])} but as {expected_shape} through the "
                            f"FlatBuffers reader. The offset table does not address "
                            f"this file's layout, so lookups against it would return "
                            f"wrong coordinates silently."
                        )


def all_cells_at_shortcut_res() -> np.ndarray:
    """Every H3 cell id at ``SHORTCUT_H3_RES``, ascending, as ``int64``."""
    cells: list[int] = []
    for res0 in h3.get_res0_cells():
        cells.extend(int(c) for c in h3.cell_to_children(res0, SHORTCUT_H3_RES))
    return np.array(sorted(cells), dtype=np.int64)


def validate_slot_layout_against_h3() -> None:
    """Check the shortcut index's bit arithmetic against h3's *public* API, cell by cell.

    This is what makes addressing entries by H3 bit position a checked invariant rather
    than a trusted one, and it is the whole answer to "h3-py does not promise the index
    encoding as API". It does not have to: ``get_base_cell_number`` and
    ``cell_to_child_pos`` are public, and between them they determine a cell's position
    exactly as the bits do. So the lookup can slice bits while this proves that slicing
    agrees with the supported accessors over every cell that exists. If h3 ever changes
    the layout, this fails where the data is produced instead of silently returning a
    neighbour's timezone.

    Cost is why it lives here: the public route is ~2.5x the whole shortcut lookup per
    query, and nothing at all once per build.

    :raises DataIntegrityError: if the bits and the public accessors disagree
    """
    cells = all_cells_at_shortcut_res()

    # a dense reference index derived only from public API
    base_offset: dict[int, int] = {}
    run = 0
    for cell in sorted(int(c) for c in h3.get_res0_cells()):
        base_offset[int(h3.get_base_cell_number(cell))] = run
        run += int(h3.cell_to_children_size(cell, SHORTCUT_H3_RES))

    base_from_bits = (cells >> SLOT_BASE_CELL_SHIFT) & SLOT_BASE_CELL_MASK
    public_index = np.empty(len(cells), dtype=np.int64)
    for i, cell_id in enumerate(cells):
        cell = int(cell_id)
        base = int(h3.get_base_cell_number(cell))
        if base != int(base_from_bits[i]):
            raise DataIntegrityError(
                f"h3's index encoding has moved: cell {cell:#x} reports base cell {base} "
                f"through get_base_cell_number and {int(base_from_bits[i])} at bits "
                f"{SLOT_BASE_CELL_SHIFT}-{SLOT_BASE_CELL_SHIFT + 6}. The shortcut index "
                f"addresses entries by those bits, so every lookup in it is now wrong. "
                f"Regenerate the data and bump SHORTCUT_LAYOUT_VERSION with "
                f"DATA_FORMAT_VERSION."
            )
        public_index[i] = base_offset[base] + int(h3.cell_to_child_pos(cell, 0))

    slots = slots_of(cells)
    # The two must order the cells identically: same base cell first, then the same digit
    # sequence. Equality of the indices themselves is not expected - the bit form is
    # base-8 per digit and therefore sparser than the public form.
    if not np.array_equal(np.argsort(slots), np.argsort(public_index)):
        raise DataIntegrityError(
            "the bit-derived shortcut slot orders cells differently from h3's public "
            "get_base_cell_number / cell_to_child_pos. The index's entry order no longer "
            "means what it did; regenerate the data and bump SHORTCUT_LAYOUT_VERSION "
            "with DATA_FORMAT_VERSION."
        )

    if len(np.unique(slots)) != len(cells) or int(slots.max()) >= SLOT_TABLE_SIZE:
        raise DataIntegrityError(
            "the shortcut slot map is no longer a bijection over the cells at "
            f"resolution {SHORTCUT_H3_RES}."
        )


def validate_shortcut_index(data_dir: Path) -> None:
    """Check that the shortcut index in ``data_dir`` says what a lookup will read from it.

    The lookup does no bounds checking and no dispatch beyond the sign of one ``int16``:
    it slices bits into the table, and follows what it finds there straight into the
    payload. Everything that makes that safe is established here - the widths chosen by
    fit rather than by headroom, the reserved table values, the precomputed stop index,
    and the padding that must read as "nothing here" - because none of it is
    self-announcing at lookup time. A stop index one too small returns a plausible wrong
    timezone; a zone id truncated into ``int16`` returns a different zone's name.

    Exhaustive on purpose. It runs where the data is produced and in the test suite over
    what is committed, never when a ``TimezoneFinder`` is built.

    :param data_dir: A compiled data directory, as written by ``scripts/file_converter.py``
    :raises DataIntegrityError: if the index does not hold together
    """
    validate_slot_layout_against_h3()

    path = get_shortcut_file_path(data_dir)
    index = read_shortcuts_binary(path)
    zone_ids = read_per_polygon_vector(get_zone_ids_path(data_dir))
    nr_of_zones = len(read_zone_names(data_dir))
    nr_of_boundaries = len(zone_ids)

    starts = index.starts.astype(np.int64)
    ends = index.ends.astype(np.int64)
    lengths = ends - starts

    if index.nr_of_entries and int(ends[-1]) != len(index.payload):
        raise DataIntegrityError(
            f"{path}: the last candidate list ends at {int(ends[-1])} but the payload "
            f"holds {len(index.payload)} polygon ids."
        )
    if np.any(lengths < 2):
        offender = int(np.argmin(lengths))
        raise DataIntegrityError(
            f"{path}: candidate list {offender} holds {int(lengths[offender])} polygon "
            "ids. Every stored list has at least two - a single candidate is unambiguous "
            "and belongs in the table as a zone id - and that is what leaves a spare "
            "table value to mean 'no cell here'."
        )
    if len(index.payload) and int(index.payload.max()) >= nr_of_boundaries:
        raise DataIntegrityError(
            f"{path}: a candidate list names boundary polygon "
            f"{int(index.payload.max())}, but {data_dir} holds {nr_of_boundaries}."
        )

    # the widths, re-checked over what is committed rather than over what was written
    check_fits(
        np.append(starts, ends[-1:]),
        np.dtype(f"uint{index.starts.dtype.itemsize * 8}"),
        what="a payload offset",
        remedy="Widen the offset column to the next unsigned width.",
    )
    check_fits(
        index.last_change,
        np.dtype(f"uint{index.last_change.dtype.itemsize * 8}"),
        what="a last-zone-change index",
        remedy="Widen the length column to the next unsigned width.",
    )

    table = index.table
    zone_id_slots = table >= 0
    if np.any(table[zone_id_slots] >= nr_of_zones):
        raise DataIntegrityError(
            f"{path}: the table answers with zone id "
            f"{int(table[zone_id_slots].max())}, but {data_dir} names {nr_of_zones} "
            "zones. Zone ids share the table with the candidate list indices, so a "
            "value out of range here is a silently wrong answer rather than an error."
        )
    entry_slots = table < ABSENT
    entry_indices = -(table[entry_slots].astype(np.int64) + 2)
    if len(entry_indices) and int(entry_indices.max()) >= index.nr_of_entries:
        raise DataIntegrityError(
            f"{path}: the table points at candidate list {int(entry_indices.max())}, but "
            f"only {index.nr_of_entries} are stored."
        )

    # the padding: base-8 slots no cell at this resolution can address must read as
    # absent, or the invariant "a slot without an entry answers nothing" is unassertable
    reachable = np.zeros(SLOT_TABLE_SIZE, dtype=bool)
    reachable[slots_of(all_cells_at_shortcut_res())] = True
    if np.any(table[~reachable] != ABSENT):
        raise DataIntegrityError(
            f"{path}: {int(np.count_nonzero(table[~reachable] != ABSENT))} table slots no "
            "H3 cell can address hold something other than the absent marker. They are "
            "unreachable, so this changes no answer - but it is what the reader fills "
            "them with, so it disagreeing means the expansion is not doing what it says."
        )

    # the precomputed stop index, against the function the query used to call
    for entry in range(index.nr_of_entries):
        candidates = index.polygons_of_entry(entry).astype(np.int64)
        expected = int(get_last_change_idx(zone_ids[candidates]))
        if int(index.last_change[entry]) != expected:
            raise DataIntegrityError(
                f"{path}: candidate list {entry} records {int(index.last_change[entry])} "
                f"as the index past which no other zone can be matched, but its polygons "
                f"give {expected}. The query reads this rather than computing it, so a "
                f"wrong value stops the point-in-polygon loop early and attributes the "
                f"point to the wrong zone."
            )
