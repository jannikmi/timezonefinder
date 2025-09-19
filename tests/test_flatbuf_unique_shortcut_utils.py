import os
import tempfile
from pathlib import Path

import numpy as np
import pytest

from timezonefinder.flatbuf.io.unique_shortcuts import (
    read_unique_shortcuts_binary,
    write_unique_shortcuts_flatbuffers,
)


@pytest.mark.parametrize(
    "dtype, mapping",
    [
        (np.dtype("<u1"), {1: 25, 123456789: 200}),
        (np.dtype("<u2"), {7: 512, 42: 1024}),
    ],
)
def test_unique_shortcut_roundtrip(dtype: np.dtype, mapping: dict[int, int]) -> None:
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        path = Path(tmp.name)

    try:
        write_unique_shortcuts_flatbuffers(mapping, dtype, path)
        result = read_unique_shortcuts_binary(path)
        assert result == mapping
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_unique_shortcut_empty_mapping() -> None:
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        path = Path(tmp.name)

    try:
        write_unique_shortcuts_flatbuffers({}, np.dtype("<u1"), path)
        result = read_unique_shortcuts_binary(path)
        assert result == {}
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_unique_shortcut_invalid_dtype() -> None:
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        path = Path(tmp.name)

    try:
        with pytest.raises(ValueError):
            write_unique_shortcuts_flatbuffers({1: 1}, np.dtype("<u4"), path)
        with pytest.raises(ValueError):
            write_unique_shortcuts_flatbuffers({1: 1}, np.dtype("<u8"), path)
    finally:
        if os.path.exists(path):
            os.unlink(path)
