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

from scripts.block_index import block_latitude_ranges, nr_blocks_for
from scripts.configs import MIN_HOLE_DEDUP_RATIO
from timezonefinder.flatbuf.schemas import (
    SCHEMA_SUFFIX,
    get_schemas_dir,
    iter_schema_files,
)
from timezonefinder.block_payload import (
    MAX_RESIDUAL_BITS,
    PAYLOAD_WORD_DTYPE,
    block_vertex_counts,
    decode_ring,
    ring_payload_length,
)
from timezonefinder.flatbuf.io.polygons import (
    derive_payload_offset_table,
    get_coordinate_path,
    get_polygon_collection,
    read_payload_at,
    read_payload_from_binary,
)
from timezonefinder.configs import (
    BLOCK_BASE_DTYPE,
    BLOCK_OFFSET_DTYPE,
    BLOCK_RANGE_DTYPE,
    BLOCK_WIDTH_DTYPE,
    POLYGON_BLOCK_SIZE,
    SOURCE_COORD_STEP,
    VERTEX_COUNT_DTYPE,
    SHORTCUT_H3_RES,
    ZONE_ID_RESULT_DTYPE,
)
from timezonefinder.np_binary_helpers import (
    get_block_bases_path,
    get_block_offsets_path,
    get_block_ranges_path,
    get_block_widths_path,
    get_nr_vertices_path,
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
    get_last_change_idx,
    get_shortcut_file_path,
    narrowest_dtype_for,
    read_shortcuts_binary,
    slots_of,
)
from timezonefinder.utils import get_boundaries_dir, get_holes_dir
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


def validate_payload_offset_table(data_dir: Path) -> None:
    """Check that the offset table addresses the same words the FlatBuffers reader does.

    The lookup path does not walk the FlatBuffers structure. It resolves every ring's
    ``(word offset, length)`` once, with whole-array arithmetic over the vtables
    (``timezonefinder.flatbuf.io.polygons.derive_payload_offset_table``), and afterwards
    addresses payload words straight in the buffer. That is what makes a candidate
    polygon cheap to fetch on the memory-mapped path, and it means the reader's
    guarantees - that a table is where its reference says, that a vtable is aligned, that
    the payload field is present - are assumed there rather than checked.

    Nothing about a violated assumption announces itself: an offset landing one word
    early still yields plausible residuals and therefore a plausible wrong timezone. So
    it is established here, over every ring in both coordinate files, by comparing
    against ``read_payload_from_binary`` - the same bytes read the slow, structural way.
    Exhaustive on purpose, which is affordable because this runs where the data is
    produced and in the test suite, never when a ``TimezoneFinder`` is built.

    :param data_dir: A compiled data directory, as written by ``scripts/file_converter.py``
    :raises DataIntegrityError: if the table disagrees with the reader for any ring
    """
    for polygon_dir in (get_boundaries_dir(data_dir), get_holes_dir(data_dir)):
        coordinate_path = get_coordinate_path(polygon_dir)
        with open(coordinate_path, "rb") as coord_file:
            with mmap.mmap(
                coord_file.fileno(), 0, access=mmap.ACCESS_READ
            ) as coord_buf:
                collection = get_polygon_collection(coord_buf, coordinate_path)
                offsets, lengths = derive_payload_offset_table(collection)

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
                # That is also why the word view is rebuilt per ring rather than hoisted:
                # a raise below would keep the frame holding it alive through its own
                # traceback, and the BufferError from leaving this block would replace
                # the real complaint.
                def compare(idx: int) -> tuple[bool, int, int]:
                    words = np.frombuffer(coord_buf, dtype=PAYLOAD_WORD_DTYPE)
                    expected = read_payload_from_binary(collection, idx)
                    actual = read_payload_at(words, offsets[idx], lengths[idx])
                    agree = actual.shape == expected.shape and np.array_equal(
                        actual, expected
                    )
                    return agree, actual.size, expected.size

                for idx in range(nr_polygons):
                    agree, actual_size, expected_size = compare(idx)
                    if not agree:
                        raise DataIntegrityError(
                            f"ring {idx} of {coordinate_path} reads as {actual_size} "
                            f"payload words at word offset {int(offsets[idx])} but as "
                            f"{expected_size} through the FlatBuffers reader. The "
                            f"offset table does not address this file's layout, so "
                            f"lookups against it would return wrong coordinates "
                            f"silently."
                        )


