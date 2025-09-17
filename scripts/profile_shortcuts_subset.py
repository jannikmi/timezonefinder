"""Entry point to run shortcut compilation against a tiny candidate subset."""

from __future__ import annotations

from pathlib import Path

import h3.api.numpy_int as h3

from scripts.configs import DEFAULT_INPUT_PATH, SHORTCUT_H3_RES
from scripts.shortcuts import compile_h3_map
from scripts.timezone_data import TimezoneData


def main(limit: int = 200) -> None:
    data = TimezoneData.from_path(Path(DEFAULT_INPUT_PATH))
    center = h3.latlng_to_cell(0.0, 0.0, SHORTCUT_H3_RES)
    candidates = set(h3.grid_disk(center, 1))
    if limit < len(candidates):
        candidates = set(list(candidates)[:limit])
    compile_h3_map(data, candidates=candidates)


if __name__ == "__main__":
    main()
