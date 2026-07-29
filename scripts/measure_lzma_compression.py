#!/usr/bin/env python3
"""Measure lzma compression ratio, round-trip correctness, and timing."""

from __future__ import annotations

import lzma
import time
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    target_path = (
        repo_root / "timezonefinder" / "data" / "boundaries" / "coordinates.fbs"
    )

    if not target_path.exists():
        raise FileNotFoundError(f"Target file not found: {target_path}")

    data = target_path.read_bytes()

    start = time.perf_counter()
    compressed = lzma.compress(data, preset=9)
    compression_time = time.perf_counter() - start

    start = time.perf_counter()
    decompressed = lzma.decompress(compressed)
    decompression_time = time.perf_counter() - start

    original_size = len(data)
    compressed_size = len(compressed)
    ratio = compressed_size / original_size if original_size else 0.0
    saved_percent = (1 - ratio) * 100 if original_size else 0.0
    roundtrip_ok = decompressed == data

    print(f"File: {target_path}")
    print(f"Original size: {original_size:,} bytes")
    print(f"Compressed size: {compressed_size:,} bytes")
    print(f"Compression ratio: {ratio:.3f}")
    print(f"Space saved: {saved_percent:.2f}%")
    print(f"Compression time: {compression_time:.6f} s")
    print(f"Decompression time: {decompression_time:.6f} s")
    print(f"Roundtrip OK: {roundtrip_ok}")


if __name__ == "__main__":
    main()
