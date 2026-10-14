"""Find sampled shortcut omissions without using shortcut geometry as the oracle.

Run with ``uv run python -m scripts.audit_shortcut_candidates --output tmp/audit.json``.
The default probes every stored cell's four corners and the midpoint of each of its
four edges. The corners are where the candidate rule is tightest: a cell owns its north
and east edges and not its south or west, so each grid line is probed from both sides -
once as one cell's ``x1`` and once as its neighbour's ``x0`` - without any point being
invented. The midpoints cover a polygon boundary crossing a cell edge between corners.
``--mode source-edges`` probes stored ring vertices and planar edge midpoints;
``--mode seams`` probes poles and both antimeridian representations.
``--points`` replays a JSON array of [longitude, latitude] pairs instead.

Only full polygon containment (including holes), independently of the shortcut,
can establish an omission. The oracle shares the runtime polygon kernel: this is
an audit of candidate selection, not of that kernel. Sampling cannot certify cell
coverage, and neither midpoints nor the perturbation below justify an exclusion.
Exit 1 means omissions were found, even when another candidate gives the same zone.
"""

import argparse
import hashlib
import json
import math
import platform
import time
from collections.abc import Iterable, Iterator
from pathlib import Path

import numpy as np

from scripts.assert_acceleration_path import active_acceleration_path
from scripts.configs import SOURCE_DATA_DIR
from scripts.utils import write_json
from timezonefinder import TimezoneFinder
from timezonefinder.configs import (
    COORD2INT_FACTOR,
    MAX_LAT_VAL_INT,
    MAX_LNG_VAL_INT,
    SHORTCUT_BLOCK_SIDE,
    SHORTCUT_ROOT_COLUMNS,
)
from timezonefinder.shortcut_index import ShortcutIndex, cell_bounds
from timezonefinder.utils import coord2int


def cell_edge_points(index: ShortcutIndex) -> Iterator[tuple[float, float]]:
    """Every stored cell's four corners and the midpoint of each of its four edges.

    The corners alone probe each grid *line* from both sides - a cell owns its north and
    east edges and its neighbour owns the other side of the same line - which is the
    property the candidate rule turns on. The midpoints are there because a *polygon*
    boundary can cross a cell edge between its corners, and nothing about a corner says
    what happens there. **Probe the edges as well as the corners**: a stream that covers
    only corners narrows this audit without saying so, and this is the only check that
    runs over a whole compiled dataset.

    ``query_coordinate`` is what makes a probe land on the intended integer: a float that
    truncates to it, not the nearest float to the division. Coordinates outside the valid
    range are skipped rather than clamped - a lookup rejects them, and the two lines that
    *are* in range but owned by no polygon as spelled (-180 and -90) are read as +180 and
    one unit north, which the ``seams`` mode probes.
    """
    for cell_id, _ in index.items():
        x0, y0, x1, y1 = cell_bounds(cell_id)
        xm, ym = (x0 + x1) // 2, (y0 + y1) // 2
        for x, y in (
            (x0, y0),
            (x0, y1),
            (x1, y0),
            (x1, y1),
            (xm, y0),
            (xm, y1),
            (x0, ym),
            (x1, ym),
        ):
            if not -MAX_LNG_VAL_INT <= x <= MAX_LNG_VAL_INT:
                continue
            if not -MAX_LAT_VAL_INT <= y <= MAX_LAT_VAL_INT:
                continue
            yield query_coordinate(x), query_coordinate(y)


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
        "cell": finder.shortcuts.cell_at(lng, lat),
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
        "--mode",
        choices=("cell-edges", "source-edges", "seams"),
        default="cell-edges",
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
            points = cell_edge_points(finder.shortcuts)
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
            grid={
                "root_columns": SHORTCUT_ROOT_COLUMNS,
                "block_side": SHORTCUT_BLOCK_SIDE,
            },
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
