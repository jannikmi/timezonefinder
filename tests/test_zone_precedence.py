"""tests for the zone-precedence rule the shortcut compilation applies to covered cells"""

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import numpy as np
import pytest

from scripts.helper_classes import Boundaries
from scripts.hex_utils import Hex
from scripts.zone_precedence import (
    FULL_SPHERE,
    resolve_covered_cells,
    spherical_ring_area,
    zone_areas,
)
from timezonefinder.utils import coord2int

if TYPE_CHECKING:
    from scripts.timezone_data import TimezoneData


def ring(lngs: list[float], lats: list[float]) -> np.ndarray:
    return np.array(
        [[coord2int(v) for v in lngs], [coord2int(v) for v in lats]], dtype=np.int32
    )


@pytest.mark.unit
class TestSphericalRingArea:
    def test_a_small_square_on_the_equator_matches_the_planar_answer(self):
        """One degree square, where the sphere is flat to within a part in 10^4."""
        area = spherical_ring_area(ring([0.0, 1.0, 1.0, 0.0], [0.0, 0.0, 1.0, 1.0]))

        assert area == pytest.approx(np.radians(1.0) ** 2, rel=1e-4)

    def test_a_lune_takes_its_share_of_the_sphere(self):
        """A 90 deg wedge from pole to pole is a quarter of the globe, exactly."""
        area = spherical_ring_area(
            ring([0.0, 90.0, 90.0, 0.0], [-90.0, -90.0, 90.0, 90.0])
        )

        assert area == pytest.approx(FULL_SPHERE / 4, rel=1e-6)

    def test_the_same_square_near_the_pole_is_far_smaller(self):
        """What a shoelace sum over the stored coordinates cannot see, and why this is
        not one: both squares span one degree by one degree in the stored plane."""
        equator = spherical_ring_area(ring([0.0, 1.0, 1.0, 0.0], [0.0, 0.0, 1.0, 1.0]))
        polar = spherical_ring_area(
            ring([0.0, 1.0, 1.0, 0.0], [80.0, 80.0, 81.0, 81.0])
        )

        assert polar < equator / 5

    def test_a_ring_straddling_the_antimeridian_needs_no_rotation(self):
        """Every Euclidean test in `scripts.hex_utils` needs one; taking each edge's
        longitude step the short way round is what spares this the same machinery."""
        across = spherical_ring_area(
            ring([179.0, -179.0, -179.0, 179.0], [0.0, 0.0, 1.0, 1.0])
        )
        elsewhere = spherical_ring_area(
            ring([10.0, 12.0, 12.0, 10.0], [0.0, 0.0, 1.0, 1.0])
        )

        assert across == pytest.approx(elsewhere, rel=1e-6)

    def test_a_cap_enclosing_a_pole_is_the_smaller_of_the_two_sides(self):
        """No rotation puts such a ring in a planar frame at all, and the ring divides
        the sphere in two rather than bounding one region."""
        cap = spherical_ring_area(
            ring(
                [-180.0, -90.0, 0.0, 90.0, 180.0],
                [80.0, 80.0, 80.0, 80.0, 80.0],
            )
        )
        expected = 2 * np.pi * (1 - np.sin(np.radians(80.0)))

        assert cap == pytest.approx(expected, rel=1e-6)
        assert cap < FULL_SPHERE / 2


SQUARE = ring([0.0, 2.0, 2.0, 0.0], [0.0, 0.0, 2.0, 2.0])
INNER = ring([0.5, 1.0, 1.0, 0.5], [0.5, 0.5, 1.0, 1.0])
FAR = ring([50.0, 51.0, 51.0, 50.0], [0.0, 0.0, 1.0, 1.0])
#: a speck sitting inside ``COVERED_CELL``: it overlaps the cell without covering it
SPECK = ring([0.62, 0.65, 0.65, 0.62], [0.62, 0.62, 0.65, 0.65])


def _data(polygons, poly_zone_ids, names, holes=None):
    holes = holes or {}
    return cast(
        "TimezoneData",
        SimpleNamespace(
            polygons=polygons,
            poly_zone_ids=np.array(poly_zone_ids, dtype=np.uint16),
            all_tz_names=names,
            nr_of_polygons=len(polygons),
            holes_in_poly=lambda poly_nr: iter(holes.get(poly_nr, [])),
            get_hex=lambda hex_id: _CELLS[hex_id],
        ),
    )


