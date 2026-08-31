"""Cross-file validation available to installed timezonefinder users."""

from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest

from timezonefinder import _data_integrity
from timezonefinder._data_integrity import (
    DataIntegrityError,
    validate_data_dir,
    validate_zone_data,
)
from timezonefinder.configs import DEFAULT_DATA_DIR
from timezonefinder.np_binary_helpers import (
    get_zone_ids_path,
    get_zone_positions_path,
    store_per_polygon_vector,
)
from timezonefinder.zone_names import write_zone_names


def _zone_data_dir(tmp_path: Path, positions: np.ndarray, zone_ids: np.ndarray) -> Path:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    write_zone_names(["Zone/A", "Zone/B"], data_dir)
    store_per_polygon_vector(get_zone_positions_path(data_dir), positions)
    store_per_polygon_vector(get_zone_ids_path(data_dir), zone_ids)
    return data_dir


@pytest.mark.unit
def test_packaged_zone_data_is_one_complete_grouping():
    validate_zone_data(DEFAULT_DATA_DIR)


@pytest.mark.unit
def test_zone_positions_and_zone_ids_can_describe_one_grouping(tmp_path: Path):
    data_dir = _zone_data_dir(
        tmp_path,
        np.array([0, 2, 3], dtype=np.uint16),
        np.array([0, 0, 1], dtype=np.uint8),
    )
    validate_zone_data(data_dir)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("positions", "zone_ids", "message"),
    [
        (
            np.array([[0, 1, 2]], dtype=np.uint16),
            np.array([0, 1], dtype=np.uint8),
            "expected one start position",
        ),
        (
            np.array([0.0, 1.0, 2.0]),
            np.array([0, 1], dtype=np.uint8),
            "zone positions must be integers",
        ),
        (
            np.array([0, 2], dtype=np.uint16),
            np.array([0, 1], dtype=np.uint8),
            "therefore needs 3",
        ),
        (
            np.array([1, 1, 2], dtype=np.uint16),
            np.array([0, 1], dtype=np.uint8),
            r"spans \[1, 2\)",
        ),
        (
            np.array([0, 2, 1], dtype=np.uint16),
            np.array([0], dtype=np.uint8),
            "decreases from 2 to 1",
        ),
        (
            np.array([0, 2, 3], dtype=np.uint16),
            np.array([0, 1, 1], dtype=np.uint8),
            "boundary 1",
        ),
    ],
)
def test_zone_data_rejects_a_broken_partition(
    tmp_path: Path, positions: np.ndarray, zone_ids: np.ndarray, message: str
):
    data_dir = _zone_data_dir(tmp_path, positions, zone_ids)
    with pytest.raises(DataIntegrityError, match=message):
        validate_zone_data(data_dir)


@pytest.mark.unit
def test_validate_data_dir_runs_every_general_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    called: list[str] = []
    validator_names = (
        "validate_shipped_schemas",
        "validate_zone_data",
        "validate_hole_references",
        "validate_payload_offset_table",
        "validate_block_index",
        "validate_block_payload",
        "validate_shortcut_index",
    )

    def recording_validator(name: str) -> Callable[[Path], None]:
        def validate(path: Path) -> None:
            assert path == tmp_path
            called.append(name)

        return validate

    for name in validator_names:
        monkeypatch.setattr(_data_integrity, name, recording_validator(name))

    validate_data_dir(tmp_path)
    assert called == list(validator_names)


@pytest.mark.unit
def test_validate_data_dir_rejects_a_missing_directory(tmp_path: Path):
    missing = tmp_path / "missing"
    with pytest.raises(DataIntegrityError, match="not a compiled data directory"):
        validate_data_dir(missing)