def validate_block_index(data_dir: Path) -> None:
    """Check that the latitude block index describes the rings stored next to it.

    The kernels *skip* on what this file says, so every failure mode of it is a silently
    wrong answer rather than an error: a range too narrow drops the block holding a
    crossing edge and flips one point's parity, and an offset column built at a
    different ``POLYGON_BLOCK_SIZE`` hands a ring some other ring's latitudes. Neither
    is visible in an answer that still names a real timezone, and neither can be caught
    at lookup time without re-deriving the index a query exists to avoid.

    So it is re-derived here instead, exhaustively, over the rings in both coordinate
    files - by the converter over what it just wrote, and by the test suite over what
    the repository ships. That is also what pins ``POLYGON_BLOCK_SIZE``: a data
    directory blocked at a different size fails the block-count check by name.

    **What this cannot witness, since polygon layout 3: the lower bound.** It is also the
    block's y frame origin, so a ring decoded against a shifted one comes back shifted by
    exactly the same amount and re-deriving the range reproduces the corrupted file. A
    number stored once has nothing to be compared against - which is the price of not
    storing it twice, and it is paid where it cannot be written rather than where it
    would be read: ``timezonefinder.block_payload.encode_ring`` is handed these ranges
    and refuses to frame a block whose latitudes they do not describe. The upper bound is
    unaffected and is checked here as before.

    :param data_dir: A compiled data directory, as written by ``scripts/file_converter.py``
    :raises DataIntegrityError: if the index does not describe the stored rings
    """
    for polygon_dir in (get_boundaries_dir(data_dir), get_holes_dir(data_dir)):
        coordinate_path = get_coordinate_path(polygon_dir)
        ranges_path = get_block_ranges_path(polygon_dir)
        offsets_path = get_block_offsets_path(polygon_dir)
        ranges = read_per_polygon_vector(ranges_path)
        offsets = read_per_polygon_vector(offsets_path)

        if (
            ranges.dtype != BLOCK_RANGE_DTYPE
            or ranges.ndim != 2
            or ranges.shape[1] != 2
        ):
            raise DataIntegrityError(
                f"{ranges_path} holds {ranges.dtype} data of shape {ranges.shape}, but "
                f"the block index is one {BLOCK_RANGE_DTYPE.name} [min, max] latitude "
                f"pair per block. The kernels read it by position without checking it."
            )
        if offsets.dtype != BLOCK_OFFSET_DTYPE:
            raise DataIntegrityError(
                f"{offsets_path} holds {offsets.dtype} data, but the block offset "
                f"column is {BLOCK_OFFSET_DTYPE.name}."
            )

        with open(coordinate_path, "rb") as coord_file:
            with mmap.mmap(
                coord_file.fileno(), 0, access=mmap.ACCESS_READ
            ) as coord_buf:
                collection = get_polygon_collection(coord_buf, coordinate_path)
                coord_offsets, lengths = derive_payload_offset_table(collection)
                bases = read_per_polygon_vector(get_block_bases_path(polygon_dir))
                widths = read_per_polygon_vector(get_block_widths_path(polygon_dir))
                ring_sizes = read_per_polygon_vector(get_nr_vertices_path(polygon_dir))

                nr_rings = len(coord_offsets)

                # The payload is a zero-copy view onto the mapping, and a mapping
                # refuses to close while an export of it is alive - so it must not
                # outlive the iteration that made it, on the raising path either. Hence
                # a function whose locals go out of scope per ring rather than a loop
                # variable.
                def block_ranges_of(idx: int, start: int, stop: int) -> np.ndarray:
                    words = np.frombuffer(coord_buf, dtype=PAYLOAD_WORD_DTYPE)
                    ring = decode_ring(
                        read_payload_at(words, coord_offsets[idx], lengths[idx]),
                        bases[start:stop],
                        ranges[start:stop],
                        widths[start:stop],
                        int(ring_sizes[idx]),
                        POLYGON_BLOCK_SIZE,
                    )
                    return block_latitude_ranges(ring[1], POLYGON_BLOCK_SIZE)

                if len(offsets) != nr_rings + 1:
                    raise DataIntegrityError(
                        f"{offsets_path} has {len(offsets)} entries but "
                        f"{coordinate_path} holds {nr_rings} rings, which needs "
                        f"{nr_rings + 1} - one boundary per ring plus the end of "
                        f"the last."
                    )
                if int(offsets[0]) != 0 or int(offsets[-1]) != len(ranges):
                    raise DataIntegrityError(
                        f"{offsets_path} spans [{int(offsets[0])}, "
                        f"{int(offsets[-1])}) but {ranges_path} holds "
                        f"{len(ranges)} block ranges."
                    )
                for idx in range(nr_rings):
                    start, stop = int(offsets[idx]), int(offsets[idx + 1])
                    nr_vertices = int(ring_sizes[idx])
                    # Before the decode, not after: decoding slices the frames by
                    # these same offsets, so a directory blocked at another size
                    # fails there first with a shape error rather than by name.
                    expected_count = nr_blocks_for(nr_vertices, POLYGON_BLOCK_SIZE)
                    if stop - start != expected_count:
                        raise DataIntegrityError(
                            f"ring {idx} of {coordinate_path} has {nr_vertices} "
                            f"vertices, which is {expected_count} blocks at "
                            f"POLYGON_BLOCK_SIZE={POLYGON_BLOCK_SIZE}, but "
                            f"{ranges_path} gives it {stop - start}. This data "
                            f"directory was blocked at a different size; "
                            f"regenerate it with scripts/file_converter.py from "
                            f"the current checkout."
                        )
                    expected = block_ranges_of(idx, start, stop)
                    if not np.array_equal(ranges[start:stop], expected):
                        offender = int(
                            np.argmax(np.any(ranges[start:stop] != expected, axis=1))
                        )
                        raise DataIntegrityError(
                            f"block {offender} of ring {idx} in {coordinate_path} "
                            f"is recorded as "
                            f"{ranges[start + offender].tolist()} but its edges "
                            f"span {expected[offender].tolist()}. A range that "
                            f"does not cover its own edges makes the kernels skip "
                            f"crossings, which changes answers rather than raising."
                        )


