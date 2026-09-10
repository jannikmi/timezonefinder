"""Find sampled shortcut omissions without using shortcut geometry as the oracle.

Run with ``uv run python -m scripts.audit_shortcut_candidates --output tmp/audit.json``.
The default probes every resolution-4 cell's vertices and both sides of spherical
edge midpoints. ``--mode source-edges`` probes stored ring vertices and planar edge
midpoints; ``--mode seams`` probes poles and both antimeridian representations.
``--points`` replays a JSON array of [longitude, latitude] pairs instead.

Only full polygon containment (including holes), independently of the shortcut,
can establish an omission. The oracle shares the runtime polygon kernel: this is
an audit of candidate selection, not of that kernel. Sampling cannot certify cell
coverage, and neither midpoints nor the perturbation below justify an exclusion.
Exit 1 means omissions were found, even when another candidate gives the same zone.
"""

import argparse
import hashlib
import itertools
import json
import math
import platform
import time
from collections.abc import Iterable, Iterator
from pathlib import Path

import h3.api.basic_int as h3
import numpy as np

from scripts.assert_acceleration_path import active_acceleration_path
from scripts.configs import SOURCE_DATA_DIR
from scripts.utils import write_json
from timezonefinder import TimezoneFinder
from timezonefinder.configs import COORD2INT_FACTOR, SHORTCUT_H3_RES
from timezonefinder.utils import coord2int


def cell_edge_points(cells: Iterable[int]) -> Iterator[tuple[float, float]]:
    """Probe reported vertices and spherical midpoints nudged toward/away from center."""
    for cell in cells:
        boundary = np.radians(h3.cell_to_boundary(cell))
        lat, lng = boundary.T
        vertices = np.array(
            [np.cos(lat) * np.cos(lng), np.cos(lat) * np.sin(lng), np.sin(lat)]
        ).T
        clat, clng = np.radians(h3.cell_to_latlng(cell))
        center = np.array(
            [np.cos(clat) * np.cos(clng), np.cos(clat) * np.sin(clng), np.sin(clat)]
        )
        mids = vertices + np.roll(vertices, -1, axis=0)
        mids /= np.linalg.norm(mids, axis=1)[:, None]
        for lat_deg, lng_deg in h3.cell_to_boundary(cell):
            yield lng_deg, lat_deg
        for direction in (-1, 1):
            probes = mids + direction * 1e-7 * center
            probes /= np.linalg.norm(probes, axis=1)[:, None]
            for vec in probes:
                yield (
                    float(np.degrees(np.arctan2(vec[1], vec[0]))),
                    float(np.degrees(np.arctan2(vec[2], np.hypot(vec[0], vec[1])))),
                )


def source_edge_points(finder: TimezoneFinder) -> Iterator[tuple[float, float]]:
    """Keep source segments in their original longitude frame, including holes."""
    for collection in (finder.boundaries, finder.holes):
        for polygon in range(len(collection)):
            ring = collection.coords_of(polygon).astype(np.float64)
            for point in ring.T:
                yield query_coordinate(point[0]), query_coordinate(point[1])
            mids = (ring + np.roll(ring, -1, axis=1)) / 2
            for point in mids.T:
                yield query_coordinate(point[0]), query_coordinate(point[1])


def query_coordinate(scaled: float) -> float:
    """Represent a source-grid query without a divide/multiply truncation slip."""
    expected = int(scaled)
    coordinate = float(scaled / COORD2INT_FACTOR)
    actual = coord2int(coordinate)
    if actual != expected:
        coordinate = math.nextafter(
            coordinate, math.inf if expected > actual else -math.inf
        )
    if coord2int(coordinate) != expected:
        raise ValueError(f"cannot represent source coordinate: {scaled}")
    return coordinate


def seam_points() -> Iterator[tuple[float, float]]:
    for lng in range(-180, 181, 15):
        for lat in (-90, 90):
            yield float(lng), float(lat)
    for lat in range(-90, 91, 5):
        for lng in (-180, 180):
            yield float(lng), float(lat)


