"""The polygon container: one payload vector per ring, and what it guarantees.

Only the container. What the words inside a payload *mean* is
``tests/test_block_payload.py``'s subject, and the two are kept apart on purpose - this
module has to keep passing over buffers that are not decodable at all, which is what
lets it pin the wire format rather than a round trip through the encoder.
"""

import struct
import numpy as np
import pytest
from timezonefinder.block_payload import PAYLOAD_WORD_DTYPE
from timezonefinder.flatbuf.io.polygons import (
    derive_payload_offset_table,
    get_polygon_collection,
    read_payload_at,
    read_payload_from_binary,
    write_polygon_collection_flatbuffer,
)
from timezonefinder.utils import close_resource

PAYLOADS = [
    np.array([0, 1, 2], dtype=PAYLOAD_WORD_DTYPE),
    np.array([6, 7, 8, 9], dtype=PAYLOAD_WORD_DTYPE),
]


@pytest.mark.parametrize("payloads", [PAYLOADS])
def test_single_polygon_collection_round_trip(tmp_path, payloads):
    """Test that writing and reading a single polygon collection gives the same results."""
    output_file = tmp_path / "polygons.bin"

    write_polygon_collection_flatbuffer(output_file, payloads)

    assert output_file.exists(), "Output file should exist after writing."
    assert output_file.stat().st_size > 0, "Output file should be non-empty."

    with open(output_file, "rb") as file:
        buffer = file.read()
    poly_collection = get_polygon_collection(buffer)
    for idx, original in enumerate(payloads):
        read_back = read_payload_from_binary(poly_collection, idx)
        np.testing.assert_array_equal(read_back, original, "Payload mismatch.")

    # An out-of-bounds index must not answer with a payload. Which exception carries
    # that is FlatBuffers' business and changed with the element type - a `[uint]`
    # vector rejects the nonsense offset it reads as a number where `[int]` failed to
    # unpack it - so what is pinned here is that it raises at all.
    with pytest.raises((struct.error, TypeError, IndexError)):
        read_payload_from_binary(poly_collection, idx + 1)

    close_resource(buffer)
    close_resource(file)


@pytest.mark.unit
def test_the_written_file_is_a_whole_number_of_words(tmp_path):
    """The reader views the whole file as ``uint32``, which a ragged tail forbids.

    FlatBuffers aligns what it writes but does not pad the end of the buffer, so without
    the writer's own padding a file could end mid-word - and ``np.frombuffer`` then
    refuses the *buffer*, failing to open a data directory rather than to read any one
    polygon. One payload per length here, so that whichever tail FlatBuffers happens to
    produce is covered.
    """
    for count in range(1, 6):
        output_file = tmp_path / f"polygons_{count}.bin"
        write_polygon_collection_flatbuffer(
            output_file, [np.arange(count, dtype=PAYLOAD_WORD_DTYPE)]
        )
        size = output_file.stat().st_size
        assert size % PAYLOAD_WORD_DTYPE.itemsize == 0, (
            f"a collection of {count} words is {size} bytes, which is not a whole "
            f"number of payload words"
        )
        buffer = output_file.read_bytes()
        # the operation the padding exists for
        np.frombuffer(buffer, dtype=PAYLOAD_WORD_DTYPE)
        close_resource(buffer)


@pytest.mark.unit
@pytest.mark.parametrize("payloads", [PAYLOADS])
def test_on_disk_payload_element_width(tmp_path, payloads):
    """The bytes on disk hold 32-bit words, checked without the reader.

    Going through :func:`read_payload_from_binary` cannot catch a writer and a reader
    that are wrong in mutually cancelling ways - every round trip still passes. Reading
    the raw vector back is the only thing that pins the wire format down, and the
    element width is the half of it that matters: at eight bytes per element every
    second word would be a zero from the high half of its neighbour, and the offset
    table would agree with the reader about the same wrong bytes.
    """
    output_file = tmp_path / "polygons.bin"
    write_polygon_collection_flatbuffer(output_file, payloads)

    with open(output_file, "rb") as file:
        buffer = file.read()
    poly_collection = get_polygon_collection(buffer)

    for idx, payload in enumerate(payloads):
        raw = poly_collection.Polygons(idx).PayloadAsNumpy()
        assert raw.dtype == np.uint32, "payload is not stored as 32-bit words"
        assert len(raw) == len(payload), "word count changed with the element width"
        np.testing.assert_array_equal(raw, payload)

    close_resource(buffer)


@pytest.mark.unit
def test_wider_integer_input_is_stored_as_a_word(tmp_path):
    """A payload that is not already ``uint32`` must still be written 4 bytes per word.

    ``np.array([0, 1])`` is int64 on every platform this runs on. The writer hands the
    array to ``Builder.CreateNumpyVector``, which takes the element width from its
    dtype, so without the cast this would lay down 8-byte elements while the schema, the
    reader and the offset table all read 4.
    """
    payload = np.array([0, 1, 2, 3])
    assert payload.dtype != PAYLOAD_WORD_DTYPE, "fixture no longer exercises the cast"
    output_file = tmp_path / "polygons.bin"

    write_polygon_collection_flatbuffer(output_file, [payload])

    with open(output_file, "rb") as file:
        buffer = file.read()
    raw = get_polygon_collection(buffer).Polygons(0).PayloadAsNumpy()

    assert len(raw) == payload.size, "word count changed with the element width"
    np.testing.assert_array_equal(raw, payload)
    close_resource(buffer)


@pytest.mark.unit
@pytest.mark.parametrize("payloads", [PAYLOADS])
def test_offset_table_and_reader_address_the_same_words(tmp_path, payloads):
    """The two ways to reach a payload have to agree, which is what the lookup path assumes.

    ``scripts.data_integrity.validate_payload_offset_table`` makes this statement over
    real data directories; here it is made over a collection built by hand, so a
    regression shows up without a regenerated 38 MB binary.
    """
    output_file = tmp_path / "polygons.bin"
    write_polygon_collection_flatbuffer(output_file, payloads)
    buffer = output_file.read_bytes()
    collection = get_polygon_collection(buffer)

    offsets, lengths = derive_payload_offset_table(collection)
    words = np.frombuffer(buffer, dtype=PAYLOAD_WORD_DTYPE)
    assert len(offsets) == len(payloads)
    for idx, payload in enumerate(payloads):
        np.testing.assert_array_equal(
            read_payload_at(words, offsets[idx], lengths[idx]), payload
        )
        np.testing.assert_array_equal(
            read_payload_at(words, offsets[idx], lengths[idx]),
            read_payload_from_binary(collection, idx),
        )
    del words
    close_resource(buffer)


if __name__ == "__main__":
    pytest.main([__file__])
