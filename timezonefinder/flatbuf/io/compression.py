"""Compression utilities for FlatBuffer binary data using zstandard (zstd)."""

import mmap
from pathlib import Path
from typing import Union

import zstandard as zstd


# Compression parameters optimized for geodata
# Higher compression level trades speed for smaller size
ZSTD_COMPRESSION_LEVEL = 19  # Maximum compression
ZSTD_DICT_SIZE = 0  # No pre-trained dictionary


def compress_file(input_path: Path, output_path: Path, level: int = ZSTD_COMPRESSION_LEVEL) -> None:
    """Compress a file using zstandard compression.

    Args:
        input_path: Path to the input file to compress
        output_path: Path to save the compressed file
        level: Compression level (1-22, default 19 for high compression)
    """
    cctx = zstd.ZstdCompressor(level=level)
    with open(input_path, "rb") as infile:
        with open(output_path, "wb") as outfile:
            cctx.copy_stream(infile, outfile)


def decompress_file(input_path: Path, output_path: Path) -> None:
    """Decompress a zstandard-compressed file.

    Args:
        input_path: Path to the compressed file
        output_path: Path to save the decompressed file
    """
    dctx = zstd.ZstdDecompressor()
    with open(input_path, "rb") as infile:
        with open(output_path, "wb") as outfile:
            dctx.copy_stream(infile, outfile)


def decompress_bytes(data: bytes) -> bytes:
    """Decompress zstandard-compressed bytes.

    Args:
        data: Compressed byte data

    Returns:
        Decompressed byte data
    """
    dctx = zstd.ZstdDecompressor()
    return dctx.decompress(data)


def decompress_mmap(compressed_mmap: Union[mmap.mmap, bytes]) -> bytes:
    """Decompress zstandard data from a memory-mapped file or bytes.

    Args:
        compressed_mmap: Memory-mapped compressed file or bytes

    Returns:
        Decompressed byte data
    """
    if isinstance(compressed_mmap, mmap.mmap):
        # Read all data from mmap for decompression
        data = compressed_mmap[:]
    else:
        data = compressed_mmap

    dctx = zstd.ZstdDecompressor()
    return dctx.decompress(data)
