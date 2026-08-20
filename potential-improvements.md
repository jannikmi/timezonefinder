# Potential improvements

The single register of what is worth doing next to `timezonefinder`, kept in the open: every
finding, one ranking across all of them, the sequencing rules, and the decisions already taken —
including the options that were considered and refused.

**Anything that improves the package belongs here**, whatever its area and however large: a
correctness defect, a slow path, an awkward API, a docs page that lies, a release step that can
fail silently, a test that cannot fail, duplication that will drift, a data encoding that wastes
half its bytes. There is one list because there is one reviewer's attention to spend, and sorting
candidates into kinds first is how the cheap ones get taken because they are cheap. Where an item
has an issue, the entry names it as a pointer; the reasoning lives here. Entries are grouped below
by the part of the repository they touch, purely so the file can be scanned — the grouping decides
nothing.

**Why here and not on the tracker.** The ranking, the sequencing and the recorded decisions used to
live in a roadmap issue. Reasoning that sits outside the repository goes stale silently: nothing
references it, no check reads it, and a reviewer never sees it in a diff. In this file an entry is
reviewed in the pull request that changes it, and every change to the ranking arrives as a diff.
Issues remain the place a single item is worked out and where outside contributors comment.

## How to read it

**The ranking below is the file's point.** Listing everything that could be improved is easy and
worth little; what costs something is deciding which findings earn a reviewer's attention, and
writing down why the rest do not. Entries are ranked by expected value — *defects that will cause a
real bug later > work that unblocks other work > duplication that will drift > readability* — with
size breaking ties only.

**A performance item is ranked on a measured share, never on an intuition about what looks
slow.** Benefit is the fraction of a query the change removes *at best* — its ceiling, read off
*The measured baseline* below — and cost is size, plus the decisions it needs, plus whether it
forces a data-format change (which is a two-distribution ordered release, the expensive
category). A ceiling below the machine's own run-to-run noise, 3–9 %, cannot be demonstrated by
the benchmark suite even when the change is real: such an item has to stand on correctness or
simplicity instead, and is ranked on that. Unmeasured is not a third case — it means the item is
a measurement, and the measurement is one profiler run.

State the ceiling as a **workload** share, not a stratum share, and prefer the count a change
removes to the time it removes: the counts are machine-independent and the shares are not. *The
measured baseline* below carries the conversion and the rest of what one machine's numbers can and
cannot be asked.

An item sits **below its own blocker**, because the list is walked top-down.

A pass takes the highest-ranked item that is *eligible*: unclaimed, preconditions met, its
maintainer-owned decisions already recorded or obtainable, and small enough to review. That is what
lets a cheap item proceed while a large one waits on a decision.

**Entry conventions.** An id is a stable handle and nothing more — `GH-<n>` means the item is also
tracked by issue `<n>`, the other prefixes are mnemonics, and neither says how a pass should treat
the entry. Locations are given by file plus a code anchor (a function or symbol name), never a line
number, so they survive reformatting. `Size` is a rough count of changed lines.

`Status` opens with one of `open`, `needs …`, `blocked …`, `conditional …`, `parked …`,
`rejected …`, `out of scope …` or `withdrawn …`, and `tests/test_improvement_ledger.py` rejects
anything else. **There is deliberately no status meaning "done"** — everything written down here is
unfinished or declined, and work that landed is *deleted* rather than marked. Do not re-litigate a
closed entry and do not re-add it under a new id.

**The ranking has no numbers**, because the row order is the ranking. A number column would have to
be re-flowed on every insertion and deletion — churn on the one operation this file exists to make
cheap, and a conflict between any two passes that both ship something.

**How it is maintained.** `.claude/skills/improvement-pass/SKILL.md` drives one pass over it. The
file is committed so that it reaches the next pass through `master`: every pass reads it before
touching a source file, re-verifies the entries it is considering against the current code, and
writes back what it found.

**It is a to-do list, not a history.** Work that landed is *deleted* — the entry and its ranking
row, in the same pull request that ships it — because the code is the evidence it is done, the
changelog says what changed, and `git log -- potential-improvements.md` still has the text. Nothing
renumbers and nothing else moves. Entries that were *rejected*, ruled *out of scope* or *withdrawn*
stay: they encode a dead end, and re-discovering one costs a whole pass. So do *Recorded decisions*
and *Deliberately checked and found sound*, which are never deleted.

An entry left in after its work shipped is the failure this file cannot detect on its own: it reads
exactly like an open one, and the next pass pays full price to rediscover that there is nothing to
do. Re-verify before ranking. **A `GH-<n>` entry whose issue has closed is the cheapest staleness
signal there is** — either the work landed or the item was dropped, and both mean the entry is
resolved rather than open. `gh issue view <n> --json state` over the ids costs seconds, and it is
what caught the one entry this file arrived with that had shipped the day before.

Every entry has exactly one row in the ranking and every row has exactly one entry;
`tests/test_improvement_ledger.py` fails otherwise. The table is the only statement of order, so
the entry sections below are grouped by the area they touch rather than sorted.

---

## The ranking

| Id | What | Area | Size | Eligibility |
|---|---|---|---|---|
| GH-499 | Batch / array lookup API | public API | L | decided — blocked by GH-477 + BUG-1 |
| DATA-BINARIES | Stop committing the packaged data binaries | packaging | L | free — decided |
| GH-542 | Establish what coordinate precision is worth | data format | M | free |
| GH-449 | Polygon encoding: delta + varint | data format | L | blocked by GH-542 + DATA-BINARIES |
| BUG-1 | A negative zone or boundary id returns the wrong zone | correctness | ~15 | free — decided |
| DOC-3 | The `zoneinfo` snippets never say Windows needs `tzdata` | docs | ~3 | free |
| GH-477 | Replace the shortcut dict with flat arrays | performance | M | free |
| GH-501 | Guardrails on the automated data update pipeline | release | M | needs decisions — thresholds proposed |
| GH-500 | Validate a data directory's cross-file invariants | data integrity | M | needs the CLI-shape decision |
| GH-428 | Data parsing UX, and the CLI shape it shares with GH-500 | CLI / UX | M | needs the CLI-shape decision |
| GH-536 | The mapped coordinate accessor costs 4.9 µs per candidate | performance | M | needs a decision |
| BIG-1 | `_iter_boundary_ids_of_zone` re-opens `zone_positions.npy` on every call | performance | ~10 | free — decided |
| GH-364 | Free-threaded Python, via a native candidate loop | performance | L | needs scoping |
| GH-502 | First-class `zoneinfo` / UTC-offset helpers | public API | S–M | free — decided |
| GH-332 | Reduced timezone dataset as a second distribution | packaging | M | parked until GH-334 |
| TOOL-7 | The data-dependency guard checks one wheel of however many it finds | release | ~10 | free — decided |
| TOOL-6 | `parse_data` rewrites the committed data report whatever `-out` it was given | tooling | ~40 | needs a decision |
| API-2 | Every submodule is reachable as a package attribute | public API | ~20 | decided — held for the next major |
| API-1 | `AbstractTimezoneFinder.__init__` takes an `in_memory` it never uses | public API | ~10 | decided — held for the next major |
| BIG-4 | `load_binary_data`'s hole branch silently yields empty lists | diagnostics | ~8 | free — decided |
| PYPI-1 | The PyPI project holds 11.37 GB of pre-split releases | packaging | S | free — maintainer action |
| GH-317 | Reduce the release artifact count | packaging | S | withdrawn |
| GH-524 | Move `timezonefinder` under `packages/` | repo layout | M | free |
| GH-362 | Reuse the `PolygonArray` binaries in file conversion | internal | M | free |
| BIG-3 | The GeoJSON parser threads nine accumulator lists through three call levels | internal | ~120 | verification is the expensive part |
| PERF-1 | `is_ocean_timezone` runs a regex on the `timezone_at_land` path | performance | ~2 | free — decided |
| PERF-2 | Two numpy calls over a handful of candidates cost 0.8 µs | performance | ~25 | free — ranked on simplicity, not on the timing |
| DUP-1 | The coordinate bounds are declared three times | internal | ~8 | free — decided |
| BIG-2 | `calculate_shortcut_index_stats` computes four unrelated things in one pass | internal | ~80 | free |
| TOOL-1 | ruff runs close to its default rule set | tooling | M | free |
| TOOL-8 | Agent-facing prose is hard-wrapped, so every edit reflows the paragraph | tooling | S each | free — piecewise, never wholesale |
| DEAD-5 | `REDUCED_TIMEZONE_MAPPING` has no consumer | internal | ~20 | free — decided |
| DEAD-6 | `_iter_boundaries_in_shortcut` has no caller outside the test suite | internal | ~20 | free |
| GH-301 | Sort shortcut polygons by overlap area | performance | M | rejected |
| GH-522 | Shrink the repository history by dropping the committed binaries | repo history | L | blocked by DATA-BINARIES |
| GH-513 | Drop hole polygons entirely | data format | L | blocked by GH-500 |
| GH-505 | Distance to the nearest timezone border | public API | L | conditional — never implement unprompted |
| GH-334 | Official mapping for the reduced set | data | S | parked upstream |
| GH-318 | Improve the timezonefinder GUI | adjacent | M | parked — different repository |

---

## Sequencing and preconditions

Check these explicitly before taking an item, and name the blocking one when you skip it.

```
DATA-BINARIES ──┬─→ GH-449 (encode)
  (stop committing ├─→ GH-317 (artifact count)   [mostly answered already]
   the binaries)   └─→ GH-522 (reclaim existing history)   [strictly after]

GH-477 (flat arrays) ─→ the vectorised half of GH-499 (batch API)

GH-536 (mapped accessor) ─→ re-prices GH-301, GH-364, GH-513   [re-measure after it, not before]

GH-301 (shortcut ordering) ─→ GH-513 (drop holes)   ←── GH-500 (ordering invariant enforced)

GH-500 ←→ GH-428: one CLI design, settled by whichever lands first

independent: GH-502, GH-362, GH-524, PERF-2
```

- **Any change that regenerates the packaged data needs the maintainer's explicit go-ahead** in the
  session, and must not collide with the weekly data-update pipeline, which opens *and auto-merges*
  its own pull requests. The cost is per *file*, not per run: a regeneration that leaves a file
  byte-identical costs nothing, which is what makes batching weaker than it looks for a change
  confined to one part of the data.
- **DATA-BINARIES sequences before GH-449.** Once the binaries stop being committed,
  regeneration no longer adds ~64 MB to this repository's history, which is what makes the rest of
  the data work cheap.
- **Do not start GH-522 before DATA-BINARIES is in force.** A history rewrite followed by one
  more data update through the current pipeline re-adds ~62 MB immediately, and the rewrite — which
  detaches every existing clone and fork — would have to be repeated. The distribution split does
  **not** satisfy this on its own: the binaries are still committed, only at a new path.
- **Publish the data distribution before the code release that requires it**, on every change that
  bumps `DATA_FORMAT_VERSION`. Since PR #529 this is *enforced*: the release job refuses to go on
  if no published `timezonefinder-data` satisfies the bound in the wheel it is about to publish.
  The rule stays stated because the guard blocks the wrong order without performing the right one —
  it tells you the data release is missing, it does not make it. Worth knowing: the guard runs only
  on tag refs, so **no pull request ever exercises it**, and the first time it can speak is the run
  that is already publishing. Dry-running it against a locally built wheel costs a minute and is
  the only way to learn its answer while the version is still spendable.
- **GH-536 is not independent of the geometry work — it is its denominator.** 4.9 µs of the
  ~9.3 µs a candidate polygon costs is the mapped accessor, so landing GH-536 roughly halves
  what candidate *ordering* can win and moves the ~3,000-vertex point below which a candidate's
  cost is the fetch rather than the geometry. Anything ranked on the *time* in the candidate loop
  — GH-364, GH-513 — is measured **after** GH-536 lands, not before.
  **A count is the exception, and it is the cheaper instrument.** What a change removes in
  candidates *tested* does not depend on what a candidate costs, so it can be enumerated over the
  packaged index today and the answer survives GH-536, a new machine and a data update alike. That
  is what settled GH-301 without waiting: reach for the count first, and only price it in time if
  the count leaves the question open.
- **GH-505 is gated on publicly voiced user interest.** Never implement it; only report whether
  interest has appeared.
- **Do not re-propose anything under *Recorded decisions*.**

---

## The measured baseline

Every timing quoted in this file comes from one run of `prototypes/query_stage_profile.py`, whose
`FINDINGS` block holds the full per-stage breakdown. Repeated here is only what the ranking needs:
the denominators, and how to tell whether they still describe the tree.

- **Taken at** `b0642ad`, 2026-08-19 — Apple arm64, Python 3.13, data 2026c, fixture set v2, both
  acceleration backends, both coordinate-access modes.
- **The denominators.** A unique-shortcut query is ~1.17 µs and contains no geometry at all; an
  ambiguous one is ~13.3 µs on the default mapped mode and ~9.1 µs with `in_memory=True`. The two
  backends differ by under 6 % on both. Every share below is a share of one of these, and the entry
  says which — a share of an ambiguous query is not a share of a workload.
- **Freshness check**, before ranking anything on one of them:

  ```
  git diff --stat b0642ad..HEAD -- timezonefinder/ packages/timezonefinder-data/timezonefinder_data/data
  ```

  Empty ⇒ the numbers describe the current tree. Non-empty ⇒ classify what changed. A docstring, an
  `__all__` list or a rename leaves them standing and is worth recording here so the next pass does
  not re-derive it; a change to the lookup flow, the polygon math, the coordinate accessors, the
  shortcut readers or the packaged data does not. *Classified inert since the anchor:*
  `timezonefinder/flatbuf/schemas/__init__.py`, an `__all__` list.
- **One machine took these, so rank on what survives leaving it.** In descending order of how
  well a figure travels:

  1. **Counts, which are exact and machine-independent** — a line's hit count does not depend on
     the hardware, only on the code. 1.13 candidate polygons per ambiguous query; one accessor
     rebuild per candidate; one FFI crossing per candidate on the clang path; two numpy calls per
     ambiguous query. State what a change removes as a count first, and use time only to size it.
  2. **Shares within one query**, which travel but not uniformly: the stages are bound by different
     things — memory latency for the mapped accessor, interpreter dispatch for the Python prologue,
     floating-point throughput for the kernel — so another machine re-weights them against each
     other. Read a share as an order of magnitude, never to one percentage point.
  3. **Absolute nanoseconds, which are this machine's alone.** Never rank on one, and never compare
     one to a figure from CI or from a report page.
- **Rank the `clang` / `in_memory=False` column, not the development machine's.** A dev checkout
  runs numba on whatever laptop is to hand; a plain `pip install` in a constrained container runs
  the C extension against memory-mapped data, which is why `docs/benchmarking_methodology.rst`
  makes that the tracked configuration for CI too. Both are measured, so this costs nothing but the
  discipline of reading the right column.
- **A share of a stratum is not a share of a workload.** Uniformly random points are ~25 % ambiguous
  (that page again), and an ambiguous query costs ~11x a unique one on the mapped path, so ambiguous
  work is ~80 % of a realistic mixed wall clock and unique work ~20 %. Multiply the stratum share
  through before comparing two items that live on different strata — that multiplication is a
  property of the fixtures, not of the machine, so it survives the move.
