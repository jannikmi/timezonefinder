#!/usr/bin/env python3

"""Price longitude/latitude-aligned shortcut indices against shipped H3.

PRELIMINARY FINDINGS (2026-09-26, Apple arm64, Python 3.14.2, data 2026d)
============================================================================

**These numbers do not close the comparison.**  TOOL-7 still needs the maintainer's
cross-zone tie rule, and this prototype uses numeric zone id only as a deterministic
placeholder.  That rule is explicitly forbidden as answer semantics.  The prototype
and its compact output are retained so the expensive geometry compilation need not be
re-derived, but the whole correctness and timing run must be repeated after TOOL-7
lands before a verdict is recorded in the shortcut-index decisions.

No measured candidate clears every constraint so far.  The only single-level grid
smaller than the shipped 617,109-byte payload is 0.5 degrees (548,090 bytes), but it
turns fewer random/on-land queries into direct answers and makes scalar
``timezone_at`` 6.7--8.5% slower on both clang and numba.  Its vectorised batch lookup
is 30.8--46.9% faster, which proves that removing H3's scalar-per-point conversion is a
real batch opportunity, but the item requires a replacement rather than a scalar
regression bought for one API.

The finer grids reverse the selectivity result.  The 0.36-degree and equal-area
variants answer 91.6/91.9% of random queries directly against H3's 89.4%, and reduce
candidate polygons per random query from 0.219 to 0.173/0.166.  Their scalar random
result is no difference or unresolved and their on-land result is 3.3--6.7% faster;
batch calls are 45.4--63.5% faster.  Both fail the non-negotiable footprint constraint:
their payloads are 1,030,792 and 1,036,724 bytes, 67--68% above H3.

Exactly nesting tiles do not rescue the exchange in this Python runtime.  Sorted sparse
z3--z10 keys plus a 1-degree fallback take 704,830 bytes, and eight mapped-array probes
make scalar calls about 12x and batches 14--17x slower.  The independent two-tier split
(a dense 0.5-degree exact layer plus the same fallback) takes 677,008 bytes, offers
coarser lists on misses, and is 17.8--20.3% slower for scalar calls.  Native tzf timings
therefore cannot be transferred to this reader.

Under the placeholder order, all five candidates agreed with the shipped answer over all 30,000 committed fixture
points and passed the Strait of Malacca edge-crossing witness before timing.  Timings
were paired and order-alternated: 31 rounds x 2,000 scalar inputs, and 31 rounds x eight
256-point public batch calls, on both backends.  Only random and on-land rank an index;
the H3 unique/ambiguous fixtures are retained as correctness probes because their class
changes with the index.  The compact evidence is committed under
``contributing/improvements/measurements/latlng-index-2026-09-26.json`` and is marked
provisional there as well.

This is a prototype, not runtime code.  Its packed arrays model a mapped-capable file;
the query adapters keep all other lookup work on the real ``TimezoneFinder`` path.
"""

from __future__ import annotations

import argparse
import json
import math
import platform
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterator, Sequence

import numpy as np
from h3.api import numpy_int as h3
from shapely import Polygon, box
from shapely.strtree import STRtree

from benchmarks.candidate_comparison import CandidateComparison, compare_candidates
from scripts.assert_acceleration_path import (
    PACKED_ACCELERATION_IMPLEMENTATIONS,
    PACKED_BUFFER_FACTORIES,
    interpreted_path_name,
)
from tests.auxiliaries import (
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
    ON_LAND_POINTS_FIXTURE,
    RANDOM_POINTS_FIXTURE,
    UNIQUE_SHORTCUT_POINTS_FIXTURE,
    benchmark_fixture_provenance,
    load_benchmark_points,
)
from timezonefinder import TimezoneFinder, utils
from timezonefinder.configs import (
    DEFAULT_DATA_DIR,
    NO_ZONE_ID,
    SHORTCUT_H3_RES,
    ZONE_ID_RESULT_DTYPE,
)
from timezonefinder.shortcut_index import ABSENT, get_shortcut_file_path


