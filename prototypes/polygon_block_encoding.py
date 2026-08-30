"""Price a *blocked* polygon layout: a latitude skip index, and a frame-of-reference payload.

Issue #449 proposed shrinking ``boundaries/coordinates.bin`` with delta + zigzag +
varint. Both encodings it reached for decode *sequentially* - LEB128 because element
boundaries are only discoverable by scanning, delta because of the prefix-sum
dependency - so each puts an O(N) serial pass in front of the O(N) ray cast that is
already the most expensive thing a query does. This script measures whether that is
the right trade by measuring the thing it would make worse (the long tail), and then
prices a family the issue did not consider: fixed-size blocks carrying a latitude
range and a per-block coordinate frame.

Four sections, in the order the argument runs:

* ``tail``   - where the long tail of ``timezone_at`` actually is, and what it is made of
* ``skip``   - how much of a polygon a horizontal ray needs, given per-block latitude ranges
* ``verify`` - that a block-encoded point-in-polygon test is the *same function* as the
               shipped kernel, over the query pairs the committed fixtures produce
* ``size``   - what each candidate encoding costs on disk, including the block index

The point-in-polygon backend is bound at *import* time and numba wins whenever it is
importable, so the tail section must be run the way CI measures::

    # clang (what a plain `pip install timezonefinder` runs, and what CI tracks)
    PYTHONPATH=. uv run --isolated --no-group numba --group proto --group test \
        python prototypes/polygon_block_encoding.py

    # numba (what a dev checkout runs)
    PYTHONPATH=. uv run python prototypes/polygon_block_encoding.py

The ``skip``, ``verify`` and ``size`` sections report counts rather than times and are
backend-independent.


FINDINGS (release 2026c, 1,322 boundary polygons / 7,925,313 vertices; times Darwin
arm64, Python 3.14.2, C extension, default memory-mapped mode):

1.  **The long tail is real, and it is one ray cast across a huge ring.** Per-query
    ``timezone_at`` over the committed fixtures, microseconds:

        stratum     mean     p50     p90     p99   p99.9      max
        random      2.33    1.00    3.08   31.83   61.42   126.67
        on_land     3.85    1.00   10.05   39.71   82.58   108.79
        ambiguous  11.69    8.08   25.50   56.09   90.96   142.54
        unique      1.05    0.96    1.12    4.00   11.04    24.04

    p99 is ~40x p50 on ``on_land``. Slicing that stratum by its own latency shows what
    the tail is made of - not many candidates, but few candidates with very many
    vertices:

        slice        time    PIP calls   vertices tested
        p0-50      0.94 us       0.00                 0
        p50-90     2.61 us       0.19               396
        p90-99    20.41 us       1.03            25,771
        p99-100   54.54 us       1.20            82,195

    corr(time, vertices tested) = 0.92; corr(time, PIP calls) = 0.76.

2.  **Vertex-proportional time is a third to a half of a whole workload**, which is the
    share to rank on. Least squares over 5,000 points per stratum:

        random   mean 2.33 us = 1.55 us + 0.616 ns/vertex  ->  30.1 % vertex-proportional
        on_land  mean 3.85 us = 1.99 us + 0.577 ns/vertex  ->  48.8 %

    Read those as "about a third" and "about a half": a second run of the same command
    gave 34.1 % and 50.0 %, which is this machine's own 3-9 % jitter and not a trend.

3.  **A per-block latitude range removes ~98 % of the edge tests.** Ray casting only
    flips parity on an edge that spans the query latitude, so a block whose range
    excludes it cannot contribute. Over the 4,827 real (point, polygon) pairs the
    ``on_land`` and ``ambiguous`` fixtures produce, against 70,992,626 edge tests today:

        B     edges scanned          block tests    total work units
        32      397,625 (0.56 %)       2,220,816         ~2.6 M  (27x less)
        128   1,398,797 (1.97 %)         557,074         ~2.0 M  (36x less)
        512   4,539,293 (6.39 %)         141,184         ~4.7 M  (15x less)

    The work-unit column weights a block test as one edge test, which holds in C and
    not in numpy; B=128 is the optimum either way. Read adversarially rather than on
    average, the largest polygon (id 406, 192,960 vertices) gives up little: a
    uniformly drawn latitude touches 137 vertices at B=32 (0.07 %) and the *worst*
    latitude anywhere in it touches 736 (0.38 %).

4.  **A block-encoded test is the same function, verified rather than argued.** Encoding
    410 distinct polygons at B=128 and replaying 1,463 real query pairs: 0 blocks failed
    the bit-packed round trip and 0 answers disagreed with ``utils.inside_polygon``,
    while testing 1.88 % of the edges. Two properties carry it. The kernel's flip
    condition ``(y > y1) ^ (y > y2)`` implies ``min(y1,y2) < y <= max(y1,y2)``, so a
    flipping edge's block always survives the filter; and parity is a sum mod 2 over
    *independent* per-edge predicates - the loop's ``y1 = y2`` carry is a cached
    comparison, not a dependency - so blocks may be visited in any order or skipped.
    Every quantity in the test is a difference, so translating the *query* into a
    block's frame is exact and the frame base is never added back per vertex.

5.  **Frame-of-reference blocks reach varint's size without varint's decode.** Payload
    plus block index, against 63,402,504 B today (varint figures reproduce issue #449's
    to the byte, which is what validates the pricing):

        encoding                              bytes   vs today
        fixed int32 SoA (today)          63,402,504      1.000
        delta+zigzag+varint @1e-7        35,320,271      0.557   sequential decode
        block-FOR B=128 bitpack @1e-7    39,355,810      0.621   random access
        delta+zigzag+varint @1e-6        29,043,454      0.458   sequential decode
        block-FOR B=128 bitpack @1e-6    32,696,514      0.516   random access

    At 1e-6 - which GH-542 established is lossless *by construction*, the source
    carrying six decimals - the random-access encoding is smaller than the sequential
    one at full precision. Median block width is 19 bits against today's fixed 32
    (p99 25); 29.7 % of polygons fit in a single B=128 block, median 3, max 1,508.

What this does **not** establish: wall clock. The reduction in finding 3 is a work
*count*, and realising it requires the filter to live inside the C/numba kernel. Section
2 measures why: the same filter written in numpy costs 2.73 us per query at B=128 and
5.31 us at B=32 on the largest polygon - dispatch charged to every query however few
blocks survive, which would swamp the ~1 us median. Also unmeasured here: whether
byte-aligned widths (+~8 MB, decode is a widening load) beat bit-packed ones.
"""

