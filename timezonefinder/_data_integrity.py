"""Integrity checks over a *compiled* binary data directory.

These run where the data is produced, where it is reviewed, and when a user explicitly
asks the CLI to validate a custom data directory. They are deliberately **not** run when
a ``TimezoneFinder`` is constructed: whether a data directory is coherent is settled
once by the build, and re-deriving it in every user's process would spend startup time
re-answering a question that already has an answer.

What that buys is the freedom to check properly. Nothing here is written to be cheap:
the hole checks resolve every ring, compare its extent against the stored bounding box,
and test every vertex against the boundary its registry entry names. That is O(all hole
vertices) and would be indefensible on an initialisation path.
"""

import json
import mmap
from pathlib import Path

import numpy as np
from h3.api import numpy_int as h3

from timezonefinder._block_index import block_latitude_ranges, nr_blocks_for
from timezonefinder.block_payload import (
    MAX_RESIDUAL_BITS,
    PAYLOAD_WORD_DTYPE,
    block_vertex_counts,
    decode_ring,
    ring_payload_length,
)
from timezonefinder.flatbuf.schemas import (
    SCHEMA_SUFFIX,
    get_schemas_dir,
    iter_schema_files,
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
    BLOCK_PAYLOAD_OFFSET_DTYPE,
    BLOCK_RANGE_DTYPE,
    BLOCK_WIDTH_DTYPE,
    POLYGON_BLOCK_SIZE,
    SOURCE_COORD_STEP,
    SHORTCUT_H3_RES,
    VERTEX_COUNT_DTYPE,
    ZONE_ID_RESULT_DTYPE,
)
from timezonefinder.np_binary_helpers import (
    get_block_bases_path,
    get_block_offsets_path,
    get_block_ranges_path,
    get_block_widths_path,
    get_nr_vertices_path,
    get_poly_ref_path,
    get_xmax_path,
    get_xmin_path,
    get_ymax_path,
    get_ymin_path,
    get_zone_ids_path,
    get_zone_positions_path,
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
from timezonefinder.utils import (
    get_boundaries_dir,
    get_hole_registry_path,
    get_holes_dir,
    inside_polygon,
)
from timezonefinder.zone_names import read_zone_names


class DataIntegrityError(ValueError):
    """A compiled data directory is internally inconsistent."""


class _JSONObjectPairs(list[tuple[str, object]]):
    """JSON object entries, retained as pairs so duplicate keys remain visible."""


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


def validate_hole_registry(data_dir: Path) -> None:
    """Check that every hole belongs to exactly one real boundary polygon.

    ``hole_registry.json`` is the only mapping from a boundary polygon to its holes.
    Lookups trust each ``[count, first_hole_id]`` range directly, so an overlap, gap, or
    wrong owner still addresses valid arrays while subtracting the wrong geometry.
    Retaining JSON object pairs also catches duplicate keys before ``dict`` parsing could
    silently keep only the last one.

    Ownership has to rest on evidence outside the registry itself. Every vertex of each
    resolved hole ring is therefore checked against its registered boundary polygon.

    :param data_dir: A compiled data directory, as written by
        ``scripts/file_converter.py``
    :raises DataIntegrityError: if the registry is malformed or assigns holes wrongly
    """
    path = get_hole_registry_path(data_dir)
    with open(path, encoding="utf-8") as registry_file:
        raw_registry = json.load(registry_file, object_pairs_hook=_JSONObjectPairs)
    if not isinstance(raw_registry, _JSONObjectPairs):
        raise DataIntegrityError(f"{path} must contain one JSON object.")

    boundaries = PolygonArray(data_location=get_boundaries_dir(data_dir))
    holes = HoleArray(
        data_location=get_holes_dir(data_dir),
        boundaries=boundaries,
    )
    owners = np.full(len(holes), -1, dtype=np.int64)
    boundary_ids: set[int] = set()

    for raw_boundary_id, raw_range in raw_registry:
        try:
            boundary_id = int(raw_boundary_id)
        except ValueError:
            raise DataIntegrityError(
                f"{path} has a non-integer boundary id {raw_boundary_id!r}."
            ) from None
        if str(boundary_id) != raw_boundary_id or boundary_id in boundary_ids:
            raise DataIntegrityError(
                f"{path} names boundary {boundary_id} more than once or with a "
                f"non-canonical key {raw_boundary_id!r}."
            )
        boundary_ids.add(boundary_id)
        if not 0 <= boundary_id < len(boundaries):
            raise DataIntegrityError(
                f"{path} assigns holes to boundary {boundary_id}, but only "
                f"{len(boundaries)} boundary polygons exist."
            )

        if (
            not isinstance(raw_range, list)
            or isinstance(raw_range, _JSONObjectPairs)
            or len(raw_range) != 2
            or any(type(value) is not int for value in raw_range)
        ):
            raise DataIntegrityError(
                f"{path} must map boundary {boundary_id} to two integers: "
                "[hole count, first hole id]."
            )
        count, first_hole_id = raw_range
        last_hole_id = first_hole_id + count
        if count <= 0 or first_hole_id < 0 or last_hole_id > len(holes):
            raise DataIntegrityError(
                f"{path} gives boundary {boundary_id} the hole range "
                f"[{first_hole_id}, {last_hole_id}), but {len(holes)} holes exist."
            )

        already_owned = np.flatnonzero(owners[first_hole_id:last_hole_id] >= 0)
        if len(already_owned):
            hole_id = first_hole_id + int(already_owned[0])
            raise DataIntegrityError(
                f"{path} assigns hole {hole_id} to both boundary "
                f"{int(owners[hole_id])} and boundary {boundary_id}."
            )
        owners[first_hole_id:last_hole_id] = boundary_id

    missing = np.flatnonzero(owners < 0)
    if len(missing):
        raise DataIntegrityError(
            f"{path} does not assign hole {int(missing[0])} to any boundary polygon."
        )

    for hole_id, boundary_id_value in enumerate(owners):
        boundary_id = int(boundary_id_value)
        boundary = boundaries.coords_of(boundary_id)
        hole = holes.coords_of(hole_id)
        for vertex_id, (x, y) in enumerate(zip(hole[0], hole[1])):
            if boundaries.outside_bbox(
                boundary_id, int(x), int(y)
            ) or not inside_polygon(int(x), int(y), boundary):
                raise DataIntegrityError(
                    f"{path} assigns hole {hole_id} to boundary {boundary_id}, but "
                    f"vertex {vertex_id} of that hole does not lie inside the boundary."
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
    """Check that the offset table addresses the same words the reader does.

    The lookup path resolves every ring's ``(word offset, length)`` once with
    :func:`derive_payload_offset_table`, then addresses payload words directly. This
    compares that arithmetic with the structural FlatBuffers reader for every ring.

    :param data_dir: A compiled data directory, as written by
        ``scripts/file_converter.py``
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

                # Views onto the mapping must not outlive this scope, including on a
                # raising path, so the word view is rebuilt per ring.
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
                            "offset table does not address this file's layout, so "
                            "lookups against it would return wrong coordinates "
                            "silently."
                        )


def validate_payload_offset_width(data_dir: Path) -> None:
    """Check that a collection's payload still fits the width its offsets are held in.

    ``PolygonArray`` hands the point-in-polygon kernels one word offset per block,
    absolute into the whole coordinate buffer, in
    :data:`~timezonefinder.configs.BLOCK_PAYLOAD_OFFSET_DTYPE`. It builds them by adding
    each ring's start to a ring-relative offset, which is unsigned arithmetic: a
    collection that outgrew the width would **wrap** rather than raise, and a wrapped
    offset addresses some other ring's residuals - a wrong timezone for the points whose
    ray crosses that block, with nothing to notice it.

    The check is exact and costs one file size, because the whole buffer's word count
    bounds every offset into it. It belongs here, where the data is produced, rather than
    in the construction a lookup waits on.

    :param data_dir: A compiled data directory
    :raises DataIntegrityError: if a coordinate file holds more words than the offset
        dtype can address
    """
    limit = int(np.iinfo(BLOCK_PAYLOAD_OFFSET_DTYPE).max)
    for polygon_dir in (get_boundaries_dir(data_dir), get_holes_dir(data_dir)):
        coordinate_path = get_coordinate_path(polygon_dir)
        nr_words = coordinate_path.stat().st_size // PAYLOAD_WORD_DTYPE.itemsize
        if nr_words > limit:
            raise DataIntegrityError(
                f"{coordinate_path} holds {nr_words:,} payload words, but a block's "
                f"payload offset is stored as {BLOCK_PAYLOAD_OFFSET_DTYPE.name}, which "
                f"addresses at most {limit:,}. PolygonArray makes those offsets "
                f"absolute against this buffer with unsigned arithmetic, so the excess "
                f"would wrap and point the kernels at another ring's residuals instead "
                f"of failing. Widen BLOCK_PAYLOAD_OFFSET_DTYPE and move "
                f"POLYGON_LAYOUT_VERSION with it."
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
    files. Since polygon layout 3 the lower bound is also the y-frame origin, so a
    shifted value reproduces itself on decode; :func:`validate_block_payload` checks
    the rest of that frame contract, and the encoder refuses a mismatched source range.

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
                payload_offsets, lengths = derive_payload_offset_table(collection)
                bases = read_per_polygon_vector(get_block_bases_path(polygon_dir))
                widths = read_per_polygon_vector(get_block_widths_path(polygon_dir))
                ring_sizes = read_per_polygon_vector(get_nr_vertices_path(polygon_dir))

                nr_rings = len(payload_offsets)
                if len(offsets) != nr_rings + 1:
                    raise DataIntegrityError(
                        f"{offsets_path} has {len(offsets)} entries but {coordinate_path} "
                        f"holds {nr_rings} rings, which needs {nr_rings + 1} - one "
                        f"boundary per ring plus the end of the last."
                    )
                if int(offsets[0]) != 0 or int(offsets[-1]) != len(ranges):
                    raise DataIntegrityError(
                        f"{offsets_path} spans [{int(offsets[0])}, {int(offsets[-1])}) "
                        f"but {ranges_path} holds {len(ranges)} block ranges."
                    )

                # A payload view must not outlive the mapping, including on a raising
                # path, so the word view and decode live in a per-ring function.
                def block_ranges_of(idx: int, start: int, stop: int) -> np.ndarray:
                    words = np.frombuffer(coord_buf, dtype=PAYLOAD_WORD_DTYPE)
                    ring = decode_ring(
                        read_payload_at(words, payload_offsets[idx], lengths[idx]),
                        bases[start:stop],
                        ranges[start:stop],
                        widths[start:stop],
                        int(ring_sizes[idx]),
                        POLYGON_BLOCK_SIZE,
                    )
                    return block_latitude_ranges(ring[1], POLYGON_BLOCK_SIZE)

                for idx in range(nr_rings):
                    start, stop = int(offsets[idx]), int(offsets[idx + 1])
                    nr_vertices = int(ring_sizes[idx])
                    expected_count = nr_blocks_for(nr_vertices, POLYGON_BLOCK_SIZE)
                    if stop - start != expected_count:
                        raise DataIntegrityError(
                            f"ring {idx} of {coordinate_path} has {nr_vertices} "
                            f"vertices, which is {expected_count} blocks at "
                            f"POLYGON_BLOCK_SIZE={POLYGON_BLOCK_SIZE}, but "
                            f"{ranges_path} gives it {stop - start}. This data "
                            f"directory was blocked at a different size; regenerate it "
                            f"with scripts/file_converter.py from the current checkout."
                        )
                    expected = block_ranges_of(idx, start, stop)
                    if not np.array_equal(ranges[start:stop], expected):
                        offender = int(
                            np.argmax(np.any(ranges[start:stop] != expected, axis=1))
                        )
                        raise DataIntegrityError(
                            f"block {offender} of ring {idx} in {coordinate_path} is "
                            f"recorded as {ranges[start + offender].tolist()} but its "
                            f"edges span {expected[offender].tolist()}. A range that "
                            f"does not cover its own edges makes the kernels skip "
                            f"crossings, which changes answers rather than raising."
                        )


def validate_block_payload(
    data_dir: Path,
    boundary_rings: list[np.ndarray] | None = None,
    hole_rings: list[np.ndarray] | None = None,
) -> None:
    """Check that the packed payload decodes to the rings its frames describe.

    With source rings supplied by the converter this proves an exact round trip. For an
    existing compiled directory it re-derives every coordinate frame from the decode,
    checking the strongest statement available once the source rings are gone.

    :param data_dir: A compiled data directory, as written by
        ``scripts/file_converter.py``
    :param boundary_rings: boundary rings as encoded, when still available
    :param hole_rings: inline hole rings as encoded, when still available
    :raises DataIntegrityError: if a payload and its frame metadata disagree
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
                    "The kernels read it by position without checking it."
                )
        if bases.ndim != 1:
            raise DataIntegrityError(
                f"{bases_path} has shape {bases.shape}, but it is one x frame origin "
                "per block - the y origin is the latitude index's own lower bound and "
                "is not stored again."
            )
        if widths.ndim != 2 or widths.shape[1] != 2:
            raise DataIntegrityError(
                f"{widths_path} has shape {widths.shape}, but it is one x and one y "
                "entry per block."
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

                # Views onto the mapping must not outlive the iteration that made them,
                # including on a raising path, hence a function per ring.
                def check(idx: int) -> str | None:
                    words = np.frombuffer(coord_buf, dtype=PAYLOAD_WORD_DTYPE)
                    start = int(block_offsets[idx])
                    stop = int(block_offsets[idx + 1])
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

                    for block in range(len(counts)):
                        first = block * POLYGON_BLOCK_SIZE
                        index = np.arange(first, first + counts[block]) % vertices
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
                                    "not a whole number of source grid steps - the ring "
                                    "is not on the grid the payload assumes"
                                )
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
                            f"ring {idx} of {coordinate_path} {complaint}. A payload "
                            "its frames do not describe decodes to plausible wrong "
                            "coordinates rather than raising."
                        )


