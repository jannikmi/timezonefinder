# Prototypes

Exploratory studies that produced committed design decisions. They are kept because the decision
is easier to trust — and to revisit — when the measurement behind it is still readable.

These scripts are **not part of the package and not part of the test suite**. Nothing imports them,
CI never runs them, and the ruff linter and mypy both skip this directory (see
`.pre-commit-config.yaml`); only the formatter still applies. They are run by hand, against the
data in the checkout, and each one records its conclusion in a `FINDINGS` block at the top of the
file. Expect them to need adjustment before they run again.

| Script | What it established |
|---|---|
| `single_resolution_bench.py` | H3 **resolution 3** as the shortcut index resolution — the central algorithmic parameter of the package. Builds a separate index per resolution, prices each in the shipped binary layout (checking that pricing against the committed file first) and benchmarks them on one set of globally random points. Its live finding is that resolution 4's old refusal no longer holds on the axis it was made on: deduplication absorbs the sevenfold cell count, so the file goes ~0.1 → ~0.6 MiB rather than past 10% of the polygon data, while removing ~60% of the point-in-polygon tests — and the cost moves to a sevenfold resident table. It also builds and refuses resolution 5: real gains (95.4% of cells unique) but 4.0 MiB on disk and 7.8 MiB resident, 99.7% of it table — each level costs ~20x more memory per candidate removed than the last. It also priced the hierarchical index that was dropped. Cited from `docs/data_format.rst`. |
| `shortcut_resolution_query_bench.py` | **Whether H3 resolution 4 is adoptable**, by swapping a resolution 4 index underneath the real `timezone_at` and comparing whole queries, paired and order-alternated. Its answer is that the question cannot be reached yet: the correctness gate ahead of the timing finds the two resolutions disagreeing on a fixture point, with resolution 4 wrong, because `Hex.lies_in_cell` tests vertex inclusion only and never a polygon edge crossing the cell — a simplification that degrades as cells shrink. It also turned up a narrower gap at the poles. Both are recorded in `potential-improvements.md`. |
| `hole_boundary_redundancy.py` | That **96.4% of hole rings are a verbatim copy of some zone's boundary polygon** (release 2026c), which is what holes being stored as references rests on — see the *Holes as Boundary References* section of `docs/data_format.rst`. Also that the holes matching nothing are not geometric outliers but are fully covered by other zones, so they are an *ordering* question; the zone-precedence engine explored for them was rejected, because making timezone answers depend on hand-maintained political configuration is a real accuracy liability for a case that needs no resolution at all. Reads the upstream GeoJSON, so re-running it against a new release re-verifies the assumption. |
| `hole_removal_impact.py` | That **hole polygons cannot be dropped**, which is the natural next step after the deduplication above and looks safe until measured. Rewrites the hole files of a mirrored data directory and diffs `timezone_at`: dropping only the holes with no boundary twin changes 160 of 6,048 hole-interior answers, dropping all of them changes 1,703 — wrongly (`Asia/Hebron` → `Asia/Jerusalem`, `America/Argentina/Cordoba` → `America/Asuncion`). The companion script's finding that every hole is fully *covered* by other zones is true and insufficient: coverage says the right zone is among the shortcut candidates, ordering decides whether it is reached first. See issue #513. |
| `query_stage_profile.py` | **Where a `timezone_at` query actually spends its time**, per stage, per acceleration backend and per coordinate access mode - taken with three instruments that fail differently (exact `line_profiler` counts scaled by an `ITIMER_REAL` sampler's time share, a prefix ladder, and the line profiler itself for ordering only), on which the batch API, shortcut ordering and the native candidate loop all rest. A unique-zone query is ~1 us of which no stage is geometry; an ambiguous one is ~10 us of which the polygon loop is ~73%; the two point-in-polygon kernels are within 15% of each other, so numba's edge is the FFI marshalling it avoids rather than a faster kernel. Two of its findings have since been acted on: the memory-mapped mode once spent 4.9 us per candidate polygon rebuilding a FlatBuffers accessor (now ~0.8 us, via a precomputed offset table), and the shortcut lookup was a decoded dict (now a slot-addressed table read). |

They need the `proto` dependency group:

```bash
uv sync --group proto
```