import sys
import time
from collections import defaultdict

import numpy as np

from tests.auxiliaries import (
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
    ON_LAND_POINTS_FIXTURE,
    RANDOM_POINTS_FIXTURE,
    UNIQUE_SHORTCUT_POINTS_FIXTURE,
    load_benchmark_points,
)
from timezonefinder import TimezoneFinder, utils
from timezonefinder.configs import DEFAULT_DATA_DIR
from timezonefinder.polygon_array import PolygonArray

# Vertices per block. The two things it trades run opposite ways: small blocks compress
# better (a tighter coordinate frame) and skip better per vertex, large blocks mean
# fewer range comparisons. Finding 3 measures the curve; 128 is its optimum.
BLOCK_SIZE = 128

N_POINTS = 5_000


def _boundaries() -> PolygonArray:
    return PolygonArray(DEFAULT_DATA_DIR / "boundaries", in_memory=True)


def _backend() -> str:
    return "clang" if TimezoneFinder.using_clang_pip() else "numba/python"


# --------------------------------------------------------------------------------------
# 1. where the tail is
# --------------------------------------------------------------------------------------


def _time_queries(finder: TimezoneFinder, points, count_vertices: bool):
    """Per-query wall clock, optionally with the vertex count each query tested."""
    tally = {"verts": 0, "pips": 0}
    original = PolygonArray.pip

    def counting_pip(self, poly_id, x, y):
        tally["pips"] += 1
        tally["verts"] += self.coords_of(poly_id).shape[1]
        return original(self, poly_id, x, y)

    if count_vertices:
        PolygonArray.pip = counting_pip
    try:
        for lng, lat in points[:300]:  # warm the paths before timing any of them
            finder.timezone_at(lng=lng, lat=lat)
        times = np.empty(len(points))
        verts = np.zeros(len(points))
        pips = np.zeros(len(points))
        for i, (lng, lat) in enumerate(points):
            tally["verts"] = tally["pips"] = 0
            start = time.perf_counter()
            finder.timezone_at(lng=lng, lat=lat)
            times[i] = time.perf_counter() - start
            verts[i], pips[i] = tally["verts"], tally["pips"]
    finally:
        PolygonArray.pip = original
    return times * 1e6, verts, pips