STRATA = {
    "random": RANDOM_POINTS_FIXTURE,
    "on_land": ON_LAND_POINTS_FIXTURE,
    # These remain useful correctness/work-shape probes, but are H3 classifications and
    # therefore must not rank a replacement index.
    "h3_unique": UNIQUE_SHORTCUT_POINTS_FIXTURE,
    "h3_ambiguous": AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
}
MALACCA_WITNESS = (100.3055, 3.4804)
WEB_MERCATOR_LIMIT = 85.0511287798066
ABSENT_KEY = np.uint32(np.iinfo(np.uint32).max)


def _smallest_uint(maximum: int) -> np.dtype:
    if maximum <= np.iinfo(np.uint8).max:
        return np.dtype(np.uint8)
    if maximum <= np.iinfo(np.uint16).max:
        return np.dtype(np.uint16)
    return np.dtype(np.uint32)


def _comparison(result: CandidateComparison) -> dict[str, object]:
    return {**asdict(result), "verdict": result.verdict}


@dataclass
class PackedEntries:
    """The part shared by every candidate: int16 answers and deduplicated lists."""

    table: np.ndarray
    starts: np.ndarray
    ends: np.ndarray
    last_change: np.ndarray
    payload: np.ndarray

    def candidates_of(self, entry: int) -> np.ndarray:
        idx = -(entry + 2)
        return self.payload[self.starts[idx] : self.ends[idx]]

    def stop_index_of(self, entry: int) -> int:
        return int(self.last_change[-(entry + 2)])

    @property
    def resident_bytes(self) -> int:
        return sum(a.nbytes for a in asdict(self).values())

    @property
    def payload_bytes(self) -> int:
        """Compact file-size model using the narrowest sufficient entry columns."""
        nr_entries = len(self.last_change)
        max_offset = int(self.ends[-1]) if nr_entries else 0
        max_length = (
            int(np.max(self.ends.astype(np.int64) - self.starts)) if nr_entries else 0
        )
        return (
            self.table.nbytes
            + nr_entries * _smallest_uint(max_offset).itemsize
            + nr_entries * _smallest_uint(max_length).itemsize
            + nr_entries * _smallest_uint(max_length).itemsize
            + self.payload.nbytes
        )


def _last_change(zones: np.ndarray) -> int:
    final = int(zones[-1])
    i = len(zones) - 1
    while i >= 0 and int(zones[i]) == final:
        i -= 1
    return i + 1


def _order_candidates(
    polygon_ids: np.ndarray, zone_ids: np.ndarray, vertices: np.ndarray
) -> np.ndarray:
    """Legacy work order with a provisional deterministic cross-zone tie-break.

    Numeric zone id is not acceptable answer semantics.  It exists here only so the
    blocked prototype emits repeatable preliminary evidence; replace it with TOOL-7's
    eventual recorded rule, then rerun every gate and timing before drawing a verdict.
    """
    ids = sorted(int(v) for v in polygon_ids)
    buckets: dict[int, list[int]] = {}
    sizes: dict[int, int] = {}
    for polygon_id in ids:
        zone_id = int(zone_ids[polygon_id])
        buckets.setdefault(zone_id, []).append(polygon_id)
        sizes[zone_id] = sizes.get(zone_id, 0) + int(vertices[polygon_id])
    ordered: list[int] = []
    for zone_id in sorted(buckets, key=lambda z: (sizes[z], z)):
        ordered.extend(sorted(buckets[zone_id], key=lambda p: (vertices[p], p)))
    return np.asarray(ordered, dtype=np.uint16)


class EntryBuilder:
    def __init__(self, zone_ids: np.ndarray, vertices: np.ndarray):
        self.zone_ids = zone_ids
        self.vertices = vertices
        self.table: list[int] = []
        self.entry_of: dict[bytes, int] = {}
        self.payloads: list[np.ndarray] = []
        self.last_change: list[int] = []

    def add(self, polygon_ids: np.ndarray) -> None:
        if len(polygon_ids) == 0:
            self.table.append(ABSENT)
            return
        zones = np.unique(self.zone_ids[polygon_ids])
        if len(zones) == 1:
            self.table.append(int(zones[0]))
            return
        ordered = _order_candidates(polygon_ids, self.zone_ids, self.vertices)
        key = ordered.tobytes()
        idx = self.entry_of.get(key)
        if idx is None:
            idx = len(self.payloads)
            self.entry_of[key] = idx
            self.payloads.append(ordered)
            self.last_change.append(_last_change(self.zone_ids[ordered]))
        self.table.append(-(idx + 2))

    def finish(self) -> PackedEntries:
        lengths = np.asarray([len(v) for v in self.payloads], dtype=np.uint32)
        ends = np.cumsum(lengths, dtype=np.uint32)
        starts = np.concatenate((np.zeros(1, dtype=np.uint32), ends[:-1]))
        payload = (
            np.concatenate(self.payloads).astype(np.uint16, copy=False)
            if self.payloads
            else np.empty(0, dtype=np.uint16)
        )
        return PackedEntries(
            table=np.asarray(self.table, dtype=np.int16),
            starts=starts,
            ends=ends,
            last_change=np.asarray(
                self.last_change,
                dtype=_smallest_uint(int(lengths.max()) if len(lengths) else 0),
            ),
            payload=payload,
        )