- **The 2x rule, for what none of the above fixes.** Act on a difference only if it survives any
  single stage turning out 2x cheaper or 2x more expensive elsewhere. It keeps the large calls
  (a 37 % workload share stays large at half the size) and refuses the ones that only exist on this
  laptop. An item that fails the rule and still matters needs a second machine class — the profiler
  is one script over committed fixtures, so a run in a Linux x86 container is the cheap way to get
  one; record it as a second column here, described the way
  `scripts/describe_benchmark_machine.py` describes a benchmark run's machine.
- **Re-measuring belongs to the change that invalidates it**, not to a follow-up pass. A pull
  request that moves the critical path re-runs the profiler on both backends (a few minutes each),
  and updates the `FINDINGS` block, this anchor and every share it moved, in that same pull request.
  Numbers left behind do not announce themselves: an entry ranked on a share that is no longer true
  reads exactly like one that is, which is the failure this file exists to prevent.

---

## Lookup, geometry and data format

### GH-499 — batch / array lookup API

- **Tracks:** issue #499.
- **Why here:** the stated primary user does high-volume lookups and the API answers one point per
  call. The profiling in #497 breaks that query down: 1.1–1.2 µs, *no stage of it geometry*, of
  which H3 cell computation (~390 ns) and coordinate validation (~250 ns) are the two that
  vectorise over an array of points — over half the query, addressable before any lookup logic is
  touched.
- **Decisions still open:** what a batch call returns, and what happens to element 999,999 when it
  is invalid. Also bound by the recorded decision that a coordinate-taking interface never infers
  which column is which.
- **Sequencing:** GH-477 is the enabler for the vectorised half — a flat array is the only shape
  in which the shortcut lookup vectorises, and there the scalar penalty that sinks it as a
  standalone change does not apply.
- **Decided, 2026-08-21 — all four open questions answered:**
  1. **Return type.** `timezone_ids_at(lngs, lats) -> np.ndarray` is the primary;
     `timezone_names_at(...) -> list[str | None]` the convenience. Ids are where the win is — a
     caller doing 10⁶ lookups should not pay for 10⁶ string lookups it maps straight back.
  2. **Input.** Any array-like, `np.asarray` internally, with a documented zero-copy path for
     C-contiguous float64 arrays. Sequences must work or the API serves only numpy users.
  3. **Invalid elements.** `on_invalid="raise" | "skip"`, defaulting to `"raise"` to match the
     scalar methods. Raising on element 999,999 and discarding the rest is hostile, so the escape
     hatch exists; silently sentinelling by default would change the contract.
  4. **Scope.** `timezone_at` only in the first slice. `timezone_at_land` follows once PERF-1 lands;
     `certain_timezone_at` is a different loop and is not bundled.
- **Ordering constraint that follows:** the `"skip"` sentinel is `-1` for ids, which is exactly the
  value BUG-1 makes dangerous — `zone_name_from_id(-1)` answers `Etc/GMT+12` today. **BUG-1 lands
  first**, and its recorded decision (validate at the public edge) is what makes `-1` safe to hand
  out. Bound also by #504's recorded decision: keyword-only `lngs`/`lats`, never a single `(N, 2)`
  array whose column order would have to be inferred.
- **Status:** open — design decided, blocked by GH-477 for the vectorised half and by BUG-1 for the
  sentinel.
- **Last touched:** 2026-08-21 — the four design questions answered; the sequencing they imply
  recorded.

### GH-449 — polygon encoding: delta + varint

- **Tracks:** issue #449. The highest-value open issue on its own merits.
- **What it is:** the issue already carries the measurements — delta + zigzag + varint at full 1e-7
  precision is *lossless* and cuts the payload 63.4 → 35.3 MB, wheel ~30 MB — the decode-cost risk
  (~8.5 ms on the largest polygon), and a better-behaved alternative (int16-delta + per-delta
  escape, ~32 MB, ~0.9 ms). Steps 1 (AoS → SoA) and 2 (a data format version constant) both
  shipped; steps 3 (encode) and 4 (precision, separately) remain.
- **Decisions still open:** pure varint vs int16-delta + escape; whether precision reduction is on
  the table at all.
- **Shape:** a binary format change cannot half-land, so this is prototyped and measured before it
  is migrated in one piece.
- **Postponed, 2026-08-21 — the trade-off cannot be decided on the evidence available.** The two
  encodings are not comparable: the varint row keeps today's 1e-7 precision, the escape row spends
  it, and ~3 MB separates them. Choosing between them means pricing ~11 cm of resolution, and
  nothing in the repository says what that resolution is worth — so the decision would be a guess
  dressed as an evaluation. **GH-542 establishes the missing facts**: what precision the closest
  competitor (`tzfpy`/`tzf-rs`, which ships a simplified dataset by default) actually offers and how
  far its answers diverge near borders, and what users have ever asked for. Either answer unblocks
  this: if ~1.1 cm is a real differentiator, this becomes a lossless-encoding question only; if it
  is not, the design space is wider.
- **Do not re-take the 1e-6 accuracy result as it stands.** The existing "0 of 200,000 lookups
  changed" figure left `hybrid_shortcuts_uint16.bin` unregenerated, and the shortcut index is
  derived from the geometry — the number has to be re-taken with the index rebuilt, and over points
  sampled *near borders* rather than uniformly, since uniform points are overwhelmingly ocean.
- **One constraint on the encoding half regardless of precision:** decode cost lands on the
  candidate loop, where GH-536 already measures ~4.9 µs per candidate just to fetch. A ~8.5 ms
  decode for the largest polygon would be catastrophic there and ~828 µs still bad, so **either
  variant needs GH-536's cache or GH-364's native loop first** — a precondition neither this entry
  nor the issue named.
- **Status:** blocked by GH-542 and DATA-BINARIES.
- **Last touched:** 2026-08-21 — postponed; the precision question split out to GH-542 so this
  entry stops carrying two decisions at once.

### GH-542 — establish what coordinate precision is worth

- **Tracks:** issue #542, opened 2026-08-21 to unblock GH-449.
- **Why it exists:** GH-449's two candidate encodings are not comparable — one keeps today's 1e-7
  precision, the other spends it — and ~3 MB separates them. Choosing means pricing ~11 cm of
  resolution, and nothing in the repository says what that resolution is worth. `CLAUDE.md` calls
  the ~1.1 cm ceiling deliberate and `docs/data_format.rst` advertises it, but neither says who
  needs it.
- **What it has to establish:** the precision the closest competitor actually ships
  (`tzfpy`/`tzf-rs`, which uses a simplified dataset by default), how far its answers diverge from
  this package **near borders** rather than over uniform points, and what users have ever asked for
  — no issue has requested sub-metre accuracy, and the size complaints were about artifact count,
  which the distribution split has answered.
- **Shape:** a prototype under `prototypes/` so the comparison can be re-run, plus a recommendation.
  Explicitly *not* an encoding change.
- **Value:** high as a decision unblocker and low as code — it produces evidence, and the evidence
  decides an L-sized item that is otherwise stalled.
- **Status:** open. Blocks GH-449.
- **Last touched:** 2026-08-21 — created.

### GH-477 — replace the shortcut dict with flat arrays

- **Tracks:** issue #477.
- **What it is:** a measured issue that correctly concludes the obvious implementation *loses* —
  `searchsorted` at 424 ns against `dict.get` at 68 ns, a +38 % regression on the unique-zone path
  the hybrid design exists to make fast. The `uint64` landmine (15.3 µs, 220× slower, silently
  correct) is worth the issue on its own.
- **The reframing that matters:** it is filed as a memory optimisation, and its real value is as
  the enabler for GH-499. Ranked as memory it competes with nothing; ranked as an enabler it
  sequences before the batch API. The **direct-index variant** (+57 ns, *smaller* table) is the
  promising one.
- **Confirmed from the query side by #497** — a different measurement from the issue's
  microbenchmark: `shortcut_mapping.get` is 78 ns of a real 1,150 ns unique-zone query, so the
  `searchsorted` variant costs ~30 % of the whole query and the direct-index one ~5 %. The scalar
  path has to stay, and the ranking of the two variants is unchanged.
- **Status:** open.
- **Last touched:** 2026-08-20 — migrated from the roadmap issue, rank 7 there.

### GH-301 — sort shortcut polygons by overlap area

- **Tracks:** issue #301.
- **What it is:** overlap area is the probability a uniform query point falls in that polygon, which
  is the right sort key. One caveat survives: it proposes adding `shapely`.
- **The mechanism survives and its stated reason does not.** #497 puts the candidate loop at 73 % of
  an ambiguous query on the default mapped mode (61 % in memory), which is the ceiling on what
  ordering can win. A bbox-passing candidate costs ~4.9 µs to open (GH-536) plus 0.24–22 µs of
  kernel, so below ~3,000 vertices what a candidate costs is the *fetch*, not the geometry.
  Ordering therefore wins by reducing **how many** candidates are opened, not by opening cheaper
  ones first — "large polygons are expensive" holds only for the largest stratum, while
  overlap-area ordering remains the right key for the reason the issue gives.
- **It never needed a machine, and the count refuses it.** The bullet above concluded ordering wins
  by opening *fewer* candidates — which is a **count**, so it can be bounded exactly and without
  waiting for GH-536, whatever a candidate turns out to cost. Enumerated over the packaged shortcut
  index (41,162 cells, 10,511 ambiguous, 23,373 polygon references), counting the candidates each
  cell tests when no early hit occurs:

  | | tests | per ambiguous cell |
  |---|---|---|
  | current ordering | 12,600 | 1.199 |
  | the best any ordering could do | 12,234 | 1.164 |
  | **headroom** | **366 — 2.90 %** | on **259 cells, 0.63 % of all cells** |

  So re-ordering can remove at most 2.9 % of point-in-polygon tests, and on 99.4 % of cells it
  changes nothing at all. That is below the noise floor before it is multiplied by the ~25 %
  ambiguous stratum share.
- **Why the headroom is that small, structurally.** `last_zone_change_idx` already makes the *last*
  zone free, and `optimise_shortcut_ordering` already sorts zones by ascending total vertex count —
  so the biggest zone is already the one never tested. And **9,046 of 10,511** ambiguous cells hold
  exactly two zones, where every ordering costs exactly one test. The current heuristic is close to
  optimal for the thing ordering controls.
- **Consequence for the `shapely` question:** the dependency was never the real objection — it would
  sit in the `data` group next to `pydantic`, a converter-time dependency that costs users nothing.
  It is simply not worth adding for 2.9 % of the tests on 0.6 % of cells. If the key is ever wanted
  anyway, sampling points uniformly in each H3 cell and counting hits with the existing kernel
  estimates the same probability with code already in the tree.
- **Consequence for GH-513, which is the larger one.** What that item needs from this one is a
  *guarantee* that the right zone is reached first — a correctness property — not a faster
  ordering. Ranking GH-513 behind a performance item has been sending it after the wrong thing;
  the blocker is an ordering **proof**, including the interaction with the early break, and it
  needs no `shapely` and no re-measurement after GH-536.
- **Rejected, 2026-08-21; issue #301 closed as not planned**, with the enumeration above as the
  justification. `shapely` is not added. **It is no longer a prerequisite for GH-513** — see there;
  that dependency was a mistake in the ranking, not a property of either item.
- **Status:** rejected — 2.90 % of point-in-polygon tests on 0.63 % of cells is not worth a
  re-ordering or a dependency. Kept, not deleted, because the sort key is genuinely the right one
  and the idea will otherwise be re-proposed on its merits.
- **Last touched:** 2026-08-21 — bounded by enumeration, then rejected and the issue closed.

### GH-536 — the memory-mapped coordinate accessor costs 4.9 µs per candidate polygon

- **Tracks:** issue #536, opened from #497's measurement — a finding nothing was looking for.
- **Why it matters:** on the default mapped mode, fetching a candidate's coordinates costs an order
  more than the FFI crossing or the geometry kernel for anything but the largest polygons — 47 % of
  an ambiguous query, ~37 % of a uniformly random workload, paid by exactly the constrained-memory
  deployments the mapped mode exists for. What it removes is machine-independent: one accessor
  rebuilt in Python per candidate polygon.
  It is removed by the same native candidate loop as GH-364, which is why the two are ranked
  together. The largest measured lever in the file, and the reason it heads the performance cluster.
- **Decisions still open**, which is why this is not simply free: the accessor is rebuilt per
  candidate, so the fix caches something — and a cached view is a holder that **pins the mapping**,
  which is a memory trade in the mode that exists to avoid one. Second, per-instance initialisation
  cost lands on every `TimezoneFinder()` construction, which the documented one-instance-per-thread
  pattern multiplies. Both belong to the maintainer.
- **Status:** needs a decision — cache lifetime versus pinning the mapping, and where the
  initialisation cost lands.
- **Last touched:** 2026-08-20 — migrated from the roadmap issue, rank 8 there with GH-364.

### GH-364 — free-threaded Python, via a native candidate loop

- **Tracks:** issue #364, currently a one-line body (a link), so it is not actionable by anyone.
- **What it is:** one FFI crossing per query instead of per polygon; the prerequisite for releasing
  the GIL.
- **Premise corrected by #497:** the crossing is ~500 ns per candidate — real, but an order below
  the 4.9 µs the mapped mode spends *fetching* that candidate's coordinates (GH-536). Both are
  removed by the same native loop, so the item stands and its justification changes.
- **The scoping work:** (a) does the C extension release the GIL, and can it — which is really the
  native-candidate-loop question, since a self-contained native lookup is what makes a GIL-free
  section possible; (b) are numpy/h3/cffi free-threaded-ready; (c) does the documented
  one-instance-per-thread pattern stop being necessary, which is where GH-477 reappears.
  `pytest-run-parallel` is already a test dependency, so the harness exists. Worth writing into the
  issue body before anyone picks it up.
- **(b) is answered: yes.** numpy 2.5.2, h3 4.5.0 and cffi 2.1.1 all publish `cp313t`/`cp314t`
  wheels today; `flatbuffers` is pure Python and needs none, and `cffi<3` already admits 2.x. No
  dependency blocks this.
- **(a) has a floor worth stating.** Releasing the GIL around a *single* point-in-polygon call is
  not worth it — a call is 239–252 ns on a 114-vertex polygon. It only pays around a whole candidate
  loop, which is the same change that removes GH-536's per-candidate accessor rebuild and the
  per-candidate FFI crossing. Scope the three as one item, not three.
- **The packaging cost, which is written down nowhere else.** The wheel strategy is one `abi3`
  wheel per platform (`py_limited_api = "cp311"` in `setup.py`). A free-threaded build cannot be
  served by it, so supporting free-threading means a separate `cp313t`/`cp314t` wheel per platform —
  roughly doubling the artifact count, directly against GH-317. That belongs in the issue body: it
  is the part a contributor would discover only after the C work was done.
- **Status:** needs scoping.
- **Last touched:** 2026-08-20 — dependency readiness verified against PyPI, the GIL-release floor
  and the abi3 consequence added. Still needs scoping, but two of the three questions now have
  answers to write into the issue.

### GH-513 — drop hole polygons entirely

- **Tracks:** issue #513.
- **What it would delete:** the whole hole subsystem — the holes directory, `hole_registry.json`,
  `HoleArray`, `_iter_hole_ids_of`, the holes-before-boundary branch in `inside_of_polygon`, and the
  reference encoding #509 added along with it.
