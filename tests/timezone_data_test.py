"""Tests for the invariants `scripts/timezone_data.py` enforces on zone data.

`ZoneCollection.validate_structure` is the only thing standing between a
malformed `poly_zone_ids` array and the binaries the converter writes, and it
runs at construction time only - so what it rejects, and what downstream code
is therefore allowed to assume, is worth pinning.
"""

import numpy as np
import pytest

from scripts.configs import ZONE_ID_DTYPE
from scripts.helper_classes import GeoJSON
from scripts.timezone_data import TimezoneData, ZoneCollection


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


def _ring(x0: float, y0: float) -> list[list[float]]:
    """A closed square ring, offset so every ring in a fixture is distinguishable."""
    return [
        [x0, y0],
        [x0 + 1.0, y0],
        [x0 + 1.0, y0 + 1.0],
        [x0, y0 + 1.0],
        [x0, y0],
    ]


def _geo_json() -> GeoJSON:
    """Two zones whose polygons and holes are all of different sizes.

    The first zone is a multipolygon of two rings, the second a single polygon;
    polygons 0 and 2 carry holes, polygon 1 carries none. That asymmetry is the
    point: a parse that paired a hole with the wrong polygon, or a length with
    the wrong ring, would still produce well-formed collections on a fixture
    where everything lines up by accident.
    """
    zone_a = {
        "type": "Feature",
        "properties": {"tzid": "Test/A"},
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [_ring(0.0, 0.0), _ring(0.2, 0.2)],
                [_ring(10.0, 10.0)],
            ],
        },
    }
    zone_b = {
        "type": "Feature",
        "properties": {"tzid": "Test/B"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [_ring(20.0, 20.0), _ring(20.2, 20.2), _ring(20.4, 20.4)],
        },
    }
    return GeoJSON.model_validate(
        {"type": "FeatureCollection", "features": [zone_a, zone_b]}
    )


@pytest.mark.unit
class TestGeoJsonParseAccumulation:
    """What `ParseAccumulator` has to keep aligned across three call levels.

    Everything here is positional: a hole is attributed to a polygon by the id
    stored beside it, and a ring's vertex count by its position in a parallel
    list. Nothing downstream re-derives either, so a misattribution reaches the
    binaries intact.
    """

    def test_holes_are_attributed_to_the_polygon_they_were_parsed_under(self):
        data = TimezoneData.from_geojson(_geo_json())
        # polygon 0 (zone A, first ring) and polygon 2 (zone B) each hold holes,
        # polygon 1 holds none; the counter that assigns them advances per polygon.
        assert data.polynrs_of_holes == [0, 2, 2]
        assert data.nr_of_holes == 3

    def test_each_ring_s_recorded_length_is_its_own_vertex_count(self):
        data = TimezoneData.from_geojson(_geo_json())
        assert data.polygon_lengths == [p.shape[1] for p in data.polygons]
        assert data.all_hole_lengths == [h.shape[1] for h in data.holes]

    def test_zone_ids_follow_the_polygons_of_each_zone(self):
        data = TimezoneData.from_geojson(_geo_json())
        assert data.all_tz_names == ["Test/A", "Test/B"]
        assert list(data.poly_zone_ids) == [0, 0, 1]

    def test_the_original_polygons_pair_with_the_parsed_boundaries(self):
        data = TimezoneData.from_geojson(_geo_json())
        originals = data.original_polygons
        assert originals is not None
        assert len(originals) == len(data.polygons)
        for original, parsed in zip(originals, data.polygons):
            assert original.shape == parsed.shape