@dataclass
class GridIndex:
    name: str
    entries: PackedEntries
    row_offsets: np.ndarray
    columns: np.ndarray

    @property
    def rows(self) -> int:
        return len(self.columns)

    def entries_of(self, lngs: np.ndarray, lats: np.ndarray) -> np.ndarray:
        rows = np.floor((lats + 90.0) * self.rows / 180.0).astype(np.int64)
        np.clip(rows, 0, self.rows - 1, out=rows)
        counts = self.columns[rows].astype(np.int64)
        cols = np.floor((lngs + 180.0) * counts / 360.0).astype(np.int64)
        np.clip(cols, 0, counts - 1, out=cols)
        return self.entries.table[self.row_offsets[rows] + cols]

    def entry_of(self, lng: float, lat: float) -> int:
        row = min(self.rows - 1, max(0, int((lat + 90.0) * self.rows / 180.0)))
        count = int(self.columns[row])
        col = min(count - 1, max(0, int((lng + 180.0) * count / 360.0)))
        return int(self.entries.table[int(self.row_offsets[row]) + col])

    def candidates_of(self, entry: int) -> np.ndarray:
        return self.entries.candidates_of(entry)

    def stop_index_of(self, entry: int) -> int:
        return self.entries.stop_index_of(entry)

    @property
    def resident_bytes(self) -> int:
        return (
            self.entries.resident_bytes + self.row_offsets.nbytes + self.columns.nbytes
        )

    @property
    def payload_bytes(self) -> int:
        return (
            self.entries.payload_bytes + self.row_offsets.nbytes + self.columns.nbytes
        )


def _cell_boxes(row: int, rows: int, columns: int) -> np.ndarray:
    south = -90.0 + 180.0 * row / rows
    north = -90.0 + 180.0 * (row + 1) / rows
    edges = np.linspace(-180.0, 180.0, columns + 1)
    return box(edges[:-1], south, edges[1:], north)


def build_grid(
    name: str,
    columns: np.ndarray,
    tree: STRtree,
    zone_ids: np.ndarray,
    vertices: np.ndarray,
) -> GridIndex:
    builder = EntryBuilder(zone_ids, vertices)
    for row, count in enumerate(columns.tolist()):
        pairs = tree.query(
            _cell_boxes(row, len(columns), count), predicate="intersects"
        )
        by_cell = np.split(pairs[1], np.searchsorted(pairs[0], np.arange(1, count)))
        for polygon_ids in by_cell:
            builder.add(polygon_ids)
    offsets = np.concatenate(
        (np.zeros(1, dtype=np.int32), np.cumsum(columns[:-1], dtype=np.int32))
    )
    return GridIndex(name, builder.finish(), offsets, columns.astype(np.int32))