def omission_at(
    finder: TimezoneFinder, lng: float, lat: float
) -> dict[str, object] | None:
    """Compare all bbox-eligible polygons with the query's actual shortcut entry."""
    if not (math.isfinite(lng) and -180 <= lng <= 180):
        raise ValueError(f"invalid longitude: {lng}")
    if not (math.isfinite(lat) and -90 <= lat <= 90):
        raise ValueError(f"invalid latitude: {lat}")
    x, y = coord2int(lng), coord2int(lat)
    bounds = finder.boundaries
    eligible = np.flatnonzero(
        (bounds.xmin <= x)
        & (bounds.xmax >= x)
        & (bounds.ymin <= y)
        & (bounds.ymax >= y)
    )
    candidates = set(finder._iter_boundaries_in_shortcut(lng=lng, lat=lat))
    missing = [
        int(poly)
        for poly in eligible
        if poly not in candidates and finder.inside_of_polygon(poly, x, y)
    ]
    if not missing:
        return None
    containing = [
        int(poly) for poly in eligible if finder.inside_of_polygon(poly, x, y)
    ]
    names = sorted({finder.zone_name_from_boundary_id(poly) for poly in containing})
    answer = finder.timezone_at(lng=lng, lat=lat)
    return {
        "longitude": lng,
        "latitude": lat,
        "integer_coordinates": [x, y],
        "cell": hex(h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES)),
        "missing_polygon_ids": missing,
        "candidate_polygon_ids": sorted(int(poly) for poly in candidates),
        "containing_polygon_ids": containing,
        "containing_zones": names,
        "timezone_at": answer,
        "answer_outside_containing_zones": answer not in names,
    }


def audit_points(
    finder: TimezoneFinder,
    points: Iterable[tuple[float, float]],
    *,
    max_points: int | None = None,
    witness_limit: int = 100,
) -> dict[str, object]:
    """Count every omission, retaining a bounded number of replayable witnesses."""
    if max_points is not None and max_points <= 0:
        raise ValueError("max_points must be positive")
    if witness_limit <= 0:
        raise ValueError("witness_limit must be positive")
    checked = missing_points = wrong_answers = 0
    witnesses: list[dict[str, object]] = []
    complete = True
    for lng, lat in points:
        if max_points is not None and checked == max_points:
            complete = False
            break
        checked += 1
        finding = omission_at(finder, lng, lat)
        if finding is None:
            continue
        missing_points += 1
        wrong_answers += int(bool(finding["answer_outside_containing_zones"]))
        if len(witnesses) < witness_limit:
            witnesses.append(finding)
    if checked == 0:
        raise ValueError("audit contains no points")
    return {
        "points_checked": checked,
        "sample_stream_exhausted": complete,
        "points_with_omissions": missing_points,
        "answers_outside_containing_zones_at_omissions": wrong_answers,
        "witnesses": witnesses,
        "witnesses_truncated": missing_points > len(witnesses),
        "completeness_proven": False,
    }


def data_hashes(data_dir: Path) -> dict[str, str]:
    """Identify the actual bytes, including regenerated data with an unchanged tag."""
    return {
        path.relative_to(data_dir).as_posix(): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in sorted(data_dir.rglob("*"))
        if path.is_file()
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=SOURCE_DATA_DIR)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--points", type=Path, help="JSON array of [longitude, latitude]"
    )
    parser.add_argument(
        "--mode", choices=("cell-edges", "source-edges", "seams"), default="cell-edges"
    )
    parser.add_argument("--max-points", type=int)
    parser.add_argument("--witness-limit", type=int, default=100)
    args = parser.parse_args(argv)
    started = time.perf_counter()
    finder = TimezoneFinder(bin_file_location=args.data_dir, in_memory=True)
    try:
        points: Iterable[tuple[float, float]]
        if args.points:
            points = json.loads(args.points.read_text(encoding="utf-8"))
        elif args.mode == "cell-edges":
            cells = itertools.chain.from_iterable(
                h3.cell_to_children(root, SHORTCUT_H3_RES)
                for root in h3.get_res0_cells()
            )
            points = cell_edge_points(cells)
        elif args.mode == "source-edges":
            points = source_edge_points(finder)
        else:
            points = seam_points()
        report = audit_points(
            finder, points, max_points=args.max_points, witness_limit=args.witness_limit
        )
        report.update(
            schema_version=1,
            probe_mode="replay" if args.points else args.mode,
            max_points=args.max_points,
            data_version=finder.data_version,
            data_sha256=data_hashes(args.data_dir),
            replay_sha256=(
                hashlib.sha256(args.points.read_bytes()).hexdigest()
                if args.points
                else None
            ),
            h3_versions=h3.versions(),
            python=platform.python_version(),
            platform=platform.platform(),
            acceleration_path=active_acceleration_path(),
            elapsed_seconds=time.perf_counter() - started,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        write_json(report, args.output)
        return int(bool(report["points_with_omissions"]))
    finally:
        finder.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
