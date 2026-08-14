"""Tests for the invariants `scripts/timezone_data.py` enforces on zone data.

`ZoneCollection.validate_structure` is the only thing standing between a
malformed `poly_zone_ids` array and the binaries the converter writes, and it
runs at construction time only - so what it rejects, and what downstream code
is therefore allowed to assume, is worth pinning.
"""

import numpy as np
import pytest

from scripts.configs import ZONE_ID_DTYPE
from scripts.timezone_data import ZoneCollection


def _zones(zone_ids: list[int], names: list[str] | None = None) -> ZoneCollection:
    ids = np.array(zone_ids, dtype=ZONE_ID_DTYPE)
    if names is None:
        names = [f"Zone/{i}" for i in range(int(ids.max()) + 1)] if len(ids) else []
    return ZoneCollection(names=names, poly_zone_ids=ids)


@pytest.mark.unit
class TestZoneCollectionValidation:
    def test_accepts_non_decreasing_ids(self):
        zones = _zones([0, 0, 1, 2, 2, 2])
        assert zones.nr_of_polygons == 6
        assert zones.nr_of_zones == 3

    def test_rejects_a_signed_dtype(self):
        # this is what makes a negative zone id unrepresentable rather than merely
        # unwanted: there is deliberately no separate `< 0` check below it
        with pytest.raises(ValueError, match="unsigned integer dtype"):
            ZoneCollection(
                names=["Zone/0"], poly_zone_ids=np.array([0], dtype=np.int32)
            )

    def test_rejects_decreasing_ids(self):
        with pytest.raises(ValueError, match="non-decreasing order"):
            _zones([0, 2, 1], names=["Zone/0", "Zone/1", "Zone/2"])

    def test_rejects_a_max_id_that_does_not_match_the_zone_count(self):
        with pytest.raises(ValueError, match="Maximum zone ID"):
            _zones([0, 1], names=["Zone/0", "Zone/1", "Zone/2"])

    def test_rejects_polygons_without_zones(self):
        with pytest.raises(ValueError, match="Zone list cannot be empty"):
            _zones([0], names=[])


@pytest.mark.unit
class TestZonePositions:
    def test_marks_where_each_zone_starts_and_ends(self):
        # one entry per zone, plus a trailing sentinel holding the polygon count,
        # so `positions[i]:positions[i + 1]` slices zone i's polygons
        assert _zones([0, 0, 1, 2, 2, 2]).zone_positions() == [0, 2, 3, 6]

    def test_handles_one_polygon_per_zone(self):
        assert _zones([0, 1, 2]).zone_positions() == [0, 1, 2, 3]

    def test_relies_on_the_ordering_guaranteed_at_construction(self):
        # the scan is not repeated here, so this documents what it may assume:
        # every collection reaching `zone_positions` has already been validated
        zones = _zones([0, 0, 1, 1])
        assert zones.zone_positions() == [0, 2, 4]