def report_tail() -> None:
    finder = TimezoneFinder()
    print(f"\n=== 1. where the tail is ({_backend()}, in_memory=False) ===\n")
    print(
        f"{'stratum':>10} {'mean':>8} {'p50':>8} {'p90':>8} {'p99':>8} {'p99.9':>9} {'max':>9}"
    )
    strata = (
        ("random", RANDOM_POINTS_FIXTURE),
        ("on_land", ON_LAND_POINTS_FIXTURE),
        ("ambiguous", AMBIGUOUS_SHORTCUT_POINTS_FIXTURE),
        ("unique", UNIQUE_SHORTCUT_POINTS_FIXTURE),
    )
    for name, fixture in strata:
        t, _, _ = _time_queries(
            finder, load_benchmark_points(fixture)[:N_POINTS], False
        )
        q = np.percentile(t, [50, 90, 99, 99.9])
        print(
            f"{name:>10} {t.mean():8.2f} {q[0]:8.2f} {q[1]:8.2f} {q[2]:8.2f} "
            f"{q[3]:9.2f} {t.max():9.2f}   (us)"
        )

    # What the tail is *made of*, and what share of a workload is proportional to it.
    print(
        f"\n{'stratum':>10}  {'slice':>8} {'time':>10} {'PIP calls':>10} {'vertices':>12}"
    )
    for name, fixture in (
        ("random", RANDOM_POINTS_FIXTURE),
        ("on_land", ON_LAND_POINTS_FIXTURE),
    ):
        t, v, p = _time_queries(finder, load_benchmark_points(fixture)[:N_POINTS], True)
        order = np.argsort(t)
        for lo, hi in ((0, 50), (50, 90), (90, 99), (99, 100)):
            sel = order[int(len(t) * lo / 100) : int(len(t) * hi / 100)]
            print(
                f"{name:>10}  {f'p{lo}-{hi}':>8} {t[sel].mean():9.2f}us "
                f"{p[sel].mean():10.2f} {v[sel].mean():12.0f}"
            )
        design = np.vstack([np.ones_like(v), v]).T
        (intercept, slope), *_ = np.linalg.lstsq(design, t, rcond=None)
        proportional = slope * v.mean()
        print(
            f"{'':>10}  fit = {intercept:.2f} us + {slope * 1000:.3f} ns/vertex"
            f"  ->  {proportional / t.mean() * 100:.1f} % of the workload mean is "
            f"vertex-proportional"
        )
        print(
            f"{'':>10}  corr(time, vertices) = {np.corrcoef(t, v)[0, 1]:.2f}, "
            f"corr(time, PIP calls) = {np.corrcoef(t, p)[0, 1]:.2f}\n"
        )


# --------------------------------------------------------------------------------------
# 2. the block latitude index
# --------------------------------------------------------------------------------------