@dataclass
class NestedIndex:
    name: str
    fallback: GridIndex
    keys: dict[int, np.ndarray]
    values: dict[int, np.ndarray]

    @staticmethod
    def _xy(lng: float, lat: float, zoom: int) -> tuple[int, int]:
        scale = 1 << zoom
        x = min(scale - 1, max(0, int((lng + 180.0) / 360.0 * scale)))
        rad = math.radians(lat)
        y = min(
            scale - 1,
            max(0, int((1.0 - math.asinh(math.tan(rad)) / math.pi) / 2.0 * scale)),
        )
        return x, y

    def entry_of(self, lng: float, lat: float) -> int:
        if -WEB_MERCATOR_LIMIT <= lat <= WEB_MERCATOR_LIMIT:
            for zoom in sorted(self.keys):
                x, y = self._xy(lng, lat, zoom)
                key = (x << zoom) | y
                pos = int(np.searchsorted(self.keys[zoom], key))
                if pos < len(self.keys[zoom]) and int(self.keys[zoom][pos]) == key:
                    return int(self.values[zoom][pos])
        return self.fallback.entry_of(lng, lat)

    def entries_of(self, lngs: np.ndarray, lats: np.ndarray) -> np.ndarray:
        # The prototype's mapped-capable representation is sparse sorted arrays.  A
        # scalar loop honestly includes those repeated probes; the fallback is still
        # vectorised as a single dense-grid gather.
        out = self.fallback.entries_of(lngs, lats).copy()
        for i, (lng, lat) in enumerate(zip(lngs.tolist(), lats.tolist(), strict=True)):
            if -WEB_MERCATOR_LIMIT <= lat <= WEB_MERCATOR_LIMIT:
                for zoom in sorted(self.keys):
                    x, y = self._xy(lng, lat, zoom)
                    key = (x << zoom) | y
                    pos = int(np.searchsorted(self.keys[zoom], key))
                    if pos < len(self.keys[zoom]) and int(self.keys[zoom][pos]) == key:
                        out[i] = self.values[zoom][pos]
                        break
        return out

    def candidates_of(self, entry: int) -> np.ndarray:
        return self.fallback.candidates_of(entry)

    def stop_index_of(self, entry: int) -> int:
        return self.fallback.stop_index_of(entry)

    @property
    def resident_bytes(self) -> int:
        return self.payload_bytes

    @property
    def payload_bytes(self) -> int:
        return self.fallback.payload_bytes + sum(
            self.keys[z].nbytes + self.values[z].nbytes for z in self.keys
        )


@dataclass
class TwoTierIndex:
    """A dense exact-zone layer in front of a separate coarse candidate grid."""

    name: str
    exact: GridIndex
    fallback: GridIndex

    def entry_of(self, lng: float, lat: float) -> int:
        entry = self.exact.entry_of(lng, lat)
        return entry if entry >= 0 else self.fallback.entry_of(lng, lat)

    def entries_of(self, lngs: np.ndarray, lats: np.ndarray) -> np.ndarray:
        exact = self.exact.entries_of(lngs, lats)
        unresolved = exact < 0
        if unresolved.any():
            exact = exact.copy()
            exact[unresolved] = self.fallback.entries_of(
                lngs[unresolved], lats[unresolved]
            )
        return exact

    def candidates_of(self, entry: int) -> np.ndarray:
        return self.fallback.candidates_of(entry)

    def stop_index_of(self, entry: int) -> int:
        return self.fallback.stop_index_of(entry)

    @property
    def resident_bytes(self) -> int:
        return (
            self.exact.entries.table.nbytes
            + self.exact.row_offsets.nbytes
            + self.exact.columns.nbytes
            + self.fallback.resident_bytes
        )

    @property
    def payload_bytes(self) -> int:
        return (
            self.exact.entries.table.nbytes
            + self.exact.row_offsets.nbytes
            + self.exact.columns.nbytes
            + self.fallback.payload_bytes
        )


def _mercator_boxes(zoom: int, tiles: np.ndarray) -> np.ndarray:
    scale = 1 << zoom
    x = tiles[:, 0]
    y = tiles[:, 1]
    west = x / scale * 360.0 - 180.0
    east = (x + 1) / scale * 360.0 - 180.0
    north = np.degrees(np.arctan(np.sinh(np.pi * (1.0 - 2.0 * y / scale))))
    south = np.degrees(np.arctan(np.sinh(np.pi * (1.0 - 2.0 * (y + 1) / scale))))
    return box(west, south, east, north)


