"""The per-block coordinate frames the boundary payload is stored in.

Polygon layout 3 stores a ring's vertices as bit-packed residuals against one
coordinate frame per block of :data:`~timezonefinder.configs.POLYGON_BLOCK_SIZE`
vertices, instead of as fixed 32-bit absolutes. The blocks are exactly the ones the
latitude index already partitions the ring into (``scripts/block_index.py``), so this
adds no structure - it changes what each block *holds*.

**One block, on disk.** ``m`` values per axis, where ``m`` is the block's vertex count
plus its bridging vertex - the first vertex of the next block, which the block owns the
edge reaching, and which wraps to vertex 0 on the last block. Storing it is what keeps a
block self-contained: both endpoints of every edge it owns are inside it, so a decoder
never has to translate between two frames. The x residuals come first, then the y ones;
residual ``k`` occupies bits ``[k*w, (k+1)*w)`` of its axis region, least significant
bit first.

**A payload is a stream of 32-bit words, not of bytes**, and each axis region starts on
a word boundary. That is what lets a kernel read any field with two aligned loads: a
field is at most 32 bits wide and begins at most 31 bits into a word, so the two words
holding it are ``bit >> 5`` and the one after. Byte addressing would make the same read
five dependent byte loads, which measured 2.2x the whole blocked kernel on the numba
backend - the alignment costs ~2 bytes per region and buys that back.

**One block, in the metadata.** ``base_x`` is stored per block (``block_bases.npy``) and
both widths are (``block_widths.npy``). **``base_y`` is not stored at all**: the latitude
index beside it already opens each block with exactly the minimum a y frame subtracts, so
a second copy would be ~0.24 MiB of the same numbers held resident on the mode that
exists to stay small - and two statements of one number that could drift. The encoder is
handed the ranges and subtracts the value the kernel adds back, which is what makes them
impossible to disagree.

The kernels get ``base_y`` for free: they have already loaded ``block_ranges[b, 0]`` to
decide whether the block survives the latitude test at all.

**Why the query point moves instead of the vertices.** Every quantity in the ray-casting
predicate is a difference of two coordinates, so subtracting a block's base from the
query is exact and the base is never added back per vertex - see
``timezonefinder/utils_numba.py``'s ``pt_in_poly_packed``. A decoded residual is
therefore what the kernel compares, and reconstructing an absolute coordinate is
something only :func:`decode_ring` does, for ``get_geometry()`` and the integrity
checks.

Widths are bit lengths, so ``w == 0`` is a block that is constant on that axis and
occupies no words for it at all.
"""

from typing import Final

import numpy as np

from timezonefinder.configs import (
    BLOCK_BASE_DTYPE,
    BLOCK_PAYLOAD_OFFSET_DTYPE,
    BLOCK_WIDTH_DTYPE,
    POLYGON_BLOCK_SIZE,
    SOURCE_COORD_STEP,
)

#: What a payload is addressed in. Little-endian because the C kernel reads the same
#: buffer as native ``unsigned int``, the assumption the packaged ``int32`` coordinates
#: already made.
PAYLOAD_WORD_DTYPE: Final[np.dtype] = np.dtype("<u4")

#: Bits in one payload word, which is also the largest bit offset a field may begin at
#: inside its word.
PAYLOAD_WORD_BITS: Final[int] = 32

# Zero words appended to every ring's payload.
#
# A field is read as the two words ``bit >> 5`` and ``(bit >> 5) + 1``, so the last field
# of a ring is read together with one word that is not part of it. Padding is what makes
# that word exist; its value is irrelevant, since the mask discards it. Two rather than
# one so that a reader may also load 64 bits at the word before it.
PAYLOAD_PADDING_WORDS: Final[int] = 2

#: What a residual is, once unpacked: unsigned, and never wider than a coordinate.
RESIDUAL_DTYPE: Final[np.dtype] = np.dtype("<u4")

