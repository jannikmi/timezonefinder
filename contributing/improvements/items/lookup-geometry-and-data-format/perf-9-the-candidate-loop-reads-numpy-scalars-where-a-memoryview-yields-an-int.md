# PERF-9 — the candidate loop reads numpy scalars where a memoryview yields a Python `int`

- **Location:** `timezonefinder/polygon_array.py` — `PolygonArray.outside_bbox` and `PolygonArray._pip_at`, both reached once per candidate polygon from `TimezoneFinder.inside_of_polygon`.
- **The premise is already recorded in this repository, and these are the two places it was not applied.** `PolygonArray.__init__` converts `block_offsets` to a `list[int]` with a comment measuring the reason: two `numpy.uint32` bounds reach the kernel at 217 ns against 117 ns for `int` ones, "because each is unboxed through `__index__`". The four bounding-box vectors and `nr_vertices` were left as numpy arrays, so `outside_bbox` performs **four numpy 0-d scalar extractions and four mixed-type comparisons per candidate**, and `_pip_at` hands the kernel `self.nr_vertices[idx]` — a fifth extraction, plus the unboxing the `block_offsets` comment is about. The classification log's own rule says it in general terms: *a numpy scalar extraction inside a Python loop costs more than most of the loop bodies in this repository*.
- **Counts removed, per ambiguous query, over the committed fixtures.** ~4.2 numpy scalar extractions in `outside_bbox` (1.053 candidates x 4), 0.779 for `nr_vertices`, and 2.1 Python bound-method calls (`outside_bbox`, `pip`) if the two are inlined into `inside_of_polygon`. Zero on the unique-shortcut stratum, which never enters the loop.
- **The form to use is `memoryview`, not `list`, and that is the whole content of the item.** All three candidate forms index to a Python `int` and all three measured the same to within the machine's noise; what separates them is footprint, measured with `tracemalloc` over construction:

  | form | ambiguous query, vs a tree carrying the hole-registry guard | construction heap |
  |---|---:|---:|
  | `list[int]` | -5.3 % min / -9.8 % median | **+333 KiB** |
  | `array.array` | -6.1 / -10.0 % | +30 KiB |
  | **`memoryview`** | **-6.1 / -10.1 %** | **+1.5 KiB** |

  A `memoryview` is a zero-copy view of the array already loaded, so there is no second copy of the data and no decision to take about spending resident memory on latency — which is what the `list` form would have made this item, on the mode whose whole purpose is to stay small and whose `init_heap` is a tracked benchmark. It also keeps one statement of each vector.
- **Measured whole-query, paired against the tree at `0c1a748`, 15 rounds a side, 2,000 fixture points per stratum** — the `memoryview` form *including* the hole-registry guard, since both were prototyped together: `ambiguous_shortcut` **-12.7 % min / -13.5 % median, 15/15 rounds**, `on_land` **-9.0 / -8.8 %, 15/15**, `random` **-5.2 / -5.2 %, 14/15**, `unique_shortcut` -2.5 / +2.7 %, 8/15 (neutral, as the counts predict). Decomposed against a guard-only build, this item's own increment is **-12.1 % of an ambiguous query and -4.5 to -5.0 % of a random workload**, of which inlining the two method calls is -2.3 / -1.3 % and the scalar indexing is the rest.
- **The fix.** Hold `memoryview`s of `xmin`, `xmax`, `ymin`, `ymax` and `nr_vertices` beside the arrays, built in `PolygonArray.__init__` next to the `block_offsets` conversion that already does this, and read them in `outside_bbox` and `_pip_at`. ~25 lines, no data-format change, no behaviour change. `HoleArray` inherits both methods unchanged.
- **The one caveat to record with it.** `memoryview` over a numpy array requires the array's dtype to be in native byte order; `np.load` gives native order on a little-endian machine, which is what the packaged `<i4` files and the C kernel reading the payload as native `unsigned int` already assume throughout. On a big-endian platform the construction would raise rather than answer wrongly, but the item should say so where the views are built.
- **Sequencing:** none. The hole-registry guard that shipped alongside it touches `timezonefinder.py` and this touches `polygon_array.py`, so the two never overlapped - the original claim that they shared a method was wrong. Independent of [PERF-2](perf-2-the-candidate-loop-builds-a-zone-id-array-to-read-one-element.md); re-measure this item's own increment against the tree it lands on.
- **Do not confuse it with the kernel's own per-edge work**, which polygon layout 3 already closed and which is retained as a [checked finding](../../checked-and-found-sound/runtime-geometry-and-data-checks.md); this is about what reaching the kernel costs.
- **Status:** open — free, small, measured.
- **Last touched:** 2026-09-05 — found and measured in the query-flow discovery round.

## Related memory

- [Query performance and shortcut decisions](../../decisions/query-performance-and-shortcut-index-decisions.md)
- [Query performance measurement baseline](../../query-performance-measurement-baseline.md)