def build_nested(
    fallback: GridIndex,
    tree: STRtree,
    zone_ids: np.ndarray,
    *,
    min_zoom: int = 3,
    max_zoom: int = 10,
) -> NestedIndex:
    frontier = np.asarray(
        [(x, y) for x in range(1 << min_zoom) for y in range(1 << min_zoom)],
        dtype=np.int32,
    )
    keys: dict[int, np.ndarray] = {}
    values: dict[int, np.ndarray] = {}
    for zoom in range(min_zoom, max_zoom + 1):
        pairs = tree.query(_mercator_boxes(zoom, frontier), predicate="intersects")
        groups = np.split(
            pairs[1], np.searchsorted(pairs[0], np.arange(1, len(frontier)))
        )
        exact_keys: list[int] = []
        exact_values: list[int] = []
        ambiguous: list[tuple[int, int]] = []
        for (x, y), polygon_ids in zip(frontier.tolist(), groups, strict=True):
            zones = np.unique(zone_ids[polygon_ids]) if len(polygon_ids) else ()
            if len(zones) == 1:
                exact_keys.append((x << zoom) | y)
                exact_values.append(int(zones[0]))
            elif zoom < max_zoom:
                ambiguous.append((x, y))
        order = np.argsort(exact_keys)
        keys[zoom] = np.asarray(exact_keys, dtype=np.uint32)[order]
        values[zoom] = np.asarray(exact_values, dtype=np.int16)[order]
        if zoom < max_zoom:
            frontier = np.asarray(
                [
                    (2 * x + dx, 2 * y + dy)
                    for x, y in ambiguous
                    for dx in (0, 1)
                    for dy in (0, 1)
                ],
                dtype=np.int32,
            )
    return NestedIndex("nested_z3_z10_plus_1deg", fallback, keys, values)


class CandidateFinder:
    """Whole public-call adapter using a candidate index and real geometry backend."""

    def __init__(
        self, finder: TimezoneFinder, index: GridIndex | NestedIndex | TwoTierIndex
    ):
        self.finder = finder
        self.index = index

    def timezone_at(self, *, lng: float, lat: float) -> str | None:
        lng, lat = utils.validate_coordinates(lng, lat)
        entry = self.index.entry_of(lng, lat)
        if entry >= 0:
            return self.finder.zone_names.name_of(entry)
        if entry == ABSENT:
            return None
        zone = self.finder._zone_id_among(
            self.index.candidates_of(entry), self.index.stop_index_of(entry), lng, lat
        )
        return self.finder.zone_names.name_of(zone)

    def timezone_ids_at(
        self, *, lngs: Sequence[float], lats: Sequence[float]
    ) -> np.ndarray:
        lng_array, lat_array = utils.coordinate_arrays(lngs, lats)
        invalid = utils.out_of_bounds(lng_array, lat_array)
        if invalid.any():
            first = int(np.argmax(invalid))
            raise ValueError(f"invalid coordinate at index {first}")
        entries = self.index.entries_of(lng_array, lat_array)
        out = np.where(entries >= 0, entries, NO_ZONE_ID).astype(ZONE_ID_RESULT_DTYPE)
        positions = np.flatnonzero(entries < ABSENT)
        prepared: dict[int, tuple[np.ndarray, int]] = {}
        for i, entry, lng, lat in zip(
            positions.tolist(),
            entries[positions].tolist(),
            lng_array[positions].tolist(),
            lat_array[positions].tolist(),
            strict=True,
        ):
            cell = prepared.get(entry)
            if cell is None:
                cell = (
                    self.index.candidates_of(entry),
                    self.index.stop_index_of(entry),
                )
                prepared[entry] = cell
            out[i] = self.finder._zone_id_among(*cell, lng, lat)
        return out


@contextmanager
def _bound(path: str) -> Iterator[None]:
    previous = (utils.inside_polygon_packed, utils.packed_buffers)
    utils.inside_polygon_packed = PACKED_ACCELERATION_IMPLEMENTATIONS[path]
    utils.packed_buffers = PACKED_BUFFER_FACTORIES[path]
    try:
        yield
    finally:
        utils.inside_polygon_packed, utils.packed_buffers = previous


def _finder_on(path: str) -> TimezoneFinder:
    with _bound(path):
        return TimezoneFinder(in_memory=False)


def _geometries(finder: TimezoneFinder) -> list[Polygon]:
    geometries = []
    for boundary_id in range(len(finder.boundaries)):
        outer = finder.boundaries.coords_of(boundary_id).T / 10_000_000
        holes = [
            finder.holes.coords_of(hole_id).T / 10_000_000
            for hole_id in finder.holes.ids_of(boundary_id)
        ]
        geometry = Polygon(outer, holes)
        if not geometry.is_valid:
            raise ValueError(
                f"invalid source polygon {boundary_id}: {geometry.is_valid_reason}"
            )
        geometries.append(geometry)
    return geometries


