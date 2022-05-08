from pathlib import Path
from typing import List

import h3.api.numpy_int as h3
import numpy as np

from scripts import file_converter
from timezonefinder import configs, hex_helpers

PATH2SHORTCUT_FILE = (
    Path(__file__).parent.parent / "timezonefinder" / configs.SHORTCUT_FILE
)

shortcuts = hex_helpers.read_shortcuts_binary(PATH2SHORTCUT_FILE)


def test_import_export():
    write_shortcuts = {
        13415131: [123, 122, 4, 12],
        13415113131: [
            123,
        ],
        13415121: [],
    }
    tmp_path = Path("tmp_shortcut.bin")
    hex_helpers.export_shortcuts_binary(write_shortcuts, tmp_path)
    read_shortcuts = hex_helpers.read_shortcuts_binary(tmp_path)
    assert isinstance(read_shortcuts, dict)
    assert len(read_shortcuts) == len(write_shortcuts)
    for k1, v1 in write_shortcuts.items():
        v2 = read_shortcuts[k1]
        assert isinstance(v2, np.ndarray)
        v1_np = np.array(v1, dtype=configs.DTYPE_FORMAT_H_NUMPY)
        np.testing.assert_equal(v2, v1_np)


def test_resolutions():
    shortcut_hex_ids = shortcuts.keys()
    resolutions = map(lambda h: h3.h3_get_resolution(h), shortcut_hex_ids)
    assert all(
        map(lambda res: res == configs.SHORTCUT_H3_RES, resolutions)
    ), f"not all shortcut resolutions match the expected resolution {configs.SHORTCUT_H3_RES}"


def test_empty_shortcut():
    for hex_id, polygon_ids in shortcuts.items():
        if len(polygon_ids) == 0:
            print(h3.h3_to_geo(hex_id))
            raise ValueError(f"found an empty shortcut entry: {hex_id}:, {polygon_ids}")


def test_unique_pole_cells():
    s_pole_ctr = 0
    n_pole_ctr = 0
    for hex_id in shortcuts.keys():
        hex = file_converter.get_hex(hex_id)
        if hex.surr_s_pole:
            s_pole_ctr += 1
        if hex.surr_n_pole:
            n_pole_ctr += 1

    assert (
        s_pole_ctr == 1
    ), f"{s_pole_ctr} cells are considered to surround the south pole"
    assert (
        n_pole_ctr == 1
    ), f"{n_pole_ctr} cells are considered to surround the north pole"


def has_coherent_sequences(lst: List[int]) -> bool:
    """
    :return: True if equal entries in the list are not separated by entries of other values
    """
    if len(lst) <= 1:
        return True
    encountered = set()
    # at least 2 entries
    lst_iter = iter(lst)
    prev = next(lst_iter)
    for e in lst:
        if e in encountered:
            # the entry appeared earlier already
            return False
        if e != prev:
            encountered.add(prev)
            prev = e

    return True


def test_has_coherent_sequences():
    assert has_coherent_sequences([])
    assert has_coherent_sequences([1])
    assert has_coherent_sequences([1, 1])
    assert has_coherent_sequences([2, 3])
    assert has_coherent_sequences([2, 3, 3, 0, 0, 4])
    assert not has_coherent_sequences([2, 3, 2])
    assert not has_coherent_sequences([2, 3, 2, 3])


def test_shortcut_sorting():
    for polygon_ids in shortcuts.values():
        assert has_coherent_sequences(polygon_ids)