def validate_zone_data(data_dir: Path) -> None:
    """Check that zone positions and boundary data describe one grouping.

    ``certain_timezone_at`` addresses the first and last polygon of a zone through
    ``zone_positions``. The main lookup assumes the parallel ``zone_ids`` vector is
    grouped by zone when it stops testing candidates early and returns the final zone
    untested. Both arrays therefore have to state the same complete partition, and that
    partition must cover the boundary coordinates and each boundary-indexed vector.

    :param data_dir: A compiled data directory, as written by
        ``scripts/file_converter.py``
    :raises DataIntegrityError: if the two zone vectors do not form one partition
    """
    positions_path = get_zone_positions_path(data_dir)
    zone_ids_path = get_zone_ids_path(data_dir)
    positions = read_per_polygon_vector(positions_path)
    zone_ids = read_per_polygon_vector(zone_ids_path)
    nr_of_zones = len(read_zone_names(data_dir))

    if positions.ndim != 1:
        raise DataIntegrityError(
            f"{positions_path} has shape {positions.shape}; expected one start position "
            "per zone plus the terminal boundary count."
        )
    if zone_ids.ndim != 1:
        raise DataIntegrityError(
            f"{zone_ids_path} has shape {zone_ids.shape}; expected one zone id per "
            "boundary polygon."
        )
    if not np.issubdtype(positions.dtype, np.integer):
        raise DataIntegrityError(
            f"{positions_path} holds {positions.dtype} values; zone positions must be "
            "integers because the lookup uses them as boundary indices."
        )
    if not np.issubdtype(zone_ids.dtype, np.integer):
        raise DataIntegrityError(
            f"{zone_ids_path} holds {zone_ids.dtype} values; zone ids must be integers."
        )
    if len(positions) != nr_of_zones + 1:
        raise DataIntegrityError(
            f"{positions_path} has {len(positions)} entries, but {data_dir} names "
            f"{nr_of_zones} zones and therefore needs {nr_of_zones + 1}."
        )
    if int(positions[0]) != 0 or int(positions[-1]) != len(zone_ids):
        raise DataIntegrityError(
            f"{positions_path} spans [{int(positions[0])}, {int(positions[-1])}), "
            f"but {zone_ids_path} holds {len(zone_ids)} boundary zone ids."
        )

    counts = np.diff(positions.astype(np.int64))
    if np.any(counts < 0):
        offender = int(np.flatnonzero(counts < 0)[0])
        raise DataIntegrityError(
            f"{positions_path} decreases from {int(positions[offender])} to "
            f"{int(positions[offender + 1])} between zones {offender} and "
            f"{offender + 1}; zone ranges must be monotonic."
        )

    expected = np.repeat(np.arange(nr_of_zones, dtype=np.int64), counts)
    actual = zone_ids.astype(np.int64)
    if not np.array_equal(actual, expected):
        mismatch = int(np.flatnonzero(actual != expected)[0])
        raise DataIntegrityError(
            f"{zone_ids_path} assigns boundary {mismatch} to zone "
            f"{int(actual[mismatch])}, but {positions_path} assigns it to zone "
            f"{int(expected[mismatch])}. The lookup requires polygons to be grouped "
            "by zone."
        )

    boundaries = PolygonArray(data_location=get_boundaries_dir(data_dir))
    boundaries_dir = boundaries.data_location
    boundary_counts = {
        get_coordinate_path(boundaries_dir): len(boundaries.coordinates),
        get_xmin_path(boundaries_dir): len(boundaries.xmin),
        get_xmax_path(boundaries_dir): len(boundaries.xmax),
        get_ymin_path(boundaries_dir): len(boundaries.ymin),
        get_ymax_path(boundaries_dir): len(boundaries.ymax),
    }
    mismatched = {
        path: count for path, count in boundary_counts.items() if count != len(zone_ids)
    }
    if mismatched:
        counts = ", ".join(f"{path} has {count}" for path, count in mismatched.items())
        raise DataIntegrityError(
            f"{zone_ids_path} holds {len(zone_ids)} boundary zone ids, but {counts}. "
            "Every boundary-indexed file must describe the same polygon collection."
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


def validate_data_dir(data_dir: Path) -> None:
    """Exhaustively validate the cross-file invariants of a compiled directory.

    This is the shared entry point used by the converter, the packaged-data tests, and
    the explicit ``timezonefinder validate-data`` command. It is intentionally absent
    from finder construction and every lookup path.

    :param data_dir: A compiled data directory
    :raises DataIntegrityError: if the path is not a directory or an invariant fails
    """
    if not data_dir.is_dir():
        raise DataIntegrityError(f"{data_dir} is not a compiled data directory.")

    validate_shipped_schemas(data_dir)
    validate_zone_data(data_dir)
    validate_hole_references(data_dir)
    validate_payload_offset_table(data_dir)
    validate_payload_offset_width(data_dir)
    validate_block_index(data_dir)
    validate_block_payload(data_dir)
    validate_hole_registry(data_dir)
    validate_shortcut_index(data_dir)