#: The widest field the packing supports, which is a full ``int32`` coordinate range.
#: Reached by the blocks of rings that straddle the antimeridian, where one block holds
#: longitudes at both +180 and -180 degrees.
MAX_RESIDUAL_BITS: Final[int] = 32


def block_vertex_counts(
    nr_vertices: int, block_size: int = POLYGON_BLOCK_SIZE
) -> np.ndarray:
    """How many values per axis each block of a ring stores, bridging vertex included.

    ``block_size + 1`` for every full block, and the ragged remainder plus one for the
    last. The bridging vertex is stored rather than read out of the next block, so that
    decoding a block never needs a second block's frame.

    :param nr_vertices: the ring's vertex count
    :param block_size: vertices per block
    :return: one count per block, ``int64``
    """
    nr_blocks = -(-nr_vertices // block_size)
    counts = np.full(nr_blocks, block_size, dtype=np.int64)
    counts[-1] = nr_vertices - (nr_blocks - 1) * block_size
    return counts + 1


def region_word_counts(counts: np.ndarray, widths: np.ndarray) -> np.ndarray:
    """Words each axis region occupies, as ``(nr_blocks, 2)``.

    :param counts: values per axis and block, as :func:`block_vertex_counts` returns
    :param widths: ``(nr_blocks, 2)`` bit widths, x then y
    """
    bits = np.asarray(counts, dtype=np.int64)[:, None] * np.asarray(
        widths, dtype=np.int64
    )
    return -(-bits // PAYLOAD_WORD_BITS)


def ring_payload_offsets(counts: np.ndarray, widths: np.ndarray) -> np.ndarray:
    """Where each block of one ring starts, as a word offset into that ring's payload.

    The exclusive cumulative sum of the per-block word counts, which is why nothing
    stores these: they follow from the widths and the vertex count, both of which are
    stored for other reasons.
    """
    sizes = region_word_counts(counts, widths).sum(axis=1)
    offsets = np.zeros(len(sizes), dtype=np.int64)
    np.cumsum(sizes[:-1], out=offsets[1:])
    return offsets


def ring_payload_length(counts: np.ndarray, widths: np.ndarray) -> int:
    """Total words one ring's payload occupies, padding included."""
    return int(region_word_counts(counts, widths).sum()) + PAYLOAD_PADDING_WORDS


def pack_residuals(values: np.ndarray, width: int) -> np.ndarray:
    """``values`` as a little-endian bit stream of ``width`` bits each, word-padded.

    :param values: non-negative residuals, each below ``2 ** width``
    :param width: bits per value; ``0`` yields no words at all
    :return: :data:`PAYLOAD_WORD_DTYPE` array of ``ceil(len(values) * width / 32)`` words
    """
    if width == 0:
        return np.empty(0, dtype=PAYLOAD_WORD_DTYPE)
    v = np.asarray(values, dtype=np.uint64)
    bits = ((v[:, None] >> np.arange(width, dtype=np.uint64)) & np.uint64(1)).astype(
        np.uint8
    )
    stream = bits.ravel()
    padding = -len(stream) % PAYLOAD_WORD_BITS
    if padding:
        stream = np.concatenate([stream, np.zeros(padding, dtype=np.uint8)])
    return np.packbits(stream, bitorder="little").view(PAYLOAD_WORD_DTYPE)


def unpack_residuals(
    payload: np.ndarray, word_offset: int, width: int, count: int
) -> np.ndarray:
    """The inverse of :func:`pack_residuals`, reading ``count`` values out of ``payload``.

    Used to reconstruct absolute coordinates (:func:`decode_ring`), never on the lookup
    path - the kernels read one residual at a time and compare it in the block's own
    frame instead.

    :param payload: the ring's payload words
    :param word_offset: where the region's bit stream begins
    :param width: bits per value
    :param count: how many values to read
    :return: ``count`` values in :data:`RESIDUAL_DTYPE`
    """
    if width == 0:
        return np.zeros(count, dtype=RESIDUAL_DTYPE)
    words = -(-count * width // PAYLOAD_WORD_BITS)
    window = np.asarray(
        payload[word_offset : word_offset + words], dtype=PAYLOAD_WORD_DTYPE
    )
    bits = np.unpackbits(window.view(np.uint8), bitorder="little")[: count * width]
    weights = np.uint64(1) << np.arange(width, dtype=np.uint64)
    return (bits.reshape(count, width).astype(np.uint64) @ weights).astype(
        RESIDUAL_DTYPE
    )


def encode_ring(
    ring: np.ndarray,
    block_ranges: np.ndarray,
    block_size: int = POLYGON_BLOCK_SIZE,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Encode one ring into its payload and the per-block frames that decode it.

    **The latitude frame is taken from ``block_ranges``, not recomputed.** A block's
    ``[min, max]`` pair opens with exactly the minimum a y frame would subtract, and its
    span is exactly what the y width has to cover - so the index already states both,
    and storing them a second time would be a quarter of a megabyte of the same numbers
    held resident on the mode that exists to stay small. Passing the ranges in rather
    than deriving them here is what makes the two impossible to disagree: the encoder
    subtracts the value the kernel will add back.

    :param ring: the ring as stored, ``(2, N)`` scaled ``int32``
    :param block_ranges: that ring's ``(nr_blocks, 2)`` latitude index, as
        ``scripts.block_index.block_latitude_ranges`` builds it over the same blocks
    :param block_size: vertices per block
    :return: ``(payload, bases, widths)`` - the ring's padded payload words, its
        ``(nr_blocks,)`` x frame origins in
        :data:`~timezonefinder.configs.BLOCK_BASE_DTYPE` and its ``(nr_blocks, 2)`` bit
        widths in :data:`~timezonefinder.configs.BLOCK_WIDTH_DTYPE`
    :raises ValueError: if a block's span does not fit :data:`MAX_RESIDUAL_BITS`, or if
        ``block_ranges`` does not describe the blocks this ring is cut into
    """
    nr_vertices = ring.shape[1]
    counts = block_vertex_counts(nr_vertices, block_size)
    nr_blocks = len(counts)
    if block_ranges.shape != (nr_blocks, 2):
        raise ValueError(
            f"a {nr_vertices}-vertex ring is {nr_blocks} blocks at block_size="
            f"{block_size}, but the latitude index given for it has shape "
            f"{block_ranges.shape}"
        )
    bases = np.empty(nr_blocks, dtype=BLOCK_BASE_DTYPE)
    widths = np.empty((nr_blocks, 2), dtype=BLOCK_WIDTH_DTYPE)
    chunks: list[np.ndarray] = []

    for block in range(nr_blocks):
        start = block * block_size
        stop = min(start + block_size, nr_vertices)
        # ... plus the bridging vertex, which is vertex 0 for the final block
        index = np.arange(start, stop + 1)
        index[-1] %= nr_vertices

        x_values = ring[0][index].astype(np.int64)
        base_x = int(x_values.min())
        # the y frame is the index's, not this function's - see the note above
        base_y = int(block_ranges[block, 0])
        y_values = ring[1][index].astype(np.int64)
        if int(y_values.min()) != base_y or int(y_values.max()) != int(
            block_ranges[block, 1]
        ):
            raise ValueError(
                f"block {block} spans latitudes [{int(y_values.min())}, "
                f"{int(y_values.max())}] but the index records "
                f"[{base_y}, {int(block_ranges[block, 1])}]. The index was built over a "
                f"different partition of this ring, so the payload it frames would "
                f"decode to different coordinates."
            )
        bases[block] = base_x

        for axis, (values, base) in enumerate(((x_values, base_x), (y_values, base_y))):
            span = values - base
            # Residuals count *source* steps, not storage steps. Every packaged
            # coordinate is a multiple of SOURCE_COORD_STEP, because that is the grid the
            # upstream data is published on (``scripts.utils.source_coord2int``), so
            # dividing by it is exact and takes log2(10) ~ 3.3 bits off every field -
            # ~6.4 MB over the collection, for one multiply where a residual is read.
            if np.any(span % SOURCE_COORD_STEP):
                raise ValueError(
                    f"block {block} of a {nr_vertices}-vertex ring holds a coordinate "
                    f"off the source grid on axis {axis}; it was not converted by "
                    f"scripts.utils.source_coord2int"
                )
            residuals = span // SOURCE_COORD_STEP
            width = int(residuals.max()).bit_length()
            if width > MAX_RESIDUAL_BITS:
                raise ValueError(
                    f"block {block} of a {nr_vertices}-vertex ring spans "
                    f"{int(span.max())} on axis {axis}, which needs {width} bits of "
                    f"residual and the payload holds at most {MAX_RESIDUAL_BITS}"
                )
            widths[block, axis] = width
            chunks.append(pack_residuals(residuals, width))

    chunks.append(np.zeros(PAYLOAD_PADDING_WORDS, dtype=PAYLOAD_WORD_DTYPE))
    payload = np.concatenate(chunks)
    expected = ring_payload_length(counts, widths)
    if len(payload) != expected:
        raise ValueError(
            f"encoded {len(payload)} payload words where the frames describe {expected}"
        )
    return payload, bases, widths


def decode_ring(
    payload: np.ndarray,
    bases: np.ndarray,
    block_ranges: np.ndarray,
    widths: np.ndarray,
    nr_vertices: int,
    block_size: int = POLYGON_BLOCK_SIZE,
) -> np.ndarray:
    """Reconstruct a ring's absolute coordinates from its payload.

    The exact inverse of :func:`encode_ring`, and the only place an absolute coordinate
    is rebuilt: ``coords_of()`` serves ``get_geometry()`` and the integrity checks
    through it, while the point-in-polygon kernels stay in each block's own frame and
    never materialise one.

    **One gather over the whole ring, not a pass per block.** Every residual is at a
    computable bit position, so the two words holding it can be addressed for all of them
    at once - which is what makes this affordable on the largest packaged ring (46,823
    vertices, 366 blocks): block-at-a-time it cost 5.4 ms of numpy call overhead, since
    each block is only ~129 values. ``get_geometry()`` is the caller that feels it.

    Bridging vertices are dropped rather than checked, because each is a copy of a vertex
    the next block stores: what proves the two agree is a round trip over the whole ring,
    which ``timezonefinder._data_integrity.validate_block_payload`` runs against the
    rings the converter was given.

    :param bases: the ring's ``(nr_blocks,)`` x frame origins
    :param block_ranges: the ring's latitude index, whose ``[:, 0]`` column *is* the y
        frame - see :func:`encode_ring` for why it is not stored twice
    :return: the ring as ``(2, nr_vertices)``, matching what was encoded
    """
    counts = block_vertex_counts(nr_vertices, block_size)
    offsets = ring_payload_offsets(counts, widths)
    words = region_word_counts(counts, widths)
    nr_blocks = len(counts)

    # Which block each stored value belongs to, and its index inside that block. Built
    # once for both axes: the two regions of a block hold the same number of values.
    block_of = np.repeat(np.arange(nr_blocks), counts)
    starts = np.zeros(nr_blocks, dtype=np.int64)
    np.cumsum(counts[:-1], out=starts[1:])
    index_in_block = np.arange(len(block_of)) - starts[block_of]
    # the trailing value of every block is its bridging vertex, which the next block
    # owns - so it is read and then dropped rather than never read: a block's region is
    # one bit stream and skipping its last field would not make the gather any cheaper
    keep = index_in_block < np.repeat(counts, counts) - 1

    origins = (
        np.asarray(bases, dtype=np.int64),
        np.asarray(block_ranges[:, 0], dtype=np.int64),
    )
    coords = np.empty((2, nr_vertices), dtype=np.int32)
    for axis in (0, 1):
        width = np.asarray(widths[:, axis], dtype=np.int64)[block_of]
        # the x region starts where the block does, the y region after it
        region = offsets[block_of] + (words[:, 0][block_of] if axis else 0)
        bit = index_in_block * width
        word = region + (bit >> 5)
        # A field spans at most two words, which PAYLOAD_PADDING_WORDS makes safe to
        # read even for the very last one. A zero width reads whatever is at the
        # region's start and masks all of it away.
        pair = payload[word].astype(np.uint64) | (
            payload[word + 1].astype(np.uint64) << np.uint64(32)
        )
        mask = (np.uint64(1) << width.astype(np.uint64)) - np.uint64(1)
        values = (pair >> (bit & 31).astype(np.uint64)) & mask
        absolute = values.astype(np.int64) * SOURCE_COORD_STEP + origins[axis][block_of]
        coords[axis] = absolute[keep].astype(np.int32)
    return coords


def derive_payload_offsets(
    nr_vertices: np.ndarray,
    widths: np.ndarray,
    block_offsets: np.ndarray,
    block_size: int = POLYGON_BLOCK_SIZE,
) -> np.ndarray:
    """Where every block of a whole collection starts inside *its own ring's* payload.

    Derived once when a collection is loaded rather than stored, because the widths and
    the vertex counts already say it. Ring-relative rather than file-relative, so that
    the kernels take the same word offset whether the payload came out of a mapping or
    out of a preloaded copy.

    **Written to allocate as little as it can**, which is why it is one flat pass rather
    than the obvious per-ring one. The result is 0.25 MB; an earlier version built it out
    of ``int64`` intermediates and a list of per-ring arrays, and cost 3.5 MB of resident
    memory that was never returned - on the mode whose whole purpose is to stay small,
    and paid by a finder that has answered nothing yet.

    :param nr_vertices: vertex count per ring
    :param widths: the collection's flat ``(total_blocks, 2)`` width array
    :param block_offsets: where each ring's blocks start in that flat array
    :param block_size: vertices per block
    :return: one word offset per block, in
        :data:`~timezonefinder.configs.BLOCK_PAYLOAD_OFFSET_DTYPE`
    """
    starts = np.asarray(block_offsets, dtype=BLOCK_PAYLOAD_OFFSET_DTYPE)
    total_blocks = len(widths)
    if total_blocks == 0:
        # a hole collection can legitimately store no inline rings at all
        return np.zeros(0, dtype=BLOCK_PAYLOAD_OFFSET_DTYPE)

    # Values per axis and block, bridging vertex included: full everywhere except each
    # ring's last block, which is ragged.
    counts = np.full(total_blocks, block_size + 1, dtype=BLOCK_PAYLOAD_OFFSET_DTYPE)
    blocks_per_ring = np.diff(starts.astype(np.int64))
    counts[starts[1:] - 1] = (
        np.asarray(nr_vertices, dtype=np.int64) - (blocks_per_ring - 1) * block_size + 1
    )

    # Words per block: each axis region rounded up to a whole word, summed.
    sizes = (counts * widths[:, 0] + PAYLOAD_WORD_BITS - 1) // PAYLOAD_WORD_BITS
    sizes += (counts * widths[:, 1] + PAYLOAD_WORD_BITS - 1) // PAYLOAD_WORD_BITS
    del counts

    offsets = np.zeros(total_blocks, dtype=BLOCK_PAYLOAD_OFFSET_DTYPE)
    np.cumsum(sizes[:-1], out=offsets[1:])
    del sizes
    # ... which is a running total over the whole collection; rebase it per ring
    offsets -= np.repeat(offsets[starts[:-1]], blocks_per_ring)
    return offsets
