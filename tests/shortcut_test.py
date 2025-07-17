"""
test the actually stored shortcut binary file
"""

import h3.api.numpy_int as h3
import numpy as np
import pytest

from scripts import file_converter
from scripts.utils import check_shortcut_sorting, has_coherent_sequences
from timezonefinder import configs
from timezonefinder.flatbuf.shortcut_utils import (
    get_shortcut_file_path,
    read_shortcuts_binary,
)
from timezonefinder.timezonefinder import TimezoneFinder

shortcut_file_path = get_shortcut_file_path()
shortcuts = read_shortcuts_binary(shortcut_file_path)


def test_resolutions():
    shortcut_hex_ids = shortcuts.keys()
    resolutions = [h3.get_resolution(h) for h in shortcut_hex_ids]
    res_matched = [res == configs.SHORTCUT_H3_RES for res in resolutions]
    assert all(res_matched), (
        f"not all shortcut resolutions match the expected resolution {configs.SHORTCUT_H3_RES}"
    )


def test_empty_shortcut():
    # since using timezone data with ocean coverage all the cells should have polygons in them
    # test for empty shortcuts
    for hex_id, polygon_ids in shortcuts.items():
        if len(polygon_ids) == 0:
            print(h3.cell_to_boundary(hex_id)[0])
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

    assert s_pole_ctr == 1, (
        f"{s_pole_ctr} cells are considered to surround the south pole"
    )
    assert n_pole_ctr == 1, (
        f"{n_pole_ctr} cells are considered to surround the north pole"
    )


def test_shortcut_uniqueness():
    """
    test that the shortcuts are unique, i.e. no duplicates in the polygon ids
    """
    for hex_id, polygon_ids in shortcuts.items():
        if len(np.unique(polygon_ids)) != len(polygon_ids):
            raise ValueError(
                f"shortcut {hex_id} contains duplicate polygon ids: {polygon_ids}"
            )


@pytest.mark.parametrize(
    "lst,expected",
    [
        ([], True),
        ([1], True),
        ([1, 1], True),
        ([2, 3], True),
        ([2, 3, 3, 0, 0, 4], True),
        ([2, 3, 2], False),
        ([2, 3, 2, 3], False),
    ],
)
def test_has_coherent_check_fct(lst, expected):
    assert has_coherent_sequences(lst) == expected


def test_shortcut_sorting():
    tf = TimezoneFinder(in_memory=True)
    for polygon_ids in shortcuts.values():
        check_shortcut_sorting(polygon_ids, tf.zone_ids)
