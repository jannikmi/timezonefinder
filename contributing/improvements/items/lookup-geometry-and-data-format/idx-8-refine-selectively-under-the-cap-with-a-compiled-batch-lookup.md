# IDX-8 — refine selectively under the cap with a compiled batch lookup

## Related memory

- [Aligned-index decisions](../../decisions/longitude-latitude-aligned-index-decisions.md) — the refusal of selective refinement this would reopen, its reopen condition, and the sweep's winner it has to beat.
- [GH-364](gh-364-a-native-candidate-loop.md) — the refused native candidate loop, whose price argument against a wider C surface a compiled lookup has to answer too.

## The idea

Within the 800 KB cap, deeper and selectively refined grid trees test fewer polygons per query than the sweep's winner, a 0.75° root with one level of 4×4 blocks, and still lose to it per batch. The NumPy batch descent pays a fixed set of array passes per level, and a selective tree one more per level for its check, on every batch whatever share of its points descends; a 256-point batch cannot amortise them. A compiled batch descent - one loop over the points, a level costing a few integer operations - removes that penalty, so the selectivity those trees buy could pay on the batch path as well as the scalar one. It would also shorten the winner's own batch descent, which is the cheapest part of the question to answer.

## What it trades

- **Batch speed against native surface.** A compiled descent the plain install runs has to live in the C extension, which widens the native surface GH-364 refused for a small gain; a numba-only version would not reach the tracked configuration.
- **Fallback parity.** The NumPy descent stays as the pure-Python path and has to answer identically, so both are tested on every encoding, the −180 and −90 lines included.
- **Format.** A selective tree needs either the selective encoding, a reader and format change that adds a branch to every refined lookup, or the shared-block encoding the shipped reader reads, which spends a block per distinct list and a larger root table.
- **Ceiling.** The polygon loop a finer leaf shortens is a minor share of a query, so the scalar gain is a few per cent at most; the batch gain is what a compiled descent unlocks, and it is unmeasured.

## Work

1. **Measure first, in the prototype.** Give `prototypes/grid_tree_config_sweep.py`'s trees a numba-compiled batch descent as a prototype-only variant, and time the winner, the best deeper tree and the best selective tree with it against their own NumPy descent and against the winner, paired, on x86-64 Linux. The deciding question: does a compiled descent make a deeper or selective tree faster than the winner per batch without losing per scalar call? If not, record that in the decision file and close this as withdrawn.
2. **If it does,** the next step is the maintainer's: whether a compiled descent joins the C extension, with its NumPy twin kept as the fallback. Record it as this entry's `**Decision needed:**` bullet rather than implementing it.
3. **Then ship** as for any index shape change: the encoding, the converter, `timezonefinder/_data_integrity.py`, `docs/data_format.rst`, regenerated data and fixtures, and paired evidence against the shipped index.

- **Where:** `ShortcutIndex.entries_at` in `timezonefinder/shortcut_index.py`; `Tree.entries_at`, `select_refinement` and `pack` in `prototypes/grid_tree_config_sweep.py`; the C extension in `timezonefinder/inside_poly_extension/`, `timezonefinder/utils_clang.py` and `build.py`.
- **Size:** L — a compiled descent with its fallback, a format change and regenerated data; the first slice, a prototype measurement, is S.
- **Status:** open — the first slice is a prototype measurement; shipping a compiled descent waits on its result and then on a maintainer decision.
