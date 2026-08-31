"""Cross-file validation available to installed timezonefinder users."""

import json
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest

from timezonefinder import _data_integrity
from timezonefinder._data_integrity import (
    DataIntegrityError,
    validate_data_dir,
    validate_hole_registry,
    validate_zone_data,
)
from timezonefinder.configs import DEFAULT_DATA_DIR
from timezonefinder.np_binary_helpers import (
    get_zone_ids_path,
    get_zone_positions_path,
    store_per_polygon_vector,
)
from timezonefinder.zone_names import write_zone_names


class _FakeBoundaries:
    """Two disjoint square boundaries for registry ownership tests."""

    rings = (
        np.array([[0, 10, 10, 0], [0, 0, 10, 10]], dtype=np.int32),
        np.array([[20, 30, 30, 20], [20, 20, 30, 30]], dtype=np.int32),
    )

    def __init__(self, data_location: Path):
        self.data_location = data_location
        self.coordinates = self.rings
        self.xmin = np.array([0, 20])
        self.xmax = np.array([10, 30])
        self.ymin = np.array([0, 20])
        self.ymax = np.array([10, 30])

    def __len__(self) -> int:
        return len(self.rings)

    def coords_of(self, boundary_id: int) -> np.ndarray:
        return self.rings[boundary_id]

    def outside_bbox(self, boundary_id: int, x: int, y: int) -> bool:
        return not (
            self.xmin[boundary_id] <= x <= self.xmax[boundary_id]
            and self.ymin[boundary_id] <= y <= self.ymax[boundary_id]
        )


class _FakeHoles:
    """One small hole inside each fake boundary."""

    rings = (
        np.array([[1, 2, 2, 1], [1, 1, 2, 2]], dtype=np.int32),
        np.array([[21, 22, 22, 21], [21, 21, 22, 22]], dtype=np.int32),
    )

    def __init__(self, data_location: Path, boundaries: _FakeBoundaries):
        self.data_location = data_location
        self.boundaries = boundaries

    def __len__(self) -> int:
        return len(self.rings)

    def coords_of(self, hole_id: int) -> np.ndarray:
        return self.rings[hole_id]


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
def test_zone_positions_and_zone_ids_can_describe_one_grouping(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(_data_integrity, "PolygonArray", _FakeBoundaries)
    data_dir = _zone_data_dir(
        tmp_path,
        np.array([0, 1, 2], dtype=np.uint16),
        np.array([0, 1], dtype=np.uint8),
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
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    positions: np.ndarray,
    zone_ids: np.ndarray,
    message: str,
):
    monkeypatch.setattr(_data_integrity, "PolygonArray", _FakeBoundaries)
    data_dir = _zone_data_dir(tmp_path, positions, zone_ids)
    with pytest.raises(DataIntegrityError, match=message):
        validate_zone_data(data_dir)


@pytest.mark.unit
def test_zone_data_rejects_a_phantom_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(_data_integrity, "PolygonArray", _FakeBoundaries)
    data_dir = _zone_data_dir(
        tmp_path,
        np.array([0, 2, 3], dtype=np.uint16),
        np.array([0, 0, 1], dtype=np.uint8),
    )
    with pytest.raises(DataIntegrityError, match="coordinates.bin has 2"):
        validate_zone_data(data_dir)


@pytest.mark.unit
def test_zone_data_rejects_a_mismatched_boundary_vector(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    class BoundariesWithMissingXmax(_FakeBoundaries):
        def __init__(self, data_location: Path):
            super().__init__(data_location)
            self.xmax = self.xmax[:-1]

    monkeypatch.setattr(
        _data_integrity,
        "PolygonArray",
        BoundariesWithMissingXmax,
    )
    data_dir = _zone_data_dir(
        tmp_path,
        np.array([0, 1, 2], dtype=np.uint16),
        np.array([0, 1], dtype=np.uint8),
    )
    with pytest.raises(DataIntegrityError, match="xmax.npy has 1"):
        validate_zone_data(data_dir)


def _write_fake_hole_registry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    registry: object,
) -> Path:
    monkeypatch.setattr(_data_integrity, "PolygonArray", _FakeBoundaries)
    monkeypatch.setattr(_data_integrity, "HoleArray", _FakeHoles)
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "hole_registry.json").write_text(json.dumps(registry))
    return data_dir


@pytest.mark.unit
def test_hole_registry_can_partition_holes_between_their_owning_boundaries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    data_dir = _write_fake_hole_registry(
        tmp_path,
        monkeypatch,
        {"0": [1, 0], "1": [1, 1]},
    )
    validate_hole_registry(data_dir)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("registry", "message"),
    [
        ({"2": [2, 0]}, "only 2 boundary polygons exist"),
        ({"0": [3, 0]}, r"range \[0, 3\)"),
        ({"0": [2, 0], "1": [1, 1]}, "assigns hole 1 to both"),
        ({"0": [1, 0]}, "does not assign hole 1"),
        (
            {"0": [1, 1], "1": [1, 0]},
            "hole 0 to boundary 1.*does not lie inside",
        ),
    ],
)
def test_hole_registry_rejects_broken_ranges_coverage_and_ownership(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    registry: dict[str, list[int]],
    message: str,
):
    data_dir = _write_fake_hole_registry(tmp_path, monkeypatch, registry)
    with pytest.raises(DataIntegrityError, match=message):
        validate_hole_registry(data_dir)


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
        "validate_hole_registry",
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