- **Blocked, and measurably so.** Dropping holes from the packaged data and re-running `timezone_at`
  changes answers today:

  | variant | hole interior points changed | random global points changed |
  |---|---|---|
  | drop only the 27 with no boundary twin | 160 / 6,048 (20 of the 27) | 0 / 20,000 |
  | drop all holes | 1,703 / 6,048 (224 of 756) | 16 / 20,000 |

  and the changed answers are wrong, not merely different: `Asia/Hebron → Asia/Jerusalem`,
  `America/Argentina/Cordoba → America/Asuncion`, `Europe/Brussels → Europe/Amsterdam`.
- **The trap worth carrying forward:** the coverage evidence is true and insufficient. Probing shows
  all 27 unmatched holes are fully covered by other zones (0 of 1,620 sampled points fell outside
  every other zone), but coverage only says the right zone is *among* the candidates — not that it
  is reached first. `optimise_shortcut_ordering`'s size-ascending sort gets many enclaves right by
  accident and these wrong. So this needs an ordering guarantee **established**, not verified,
  including the interaction with `last_zone_change_idx`'s early break (GH-500) and the composite
  cases covered only by a union of zones.
- `prototypes/hole_boundary_redundancy.py` reads the upstream GeoJSON, so re-running it against a
  new release re-verifies the premise rather than restating it.
- **No longer blocked by GH-301, 2026-08-21, and the reason generalises.** That item was ranked
  ahead of this one because dropping holes needs a guarantee about which zone a query reaches
  first, and shortcut ordering looked like where such a guarantee would live. It is not. Zone
  precedence is a property of the zones and their geometry; **expressing it per H3 cell would make
  correctness depend on the spatial index**, which is an implementation detail free to change — its
  resolution, its layout, the hybrid unique-zone encoding. Recorded below, since it binds anything
  that reaches for the shortcut index to express a correctness property.
- **What it is still blocked by** is unchanged: the ordering *proof* itself, and GH-500's enforcement
  of whatever invariant that proof relies on, including the interaction with `last_zone_change_idx`'s
  early break.
- **Status:** blocked by GH-500.
- **Last touched:** 2026-08-21 — the GH-301 dependency removed as mis-ranked; the H3-independence
  constraint recorded.

### GH-505 — distance to the nearest timezone border

- **Tracks:** issue #505, a demand-signal issue.
- **Signal check, 2026-08-20: none.** Zero reactions and zero third-party comments; the only comment
  is the maintainer's own note that a `closest_timezone_at` existed historically and the history is
  worth scanning first. Re-checking costs one `gh issue view 505` and is the whole of what a pass
  should do here.
- **Status:** conditional on publicly voiced user interest — **never implement it unprompted**; only
  report whether interest has appeared. It is an L-sized permanent maintenance surface justified by
  a hypothesis about who wants it, so the demand signal comes first.
- **Last touched:** 2026-08-20 — signal checked and recorded, so the next pass can see when it was
  last looked at rather than re-deciding whether to look.

### PERF-1 — `is_ocean_timezone` runs a regex on the `timezone_at_land` path

- **Location:** `timezonefinder/utils.py`, `is_ocean_timezone`; called from
  `AbstractTimezoneFinder.timezone_at_land`.
- **Defect:** the check is `re.match(OCEAN_TIMEZONE_PREFIX, timezone_name)` against the result
  *string*, on every call. Ocean-ness is a fixed property of a zone id for a given dataset, so this
  recomputes a constant from a string per query and couples a behavioural decision to zone naming:
  an upstream rename of the `Etc/GMT` family would silently change which results count as ocean.
- **The ceiling has been taken, and the prediction held.** One `re.match` per `timezone_at_land`
  call, measured at ~310 ns against ~58 ns for the `str.startswith` that replaces it — so the check
  costs ~250 ns, which is ~21 % of a unique-shortcut query, ~2 % of an ambiguous one, and **~6 % of
  a mixed `timezone_at_land` workload** once the strata are weighted. That is inside the 3–9 % noise
  floor, so the benchmark suite cannot demonstrate it even though the saving is real: per the
  ranking rule this ships on simplicity, not as a speed-up, and no before/after in a no-numba
  environment is worth taking. (Numba backend, mapped mode, anchor machine class; the count and the
  ratio travel, the nanoseconds do not.)
- **Fix, corrected.** `OCEAN_TIMEZONE_PREFIX` is `r"Etc/GMT"` — no regex metacharacters — and
  `re.match` anchors at the start, so `name.startswith(OCEAN_TIMEZONE_PREFIX)` is **exactly**
  equivalent and captures the whole measured saving in one line. The boolean array this entry
  originally proposed buys nothing further on speed and is not free: `timezone_at_land` receives a
  *name*, and `is_ocean_timezone` takes one, so an id-indexed array means restructuring both plus a
  per-instance array that `make memory` would show. What the array alone buys is decoupling the
  behaviour from zone naming — worth having only if upstream ever renames the `Etc/GMT` family, and
  the cheap change does not foreclose it.
- **Value:** low to moderate. `timezone_at_land` is public and the packaged data covers the oceans,
  so the branch is taken constantly — but the regex runs on the *result*, after the lookup that
  dominates the query.
- **Decided, 2026-08-20 — take the one-line `str.startswith`, not the boolean array.** The options
  put were: the equivalent one-liner; the precomputed array indexed by zone id that this entry was
  written around; or the one-liner now and the array only if upstream ever renames the `Etc/GMT`
  family. The first was chosen. It ships as a simplification rather than as a speed-up, per the
  measured ceiling above. The array is refused for now and the reason recorded below, so it is not
  re-proposed when this entry is deleted.
- **What implementing it means:** one line in `timezonefinder/utils.py`, and the `import re` goes
  with it if nothing else in the module uses it. Keep `OCEAN_TIMEZONE_PREFIX` as the constant so the
  prefix is still declared once. Changelog bullet in the **Internal** list — no observable behaviour
  changes.
- **Status:** open — decision taken, implementation not started.
- **Last touched:** 2026-08-20 — ceiling measured, the proposed fix corrected to its one-line
  equivalent, then decided.

### BIG-1 — `_iter_boundary_ids_of_zone` re-opens `zone_positions.npy` on every call

- **Location:** `timezonefinder/timezonefinder.py`, `_iter_boundary_ids_of_zone`.
- **Defect:** calls `np.load(..., mmap_mode="r")` per invocation, under a comment reading *"load
  only on demand"*. Off the `timezone_at` hot path — that method inlines the shortcut branch and
  never calls the iterator — but on `certain_timezone_at`'s and `get_geometry`'s.
- **What it removes, as a count:** **one file open, header parse and `mmap` per call**, for a file
  that is read twice and never changes. Same shape as GH-536 — a per-call rebuild of something
  constant — on a different function.
- **Measured.** Numba backend, mapped mode, anchor machine class; `certain_timezone_at` is not one
  of *The measured baseline*'s denominators, so the share below is of that call, not of a workload:

  | | today | with the array read once | share of the call |
  |---|---|---|---|
  | `certain_timezone_at`, Berlin | 198 µs | 83 µs | 58 % |
  | `certain_timezone_at`, Moscow | 188 µs | 78 µs | 58 % |
  | `certain_timezone_at`, Aspen CO | 142 µs | 29 µs | 79 % |
  | `certain_timezone_at`, Pacific ocean | 129 µs | 19 µs | 85 % |
  | `get_geometry`, Berlin | 6.60 ms | 5.88 ms | 11 % |

  Reproduced twice against a generator of identical shape, so the delta is the `np.load` and not
  generator overhead. The absolute figures are this machine's; the ratios and the count are not.
- **The memory/latency trade this was blocked on does not exist.** `zone_positions.npy` is
  **1,018 bytes** — 445 `uint16`. Reading it into memory at construction costs about a kilobyte per
  instance and *removes* a per-call mmap rather than adding a resident one, so the mapped mode gets
  strictly better rather than paying for the fast one. `zone_ids` (2,772 B) is already read eagerly
  in the same `__init__`, which makes the current laziness an inconsistency rather than a strategy.
  Needs one `__slots__` entry.
- **Decided, 2026-08-20 — cache lazily on first use, do not read it at construction.** The options
  put were: read the array eagerly in `__init__` (no open mapping, but the cost lands on every
  construction); cache the mapping lazily on first use (free construction, one mapping pinned for
  the instance lifetime, a `cleanup()` path to write); or leave it. The second was chosen, against
  the eager reading this entry originally recommended, and **the reason is the one the eager case
  under-weighted**: `zone_positions` serves only `certain_timezone_at` and `get_geometry`, which the
  `timezone_at` majority never calls, so an eager read charges every user for an array most of them
  do not touch — on a path that is *itself* a tracked benchmark
  (`docs/benchmark_results_initialization.rst`) and that the documented one-instance-per-thread
  pattern multiplies by the thread count. Lazily, the cost is paid once by the callers who want it
  and by nobody else. The pinning objection that makes this trade hard in GH-536 does not apply at
  a kilobyte.
- **What implementing it means:** one `__slots__` entry holding the mapping, populated on first
  call and released in `cleanup()` next to the boundary and hole accessors — `close_resource`
  already takes anything with a `close()`, so `__del__` and the context manager are covered by the
  existing two-tier handler rather than by a third path. The "load only on demand" comment stays
  true and starts being accurate.
- **Status:** open — decision taken, implementation not started.
- **Last touched:** 2026-08-20 — measured, re-ranked into the performance cluster on the strength of
  it, then decided. The benchmark the entry was waiting on has been taken.

### DUP-1 — the coordinate bounds are declared three times

`±90` / `±180` appear as literals in executable code in three places:

| Location | Role |
|---|---|
| `timezonefinder/configs.py` — `MAX_LAT_VAL` / `MAX_LNG_VAL` | canonical, exported in `__all__` |
| `timezonefinder/utils_numba.py` — `is_valid_lat` / `is_valid_lng` | the actual bounds check |
| `timezonefinder/utils.py` — `validate_lat` / `validate_lng` | literals passed to `_validate_coordinate` **only** to build the error message |

- **Defect:** `_validate_coordinate`'s `min_bound` / `max_bound` are never compared against
  anything — they are interpolated into an f-string. The validator and the message describing it
  are independent and can disagree with nothing to catch it.
- **Fix:** import the constants. Size: ~6 lines.
- **Value:** low. Unlike a file name or an H3 resolution, ±90/±180 are physical facts about the
  coordinate system and will never change; the duplication is real but the drift risk is close to
  nil.
- **Cost, and why it stayed open:** both remaining copies sit on the lookup fast path.
  `validate_coordinates` runs on every query, and in the tracked no-numba configuration `njit` is a
  no-op, so `is_valid_lat` is plain Python — the substitution trades two `LOAD_CONST` for two
  `LOAD_GLOBAL` plus a negation, per call.
- **The exposure is now bounded, which unblocks it.** The whole of `validate_coordinates` is
  218–270 ns of a ~1,174 ns unique-zone query; a few bytecodes inside it are a fraction of that,
  which is far below the 3–9 % run-to-run noise the benchmark suite would have to see it through.
  So no before/after can either justify or refuse this change, and it is decided on the duplication
  alone.
- **Which form, though, is not free — and one of the two is.** Measured per coordinate on the
  pure-Python validator: `-90.0 <= lat <= 90.0` at 127.3 ns, `-MAX_LAT_VAL <= lat <= MAX_LAT_VAL` at
  141.2 ns (~14 ns, two of them per query, ~3 % of a unique-shortcut query), and
  `MIN_LAT_VAL <= lat <= MAX_LAT_VAL` at **127.3 ns — indistinguishable from the literals**. The
  cost is the `UNARY_NEGATIVE`, not the global load, which 3.11's specialising interpreter makes
  free. **So declare `MIN_LAT_VAL` / `MIN_LNG_VAL` alongside the existing maxima and import both;
  do not negate at the call site.** With that, the substitution has no cost to weigh at all.
- **Decided, 2026-08-20 — import the constants, in the pre-negated form.** `MIN_LAT_VAL` and
  `MIN_LNG_VAL` are declared next to the existing maxima in `configs.py` and imported by both
  `utils.py`'s `validate_lat` / `validate_lng` and `utils_numba.py`'s `is_valid_lat` /
  `is_valid_lng`, so the validator, the message describing it and the canonical constant stop being
  three independent statements of the same fact.
- **What implementing it means.** Four sites read the constants and none of them negates. Two
  details that are easy to get wrong:
  - **Put the reason next to the constants, not in a commit message.** *Why* they are declared
    negative rather than derived with a `-` at each use is exactly the kind of fact `CLAUDE.md` says
    belongs at the point of decision — one comment on the `MIN_*` pair, saying the negation is what
    costs and the global load is not, so the next reader does not "simplify" them away.
  - **`MAX_LAT_VAL` / `MAX_LNG_VAL` are in `configs.__all__`, so the `MIN_*` pair joins them** —
    that widens the declared surface by two names while API-2 is about narrowing the *undeclared*
    one. No tension in practice: `configs` is reachable today only through the seam API-2 would
    close, and a constant that two modules import is exactly what `__all__` is for.
  - No changelog bullet in the main list — nothing observable changes; **Internal** is the place.
- **Status:** open — decision taken, implementation not started.
- **Last touched:** 2026-08-20 — measured, then decided. The bounded-exposure argument stands and is
  joined by a positive result: in the pre-negated form the change is free outright.

### PERF-2 — two numpy calls over a handful of candidates cost 0.8 µs per ambiguous query

- **Location:** `timezonefinder/timezonefinder.py` — `zone_ids_of`, and the `get_last_change_idx`
  call directly below it in the candidate-narrowing block (bound in `utils.py`, implemented in
  `utils_numba.py`).
- **Measured:** `zone_ids_of` 617/578 ns and `get_last_change_idx` 149/283 ns (numba/clang) —
  together ~6 % of an ambiguous query, which is *more than coordinate validation, the H3 cell
  lookup and the shortcut lookup put together*, and ~9 % of an `in_memory=True` query. The
  unique-shortcut path pays none of it.
- **Why it is there:** both are numpy operations over a candidate list of a handful of elements,
  where the per-call overhead dominates whatever is computed — `zone_ids_of` is a fancy-index,
  `get_last_change_idx` a scan over the result.
- **Fix:** narrow the candidates in one pass without the numpy round-trip. ~25 lines, no data-format
  change, no behaviour change. Precomputing the index into the shortcut binaries instead is refused
  under *Recorded decisions*.
- **Ranked on simplicity, not on the timing.** ~6 % of an ambiguous query is ~5 % of a random
  workload — the same order as the machine's own noise, so the benchmark suite cannot demonstrate it and it must not be sold as a
  speed-up; what carries it is that a scalar loop over three elements is also the simpler code. Take
  the before/after with `prototypes/query_stage_profile.py` on both backends anyway, and record it
  here — it is the only place the number will exist.
- **Status:** open.
- **Last touched:** 2026-08-20 — from #497's finding 6, which reached no entry when the rest of that
  profiling did.

---

## Public API and behaviour

### BUG-1 — a negative zone or boundary id silently returns the wrong zone