@pytest.mark.unit
class TestZoneAreas:
    def test_a_hole_is_taken_off_its_zone(self):
        data = _data([SQUARE], [0], ["A"], holes={0: [INNER]})

        areas = zone_areas(data)

        assert areas[0] == pytest.approx(
            spherical_ring_area(SQUARE) - spherical_ring_area(INNER), rel=1e-9
        )

    def test_a_zone_larger_than_a_hemisphere_is_refused(self):
        """The assumption `spherical_ring_area` makes when it picks a side of a
        pole-enclosing ring; nothing else would notice it stop holding."""
        hemisphere = ring([0.0, 90.0, 180.0, -90.0], [-90.0, 0.0, 90.0, 0.0])
        data = _data([hemisphere, hemisphere], [0, 0], ["A"])

        with pytest.raises(ValueError, match="more than the hemisphere"):
            zone_areas(data)

    def test_a_zone_its_holes_cancel_is_refused(self):
        data = _data([SQUARE], [0], ["A"], holes={0: [SQUARE]})

        with pytest.raises(ValueError, match="cannot be ordered"):
            zone_areas(data)


def _cell(hex_id: int, coords: np.ndarray) -> Hex:
    return Hex(
        id=hex_id,
        res=4,
        coords=coords,
        bounds=Boundaries(
            xmax=float(coords[0].max()),
            xmin=float(coords[0].min()),
            ymax=float(coords[1].max()),
            ymin=float(coords[1].min()),
        ),
        x_overflow=False,
        surr_n_pole=False,
        surr_s_pole=False,
        data=cast("TimezoneData", None),
    )


#: a cell sitting well inside ``INNER``, and therefore inside ``SQUARE`` too
COVERED_CELL = _cell(1, ring([0.6, 0.7, 0.7, 0.6], [0.6, 0.6, 0.7, 0.7]))
#: a cell straddling ``INNER``'s edge: inside ``SQUARE``, only half inside ``INNER``
STRADDLING_CELL = _cell(2, ring([0.9, 1.1, 1.1, 0.9], [0.6, 0.6, 0.7, 0.7]))
_CELLS = {1: COVERED_CELL, 2: STRADDLING_CELL}


@pytest.mark.unit
class TestResolveCoveredCells:
    """`SQUARE` (zone A) wholly contains `INNER` (zone B), so B is the enclave."""

    NAMES = ["A", "B"]

    def _data(self):
        data = _data([SQUARE, INNER], [0, 1], self.NAMES)
        for cell in _CELLS.values():
            cell.data = data
        return data

    def test_the_enclave_takes_a_cell_both_zones_cover(self):
        resolved = resolve_covered_cells(self._data(), {1: [0, 1]})

        assert resolved == {1: 1}

    def test_a_cell_the_enclave_only_reaches_into_keeps_its_candidates(self):
        """The coverer is the larger zone here, and the smaller one takes precedence
        in the part of the cell it reaches - so no single zone answers the whole cell."""
        resolved = resolve_covered_cells(self._data(), {2: [0, 1]})

        assert resolved == {}

    def test_a_cell_no_polygon_covers_keeps_its_candidates(self):
        """One candidate is disjoint from the cell, the other sits inside it - the
        cell is ambiguous and geometry is the only thing that can answer it."""
        data = _data([FAR, SPECK], [0, 1], self.NAMES)
        for cell in _CELLS.values():
            cell.data = data

        assert resolve_covered_cells(data, {1: [0, 1]}) == {}

    def test_a_single_zone_cell_is_left_to_the_unique_mapping(self):
        """`compute_unique_shortcut_mapping` already answers it, and re-deriving the
        answer here would run the coverage geometry over 89 % of the index for nothing."""
        data = _data([SQUARE, INNER], [0, 0], ["A"])
        for cell in _CELLS.values():
            cell.data = data

        assert resolve_covered_cells(data, {1: [0, 1]}) == {}