def validate_block_payload(
    data_dir: Path,
    boundary_rings: list[np.ndarray] | None = None,
    hole_rings: list[np.ndarray] | None = None,
) -> None:
    """Check that the packed payload decodes to the rings it was made from.

    Polygon layout 3 stores no coordinates: a ring is bit-packed residuals against one
    frame per block, and the frames live in three files beside the payload. Every way
    that can go wrong is silent - a width one bit short truncates a coordinate into a
    plausible other one, a base off by a step shifts a whole block, and a stale
    ``nr_vertices`` makes the last block ragged in the wrong place. None of it raises,
    and all of it moves borders.

    Two levels, because the converter and the test suite can prove different things.
    With ``boundary_rings`` / ``hole_rings`` - the rings the converter just encoded -
    this compares the decode against them directly, which is the strongest statement
    available and the only moment it can be made. Without them, over the shipped
    binaries, it re-derives each frame from its own decode and checks the latitude index
    against it: ``block_ranges`` opens with exactly the minimum the y frame subtracts,
    so the two files are two statements of one number and cannot drift unnoticed.

    :param data_dir: A compiled data directory, as written by ``scripts/file_converter.py``
    :param boundary_rings: the boundary rings as stored, if they are still in hand
    :param hole_rings: the inline hole rings as stored, if they are still in hand
    :raises DataIntegrityError: if the payload does not describe the stored rings
    """
    sources = (
        (get_boundaries_dir(data_dir), boundary_rings),
        (get_holes_dir(data_dir), hole_rings),
    )
    for polygon_dir, rings in sources:
        coordinate_path = get_coordinate_path(polygon_dir)
        bases_path = get_block_bases_path(polygon_dir)
        widths_path = get_block_widths_path(polygon_dir)
        vertices_path = get_nr_vertices_path(polygon_dir)
        bases = read_per_polygon_vector(bases_path)
        widths = read_per_polygon_vector(widths_path)
        nr_vertices = read_per_polygon_vector(vertices_path)
        block_offsets = read_per_polygon_vector(get_block_offsets_path(polygon_dir))
        block_ranges = read_per_polygon_vector(get_block_ranges_path(polygon_dir))

        for path, array, dtype in (
            (bases_path, bases, BLOCK_BASE_DTYPE),
            (widths_path, widths, BLOCK_WIDTH_DTYPE),
            (vertices_path, nr_vertices, VERTEX_COUNT_DTYPE),
        ):
            if array.dtype != dtype:
                raise DataIntegrityError(
                    f"{path} holds {array.dtype} data, but the column is {dtype.name}. "
                    f"The kernels read it by position without checking it."
                )
        if bases.ndim != 1:
            raise DataIntegrityError(
                f"{bases_path} has shape {bases.shape}, but it is one x frame origin "
                f"per block - the y origin is the latitude index's own lower bound and "
                f"is not stored again."
            )
        if widths.ndim != 2 or widths.shape[1] != 2:
            raise DataIntegrityError(
                f"{widths_path} has shape {widths.shape}, but it is one x and one y "
                f"entry per block."
            )
        if len(bases) != len(widths):
            raise DataIntegrityError(
                f"{bases_path} has {len(bases)} entries and {widths_path} "
                f"{len(widths)}; both are one per block."
            )
        if len(nr_vertices) != len(block_offsets) - 1:
            raise DataIntegrityError(
                f"{vertices_path} has {len(nr_vertices)} entries but "
                f"{coordinate_path} holds {len(block_offsets) - 1} rings."
            )
        if int(widths.max(initial=0)) > MAX_RESIDUAL_BITS:
            raise DataIntegrityError(
                f"{widths_path} holds a width of {int(widths.max())} bits, above the "
                f"{MAX_RESIDUAL_BITS} a residual may occupy."
            )

        with open(coordinate_path, "rb") as coord_file:
            with mmap.mmap(
                coord_file.fileno(), 0, access=mmap.ACCESS_READ
            ) as coord_buf:
                collection = get_polygon_collection(coord_buf, coordinate_path)
                offsets, lengths = derive_payload_offset_table(collection)

                # Views onto the mapping must not outlive the iteration that made
                # them, on the raising path either - hence a function per ring.
                def check(idx: int) -> str | None:
                    words = np.frombuffer(coord_buf, dtype=PAYLOAD_WORD_DTYPE)
                    start, stop = int(block_offsets[idx]), int(block_offsets[idx + 1])
                    ring_bases = bases[start:stop]
                    ring_widths = widths[start:stop]
                    vertices = int(nr_vertices[idx])
                    counts = block_vertex_counts(vertices, POLYGON_BLOCK_SIZE)
                    if len(counts) != stop - start:
                        return (
                            f"has {vertices} vertices, which is {len(counts)} blocks, "
                            f"but the frames give it {stop - start}"
                        )
                    expected_words = ring_payload_length(counts, ring_widths)
                    if int(lengths[idx]) != expected_words:
                        return (
                            f"occupies {int(lengths[idx])} payload words where its "
                            f"frames describe {expected_words}"
                        )
                    ring = decode_ring(
                        read_payload_at(words, offsets[idx], lengths[idx]),
                        ring_bases,
                        block_ranges[start:stop],
                        ring_widths,
                        vertices,
                        POLYGON_BLOCK_SIZE,
                    )
                    if rings is not None and not np.array_equal(ring, rings[idx]):
                        return "does not decode to the ring it was encoded from"
                    # Re-derive the frames from the decode. Cheap, and it is what makes
                    # this worth running over binaries whose source rings are gone.
                    for block in range(len(counts)):
                        first = block * POLYGON_BLOCK_SIZE
                        index = np.arange(first, first + counts[block]) % vertices
                        # x is framed by block_bases; y by the latitude index itself,
                        # which is the whole reason there is no second y column to check
                        # against - the two cannot disagree because there is one of them
                        origins = (
                            int(ring_bases[block]),
                            int(block_ranges[start + block, 0]),
                        )
                        for axis in (0, 1):
                            values = ring[axis][index].astype(np.int64)
                            base = int(values.min())
                            span = int(values.max()) - base
                            if base != origins[axis]:
                                return (
                                    f"block {block} axis {axis} is framed at "
                                    f"{origins[axis]} but its values start at {base}"
                                )
                            if span % SOURCE_COORD_STEP:
                                return (
                                    f"block {block} axis {axis} spans {span}, which is "
                                    f"not a whole number of source grid steps - the "
                                    f"ring is not on the grid the payload assumes"
                                )
                            # the stored width counts source steps, not coordinate
                            # units; see timezonefinder/block_payload.py
                            width = (span // SOURCE_COORD_STEP).bit_length()
                            if width != int(ring_widths[block, axis]):
                                return (
                                    f"block {block} axis {axis} is stored at "
                                    f"{int(ring_widths[block, axis])} bits but its "
                                    f"residuals span {width}"
                                )
                    return None

                if rings is not None and len(rings) != len(offsets):
                    raise DataIntegrityError(
                        f"{coordinate_path} holds {len(offsets)} rings but "
                        f"{len(rings)} were encoded into it."
                    )
                for idx in range(len(offsets)):
                    complaint = check(idx)
                    if complaint is not None:
                        raise DataIntegrityError(
                            f"ring {idx} of {coordinate_path} {complaint}. A "
                            f"payload its frames do not describe decodes to "
                            f"plausible wrong coordinates rather than raising."
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
    # Also where an offset column too narrow for the payload is caught: the offsets are
    # ascending, so one that wrapped leaves the entry before it with a hugely negative
    # length, and one that wrapped on the *last* entry fails the check above. Reading the
    # column back cannot show it directly - it comes off disk through the very width that
    # truncated it, so every value in it fits that width by construction.
    if np.any(lengths < 2):
        offender = int(np.argmin(lengths))
        raise DataIntegrityError(
            f"{path}: candidate list {offender} holds {int(lengths[offender])} polygon "
            "ids. Every stored list has at least two - a single candidate is unambiguous "
            "and belongs in the table as a zone id - and that is what leaves a spare "
            "table value to mean 'no cell here'. A negative length here means the offset "
            "column is too narrow for the payload and wrapped; widen it, and bump "
            "SHORTCUT_LAYOUT_VERSION and DATA_FORMAT_VERSION with it."
        )
    if len(index.payload) and int(index.payload.max()) >= nr_of_boundaries:
        raise DataIntegrityError(
            f"{path}: a candidate list names boundary polygon "
            f"{int(index.payload.max())}, but {data_dir} holds {nr_of_boundaries}."
        )

    # The two data-dependent widths are still the narrowest that fit. This is the "by fit,
    # not by headroom" property of the format asserted over what shipped, and the only
    # form of it a reader can check: a *too narrow* width is caught by the length and
    # payload-end checks above, since a wrapped value is indistinguishable from an
    # intended one once it has been read back through the width that wrapped it. What is
    # left to catch is the other direction - a converter that quietly started padding,
    # which nothing else would ever notice.
    for column, itemsize, what in (
        (
            np.append(starts, ends[-1:]),
            index.starts.dtype.itemsize,
            "the offset column",
        ),
        (index.last_change, index.last_change.dtype.itemsize, "the length column"),
    ):
        largest = int(np.max(column)) if len(column) else 0
        expected = narrowest_dtype_for(largest, what=what)
        if expected.itemsize != itemsize:
            raise DataIntegrityError(
                f"{path}: {what} is {itemsize * 8} bits wide, but the largest value in it "
                f"is {largest:,}, which {expected.name} holds. The format records each "
                f"width in the header so that it can be the narrowest that fits; a wider "
                f"one costs size for nothing and means the writer and this check no "
                f"longer agree on how the width is chosen."
            )

    # Both widths that carry a zone id are int16 and both are chosen by fit: the table
    # stores one per unique cell, and a batch lookup answers with an array of them. A
    # zone count past that ceiling would wrap in either, so it is refused here rather
    # than truncated there - and here rather than at lookup time, because a finder must
    # not re-derive what the build already settled.
    zone_id_ceiling = int(np.iinfo(ZONE_ID_RESULT_DTYPE).max)
    if nr_of_zones - 1 > zone_id_ceiling:
        raise DataIntegrityError(
            f"{data_dir} names {nr_of_zones:,} zones, so the largest zone id is "
            f"{nr_of_zones - 1:,}, but the widest a zone id may be is "
            f"{ZONE_ID_RESULT_DTYPE.name} and it holds at most {zone_id_ceiling:,}. "
            "Widen ZONE_ID_RESULT_DTYPE (timezonefinder/configs.py) and TABLE_DTYPE "
            "(timezonefinder/shortcut_index.py) to int32 together. TABLE_DTYPE changes "
            "the binary layout, so bump SHORTCUT_LAYOUT_VERSION and DATA_FORMAT_VERSION "
            "with it and publish the data distribution before the code that reads it."
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