def _stats(
    index: GridIndex | NestedIndex | TwoTierIndex,
    points: Sequence[tuple[float, float]],
) -> dict[str, float | int]:
    unique = 0
    candidates = 0
    for lng, lat in points:
        entry = index.entry_of(lng, lat)
        if entry >= 0:
            unique += 1
        elif entry < ABSENT:
            candidates += len(index.candidates_of(entry))
    return {
        "points": len(points),
        "unique": unique,
        "unique_share": unique / len(points),
        "candidate_polygons": candidates,
        "candidates_per_query": candidates / len(points),
    }


def _h3_stats(
    finder: TimezoneFinder, points: Sequence[tuple[float, float]]
) -> dict[str, float | int]:
    unique = 0
    candidates = 0
    for lng, lat in points:
        entry = finder.shortcuts.entry_of(h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES))
        if entry >= 0:
            unique += 1
        elif entry < ABSENT:
            candidates += len(finder.shortcuts.candidates_of(entry))
    return {
        "points": len(points),
        "unique": unique,
        "unique_share": unique / len(points),
        "candidate_polygons": candidates,
        "candidates_per_query": candidates / len(points),
    }


def _check(
    shipped: TimezoneFinder,
    candidate: CandidateFinder,
    points: Sequence[tuple[float, float]],
) -> int:
    lngs = np.asarray([p[0] for p in points])
    lats = np.asarray([p[1] for p in points])
    expected = shipped.timezone_ids_at(lngs=lngs, lats=lats)
    actual = candidate.timezone_ids_at(lngs=lngs, lats=lats)
    return int(np.count_nonzero(expected != actual))


def _scalar_call(finder: object) -> Callable[[tuple[float, float]], object]:
    return lambda point: finder.timezone_at(lng=point[0], lat=point[1])


def _batch_call(finder: object) -> Callable[[tuple[np.ndarray, np.ndarray]], object]:
    return lambda batch: finder.timezone_ids_at(lngs=batch[0], lats=batch[1])