- **Location:** `timezonefinder/timezonefinder.py`, `AbstractTimezoneFinder.zone_id_of`,
  `zone_ids_of`, `zone_name_from_id` and `zone_name_from_boundary_id`.
- **Defect:** all four index a Python list / numpy array directly, so a negative id is a valid index
  counting from the end rather than an error. **Four public methods, not the two this entry was
  written about** — re-verified against the packaged data (`nr_of_zones == 444`):

  | call | returns today | should |
  |---|---|---|
  | `zone_name_from_id(-1)` | `'Etc/GMT+12'` | raise |
  | `zone_id_of(-1)` | `443` | raise |
  | `zone_name_from_boundary_id(-1)` | `'Etc/GMT+12'` | raise |
  | `zone_ids_of(np.array([-1]))` | `array([443])` | raise |
  | `get_geometry(tz_id=-1)` | `ValueError` | already correct |

  `zone_name_from_id` explicitly range-checks in its `except IndexError` handler, which a negative
  id never reaches, so the guard reads as complete and is not.
- **Value:** a caller propagating a `-1` sentinel — the conventional "not found" from an index
  lookup — gets a plausible timezone name back instead of an exception. All four are public API.
- **Fix:** reject `< 0` explicitly, alongside the existing upper-bound check. Size: ~15 lines across
  the four. **This is a behaviour change** (a call that returns today would raise), so it wants a
  maintainer decision and a changelog bullet in the main list.
- **Decided, 2026-08-20 — validate at the public edge, not on the internal path.** The three
  options put were: guard in place everywhere; guard the four public methods and route the internal
  callers through an unchecked private accessor; or document the behaviour and leave it. The second
  was chosen. `zone_name_from_id` is on the query path — seven internal call sites, one per
  successful `timezone_at` — and a bare `if zone_id < 0` measures ~10 ns, order 1 % of a
  unique-shortcut query; about nine extra lines removes that cost entirely, and the internal callers
  cannot produce a negative id in the first place. Recorded under *Recorded decisions* as well,
  because it binds every future id-taking interface.
- **What implementing it means:** reject `< 0` in `zone_id_of`, `zone_ids_of`, `zone_name_from_id`
  and `zone_name_from_boundary_id`; add the unchecked private accessor the seven internal sites
  call; a changelog bullet in the **main** list, since a call that returns today will raise.
- **Still ahead of GH-499**, whose `on_invalid` policy wants `-1` as its sentinel — which is exactly
  the value that round-trips to `Etc/GMT+12` until this lands.
- **Status:** open — decision taken, implementation not started.
- **Last touched:** 2026-08-20 — re-verified (two more public methods affected than recorded, guard
  cost measured), then decided.

### GH-502 — first-class `zoneinfo` / UTC-offset helpers

- **Tracks:** issue #502.
- **Why here:** moves the two most common downstream steps into the library. See DOC-3 for the
  Windows caveat any such helper inherits.
- **Its strongest argument has been half spent by #538, and the entry should say so.** The issue
  rests on the inverted `Etc/GMT±X` sign — `timezone_at(lng=-150, lat=0)` returns `Etc/GMT+10`,
  whose offset is −10:00 — and on the library being the only party that knows the convention. #538
  put that warning in `docs/2_use_cases.rst`, so a reader who gets that far is now told. What
  remains is the readers who never open the page, which is a real but weaker argument than "nothing
  anywhere says this".
- **DOC-3 is the other half of the same paragraph and is still open**, so whichever of the two is
  taken should take both: a helper inherits the Windows `tzdata` gap, and the page that warns about
  the sign still does not warn about the database.
- **Decided, 2026-08-21 — ship the full set:** `zoneinfo_at`, `utc_offset_at` and `localize` on
  `AbstractTimezoneFinder`, mirrored in `global_functions.py`. Chosen over docs-only and over an
  offset-only helper. `zoneinfo` is stdlib, so this adds no dependency; what it adds is a permanent
  public surface, which is why it belongs with the other API work rather than trickling out.
  **Additive**, so unlike API-1 and API-2 it does not *need* a major — but it should ride the same
  release, so the API documentation is rewritten once.
- **Two things it must carry**, both currently absent from the code and one of them from the docs:
  the `Etc/GMT±X` inversion (`utc_offset_at` is the method that makes the trap unreachable, which is
  the point of owning the conversion), and the Windows `tzdata` caveat that DOC-3 covers — a helper
  returning a `ZoneInfo` raises `ZoneInfoNotFoundError` on a clean Windows install just as the
  documented snippet does. **DOC-3 ships with it or before it, not after.**
- **Status:** open — decision taken, implementation not started.
- **Last touched:** 2026-08-21 — decided; the sign warning is present since #538, the `tzdata`
  caveat is absent from `docs/`, `README.rst` and `pyproject.toml` alike.

### API-1 — `AbstractTimezoneFinder.__init__` takes an `in_memory` it never uses

- **Location:** `timezonefinder/timezonefinder.py`, `AbstractTimezoneFinder.__init__`.
- **Defect:** the parameter is accepted and then not read; `TimezoneFinder.__init__` applies its
  *own* copy of the argument to the two `PolygonArray` constructors after calling `super()`. The
  base class loads only data it always keeps in memory, so there is nothing for it to select.
- **Fix:** either drop it from the base signature (subclasses stop forwarding it) or have the base
  store it for subclasses to read. Size: ~10 lines. Note the base cannot store it as things stand —
  `in_memory` is not in `__slots__`, so option two costs a slot.
- **The premise this entry was written on is wrong, and that changes how much it touches.**
  `AbstractTimezoneFinder` is **not** importable from the package root:
  `from timezonefinder import AbstractTimezoneFinder` raises `ImportError`. It is reachable only as
  `timezonefinder.timezonefinder.AbstractTimezoneFinder` — which is public solely because API-2 is
  unresolved. So how much public surface a signature change here touches is decided by API-2, not
  by this entry, and the two want answering in that order.
- **`TimezoneFinderL` is the user-visible half.** Its `__init__` is a pure pass-through that could
  be deleted outright, and it accepts `in_memory=True` in silence while loading no polygon data.
  **The repository already made this call in the opposite direction:** `command_line.py` *refuses*
  `--in-memory` with `-f 3`/`-f 4`, under the comment that accepting it "would promise a speedup it
  cannot deliver, which is worse than refusing it". The Python API and its own CLI disagree, which
  is the sharpest form of the question.
- **Decided, 2026-08-21 — drop it everywhere.** From `AbstractTimezoneFinder.__init__` and from
  `TimezoneFinderL.__init__`, which is a pure pass-through and goes with it. `TimezoneFinderL(
  in_memory=True)` becomes a `TypeError`, which is what the CLI already does for the same call and
  is the whole point: a parameter that cannot do anything should say so. **This is a breaking
  change**, so it ships in a major — see the release-strategy decision below, which is why this
  entry no longer moves on its own.
- **Status:** open — decision taken, held for the next major.
- **Last touched:** 2026-08-21 — decided, and bound to the batched-major decision.

### API-2 — every submodule is reachable as a package attribute, so the public API is wider than `__all__` says

- **Location:** `timezonefinder/__init__.py`.
- **Defect:** `__all__` constrains `import *` only. Because `__init__.py` imports from
  `timezonefinder.timezonefinder` and `timezonefinder.global_functions`, and those import further
  modules, `dir(timezonefinder)` also exposes `utils`, `configs`, `polygon_array`,
  `coord_accessors`, `flatbuf`, `np_binary_helpers`, `zone_names`, `utils_clang`, `utils_numba` and
  `inside_polygon_ext`. `docs/4_api.rst` documents seven names; roughly twenty are reachable, and
  `timezonefinder.utils.validate_coordinates` is as importable as the documented API while being
  covered by no stability promise.
- **Fix:** a module-level `__getattr__` (PEP 562) for lazy submodule access, which narrows the
  eagerly bound surface and keeps submodule imports out of `import timezonefinder`. Size: ~20 lines.
- **Why it is not a straight refactor:** removing an attribute someone imports today is a breaking
  change even though it was never documented, so this needs a decision on whether to deprecate
  first. Same shape as API-1. Note that under PEP 562 `import timezonefinder.utils` keeps working
  either way — only `timezonefinder.utils` as an *attribute* of the already-imported package
  changes, which is a much narrower break than the entry's framing suggests.
- **One of the twenty needs no decision and should not wait for one.** The exact count is 20 public
  names against `__all__`'s 7, and the twentieth is not a submodule: `PackageNotFoundError`, the
  stdlib exception bound by the version lookup at the bottom of `__init__.py`. Renaming it to
  `_PackageNotFoundError` is one character of intent over a name nobody can be depending on
  deliberately. **Split it out** — bundling it with the twelve submodules makes an unarguable
  one-line fix wait on an arguable design decision.
- **It also decides API-1's blast radius**, since `AbstractTimezoneFinder` is public only through
  this seam. Answer this one first.
- **Decided, 2026-08-21 — PEP 562 `__getattr__`, without a deprecation cycle.** Chosen over
  warning for a minor first, and over documenting the surface and changing nothing. The break is
  narrower than it looks: `import timezonefinder.utils` keeps working, and only attribute access on
  the already-imported package changes. It also removes the eager submodule binding from
  `import timezonefinder`, which is a small import-time win. **Breaking**, so it ships in the same
  major as API-1 — and it goes **first within that major**, since it decides how much surface API-1
  touches.
- **The `PackageNotFoundError` half does not wait for the major.** Renaming it to
  `_PackageNotFoundError` breaks nothing anyone could have relied on deliberately and can ship at
  any time.
- **Status:** open — decision taken, held for the next major (bar the exception rename).
- **Last touched:** 2026-08-21 — decided, and bound to the batched-major decision.

---

## Packaging, distribution and release

### DATA-BINARIES — stop committing the packaged data binaries

- **Tracks:** nothing open. It was decision 2 of #446, which is closed; this entry is now its only
  home, which is why it carries the reasoning rather than a link.
- **What it is:** the data is already its own distribution (`timezonefinder-data`, released
  2026-08-19), but its binaries are still committed, at
  `packages/timezonefinder-data/timezonefinder_data/data/`. Until they stop being committed, every
  regeneration still adds ~64 MB to this repository's history permanently, which is the constraint
  that makes all the data-format work expensive.
- **Value:** measured across the distribution split, a code release went from 220.05 MB to 1.02 MB
  for the same four files. This half is what dissolves the regeneration cost, and it unblocks
  GH-449, GH-317 and GH-522.
- **Accepted cost, already weighed:** `git bisect` across a format change stops working from a bare
  checkout unless the matching data version resolves per commit.
- **Decisions still open:** where the binaries come from for a development checkout and for CI once
  they are not in the tree.
- **Decided, 2026-08-21 — keep the workspace member, git-ignore its `data/`, fetch it in one
  bootstrap step.** Chosen over resolving `timezonefinder-data` from PyPI (which would need the
  workspace source override put back for every format change, and makes a dev checkout's data
  version a resolver outcome rather than a stated one) and over Git LFS (which reclaims none of the
  existing history and puts a bandwidth quota in front of every fork and CI run).
- **What implementing it means:** `packages/timezonefinder-data/timezonefinder_data/data/` is
  git-ignored; a `make bootstrap` populates it from the published wheel or the GitHub Release; CI
  runs the same target, so dev and CI have one path rather than two. The converter is untouched —
  it still writes to `scripts.configs.SOURCE_DATA_DIR`, which is that same directory. Two things to
  get right: the bootstrap has to be **idempotent and version-aware**, or a stale checkout silently
  tests yesterday's data against today's code; and every entry point that currently assumes the
  data is present (`make test`, `make reports`, the ledger of packaging guards in
  `tests/test_package_contents.py`) needs to fail with "run `make bootstrap`" rather than a
  `FileNotFoundError` from three frames down.
- **Accepted costs, restated so they are not re-litigated:** `git bisect` across a format change
  stops working from a bare checkout unless the matching data version resolves per commit; and this
  does **not** shrink the existing 357 MiB pack — only GH-522 does, and strictly after this is in
  force, or the next data update re-adds ~62 MB and the rewrite has to be repeated.
- **Status:** open — decision taken, implementation not started. Unblocks GH-449 and GH-522.
- **Last touched:** 2026-08-21 — decided. Migrated from the roadmap issue, where it was ranked 3 as "#446
  decision 2". Ranked above GH-449 here because the list is walked top-down and GH-449 is
  blocked by it.

### GH-501 — guardrails on the automated data update pipeline

- **Tracks:** issue #501.
- **What it is:** the weekly pipeline auto-merges and auto-tags a PyPI release from an unpinned,
  unchecksummed, undiffed 64 MB upstream drop. The release-notes half shipped in #519 — a data
  release is now withheld whenever anything else is pending. What remains is that nothing knows
  what the 64 MB actually changed. Its one prerequisite is met: #523 exposed the dataset version at
  runtime (`timezonefinder_data.__version__`), so a diff report has something to name.
- **Thresholds, calibrated against the last three upstream transitions** (2025c→2026a→2026b→2026c,
  measured from the committed data 2026-08-21) rather than guessed:

  | signal | 2026a | 2026b | 2026c | proposed gate |
  |---|---|---|---|---|
  | zone set | unchanged | unchanged | unchanged | see below |
  | boundary payload | +0.29 % | +0.65 % | +1.47 % | **any decrease, or growth > +5 %, blocks** |
  | hole payload | −0.07 % | +0.09 % | −0.31 % | report only |
  | boundary polygon count | +4 | −3 | +2 | **change > ±2 % blocks** |
  | changed-answer rate | not computable — see below | | | **> 0.5 % blocks**, once it exists |

  Two calibrations worth keeping. **Boundary data has grown monotonically** across all four
  releases — refinement adds vertices, it does not remove them — so the useful gate is *asymmetric*:
  a decrease is the anomaly, not a symmetric ±band. And the observed moves are an order of magnitude
  below the ±10 % first proposed here, which would have caught gross truncation and nothing else.
- **Zone changes must not block, which corrects this entry's first proposal.** Upstream adding a
  zone, or splitting one, is routine. A **rename is a removal plus an addition and cannot be told
  apart from the data alone**, so "any zone removed or renamed blocks" would fire on a normal event
  and train the maintainer to click through it. Report the full added/removed list every time —
  it is the most readable line in the diff — and block only on a **net decrease in zone count**,
  which is the shape a truncated or partial dataset takes.
