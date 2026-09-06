"""Tests for the invariants `scripts/timezone_data.py` enforces on zone data.

`ZoneCollection.validate_structure` is the only thing standing between a
malformed `poly_zone_ids` array and the binaries the converter writes, and it
runs at construction time only - so what it rejects, and what downstream code
is therefore allowed to assume, is worth pinning.
"""

import math

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


def _ring(x0: float, y0: float, nr_vertices: int) -> list[list[float]]:
    """A closed ring of `nr_vertices` distinct vertices, offset to `(x0, y0)`.

    Both the size and the offset vary per ring in the fixture below, so a
    misattributed ring is visible in a length and in a coordinate rather than
    only in a list position.
    """
    step = 2 * math.pi / nr_vertices
    # the converter stores boundary coordinates on the source's own grid of six
    # decimal places and refuses a seventh, so the fixture is built on it too
    ring = [
        [round(x0 + math.cos(i * step), 6), round(y0 + math.sin(i * step), 6)]
        for i in range(nr_vertices)
    ]
    return [*ring, ring[0]]


def _geo_json() -> GeoJSON:
    """Two zones, no two rings of the same size and no two at the same place.

    Zone A is a multipolygon of two polygons - the first carrying one hole, the
    second none - and zone B a single polygon carrying two holes. That asymmetry
    is the point: on a fixture where every ring is the same size and every
    polygon carries the same number of holes, a parse that paired a hole with the
    wrong polygon, or a length with the wrong ring, would still produce
    well-formed collections.
    """
    zone_a = {
        "type": "Feature",
        "properties": {"tzid": "Test/A"},
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [_ring(0.0, 0.0, 4), _ring(0.2, 0.2, 5)],
                [_ring(10.0, 10.0, 6)],
            ],
        },
    }
    zone_b = {
        "type": "Feature",
        "properties": {"tzid": "Test/B"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                _ring(20.0, 20.0, 7),
                _ring(20.2, 20.2, 8),
                _ring(20.4, 20.4, 9),
            ],
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
        # polygon 0 (zone A, first polygon) and polygon 2 (zone B) carry holes,
        # polygon 1 carries none; the counter that assigns them advances per polygon.
        assert data.polynrs_of_holes == [0, 2, 2]

    def test_each_ring_s_recorded_length_is_its_own_vertex_count(self):
        data = TimezoneData.from_geojson(_geo_json())
        # the sizes the fixture builds, in parse order, spelled out rather than
        # read back off the arrays they are supposed to describe
        assert data.polygon_lengths == [4, 6, 7]
        assert data.all_hole_lengths == [5, 8, 9]

    def test_zone_ids_follow_the_polygons_of_each_zone(self):
        data = TimezoneData.from_geojson(_geo_json())
        assert data.all_tz_names == ["Test/A", "Test/B"]
        assert list(data.poly_zone_ids) == [0, 0, 1]

    def test_the_original_polygons_pair_with_the_parsed_boundaries(self):
        data = TimezoneData.from_geojson(_geo_json())
        originals = data.original_polygons
        assert originals is not None
        # each boundary ring's own offset, so a permuted or shifted list of
        # originals fails here rather than matching on a shared shape
        assert [pytest.approx(o[0].mean(), abs=1e-6) for o in originals] == [
            0.0,
            10.0,
            20.0,
        ]
        assert [o.shape[1] for o in originals] == data.polygon_lengths