def _batches(
    points: Sequence[tuple[float, float]], size: int = 256
) -> list[tuple[np.ndarray, np.ndarray]]:
    result = []
    for start in range(0, len(points), size):
        chunk = points[start : start + size]
        result.append(
            (
                np.asarray([p[0] for p in chunk], dtype=np.float64),
                np.asarray([p[1] for p in chunk], dtype=np.float64),
            )
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--rounds", type=int, default=31)
    parser.add_argument("--points", type=int, default=2_000)
    parser.add_argument("--no-timing", action="store_true")
    args = parser.parse_args()

    started = time.perf_counter()
    geometry_finder = _finder_on("clang")
    geometries = _geometries(geometry_finder)
    tree = STRtree(geometries)
    zone_ids = geometry_finder.zone_ids
    vertices = geometry_finder.boundaries.nr_vertices

    half_degree = np.full(360, 720, dtype=np.int32)
    point36 = np.full(500, 1_000, dtype=np.int32)
    equal_area_rows = 628
    lat_mid = -90.0 + (np.arange(equal_area_rows) + 0.5) * 180.0 / equal_area_rows
    equal_area = np.maximum(
        1,
        np.rint(360.0 * np.cos(np.radians(lat_mid)) / (180.0 / equal_area_rows)),
    ).astype(np.int32)
    coarse = np.full(180, 360, dtype=np.int32)

    indices: list[GridIndex | NestedIndex] = []
    for name, columns in (
        ("equal_angle_0_5deg", half_degree),
        ("equal_angle_0_36deg", point36),
        ("equal_area_500k", equal_area),
    ):
        print(f"building {name} ...", flush=True)
        indices.append(build_grid(name, columns, tree, zone_ids, vertices))
    print("building nested z3-z10 + 1deg fallback ...", flush=True)
    fallback = build_grid("coarse_1deg", coarse, tree, zone_ids, vertices)
    indices.append(build_nested(fallback, tree, zone_ids))
    indices.append(TwoTierIndex("two_tier_0_5deg_plus_1deg", indices[0], fallback))

    fixtures = {
        label: load_benchmark_points(fixture) for label, fixture in STRATA.items()
    }
    report: dict[str, object] = {
        "schema": 1,
        "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "platform": {
            "python": platform.python_version(),
            "machine": platform.machine(),
        },
        "fixture": benchmark_fixture_provenance(),
        "shipped": {
            "payload_bytes": get_shortcut_file_path(DEFAULT_DATA_DIR).stat().st_size,
            "resident_bytes": sum(
                array.nbytes
                for array in (
                    geometry_finder.shortcuts.table,
                    geometry_finder.shortcuts.starts,
                    geometry_finder.shortcuts.ends,
                    geometry_finder.shortcuts.last_change,
                    geometry_finder.shortcuts.payload,
                )
            ),
            "strata": {
                label: _h3_stats(geometry_finder, points)
                for label, points in fixtures.items()
            },
        },
        "candidates": {},
    }

    malacca_lng, malacca_lat = MALACCA_WITNESS
    malacca_x = utils.coord2int(malacca_lng)
    malacca_y = utils.coord2int(malacca_lat)
    malacca_polygons = [
        boundary_id
        for boundary_id in range(len(geometry_finder.boundaries))
        if geometry_finder.inside_of_polygon(boundary_id, malacca_x, malacca_y)
    ]
    if not malacca_polygons:
        raise AssertionError(
            "the Malacca edge-crossing witness is in no source polygon"
        )
    malacca_zones = {int(zone_ids[boundary_id]) for boundary_id in malacca_polygons}
    for index in indices:
        adapter = CandidateFinder(geometry_finder, index)
        entry = index.entry_of(malacca_lng, malacca_lat)
        offered = index.candidates_of(entry).tolist() if entry < ABSENT else []
        correctness = {
            label: _check(geometry_finder, adapter, points)
            for label, points in fixtures.items()
        }
        correctness["malacca_answer"] = int(
            adapter.timezone_at(lng=malacca_lng, lat=malacca_lat)
            == geometry_finder.timezone_at(lng=malacca_lng, lat=malacca_lat)
        )
        correctness["malacca_containing_polygon_offered"] = int(
            (entry >= 0 and entry in malacca_zones)
            or any(boundary_id in offered for boundary_id in malacca_polygons)
        )
        report["candidates"][index.name] = {
            "payload_bytes": index.payload_bytes,
            "resident_bytes": index.resident_bytes,
            "cells": len(index.entries.table) if isinstance(index, GridIndex) else None,
            "strata": {
                label: _stats(index, points) for label, points in fixtures.items()
            },
            "correctness": correctness,
            "timing": {},
        }

    failures = {
        name: data["correctness"]
        for name, data in report["candidates"].items()
        if any(
            value != 0 for key, value in data["correctness"].items() if key in STRATA
        )
        or not data["correctness"]["malacca_answer"]
        or not data["correctness"]["malacca_containing_polygon_offered"]
    }
    if failures:
        print(json.dumps(report, indent=2))
        raise SystemExit(f"correctness gate refused timing: {failures}")

    if not args.no_timing:
        paths = ("clang", interpreted_path_name())
        for path in paths:
            print(f"timing {path} ...", flush=True)
            shipped = _finder_on(path)
            try:
                for index in indices:
                    candidate = CandidateFinder(shipped, index)
                    timing = report["candidates"][index.name]["timing"]
                    timing[path] = {}
                    for label, all_points in fixtures.items():
                        points = all_points[: args.points]
                        scalar = compare_candidates(
                            ("h3", _scalar_call(shipped)),
                            (index.name, _scalar_call(candidate)),
                            points,
                            rounds=args.rounds,
                            batch_size=min(len(points), 2_000),
                        )
                        batches = _batches(points)
                        batch = compare_candidates(
                            ("h3", _batch_call(shipped)),
                            (index.name, _batch_call(candidate)),
                            batches,
                            rounds=args.rounds,
                            batch_size=min(len(batches), 8),
                        )
                        timing[path][label] = {
                            "scalar": _comparison(scalar),
                            "batch_256": _comparison(batch),
                        }
            finally:
                shipped.cleanup()

    report["elapsed_seconds"] = time.perf_counter() - started
    rendered = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered)
        print(f"wrote {args.output}")
    else:
        print(rendered)
    geometry_finder.cleanup()


if __name__ == "__main__":
    main()
