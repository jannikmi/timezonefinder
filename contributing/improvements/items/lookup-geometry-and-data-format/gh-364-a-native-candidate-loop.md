# GH-364 — a native candidate loop

- **What it was:** moving `timezone_at`'s per-candidate work into C, so that a query costs one FFI crossing instead of one per candidate polygon. It was the last slice of issue #364's free-threading scoping; the rest of that family shipped.
- **Refused by the maintainer: no native candidate loop.** Both reasons it was ranked L-worthy — the time in the coordinate fetch and the GIL — are answered by other work, and what is left does not pay for an L-sized change with a wider C surface to maintain and package.
- **The facts that decided it, kept because they are what a re-proposal has to answer.**
  - **The fetch it was meant to remove is already cheap.** The polygon offset table serves a candidate's coordinates in ~0.83 µs. What a native loop could still remove is roughly 830 ns of fetch, ~650 ns of FFI, and the Python bbox and hole work per candidate tested — and the grid-tree index answers 95.1 % of area-weighted random queries with no geometry at all, at 0.100 candidates offered per query. That is single-digit percent of a mixed workload at most, inside the batch suite's 3–9 % noise floor.
  - **The counts it removes are exact but small:** per candidate-loop query, measured at 1.13 candidates each, FFI crossings 1.13 → 1, numpy array constructions 1.13 → 0, numpy scalar comparisons ~4.5 → 0, dict lookups and generator constructions 1.13 → 0. Sub-noise did not refuse it — the [ranking rule](../../improvement-ranking-and-eligibility.md) accepts an exact count as evidence — the price did.
  - **Free-threading does not need it.** The extension already releases the GIL on every call (cffi does it automatically, ≤13 ns), and per-thread instances scale 4.84x at eight threads without it.
  - **Its cost is the C surface, not the algorithm:** the `hole_registry` dict would become a flat `(count, first_hole_id)` vector pair derived at load, and the coordinate fetch would read the offset table's `base_ptr + table`.
- **What would revive it:** a profile, against the then-current [measured baseline](../../query-performance-measurement-baseline.md), showing the per-candidate Python and FFI work as a non-noise share of a realistic workload — for instance a shortcut index change that sends far more queries to the candidate loop — or a workload where the candidate loop dominates. Re-measure; do not re-argue from the figures above.
- **Status:** rejected — no native candidate loop; kept as the argument against re-proposing it on the per-candidate counts.
- **Last touched:** 2026-10-14 — refused by the maintainer, as the entry recommended.

## Related memory

- [Query performance and shortcut decisions](../../decisions/query-performance-and-shortcut-index-decisions.md)
- [Query performance measurement baseline](../../query-performance-measurement-baseline.md)