def latitude_ranges(y: np.ndarray, block_size: int):
    """Per-block ``[min, max]`` latitude, each block extended by its bridging vertex.

    Block ``b`` owns the edges leaving its own vertices, so its last edge reaches the
    first vertex of block ``b+1`` (wrapping to vertex 0 on the last block). Including
    that vertex is what makes every edge lie inside exactly one block's range.
    """
    n = y.shape[0]
    n_blocks = -(-n // block_size)
    padded = np.full(n_blocks * block_size, y[-1], dtype=np.int64)
    padded[:n] = y
    blocks = padded.reshape(n_blocks, block_size)
    bridging = np.roll(blocks[:, 0], -1)
    bridging[-1] = y[0]
    return np.minimum(blocks.min(1), bridging), np.maximum(blocks.max(1), bridging)


def _recorded_pip_calls(finder: TimezoneFinder, limit: int):
    """Every (polygon, x, y) the fixtures actually reach a point-in-polygon test with."""
    calls = []
    original = PolygonArray.pip

    def recording_pip(self, poly_id, x, y):
        calls.append((int(poly_id), int(x), int(y)))
        return original(self, poly_id, x, y)

    PolygonArray.pip = recording_pip
    try:
        for fixture in (ON_LAND_POINTS_FIXTURE, AMBIGUOUS_SHORTCUT_POINTS_FIXTURE):
            for lng, lat in load_benchmark_points(fixture)[:limit]:
                finder.timezone_at(lng=lng, lat=lat)
    finally:
        PolygonArray.pip = original
    return calls


def report_skip() -> None:
    print("\n=== 2. how much of a polygon a horizontal ray needs ===\n")
    calls = _recorded_pip_calls(TimezoneFinder(), N_POINTS)
    boundaries = _boundaries()
    print(f"PIP calls the fixtures produce: {len(calls):,}")
    for block_size in (32, 128, 512):
        cache: dict[int, tuple] = {}
        total = scanned = block_tests = 0
        for poly_id, _, y in calls:
            if poly_id not in cache:
                coords = boundaries.coords_of(poly_id)
                cache[poly_id] = (
                    *latitude_ranges(np.asarray(coords[1], dtype=np.int64), block_size),
                    coords.shape[1],
                )
            lo, hi, n = cache[poly_id]
            total += n
            scanned += min(int(((lo <= y) & (hi >= y)).sum()) * block_size, n)
            block_tests += len(lo)
        print(
            f"B={block_size:<4d} {total:>11,} edges -> {scanned:>10,} scanned "
            f"({scanned / total * 100:5.2f} %) + {block_tests:>9,} block tests"
        )

    # The adversarial reading of the same structure: not an average over the queries
    # that happened, but the worst latitude anywhere in the largest polygon.
    sizes = np.array([boundaries.coords_of(i).shape[1] for i in range(len(boundaries))])
    largest = int(sizes.argmax())
    y = np.asarray(boundaries.coords_of(largest)[1], dtype=np.int64)
    print(f"\nlargest polygon (id {largest}, {sizes[largest]:,} vertices):")
    for block_size in (32, 128):
        lo, hi = latitude_ranges(y, block_size)
        span = int(y.max() - y.min())
        expected = float(np.clip(hi - lo, 0, span).sum() / span) * block_size
        probes = np.linspace(y.min(), y.max(), 4001)
        worst = int(
            ((lo[None, :] <= probes[:, None]) & (hi[None, :] >= probes[:, None]))
            .sum(1)
            .max()
        )
        worst *= block_size
        print(
            f"  B={block_size:<4d} uniformly drawn latitude touches {expected:>7.0f} vertices "
            f"({expected / sizes[largest] * 100:5.2f} %), worst latitude {worst:>7,} "
            f"({worst / sizes[largest] * 100:5.2f} %)"
        )
        # What the filter costs at the *numpy* level, which is why it cannot live there:
        # the dispatch alone is charged to every query, however few blocks survive.
        lo32, hi32 = lo.astype(np.int32), hi.astype(np.int32)
        probes32 = probes.astype(np.int32)[:2000]
        start = time.perf_counter()
        for probe in probes32:
            ((lo32 <= probe) & (hi32 >= probe)).sum()
        per_query = (time.perf_counter() - start) / len(probes32) * 1e6
        print(
            f"  {'':<6} the same filter written in numpy costs {per_query:.2f} us per query"
        )


# --------------------------------------------------------------------------------------
# 3. a block-encoded point-in-polygon test, verified against the shipped kernel
# --------------------------------------------------------------------------------------


def pack(values: np.ndarray, width: int) -> bytes:
    if width == 0:
        return b""
    acc = 0
    for k, value in enumerate(values):
        acc |= int(value) << (k * width)
    return acc.to_bytes((len(values) * width + 7) // 8, "little")


def unpack(buffer: bytes, width: int, n: int) -> np.ndarray:
    if width == 0:
        return np.zeros(n, dtype=np.int64)
    acc = int.from_bytes(buffer, "little")
    mask = (1 << width) - 1
    return np.fromiter(((acc >> (k * width)) & mask for k in range(n)), np.int64, n)


def encode(coords: np.ndarray, block_size: int) -> list[dict]:
    """Split a ring into blocks, each with its own coordinate frame and bit width."""
    n = coords.shape[1]
    blocks = []
    for start in range(0, n, block_size):
        stop = min(start + block_size, n)
        # ... plus the bridging vertex, so the block holds both ends of every edge it owns
        index = list(range(start, stop)) + [stop % n]
        vx = coords[0][index].astype(np.int64)
        vy = coords[1][index].astype(np.int64)
        base_x, base_y = int(vx.min()), int(vy.min())
        dx, dy = vx - base_x, vy - base_y
        blocks.append(
            {
                "base_x": base_x,
                "base_y": base_y,
                "width_x": int(dx.max()).bit_length(),
                "width_y": int(dy.max()).bit_length(),
                "n": len(index),
                "y_lo": base_y,  # the frame's own origin, so it costs no extra bytes
                "y_hi": int(vy.max()),
                "payload_x": pack(dx, int(dx.max()).bit_length()),
                "payload_y": pack(dy, int(dy.max()).bit_length()),
            }
        )
    return blocks


def block_pip(x: int, y: int, blocks: list[dict]) -> tuple[bool, int]:
    """Ray-cast parity over the surviving blocks only, never leaving a block's frame."""
    inside = False
    scanned = 0
    for block in blocks:
        if y < block["y_lo"] or y > block["y_hi"]:
            continue  # no edge in here can span the ray
        bx = unpack(block["payload_x"], block["width_x"], block["n"])
        by = unpack(block["payload_y"], block["width_y"], block["n"])
        # Every quantity below is a difference, so translating the query is exact and
        # the frame base is never added back per vertex.
        xq = x - block["base_x"]
        yq = y - block["base_y"]
        scanned += block["n"] - 1
        for j in range(block["n"] - 1):
            y1, y2 = by[j], by[j + 1]
            above1, above2 = yq > y1, yq > y2
            if above1 == above2:
                continue
            x1, x2 = bx[j], bx[j + 1]
            right1, right2 = xq <= x1, xq <= x2
            if not (right1 or right2):
                continue
            if right1 and right2:
                inside = not inside
            else:
                slope1 = (y2 - yq) * (x2 - x1)
                slope2 = (y2 - y1) * (x2 - xq)
                if (slope1 <= slope2) if above1 else (slope1 >= slope2):
                    inside = not inside
    return inside, scanned


def report_verify() -> None:
    print(
        f"\n=== 3. block-encoded PIP against the shipped kernel (B={BLOCK_SIZE}) ===\n"
    )
    calls = _recorded_pip_calls(TimezoneFinder(), 1_500)
    boundaries = _boundaries()
    encoded: dict[int, list[dict]] = {}
    rings: dict[int, np.ndarray] = {}
    disagreed = total = scanned = 0
    for poly_id, x, y in calls:
        if poly_id not in encoded:
            rings[poly_id] = boundaries.coords_of(poly_id)
            encoded[poly_id] = encode(rings[poly_id], BLOCK_SIZE)
        expected = utils.inside_polygon(x, y, rings[poly_id])
        got, touched = block_pip(x, y, encoded[poly_id])
        disagreed += bool(expected) != bool(got)
        total += rings[poly_id].shape[1]
        scanned += touched

    broken = 0
    for poly_id, blocks in encoded.items():
        n = rings[poly_id].shape[1]
        for b, block in enumerate(blocks):
            stop = min(b * BLOCK_SIZE + BLOCK_SIZE, n)
            index = list(range(b * BLOCK_SIZE, stop)) + [stop % n]
            x_back = (
                unpack(block["payload_x"], block["width_x"], block["n"])
                + block["base_x"]
            )
            y_back = (
                unpack(block["payload_y"], block["width_y"], block["n"])
                + block["base_y"]
            )
            broken += int(
                (x_back != rings[poly_id][0][index]).any()
                or (y_back != rings[poly_id][1][index]).any()
            )

    print(f"query pairs replayed      : {len(calls):,}")
    print(f"distinct polygons encoded : {len(encoded):,}")
    print(f"blocks failing round-trip : {broken}")
    print(f"answers disagreeing       : {disagreed}")
    print(f"edges tested today        : {total:,}")
    print(f"edges tested with blocks  : {scanned:,}  ({scanned / total * 100:.2f} %)")


# --------------------------------------------------------------------------------------
# 4. what each encoding costs on disk
# --------------------------------------------------------------------------------------


def _varint_bytes(values: np.ndarray) -> int:
    v = np.asarray(values, dtype=np.uint64)
    bit_length = np.zeros(v.shape, dtype=np.int64)
    remaining = v.copy()
    while remaining.any():
        bit_length += (remaining > 0).astype(np.int64)
        remaining >>= np.uint64(1)
    return int(np.maximum(1, (bit_length + 6) // 7).sum())


def report_size() -> None:
    print("\n=== 4. what each encoding costs on disk ===\n")
    boundaries = _boundaries()
    rings = [
        np.asarray(boundaries.coords_of(i), dtype=np.int64)
        for i in range(len(boundaries))
    ]
    vertices = sum(r.shape[1] for r in rings)
    fixed = vertices * 8
    print(f"{len(rings):,} polygons / {vertices:,} vertices")
    print(f"\n{'encoding':<36}{'bytes':>12}{'vs today':>10}")
    print(f"{'fixed int32 SoA (today)':<36}{fixed:>12,}{1.0:>10.3f}")

    widths: dict[int, list[int]] = defaultdict(list)
    for scale, label in ((1, "1e-7"), (10, "1e-6")):
        varint = 0
        for ring in rings:
            for axis in (0, 1):
                a = ring[axis] // scale if scale != 1 else ring[axis]
                delta = np.diff(a, prepend=0)
                varint += _varint_bytes(np.abs(delta) * 2 - (delta < 0))
        print(
            f"{f'delta+zigzag+varint @{label}':<36}{varint:>12,}{varint / fixed:>10.3f}"
        )

        for block_size in (32, 128, 512):
            payload = index = 0
            for ring in rings:
                for axis in (0, 1):
                    a = ring[axis] // scale if scale != 1 else ring[axis]
                    n = a.shape[0]
                    n_blocks = -(-n // block_size)
                    padded = np.full(n_blocks * block_size, a[-1], dtype=np.int64)
                    padded[:n] = a
                    blocks = padded.reshape(n_blocks, block_size)
                    span = blocks.max(1) - blocks.min(1)
                    bits = np.where(
                        span == 0, 0, np.maximum(1, np.ceil(np.log2(span + 1)))
                    )
                    payload += int(np.ceil(bits * block_size / 8).sum())
                    payload += n_blocks * 5  # int32 frame base + width code
                    index += (
                        n_blocks * 4
                    )  # y_hi (y_lo is the frame base) or byte offset
                    if scale == 1 and block_size == BLOCK_SIZE:
                        widths[block_size].extend(bits.astype(int).tolist())
            total = payload + index
            print(
                f"{f'block-FOR B={block_size} bitpack @{label}':<36}{total:>12,}"
                f"{total / fixed:>10.3f}   (payload {payload:,} + index {index:,})"
            )

    w = np.array(widths[BLOCK_SIZE])
    sizes = np.array([r.shape[1] for r in rings])
    n_blocks = -(-sizes // BLOCK_SIZE)
    print(
        f"\nat B={BLOCK_SIZE}: block width median {np.median(w):.0f} bits, "
        f"p99 {np.percentile(w, 99):.0f}, max {w.max()} (today: fixed 32)"
    )
    print(
        f"blocks per polygon: median {np.median(n_blocks):.0f}, max {n_blocks.max():,}; "
        f"{(n_blocks == 1).mean() * 100:.1f} % of polygons fit in one block"
    )


if __name__ == "__main__":
    sections = {
        "tail": report_tail,
        "skip": report_skip,
        "verify": report_verify,
        "size": report_size,
    }
    wanted = sys.argv[1:] or list(sections)
    for name in wanted:
        sections[name]()