- **The diff report cannot be built by comparing two packaged datasets.** This is the finding that
  changes the design, not just the numbers: the binary format changed three times in August 2026
  (per-axis coordinates in #457, hole references in #509, `.bin` naming in #528), and the current
  reader cannot open the 2026c binaries at all. A report that loads "the previous packaged data"
  breaks on exactly the releases where review matters most. **Commit a fixed sample of points with
  their answers instead**, regenerated as part of each data release: the diff is then one text file
  against another, survives every format change, reviews in a pull request, and is the changelog
  entry for a data update rather than something written from the version number.
- **Decisions still open:** whether the gates above are the right ones, and what happens when one
  trips — the proposal is to label `automation-failed` and open the notification issue instead of
  merging, since that failure path already exists in `check_data_updates.yml`.
- **Preventive, not corrective:** no timezone-boundary-builder release has ever been bad. That
  lowers the urgency and not the value — the argument never rested on a past incident, it rests on
  the pipeline auto-merging and auto-tagging with no human diff review.
- **Status:** needs decisions — the thresholds above, and the trip behaviour. Part (a), pinning and
  checksumming the download, needs no threshold and no decision and can be taken on its own.
- **Last touched:** 2026-08-21 — thresholds calibrated against the last three transitions, the
  zone-change gate corrected, and the binary-diff approach found unworkable across format changes.

### GH-317 — reduce the release artifact count

- **Tracks:** issue #317.
- **What it is:** the PyPI project storage quota (10 GB, already hit, old releases deleted to
  recover space), driven by *artifact count × artifact size*. GH-449 owns size; this owns count.
- **Largely answered by the distribution split:** the data is no longer one of the artifacts. A code
  release now ships three platform wheels plus an sdist, and the data ships once per data release as
  a single `py3-none-any` wheel with no sdist. Read off PyPI: **`timezonefinder` 8.3.0 is 1.02 MB
  across 4 files** (wheels at 82.0 / 81.8 / 83.9 KiB, sdist 764 KB); `timezonefinder-data` 1.2026.3
  is 51.94 MB in one file.
- **The near-identical claim was stale and is corrected.** The three wheels are not "99.995 %
  identical differing in a 2,915-byte `.so`" — that predates the split, when a wheel was ~55 MB of
  data. Diffed entry by entry, they agree on **58 of 61** members and differ in exactly three:
  `RECORD`, `WHEEL`, and `inside_polygon_ext.abi3.so` at 32,392 / 31,760 / 36,464 bytes. So dropping
  two of them saves ~0.17 MB per release and costs manylinux2014 or musl users their wheel. **That
  is not a trade worth making**, which effectively answers the item's own question.
- **The quota is a history problem, not a release-size one.** The `timezonefinder` project holds
  **11.37 GB across 241 files and 57 versions** — the pre-split fat releases. At ~52 MB per data
  release the data project has order 190 releases of headroom. If the quota is to be reclaimed the
  lever is deleting old releases, not shipping fewer wheels; worth splitting out as its own item
  rather than leaving it inside this one.
- **Pulls the other way:** GH-364 would *raise* the artifact count — see there.
- **Decided, 2026-08-21 — closed as answered by the distribution split.** The question it asked,
  *"do we really need 10 wheels?"*, was about artifact count when an artifact was ~55 MB of packaged
  data. It is now 82 KiB, so dropping two of the three platform wheels saves 0.17 MB of a 1.02 MB
  release and costs manylinux2014 or musl users their wheel. The quota problem it was opened for is
  real and entirely historical, so it moves to PYPI-1 rather than staying here under a title about
  artifact count.
- **Status:** withdrawn — superseded by the distribution split; the storage half continues as
  PYPI-1.
- **Last touched:** 2026-08-21 — figures re-measured against PyPI and the published wheels, the
  near-identical claim corrected rather than deleted, then withdrawn.

### PYPI-1 — the PyPI project holds 11.37 GB of pre-split releases

- **Location:** not the repository — the `timezonefinder` project on PyPI. Split out of GH-317,
  which was about artifact *count* and is answered; this is what was actually driving that issue.
- **The numbers, read off the index 2026-08-20:** 11.37 GB across **241 files and 57 versions**,
  against a 10 GB project quota that was already hit once (a support request and the deletion of
  every release up to 3.4.2 recovered the space). Current releases are not the cause and cannot
  become it: `timezonefinder` 8.3.0 is 1.02 MB and `timezonefinder-data` 1.2026.3 is 51.94 MB in a
  project of its own with its own quota — order 190 data releases of headroom.
- **Fix:** a one-off deletion of the pre-8.x releases, which are the ~55 MB-per-file ones. It is a
  maintainer action against PyPI, not a code change, which is why it is an entry here and not an
  issue anybody else could take.
- **Weigh before deleting**, because it is irreversible and PyPI never re-accepts a version number:
  a deleted release breaks any pin to it and any lockfile hash referencing it. Yanking is the
  reversible half-measure and **does not free storage**, so it does not solve this. The honest
  framing is that old releases of a package whose whole payload was a since-superseded dataset have
  little archival value, but that is a judgement about this package's users, not a general rule.
- **Value:** moderate and non-urgent — nothing breaks until the quota is hit again, and the split
  has made that far slower to arrive.
- **Status:** open.
- **Last touched:** 2026-08-21 — split out of GH-317 when its artifact-count half was answered.

### GH-332 — reduced timezone dataset as a second distribution

- **Tracks:** issue #332 (and GH-334 for the mapping).
- **The reframing:** 92 zones instead of 444. It reads as a build-time switch and is really a second
  published data distribution the user installs instead — which turns a hard problem into a
  packaging decision.
- **Now unblocked:** the distribution split shipped the machinery it needs — a workspace member, a
  `DATA_DIR` indirection and a version scheme — and it no longer depends on DATA-BINARIES.
- **Decided, 2026-08-21 — park it until GH-334 unblocks.** Shipping with a hand-maintained mapping
  was declined, and so was closing it outright: the distribution split removed the hard engineering
  problem, so this is worth doing *when* the official mapping exists. Until then a hand-curated
  table is the same liability the zone-precedence engine was rejected for. GH-334 already tracks
  the upstream trigger (evansiroky/timezone-boundary-builder#195), so nothing else has to watch it.
- **Status:** parked until GH-334 unblocks — decision taken, not a candidate for any pass before
  then.
- **Last touched:** 2026-08-21 — decided to park; migrated from the roadmap issue.

### GH-334 — official mapping for the reduced timezone set

- **Tracks:** issue #334.
- **Status:** parked, blocked upstream on evansiroky/timezone-boundary-builder#195. Nothing to do
  here until that lands; it moves with GH-332 when it does.
- **Last touched:** 2026-08-20 — migrated from the roadmap issue.

### GH-524 — move `timezonefinder` under `packages/` for a symmetric workspace layout

- **Tracks:** issue #524 — the asymmetry the distribution split deliberately left behind.
- **Status:** open. Triggered by GH-332 if that lands first.
- **Last touched:** 2026-08-20 — migrated from the roadmap issue.

### GH-522 — shrink the repository history by dropping the committed coordinate binaries

- **Tracks:** issue #522.
- **What it would reclaim:** of 571.4 MiB of unique blobs across all history, the coordinate
  binaries are 543.8 MiB (**95 %**) across 46 distinct blobs. The pack is ~357 MiB; dropping them
  takes the repository to single-digit MiB. Everything else under the data directory totals 1.79 MB
  and is not worth rewriting history over.
- **What it costs:** `git filter-repo` rewrites every commit SHA — every existing clone and fork is
  detached, all tags are rewritten and any signatures on them invalidated, links to commit SHAs
  from issues, changelogs and external references break, and it is a force-push over `master` and
  every tag. None of that is recoverable by halves, so it is worth doing exactly once.
- **Status:** blocked by DATA-BINARIES — see *Sequencing*.
- **Last touched:** 2026-08-20 — migrated from the roadmap issue.

### TOOL-7 — the data-dependency guard checks one wheel of however many it finds

- **Location:** `scripts/check_data_dependency.py`, `find_wheel`.
- **Defect:** `sorted(dist_dir.glob(f"{prefix}-*.whl"))[0]` and no word about the rest. The release
  job runs this over a `dist/` that cibuildwheel has filled with one wheel per platform target, so
  the discarded majority is the normal case, not the edge one. It is correct today because every
  wheel of a build carries the same `Requires-Dist`; it stops being correct the moment `dist/`
  holds two versions, and the guard would then pass on the wrong one — silently, in the one script
  whose entire job is to not pass vacuously (its own `read_requirement` raises rather than let a
  missing requirement do that).
- **Fix:** read the requirement from every matching wheel and raise `UndeterminedError` if they
  disagree. Size: ~10 lines.
- **Why it needs a decision:** it changes when the script exits `2`, for an input that exits `0`
  today, in the gate ahead of an irreversible publish.
- **Decided, 2026-08-21 — assert that `dist/` holds exactly one version, and refuse otherwise.**
  Stricter than reading every wheel and comparing their requirements, and chosen over it: a `dist/`
  holding two versions is not a disagreement to adjudicate, it is a staging accident, and the guard
  cannot tell which version is the one being released. It also catches the case reading-and-comparing
  misses entirely — a stale wheel of an *older* version left behind, whose `Requires-Dist` agrees
  with the new one and so passes a comparison while proving nothing about what is about to be
  published.
- **What implementing it means:** `find_wheel` returns all matches; raise `UndeterminedError` naming
  the versions found when the set has more than one. Exit 2 already means "could not be carried
  out" and already blocks, so no new failure mode reaches the release job — only a new reason to
  reach an existing one. **Add a test**: this is the guard nothing else covers, and no pull request
  ever exercises it, since it runs on tag refs only. Changelog bullet in the **Internal** list.
- **Status:** open — decision taken, implementation not started.
- **Last touched:** 2026-08-21 — decided; found on the first read of the module.

---

## Data pipeline and developer tooling

### GH-500 — validate a data directory's cross-file invariants

- **Tracks:** issue #500.
- **What it is:** the fast path's core invariant is enforced only at generation time, and custom
  data directories are public API. The first slice and the placement rule shipped in #509.
- **Constrained by a recorded decision:** validation belongs to the build and the test suite, never
  to `__init__`. Its `--validate-data` CLI mode is the right shape precisely because it is explicit
  and opt-in.
- **Decisions still open:** which invariants, and the CLI shape it shares with GH-428.
- **Status:** needs the CLI-shape decision.
- **Last touched:** 2026-08-20 — migrated from the roadmap issue, rank 6 there.

### GH-428 — data parsing UX, and the CLI shape it shares with GH-500

- **Tracks:** issue #428. User-driven, from #363.
- **The overlap that has to be settled:** the proposed `timezonefinder update_data` CLI is the
  natural sibling of GH-500's proposed `--validate-data`, and both should share one CLI design
  rather than accreting subcommands separately. This is no longer hypothetical. `--stdin` landed as
  six options on the one flat command — `--stdin`, `-d`/`--delimiter`, `--lng-col`, `--lat-col`,
  `--header`/`--no-header` and `--in-memory` — four of which mean nothing outside `--stdin` and are
  refused there by hand in `_parse_arguments`, because argparse has no way to express it. So
  whichever of GH-428 / GH-500 lands next has to settle flags versus subcommands **for both**,
  rather than adding a seventh flag and leaving the question to the one after.
- Note also that the distribution split may obsolete part of this outright: "generate the full
  dataset after pip installing" competes with "pip install the dataset".
- **Status:** needs the CLI-shape decision.
- **Last touched:** 2026-08-20 — migrated from the roadmap issue.

### GH-362 — reuse the `PolygonArray` binaries in file conversion

- **Tracks:** issue #362.
- **What it is:** well-specified and self-contained, with no dependencies on anything else here.
  Correctly labelled `good-first-issue`.
- **Status:** open.
- **Last touched:** 2026-08-20 — migrated from the roadmap issue.

### TOOL-6 — `parse_data` rewrites the committed data report whatever `-out` it was given

- **Location:** `scripts/file_converter.py`, `parse_data`'s call to
  `write_data_report_from_binary`; `scripts/reporting.py`, `write_data_report_from_binary`, which
  writes to `DATA_REPORT_FILE` (`scripts/configs.py`, anchored at the checkout's `docs/`).
- **Defect:** the function's `data_path` selects which binaries to *read*; the destination is fixed.
  So `make testparse`, which parses `tests/test_input.json` into `tmp/parsed_data`, leaves the
  committed `docs/data_report.rst` describing the three-zone fixture — as does any user following
  `docs/2_use_cases.rst` with their own `-out`. Nothing warns, and the report is a generated file
  nobody re-reads, so the corruption is only caught by `git status`.
- **Fix:** write the report beside the parsed data when the output directory is not the packaged
  one, or have `parse_data` skip the report for a non-default `-out` and leave it to
  `make reports`. Size: ~10 lines.
- **Both fixes above were the wrong shape, and the better one is to delete the decorator.**
  `redirect_output_to_file` is applied exactly three times, all in `scripts/reporting.py`, all with
  the same constant, over three functions called consecutively from the one place. It is not an
  abstraction — it is the *reason* the destination cannot be a parameter, because a decorator binds
  its argument at import time. Removing it collapses the problem:

  ```python
  def write_data_report_from_binary(
      data_path=..., zone_id_dtype=..., report_path=DATA_REPORT_FILE
  ):
      data = load_binary_data(data_path)
      with redirect_output_to_file_contextmanager(report_path):  # opens "w"
          report_data_statistics(...)
          print_shortcut_statistics(...)
          report_file_sizes(...)
  ```

  The destination becomes an ordinary defaulted parameter, which is all `parse_data` ever needed.
  Four things fall out that neither earlier option got:
  - the `if DATA_REPORT_FILE.exists(): unlink()` dance goes, because the context manager opens
    `"w"` and truncates. The current code truncates then appends three times; one truncating block
    around all three is byte-identical output
  - the file is opened **once** instead of three times
  - the three functions become plain functions that `print`, testable with `capsys` instead of by
    writing a file and reading it back — none of them has a test today
  - `main()`'s `--data-path` gains a matching `--out`, closing the same defect in the CLI, which has
    it too
- **Interacts with a *Deliberately checked and found sound* entry**, which has to be updated rather
  than quietly contradicted: pass 8 recorded that the decorator and the context manager "look like
  duplicates but differ in append-vs-truncate, and both have callers that depend on which they got".
  That was true. It stops being true here — with one block around all three calls, append mode has
  no caller left and the decorator goes with it. `redirect_output_to_file_contextmanager` stays;
  `scripts/benchmark_utils.py` uses it.
- **Neutrality is provable in seconds**, which is what makes this safe: `uv run python -m
  scripts.reporting`, then confirm `git diff docs/data_report.rst` is empty. Verified 2026-08-21
  that the committed report already regenerates byte-identically from the packaged data, so the
  diff is a real signal rather than a coin toss.
- **Size:** ~40 lines, most of it deletion. **Still a behaviour change** for anyone calling
  `parse_data(output_path=...)` — they get their report next to their data instead of overwriting
  the checkout's — which is the change worth having.
- **Status:** needs a decision — between this and leaving the `Makefile` note.
- **Last touched:** 2026-08-21 — re-scoped. The decorator, not the destination, is the defect;
  found immediately after making `make testparse` runnable again, which is why no earlier pass saw
  the site at all.

### TOOL-1 — ruff runs close to its default rule set

- **Location:** `pyproject.toml`, `[tool.ruff]` — no `lint.select`.
- **Defect:** several findings in this register (`B904`, `RUF013`, `A001`, `A002`, `PLW2901`,
  `PLR09xx`) were surfaced by ad-hoc `uv run ruff check --select ...` runs and are not caught by CI
  as configured.
- **Fix:** enable a chosen subset. Best done *after* the existing findings are cleared, so the first
  run is not a wall of noise. Note that `TRY003` / `EM101` / `EM102` fire in the hundreds across
  `scripts/` and are not worth adopting — pick deliberately rather than taking a whole family.
- **Status:** open.
- **Last touched:** 2026-08-14 — `RUF013`, `A001`, `A002` and `PLW2901` are all clean repo-wide, so
  of the families named above only `PLR09xx` still has sites. `B904` and `B023` are clean too
  (excluding `prototypes/`) and could be enabled on their own. `B905` is down to 9 sites: two in
  `scripts/timezone_data.py`'s validators and one in `tests/utils_test.py` where the lengths are
  checked on the line above, the rest genuinely paired by construction.
  **One earlier conclusion here was wrong. It is corrected rather than deleted, because the site
  still looks alarming and the next pass would otherwise re-raise it at full price.** The worry was
  that `timezonefinder/flatbuf/io/hybrid_shortcuts.py`'s `zip(poly_id_hex_ids, poly_id_lengths)` —
  the only `B905` site on the library's own load path — could truncate silently, dropping shortcut
  entries while `_iter_boundaries_in_shortcut` reads a missing hex id as "no candidate polygons"
  (`shortcut_mapping.get(hex_id)` is `None` → `return`), so those coordinates would answer `None`
  rather than raise. The two lists cannot differ in length: they are local accumulators appended in
  the same iteration of the same loop, a few lines above the `zip`, and no file — corrupt or
  otherwise — is read between the two. `strict=True` there would assert what the control flow
  already guarantees, so `B905` has no site on the load path and the family stands or falls on the
  other eight.

### BIG-2 — `calculate_shortcut_index_stats` computes four unrelated things in one pass

- **Location:** `scripts/reporting.py`, `calculate_shortcut_index_stats`.
- **Defect:** computes coverage, uniqueness, storage and frequency metrics in one pass.
- **Fix:** split along those four seams. Its output is committed in `docs/data_report.rst`, so it
  needs a regenerate-and-diff to prove neutral — cheap: `uv run python -m scripts.reporting`, then
  confirm `git diff docs/data_report.rst` is empty. Size: ~80 lines moved.
- **Value:** readability only, and lower than when this entry was written. The title used to read
  "13 branches / 57 statements, over ruff's `PLR0912`/`PLR0915` defaults"; replacing the hard-coded
  H3 ladder removed six branches, so it now trips neither (40 statements against a default of 50).
  Nothing in CI asks for this split any more.
- **Status:** open.
- **Last touched:** 2026-08-14 — re-verified and corrected.

### BIG-3 — the GeoJSON parser threads nine accumulator lists through three call levels

- **Location:** `scripts/timezone_data.py`, `TimezoneData.from_geojson` and the three classmethods
  below it: `_process_timezone_feature` (12 parameters), `_process_polygon_with_holes` (12),
  `_process_hole` (8).
- **Defect:** `from_geojson` declares nine empty lists plus two counters and passes them down two
  levels for the callees to append to. `poly_id` and `nr_of_holes` are additionally returned and
  reassigned at each level, so each function both mutates shared state and threads a counter — and
  which arguments are inputs and which are outputs is visible only by reading the bodies. The
  parameter order also has to match at three call sites with nothing checking it: several
  neighbouring parameters share a type (`PolygonList` appears twice, `list[int]` three times), so
  a transposition type-checks.
- **Fix:** one mutable accumulator (a dataclass with the nine lists and two counters) passed once,
  turning the three signatures into `(accumulator, <the thing being parsed>)`. Size: ~120 lines
  touched, no logic moved.
- **Why it is not a straight refactor:** this is the data converter, and the only thing that proves
  it neutral is regenerating the binaries and confirming
  `git status --short packages/timezonefinder-data/timezonefinder_data/data` is empty — which needs
  a timezone-boundary-builder download (`update_data.sh`), not just a test run. Worth doing, but
  the verification is the expensive part, so it should be its own pass.
- **Status:** open.
- **Last touched:** 2026-08-09 — found.

### BIG-4 — `load_binary_data`'s hole branch silently yields empty lists when a file is missing

- **Location:** `scripts/reporting.py`, `load_binary_data`.
- **Defect:** the `if hole_registry_path.exists() and hole_coord_path.exists():` branch has no
  `else`, so a data directory missing either file reports zero holes rather than saying so. Every
  hole figure in `docs/data_report.rst` then reads as a legitimate zero.
- **Fix:** raise, or state the absence in the report. Size: ~8 lines.
- **The check this entry asked for has been made: raising is not a behaviour change.**
  `scripts/file_converter.py` writes both files on every run unconditionally —
  `create_and_write_hole_registry` and
  `write_polygon_collection_flatbuffer(hole_polygon_file, data.inline_holes)` — even for a dataset
  with no holes at all, so no in-repo path can produce a directory that reaches the branch. It is
  reachable only for a hand-assembled or half-copied directory, which is precisely the case a
  legitimate-looking zero is worst for. The entry stays here rather than moving under *Behaviour and
  public API*.
- **Value:** low-moderate, and narrower than when this entry was first written. It originally also
  covered the function being 37 statements with a function-local import mid-body; PR #509 rewrote
  the loads through `PolygonArray`/`HoleArray`, taking it to 24 statements with no local import, so
  only the silent-empty branch is left.
- **Decided, 2026-08-20 — raise.** The alternative put was to state the absence in the report, which
  was refused because it makes one report describe two different things: a reader cannot tell a
  hole-less dataset from an incomplete directory without checking which sentence the generator
  chose. Raising means every hole figure in `docs/data_report.rst` is either real or the file is not
  written at all. No *Recorded decisions* line: once this ships the reasoning lives in the exception
  message, which is where a reader meets it.
- **What implementing it means:** replace the bare `if hole_registry_path.exists() and
  hole_coord_path.exists():` with a check that raises naming **which** of the two files is missing —
  the useful half of the diagnosis, since the two fail for different reasons. `make testparse` and
  the packaged data both keep working unchanged, so the existing suite covers the happy path and the
  new test is over a directory with a file removed. Changelog bullet in the **Internal** list.
- **Status:** open — decision taken, implementation not started.
- **Last touched:** 2026-08-20 — the behaviour-change question answered against the converter, then
  decided.

### DEAD-5 — `REDUCED_TIMEZONE_MAPPING` has no consumer

- **Location:** `tests/locations.py`, `REDUCED_TIMEZONE_MAPPING`.
- **Defect:** unreferenced. Its only reader was `tests/auxiliaries.py`'s
  `convert_to_reduced_timezone`, deleted with DEAD-1, and its own comment already said
  *"unused, but kept for future reference"*.
- **Fix:** delete it. Size: ~35 lines removed. **Only the deletion is left** — the second half of
  this entry, the `set[str, str]` annotation on a `dict` literal, was corrected when `tests/` came
  under the mypy hook, which is also what now stops the same mistake recurring anywhere in the
  directory.
- **Value:** low. It is reference data rather than code — the zone merges of the reduced
  `timezones-now` dataset, which GH-332 would revisit — which is why DEAD-1 deleted its consumer
  and left it standing rather than deciding for the maintainer. Deleting data someone wrote down on
  purpose is the maintainer's call; recorded so it is made once.
- **Sharpened by GH-332's state.** The table is a hand-derived *fragment* — 18 pairs out of a
  444 → 92 mapping — added by #324 on the reduced-dataset branch and orphaned when #381 reverted to
  the full dataset. GH-334 exists precisely to obtain the **official** mapping from upstream, so
  whatever GH-332 eventually uses, it is not this. If GH-332 is ever closed as won't-do, this
  deletion follows without a further decision.
- **Decided, 2026-08-20 — delete it.** The alternatives put were moving it to `prototypes/` or a
  docs note, and keeping it as reference data; both were declined. `git log -S
  REDUCED_TIMEZONE_MAPPING` still has the table, which is the archive a deleted fragment deserves.
  The half that outlives this entry — that a reduced-zone mapping comes from upstream or not at all
  — is under *Recorded decisions*, so deleting the entry does not lose it.
- **What implementing it means:** delete the constant and its two comment lines from
  `tests/locations.py`; nothing imports it, so nothing else moves. This entry and its ranking row go
  in the same pull request. Changelog bullet in the **Internal** list.
- **Status:** open — decision taken, implementation not started.
- **Last touched:** 2026-08-20 — re-verified unreferenced, provenance traced, then decided.

### DEAD-6 — `_iter_boundaries_in_shortcut` has no caller outside the test suite

- **Location:** `timezonefinder/timezonefinder.py`,
  `AbstractTimezoneFinder._iter_boundaries_in_shortcut`.
- **Defect:** a method on the shipped base class whose only call site in the whole tree is
  `tests/main_test.py`. `TimezoneFinder.timezone_at` and `certain_timezone_at` both inline the same
  `match` on the shortcut value rather than calling it, so it is a third copy of that dispatch that
  nothing in the package executes — and being a copy, it can drift from the two that matter without
  any test noticing, since the test that calls it is the only thing pinning it.
- **Fix:** delete it and have the test walk the shortcut mapping directly, or — if it is meant as
  the readable form of a dispatch the hot paths inline for speed — say so in a comment naming the
  two inlined copies, so the next reader does not delete the wrong one. Size: ~20 lines either way.
- **Value:** low, and it is the *drift* that carries it rather than the dead weight. Ranked
  accordingly.
- **Status:** open.
- **Last touched:** 2026-08-20 — found while tracing BIG-1's call sites.

### TOOL-8 — agent-facing prose is hard-wrapped, so every edit reflows the paragraph

- **Location:** `potential-improvements.md` and `CLAUDE.md`, both hard-wrapped at ~99 columns.
- **Nothing enforces it.** There is no markdown formatter in `.pre-commit-config.yaml` and no test
  asserts a width; it is authoring habit, and not a consistent one — `CONTRIBUTING.md` and
  `README.rst` are effectively unwrapped.
- **Defect:** it optimises for a rendered view these files never get. A single newline inside a
  paragraph renders as a space, so the wrapping is invisible where Markdown is rendered — and these
  two are read raw, by an agent loading them into context and by a maintainer reading a diff, which
  is the one mode the mid-sentence breaks show up in. The cost that is not cosmetic: editing a word
  early in a paragraph reflows every line after it, so a one-word change arrives as six changed
  lines and two passes that touched the same paragraph conflict over sentences neither disagreed
  about. The skill already names that cost — *"Reflowing a paragraph you did not change turns a
  clean merge into a conflict for no gain"* — without naming hard wrapping as its cause.
- **Fix:** semantic line breaks — one sentence per line, long sentences split at clause boundaries.
  `.claude/skills/improvement-pass/SKILL.md` is already converted; it was a new file in the pull
  request that introduced it, so its reflow cost a reviewer nothing.
- **Piecewise, never wholesale.** A single reflow commit over this file is a whole-file diff that
  buries whatever substantive change ships beside it and conflicts with every pass in flight.
  Convert a section when a pass is already rewriting it, where the churn is already paid.
- **Verify by word identity, not by eye** — `original.split() == converted.split()` over the file,
  which is what proves a reflow changed no wording. Structure has to be copied verbatim rather than
  reflowed: frontmatter, fenced code, tables, block quotes, headings.
- **Value:** low as readability, real as merge behaviour — this is the file concurrent passes are
  most likely to collide in, and paragraph reflow is what turns their edits into conflicts.
- **Status:** open.
- **Last touched:** 2026-08-20 — raised when the reflow of `SKILL.md` made the rest visible.

---

## Documentation

### DOC-3 — the `zoneinfo` snippets never say that Windows needs `tzdata`

- **Location:** `docs/2_use_cases.rst`, sections *Creating aware datetime objects* and *Getting a
  location's time zone offset* — the two `ZoneInfo(tz_name)` snippets and the sentence recommending
  the stdlib module for new code.
- **Defect:** `zoneinfo` resolves keys through `zoneinfo.TZPATH`, which names system directories
  (`/usr/share/zoneinfo` and friends) that exist on Linux and macOS and do not exist on Windows;
  CPython there falls back to the `tzdata` PyPI package, which is not a dependency of
  `timezonefinder` and is not installed by anything in this repository. Both documented snippets
  therefore raise `ZoneInfoNotFoundError` on a clean Windows install, and the prose recommends the
  module without the caveat.
- **Value:** this is the first thing a new user runs, and the exception names the timezone key
  rather than the missing database, so the reader's first hypothesis is that the lookup returned a
  bad zone name — a bug report against this package rather than a one-line install.
- **Fix:** one sentence after the first snippet, saying that Windows has no system zone database
  and needs `pip install tzdata`. Deliberately *not* a dependency: `zoneinfo` is the user's choice
  of consumer, not something this package imports, and `pytz` users need nothing. Size: ~3 lines.
  GH-502 inherits the same caveat if it lands first.
- **Status:** open — the snippets arrived in 8.3.0 without the caveat; PR #538 added the explicit
  recommendation on top of them, also without it. Docs-only, so no decision is needed.
- **Last touched:** 2026-08-20 — found while reviewing PR #538. Verified the mechanism rather than
  the platform: `zoneinfo.TZPATH` holds only system paths, `tzdata` is absent from the environment
  and undeclared in either `pyproject.toml`.

---

## Adjacent

### GH-318 — improve the timezonefinder GUI

- **Tracks:** issue #318.
- **Status:** parked — lives in `timezonefinder_gui` and is community-dependent. Out of scope here;
  listed so the register is complete.
- **Last touched:** 2026-08-20 — migrated from the roadmap issue.

---

## Recorded decisions

**Kept, never deleted** — including the rejected options, which is most of their value. The next
pass re-proposes whatever is not written down as already refused. Correct the reasoning when a
premise moves; do not reverse a decision silently.

- **Raster fast-path in front of the H3 index — dropped.** A ~2 MB lookup table answering
  unambiguous cells with one array index, falling through to H3 otherwise. Rejected: it buys query
  time with storage, and storage is the dimension this package can least afford to spend on.
- **Border proximity — conditional on publicly voiced user interest.** See GH-505. The demand
  signal comes first, because it is an L-sized permanent maintenance surface justified by a
  hypothesis about who wants it.
- **Data-directory validation belongs to the build and the test suite, never to `__init__`.**
  Settled while reviewing #509, which first put the hole checks in `HoleArray.__init__` and then
  moved them out. Whether a data directory is coherent is established once, by the build;
  re-deriving it in every user's process spends startup time — multiplied by the per-thread
  instances concurrent workloads are told to use — to re-answer a settled question. The checks live
  in `scripts/data_integrity.py` and run in two places: the converter, over what it just wrote, and
  the test suite, over what the repository ships, sharing one implementation so they cannot drift.
  **This constrains GH-500**: its `--validate-data` CLI mode is the right shape precisely because
  it is explicit and opt-in; validating on construction is ruled out. The second reason matters as
  much as the first — off the init path a check can afford to be exhaustive, which is why #509's
  resolves every hole ring in the dataset. A check constrained to be cheap ends up shallow.
  Recorded in `CLAUDE.md` and `CONTRIBUTING.md`.
- **Hole coverage does not imply hole removability.** Every hole is covered by other zones, and
  that is not enough to drop it: coverage says the right zone is among the shortcut candidates,
  ordering decides whether it is reached first. Measured in GH-513 — dropping holes changes
  answers today, wrongly. Any future "the holes are redundant" argument has to be an argument about
  candidate ordering, not about geometry.
- **A zone-precedence engine for hole conflicts — rejected.** Explored on the original #350 branch:
  configurable political precedence rules, overlap scoring and caching, to decide which zone "wins"
  where a hole overlaps another zone. Rejected on the evidence above — the unmatched holes need no
  resolution at all, they are an ordering question — and on principle: it would make timezone
  answers depend on hand-maintained political configuration, which is an accuracy and maintenance
  liability for a package whose selling point is that it does not simplify. Kept as a one-line
  record in `prototypes/README.md` as well.
- **One layout marker per unreleased batch, not per change.** `POLYGON_LAYOUT_VERSION` was briefly
  bumped to 2 in #509 so a released version would reject deduplicated hole data. It was reverted:
  layout 1 arrived with the per-axis coordinate encoding in 5947b1b, which is not an ancestor of
  8.2.5, so no version in the wild reads or writes it and there was nothing to protect against. The
  bump would have rewritten the 63 MB boundary coordinate file for a single byte. Check whether the
  layout being superseded has actually shipped before bumping.
- **Ocean-ness is tested with `str.startswith`; the zone-id lookup table was refused.** Settled
  2026-08-20 for PERF-1. `OCEAN_TIMEZONE_PREFIX` is `r"Etc/GMT"`, which has no regex
  metacharacters, and `re.match` anchors at the start — so `startswith` is exactly equivalent and
  captures the whole measured saving (~250 ns per `timezone_at_land`, ~6 % of a mixed workload,
  inside the noise floor) in one line. The rejected alternative is worth keeping because it reads as
  the more principled fix: a boolean array indexed by zone id, precomputed at load, which would also
  decouple the behaviour from zone *naming* so that an upstream rename of the `Etc/GMT` family
  could not silently change which results count as ocean. It was refused on cost, not on merit —
  `timezone_at_land` receives a name and `is_ocean_timezone` takes one, so an id-indexed table means
  restructuring both plus a per-instance array — and the one-liner does not foreclose it. Re-propose
  it only against an actual upstream rename.
- **Breaking API changes are batched into one major, never trickled out.** Settled 2026-08-21,
  while deciding API-1 and API-2. Each is individually small — a dead parameter, a wider-than-stated
  attribute surface — and each on its own would be a major version whose entire content is one
  removal nobody asked for. Every *known* breaking change ships together instead: API-1 (drop
  `in_memory` from the base and from `TimezoneFinderL`), API-2 (PEP 562 submodule access), and any
  further removal found before that release. Consequences worth stating, because they are what the
  rule costs: an entry can be *decided* and still not eligible for a pass, so decided-and-held is a
  real state the ranking has to show; API-2 goes first within the major, since it decides how much
  surface API-1 touches; and additive work that does not need a major (GH-502, GH-499) should still
  ride the same release, so the API documentation is rewritten once rather than three times. The
  public API must not break between minors — that constraint is unchanged; this is about not
  spending majors one removal at a time.
- **A correctness property is never expressed in terms of the H3 shortcut index.** Settled
  2026-08-21, while removing GH-301 as GH-513's blocker. Zone precedence — which zone a query should
  reach first where several cover a point — is a property of the zones and their geometry. Stating
  it per H3 cell would make correctness depend on the spatial index, whose resolution, layout and
  hybrid unique-zone encoding are implementation details the package is free to change; a future
  resolution change would then silently move answers rather than only performance. The index is a
  candidate *filter* and may be reordered, rebuilt or replaced freely, which is exactly why nothing
  load-bearing may be derived from its structure. Applies to GH-513 first, and to any future
  argument that reaches for the shortcuts to prove something about answers.
- **A reduced-zone mapping comes from upstream or not at all.** Settled 2026-08-20 while deleting
  `REDUCED_TIMEZONE_MAPPING` (DEAD-5), a hand-derived 18-pair fragment of the 444 → 92
  `timezones-now` mapping, left behind when #381 reverted to the full dataset. It is recorded here
  rather than left in that entry, because the entry disappears with the deletion and the question
  comes back the moment anyone picks up GH-332: **do not re-derive a mapping by hand.** GH-334
  exists to obtain the official one and is blocked upstream on
  evansiroky/timezone-boundary-builder#195; until that lands, a hand-maintained mapping is the same
  liability the zone-precedence engine was rejected for — timezone answers depending on a table
  somebody curated, in a package whose selling point is that it does not simplify. `git log -S` has
  the deleted table if a future reader wants to see what was there.
- **Data serving an optional path is cached lazily, not loaded at construction.** Settled
  2026-08-20 for BIG-1. Construction is not a free place to put work here: it is a tracked benchmark
  (`docs/benchmark_results_initialization.rst`), and the documented one-instance-per-thread pattern
  multiplies whatever it costs by the thread count — so an eager load charges the whole user base
  for something only some methods read. `zone_positions` is read by `certain_timezone_at` and
  `get_geometry` and by nothing on the `timezone_at` path, which makes it exactly that case.
  Rejected: reading it eagerly in `__init__`, which is otherwise attractive because the array is a
  kilobyte and eager loading opens no mapping. The rule pairs with the validation decision below —
  both are about **not making every construction pay for a question only some callers ask**, which
  is also why data-directory validation is opt-in. Applies directly to GH-536, whose open decision
  is the same one at a size where the pinning half is load-bearing too.
- **An id-taking interface validates at the public edge, never on the internal path.** Settled
  2026-08-20 for BUG-1, where four public methods index a list or array directly and so read a
  negative id as a valid index from the end — `zone_name_from_id(-1)` answers `Etc/GMT+12` rather
  than raising. Guarding in place was measured at ~10 ns, order 1 % of a unique-shortcut query, on a
  method called once per successful `timezone_at`; guarding the public methods and routing the seven
  internal callers through an unchecked private accessor costs about nine more lines and nothing per
  query. Rejected: guarding in place everywhere (pays the check on a path that cannot produce a bad
  id), and documenting the behaviour instead (leaves a public method answering a bad question with a
  real timezone name). The generalisable half is the placement rule, and it is the same shape as the
  validation decision above: a check belongs where the untrusted value enters, not where the
  settled one is used. It binds any future id-taking or sentinel-returning API — GH-499's
  `on_invalid` policy first, since `-1` is its natural sentinel.
- **A coordinate-reading interface never infers which column is which.** Settled in #504. Its first
  cut read bare `lng,lat` pairs positionally; for any longitude between -90 and 90 — most of the
  populated world — the swapped pair is still a valid coordinate, so a wrong order returns a real
  but wrong zone rather than raising. 13 of 15 major cities tested have a silently valid swap, and
  the wrong answers look plausible (Moscow's pair swapped gives `Asia/Tehran`). What shipped
  resolves columns by header name or by an explicit flag, and rejects input it cannot resolve
  instead of guessing. The same reasoning binds any future interface that takes coordinates in bulk
  — a batch API signature under GH-499, a file format, an `update_data`-style subcommand.
- **Has a timezone-boundary-builder release ever been bad? No.** So GH-501's guardrails are
  preventive, not corrective. That lowers their urgency but not their value: the argument never
  rested on a past incident, it rests on the pipeline auto-merging and auto-tagging with no human
  diff review.
- **A branch-name prefix is not an authorization check.** Settled in #519. The `workflow_run` jobs
  that merge and tag a data update select their work with
  `startsWith(head_branch, 'data-update-')`, and any fork can open a pull request from a branch
  with that prefix — the condition says which runs are *interesting*, never which are *trusted*.
  What gates the merge is the head repository's owner, checked in one shared composite action
  (`.github/actions/resolve-update-pr`) that every acting step resolves its pull request number
  through, so no step can grow a second copy that omits it. The same reading applies to any future
  workflow keyed on a branch, tag or path pattern.
- **The data distribution ships no reader — rejected.** Considered while planning the distribution
  split: move the binary-format layer (`flatbuf/generated/*`, `flatbuf/io/*`, `coord_accessors.py`,
  `np_binary_helpers.py`, `zone_names.py`, ~1,800 of ~4,250 LOC) into `timezonefinder-data`. The
  seam is real — exactly one edge crosses back — so feasibility was never the objection. It is
  **neutral on the only axis the split is about**: the reader is ~50 KB of pure Python and the C
  extension forcing the platform-wheel matrix stays in the lookup layer either way. It would make a
  reader bug cost a 63 MB upload; it relocates the compatibility problem rather than removing it,
  trading a cheap in-file format guard for an unguarded cross-distribution Python API on a package
  versioned by upstream data tags; it forces the upper bound on the *data* axis that the whole
  design refuses, since `timezonefinder 9.0` could not be trusted against a reader shipped in
  `timezonefinder-data 2029.1`; and it inverts the converter, which imports `flatbuf/io` to *write*.
  What it would genuinely have bought — the shortcut files carrying no identifier — was worth fixing
  directly, and #458 did. Not to be re-proposed without an argument that addresses the
  three-orthogonal-axes problem (data version, format version, reader-API version; one version
  number). Also recorded in `CLAUDE.md`.
- **The data version carries the format generation, not just the upstream release.** Recorded
  because the first draft got it wrong in a way that reads as reasonable: "floor only, no upper
  bound" on `timezonefinder-data`. That silently floats a pinned `timezonefinder` across a format
  break — the install resolves, the first lookup raises. The version is
  `<DATA_FORMAT_VERSION>.<year>.<letter>` with the letter in **bijective base-26** (`z`=26, `aa`=27,
  since upstream tags are `[a-z]+` and a lookup table would collide), and the root bounds it
  `>=…,<N+1`. The two mechanisms that look redundant are not: the version string governs
  *resolution* and is the only thing pip can read; the in-file identifier and `layout_version` govern
  *loading* and are the only thing protecting a hand-built `bin_file_location` — which has no
  distribution metadata at all — and the only thing that catches a *mixed* directory. Consequence:
  a format change is an **ordered two-distribution release, data first**.
- **The release-ordering check reads the built wheel and asks the index, and it sits ahead of the
  GitHub Release.** Shipped in #529. Reading the bound from `pyproject.toml` instead was rejected:
  the wheel is the artefact a resolver reads, and the only one whose metadata is what users get.
  The placement is equally deliberate — ahead of the **GitHub Release**, not next to the PyPI
  upload, because that Release is the first of the two steps that cannot be taken back, and the
  upload job depends on the one carrying the check, so one placement covers both. *Open, not
  settled:* whether the same property should additionally fall out of resolution, by having tox
  install `timezonefinder-data` from PyPI rather than from the workspace. That would trade a
  targeted release-time check for a side effect of every CI run, and it collides with the
  data-update pull request, whose whole purpose is to validate binaries that are by definition not
  published yet.
- **One repository, two distributions — the data does not get its own repository.** Settled in
  #446, which was opened proposing an org holding `timezonefinder` and `timezonefinder-data`
  separately. Publishing two PyPI projects from one repository is routine (a `uv` workspace, two
  Trusted Publishing entries, prefixed tags), so the question was only ever whether a second
  *repository* buys anything a second *distribution* does not. The argument that it did — every
  regeneration adds ~64 MB to this repository's history permanently — **does not survive**:
  deleting the data directory leaves every past blob in place, so the clone stays ~357 MiB either
  way. Only a history rewrite reclaims it (GH-522), and that is available to a single repository;
  what stops the *growth* is not committing the file again (DATA-BINARIES), likewise
  topology-independent. Against a second repository stand the writer/reader format sync `CLAUDE.md`
  already flags for `COORD2INT_FACTOR` / `DECIMAL_PLACES_SHIFT`, the deliberately shared
  `scripts/data_integrity.py`, doubled CI and release tooling for a solo maintainer, and a harder
  format-change bootstrap: across two repositories every format change needs a pre-release data
  wheel published from one before the other's pull request can go green. The generalisable part,
  worth applying to the next proposal of this shape: **ask whether a proposed repository split is
  really a distribution split.** Packaging, release cadence and download size are properties of the
  distribution; only history and access control are properties of the repository.
- **A release has one trigger, and it is the tag.** Found while releasing 8.3.0 and shipped since.
  `build.yml`'s `release` job used to be gated on `master` pushes *and* tags, so a plain push to
  `master` created the GitHub Release and its tag on its own. Two consequences that looked
  unrelated and were not: the ~10-minute tox matrix ran twice on the identical SHA, and a manually
  pushed tag raced the master run, where losing is silent (`git push` reports "Everything
  up-to-date", fires no webhook, and the release proceeds from a run the pusher is not watching).
  Two dead ends worth not re-walking. *Reusing the master run's build artifacts on the tag run*
  buys almost nothing — the wheels take ~1 minute and the matrix is ~10, so the expensive half is
  the part that cannot be copied. *Auto-releasing on merge* removes the last human checkpoint
  before an irreversible upload, which is the one gate `.claude/skills/cut-release` deliberately
  keeps. Skipping the matrix on tags also needs care in two places: a **skipped** `needs:` job
  skips its dependents unless the dependent's `if:` uses `!cancelled()`, and an ancestry check
  proves a commit is *on* master, not that a green run exists for that SHA — so the skip has to be
  paid for with an explicit assertion that one does.
- **The two point-in-polygon kernels are the same speed; numba's edge is the FFI crossing it does
  not make.** Measured in #497 on identical inputs: 239 vs 252 ns on a 114-vertex polygon, 22.18 vs
  22.27 µs on a 47k-vertex one — within 5 % across three size strata. What separates the two
  backends on an ambiguous query is the ~500 ns per candidate the clang path spends in
  `ffi.from_buffer`; on the *unique-zone* path numba is the slower of the two, because
  `validate_coordinates` calls two njit'd scalar functions whose dispatch costs more than the
  pure-Python comparison they replace (270 vs 218 ns). Recorded because "numba is the fast path" is
  the natural reading of the tox matrix and of `utils.py` preferring it, and it is not what the
  numbers say. Any future argument that reaches for a faster kernel has to say which kernel.
- **Below ~10 µs, `line_profiler` distorts the ratio it is being asked about — attribute time by
  sampling and by a stage ladder, and use `line_profiler` only for line *ordering* and for its
  exact hit counts.** Settled in #497 and implemented in `prototypes/query_stage_profile.py`, whose
  primary instrument is those hit counts — invariant under the perturbation, since deoptimising the
  interpreter does not change how many times a line runs — scaled by the time share of a signal
  sampler that installs no hooks. The ladder is the second instrument, for splits inside a block
  and for the ~1 µs strata no profiler resolves. The obvious objection ("subtract the probe cost")
  does not work, because its cost is **not** a per-line probe: enabling it deoptimises the
  whole interpreter, so code that never calls the profiled function slows down too — with only
  `timezone_at` registered, `validate_coordinates` measures 284 → 2,251 ns and `h3.latlng_to_cell`
  390 → 1,090 ns in loops calling neither, both reverting when it is switched off. The inflation is
  non-uniform by stage type: ~8× for a pure-Python stage, ~2.8× for a C-extension one, ~1× for time
  inside numba or the C extension. It therefore shifts attribution *away from geometry and towards
  the Python prologue* — the exact ratio #497 existed to settle. `prototypes/query_stage_profile.py`
  instead runs prefixes of the real function, each stopping one stage further on, and differences
  them; nothing is instrumented, and the copy is kept honest by measuring the real `timezone_at`
  underneath every table. *The ladder's own weaknesses, since it is a hand-rolled instrument:* it is
  a copy that can drift from the function it mirrors, and a stage measured as the difference of two
  large numbers is noise. The right independent check is a **sampling** profiler, not another
  instrumenting one — `py-spy` needs root on macOS, so the sampling half is a signal-based
  (`ITIMER_REAL`) sampler, which needs no privileges and installs no tracing hooks. **Wall clock,
  not `ITIMER_PROF`, on purpose:** CPU-time sampling hides memory stalls, and the mapped coordinate
  accessor (GH-536) — the largest single finding — is one, so a CPU-time profile would have missed
  it. It agrees: candidate loop 79.4 % of an ambiguous query against the ladder's 87.5 %, H3 4.7 %
  against 2.9 %, validation 2.4 % against 2.1 %. Its one apparent disagreement is a known artefact — signal
  delivery is deferred to the next bytecode boundary, so a numpy call's time lands on the
  *following* line. Read a sampler's line attribution as ±1 line. Applies to the next profiling
  pass of any hot path here.
- **Precomputing `last_zone_change_idx` into the shortcut binaries — measured, and refused.**
  Proposed twice: issue #256, closed in 2025 on the argument that throughput is dominated by the
  point-in-polygon work, and draft PR #348, which implemented it and is now closed with this
  reasoning. The half of that draft worth having shipped by another route — the hybrid shortcut
  binary stores a unique cell's zone id inline, so the common case never reaches a polygon list. #497 sizes what it
  removes: `get_last_change_idx` is 149 ns on numba and 283 ns on clang of a ~13.3 µs ambiguous
  query, and nothing at all on a unique-shortcut one — 1–2 % there, ~1 % of a random workload,
  below the 3–9 % noise of the machine that would have to demonstrate it. What it costs is a shortcut-layout version bump, therefore a
  `DATA_FORMAT_VERSION` bump, therefore an ordered two-distribution release. The 2025 verdict was
  right and now has a number under it; the open draft is superseded by this entry rather than
  pending. The Python-side half of the same block stays open as PERF-2, which needs no format
  change.
- **Shrink the runtime dependency surface (numpy / h3 / cffi / flatbuffers) — considered and
  parked.** Each does one small thing, so the idea recurs. Reimplementing H3 indexing is a
  well-known source of subtle bugs and `h3` sits on the common path of every query; an open item
  would be an invitation to attempt it. Revisit only if import time or cold start is ever measured
  to be a real problem.

---

## Scope notes

`prototypes/` is excluded throughout — it carries its own crop of ruff findings (`RUF012` mutable
class defaults, `RUF034` useless `if`/`else`, `B905` unstrict `zip`) that are appropriate to leave
in exploratory code.

`packages/timezonefinder-data/timezonefinder_data/data/` and `timezonefinder/flatbuf/generated/`
are generated and are never edited directly; findings there belong against the generator or the
schema instead.

The `timezonefinder-data` distribution is deliberately thin — one `DATA_DIR` constant and a version
in `packages/timezonefinder-data/timezonefinder_data/__init__.py`, plus the payload. Pass 10 read
it and found nothing; there is no code there to carry debt, and *Recorded decisions* above refuses
moving the binary-format reader into it.

An entry belongs here if it names something a pass could act on and later re-verify — code that
exists, a file that is built, a decision that can be taken. A finding with no such anchor can never
be resolved by the pass that reads it, so it stays open for ever.

---

## Coverage log

| Pass | Date | Swept | Not reached |
|---|---|---|---|
| 1 | 2026-08-06 | `timezonefinder/`, `scripts/`, `tests/`, `benchmarks/` — broad triage, findings above | `prototypes/` (deliberate), `docs/`, `.github/workflows/` |
| 2 (error diagnostics) | 2026-08-07 | Every `raise` and `except` site in `timezonefinder/` and `scripts/` (via `rg` plus ruff `B904`/`BLE`/`TRY`/`EM`/`RSE`/`S110`/`S112`); `timezonefinder/command_line.py` read in full | `docs/`, `.github/workflows/`, `benchmarks/`, `scripts/` report-rendering internals |
| 3 (CLI output path) | 2026-08-07 | `timezonefinder/command_line.py` and `tests/cli_test.py` (rewritten); the previously-unswept `timezonefinder/np_binary_helpers.py`, `benchmarks/conftest.py` and the `scripts/` benchmark-CI helpers (`normalize_benchmark_json.py`, `compare_benchmark_runs.py`, `benchmark_noise.py`) read in full; a repo-wide ruff `--select ALL` triage over everything but `prototypes/` and the generated bindings | `docs/`, `.github/workflows/`, `scripts/render_benchmark_reports.py`, `scripts/describe_benchmark_machine.py`, `benchmarks/test_*.py` |
| 4 (docstring contracts) | 2026-08-08 | The three previously-unswept modules — `scripts/render_benchmark_reports.py`, `scripts/describe_benchmark_machine.py` and all three `benchmarks/test_*.py` — read in full; `timezonefinder/timezonefinder.py`, `utils.py`, `zone_names.py`, `polygon_array.py`, `global_functions.py` re-read for docstring/behaviour agreement, every `:raises:`/`:return:` claim in `timezonefinder/` checked against the running code | `docs/`, `.github/workflows/`, `scripts/timezone_data.py`, `scripts/measure_memory.py`, `scripts/generate_benchmark_fixtures.py`, the larger `tests/` modules |
| 5 (checks that cannot fail) | 2026-08-09 | `tests/main_test.py`, `scripts/timezone_data.py`, `scripts/measure_memory.py` and `scripts/generate_benchmark_fixtures.py` read in full — the four previously unswept modules named by pass 4; every multi-statement `pytest.raises`/`pytest.warns` block in `tests/` and `benchmarks/` enumerated with an AST scan | `docs/`, `.github/workflows/`, `tests/test_benchmark_ci_tooling.py`, `tests/test_optimized_hybrid_shortcuts.py`, `tests/test_render_benchmark_reports.py` |
| 6 (packaging guard patterns) | 2026-08-10 | The five test modules pass 5 left unread — `tests/test_package_contents.py`, `tests/test_benchmark_ci_tooling.py`, `tests/test_optimized_hybrid_shortcuts.py`, `tests/test_render_benchmark_reports.py`, `tests/utils_test.py` — plus `tests/auxiliaries.py` and `tests/main_test.py` re-read; every `UNWANTED_DIST_PATTERNS` entry matched against the working tree, and `MANIFEST.in` / the `check-manifest` ignore list compared against it | `docs/`, `.github/workflows/` |
| 7 (leaked state and duplicate checks) | 2026-08-14 | `.github/workflows/` read in full - the last area with no coverage in any pass (new guard: `tests/test_python_version_support.py`); `scripts/hex_utils.py` and `scripts/shortcuts.py` re-read in full; `scripts/timezone_data.py`'s `ZoneCollection` validators read and given their first tests; a repeated repo-wide ruff `--select ALL` triage | `docs/` prose; `scripts/reporting.py` and `scripts/render_benchmark_reports.py` internals beyond the ruff sweep |
| 8 (the data report generator) | 2026-08-14 | `scripts/reporting.py` read in full — the last large module no pass had read end to end; `scripts/hex_utils.py`'s `Hex` cache properties and `scripts/utils.py` re-read. `uv run mypy` run by hand over `scripts/`, which the pre-commit hook excluded — the first time any pass had done so, and the mechanism behind most findings that pass | `docs/` prose; `scripts/shortcuts.py`, `benchmark_utils.py`, `file_converter.py`, `timezone_data.py`, `measure_memory.py`; `scripts/data_integrity.py` |
| 9 (scripts/ entry point and typing) | 2026-08-14 | The five `scripts/` modules pass 8 named as unreached, read at their mypy error sites and around them; `Makefile`, `update_data.sh` and `docs/2_use_cases.rst` compared for how the converter is invoked; `tests/main_test.py`'s cleanup class and `tests/auxiliaries.py` re-read. `uv run mypy` over `scripts/` (15 errors, all cleared, directory now in the hook) and over `tests/` (14 errors) | `docs/` prose; `scripts/data_integrity.py`; `scripts/reporting.py` internals |
| 10 (the data-package split, and `tests/` typing) | 2026-08-19 | The six modules the distribution split added or rewrote, none of which any pass had read: `packages/timezonefinder-data/timezonefinder_data/__init__.py`, `scripts/data_integrity.py`, `scripts/check_data_dependency.py`, `scripts/data_releases.py`, `timezonefinder/flatbuf/schemas/__init__.py` and `timezonefinder/zone_names.py` — plus `tests/test_integration.py` and `tests/test_script_invocations.py`. Every open entry re-verified against the current code; `uv run mypy` re-run over `tests/` (19 errors, the 8 real ones cleared and the directory now in the hook) | `docs/` prose; the larger new test modules read only at their headers; no repeat of the repo-wide `--select ALL` triage |
| 11 (register unification) | 2026-08-20 | No source sweep: the roadmap issue's ranking, sequencing and recorded decisions were migrated into this file and the two pass skills merged into one. Every entry's anchor re-verified against the working tree, and every issue the file names checked for state - which found #498 (runtime dataset provenance) shipped in #523 and deleted it | everything else — this pass read the register and the skills, not the code |

Every module under `tests/` has been read at least once, pass 7 covered `.github/workflows/`, pass 8
`scripts/reporting.py` and pass 10 everything the data-distribution split added. The only area with
**no coverage in any pass** is `docs/` prose. The cheapest real starting point is therefore the
ranking above rather than fresh discovery — with two things worth knowing.

Running mypy by hand over a directory the pre-commit hook excludes surfaced defects no pass had
seen, twice: 15 in `scripts/` and 8 real ones in `tests/`. **Both directories are now in the hook**,
so that particular seam is closed and the technique has nothing left to find here — `prototypes/`,
`docs/` and `benchmarks/` are what the exclude still names, and the first of those is out of scope
by choice.

And an open entry's *premise* goes stale faster than its location. Pass 10 re-verified all of them
after six merged pull requests and found one conclusion resting on something untrue (TOOL-1's B905
site) and one half-shipped by unrelated work (DEAD-5's annotation). Re-verify before ranking, not
after picking.

The `--select ALL` triage is worth repeating, but its output needs filtering: 180 findings, of which
the ones already judged not worth acting on are `EXE001`/`EXE002` (shebangs on modules run via
`-m`), `S311` (the fixture samplers are not cryptographic), `S603`/`S607` (subprocess calls in tests
and build scripts with fixed argument lists), `RUF022`/`RUF023` (`__all__` ordering — the current
order groups by meaning, which is more useful than alphabetical) and the `TD`/`FIX` family.

---

## Deliberately checked and found sound

Do not re-raise these.

- Pass 2: the broad `except Exception` in `MemoryCoordAccessor`/`FileCoordAccessor.__init__` (cleans
  up partial state and re-raises), `utils.close_resource`'s suppression list (documented at length,
  `BufferError` included on purpose), `TimezoneFinder.__del__`'s two-tier handler (warns on the
  unexpected case), and `scripts/reporting.py`'s `main` catching `Exception` to print a traceback
  and return an exit code.
- Pass 3: `coord_accessors.py`'s bare `open()` (ruff `SIM115`) — the handle deliberately outlives
  the call and is closed by `cleanup()`; the `profile` name probes in `scripts/hex_utils.py` and
  `scripts/shortcuts.py` (ruff `B018`) — the standard `line_profiler` idiom, not a stray
  expression; `scripts/measure_memory.py`'s `subprocess.run` without `check=` (ruff `PLW1510`) —
  it inspects `returncode` on the next line and raises with the child's output, which is strictly
  better than `CalledProcessError`; and `np_binary_helpers.py`'s six near-identical `get_*_path`
  helpers — collapsing them into a mapping would trade six importable names for one lookup key and
  works against the declare-each-path-once rule.
- Pass 4: `scripts/describe_benchmark_machine.py` (read in full, nothing found); the three
  `benchmarks/test_*.py` suites (thin by design — parametrize tables plus a `_run_over` loop, and
  the shared `_run_over` in two of them is deliberately not hoisted into `conftest.py`, since an
  import would put a function call between the benchmark and the code it times);
  `render_benchmark_reports.py`'s four `render_*` functions sharing a load/headline/table/summary
  shape — extracting it would trade four readable functions for a framework, and the differences
  are exactly the report-specific parts.
- Pass 5: `scripts/measure_memory.py` (read in full, nothing found);
  `benchmarks/test_inside_polygon.py`'s `STRATA` list, which repeats the `PIP_STRATA` names as
  explicit `pytest.param` ids — deliberate, since `CONTRIBUTING.md` requires benchmark ids to be
  written out rather than derived, and deriving them from a data file would let a fixture
  regeneration silently reset chart history; `tests/main_test.py`'s `test_edge_shortcut_validity`,
  which asserts nothing beyond "does not raise" on the base class — that *is* its subject, and
  `test_edge_shortcut_result` covers the expected values for the class that has polygon data.
- Pass 6: `tests/test_benchmark_ci_tooling.py` and `tests/test_render_benchmark_reports.py` (both
  read in full, nothing found — each assertion names why it exists); `tests/auxiliaries.py`'s
  `matches_pattern`, whose `fnmatch` semantics (`*` crosses `/`, POSIX case sensitivity) are what
  the packaging patterns depend on and are correct as documented; the `.git/*` entry in
  `UNWANTED_DIST_PATTERNS`, which matches nothing in a working tree by design and is exempted
  rather than removed.
- Pass 7: `.github/workflows/benchmark.yml`, `benchmark-comment.yml`, `check_data_updates.yml` and
  `release_data_update.yml` (read in full, nothing found beyond the version drift now guarded);
  `timezonefinder/global_functions.py`'s module-level `TF_INSTANCE` and its `global` statement
  (ruff `PLW0603`) — deliberate and documented as not thread-safe, with per-thread instances the
  stated alternative; `scripts/hex_utils.py`'s `get_corrected_hex_boundaries` (the antimeridian and
  pole clipping, covered by `tests/hex_utils_test.py`).
- Pass 8: `scripts/reporting.py`'s two output redirectors — `redirect_output_to_file` (a decorator,
  opening `"a"`) and `redirect_output_to_file_contextmanager` (opening `"w"`) — which look like
  duplicates but differ in append-vs-truncate, and both have callers that depend on which they got;
  `calculate_shortcut_index_stats`'s `naive_storage_bytes`, whose conditional covers the whole
  parenthesised expression rather than just the division, so a zero entry count yields `0 * 0` and
  not a `ZeroDivisionError` — correct, and confusing enough to re-derive rather than re-raise;
  `generate_metrics_rows`'s non-numeric `str(value)` fallback, kept reachable by annotating the
  parameter `Mapping[str, object]` rather than deleted to satisfy a narrower annotation.
- Pass 10: `scripts/data_integrity.py` (read in full — its two validators each build their own
  `PolygonArray`/`HoleArray`, which looks like duplication and is not worth collapsing: they are
  separate entry points with different subjects, one about whether a directory's files agree and
  one an expectation about the upstream data, and `__del__` releases the accessors either way);
  `packages/timezonefinder-data/timezonefinder_data/__init__.py` and `scripts/data_releases.py`
  (read in full, nothing found); `timezonefinder/zone_names.py`, whose asymmetric defaults —
  `read_zone_names` takes a path, `write_zone_names` requires one — are deliberate and documented,
  since defaulting the write side to `DEFAULT_DATA_DIR` would rewrite the installed dataset in
  `site-packages`.
