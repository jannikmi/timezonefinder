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
| GH-499 | Batch / array lookup API | public API | L | needs decisions |
| DATA-BINARIES | Stop committing the packaged data binaries | packaging | L | needs a decision |
| GH-449 | Polygon encoding: delta + varint | data format | L | blocked by DATA-BINARIES |
| BUG-1 | A negative zone or boundary id returns the wrong zone | correctness | ~6 | needs a decision |
| DOC-3 | The `zoneinfo` snippets never say Windows needs `tzdata` | docs | ~3 | free |
| GH-477 | Replace the shortcut dict with flat arrays | performance | M | free |
| GH-501 | Guardrails on the automated data update pipeline | release | M | needs decisions |
| GH-500 | Validate a data directory's cross-file invariants | data integrity | M | needs the CLI-shape decision |
| GH-428 | Data parsing UX, and the CLI shape it shares with GH-500 | CLI / UX | M | needs the CLI-shape decision |
| GH-536 | The mapped coordinate accessor costs 4.9 µs per candidate | performance | M | needs a decision |
| GH-301 | Sort shortcut polygons by overlap area | performance | M | needs the `shapely` decision |
| GH-364 | Free-threaded Python, via a native candidate loop | performance | L | needs scoping |
| GH-502 | First-class `zoneinfo` / UTC-offset helpers | public API | S–M | needs a decision |
| GH-332 | Reduced timezone dataset as a second distribution | packaging | M | needs a decision |
| TOOL-7 | The data-dependency guard checks one wheel of however many it finds | release | ~10 | needs a decision |
| TOOL-6 | `parse_data` rewrites the committed data report whatever `-out` it was given | tooling | ~10 | needs a decision |
| API-1 | `AbstractTimezoneFinder.__init__` takes an `in_memory` it never uses | public API | ~10 | needs a decision |
| API-2 | Every submodule is reachable as a package attribute | public API | ~20 | needs a decision |
| BIG-4 | `load_binary_data`'s hole branch silently yields empty lists | diagnostics | ~8 | check whether it is a behaviour change |
| BIG-1 | `_iter_boundary_ids_of_zone` re-opens `zone_positions.npy` on every call | performance | M | needs a decision + benchmark |
| GH-317 | Reduce the release artifact count | packaging | S | free |
| GH-524 | Move `timezonefinder` under `packages/` | repo layout | M | free |
| GH-362 | Reuse the `PolygonArray` binaries in file conversion | internal | M | free |
| BIG-3 | The GeoJSON parser threads nine accumulator lists through three call levels | internal | ~120 | verification is the expensive part |
| PERF-1 | `is_ocean_timezone` runs a regex on the `timezone_at_land` path | performance | ~15 | free — the ceiling is one profiler run |
| PERF-2 | Two numpy calls over a handful of candidates cost 0.8 µs | performance | ~25 | free — ranked on simplicity, not on the timing |
| DUP-1 | The coordinate bounds are declared three times | internal | ~6 | free — the exposure is bounded below noise |
| BIG-2 | `calculate_shortcut_index_stats` computes four unrelated things in one pass | internal | ~80 | free |
| TOOL-1 | ruff runs close to its default rule set | tooling | M | free |
| DEAD-5 | `REDUCED_TIMEZONE_MAPPING` has no consumer | internal | ~35 | needs a decision |
| GH-522 | Shrink the repository history by dropping the committed binaries | repo history | L | blocked by DATA-BINARIES |
| GH-513 | Drop hole polygons entirely | data format | L | blocked by GH-301 + GH-500 |
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
  cost is the fetch rather than the geometry. Anything ranked on the size of the candidate loop
  — GH-301, GH-364, GH-513 — is measured **after** GH-536 lands, not before.
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
- **Status:** needs decisions.
- **Last touched:** 2026-08-20 — migrated from the roadmap issue, rank unchanged.

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
- **Status:** blocked by DATA-BINARIES.
- **Last touched:** 2026-08-20 — migrated from the roadmap issue, rank 2 there.

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
- **Measure it after GH-536, not before.** Its ceiling is the candidate loop, and GH-536 removes
  ~half of what a candidate costs; a before/after taken on today's tree credits ordering with
  time that another item is about to delete.
- **Status:** needs the `shapely` decision. Prerequisite for GH-513.
- **Last touched:** 2026-08-20 — migrated from the roadmap issue.

### GH-536 — the memory-mapped coordinate accessor costs 4.9 µs per candidate polygon

- **Tracks:** issue #536, opened from #497's measurement — a finding nothing was looking for.
- **Why it matters:** on the default mapped mode, fetching a candidate's coordinates costs an order
  more than the FFI crossing or the geometry kernel for anything but the largest polygons — 47 % of
  an ambiguous query, paid by exactly the constrained-memory deployments the mapped mode exists for.
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
- **Status:** needs scoping.
- **Last touched:** 2026-08-20 — migrated from the roadmap issue, rank 8 there.

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
- **Status:** blocked by GH-301 + GH-500.
- **Last touched:** 2026-08-20 — migrated from the roadmap issue, rank 10 there.

### GH-505 — distance to the nearest timezone border

- **Tracks:** issue #505, a demand-signal issue.
- **Status:** conditional on publicly voiced user interest — **never implement it unprompted**; only
  report whether interest has appeared. It is an L-sized permanent maintenance surface justified by
  a hypothesis about who wants it, so the demand signal comes first.
- **Last touched:** 2026-08-20 — migrated from the roadmap issue, rank 11 there.

### PERF-1 — `is_ocean_timezone` runs a regex on the `timezone_at_land` path

- **Location:** `timezonefinder/utils.py`, `is_ocean_timezone`; called from
  `AbstractTimezoneFinder.timezone_at_land`.
- **Defect:** the check is `re.match(OCEAN_TIMEZONE_PREFIX, timezone_name)` against the result
  *string*, on every call. Ocean-ness is a fixed property of a zone id for a given dataset, so this
  recomputes a constant from a string per query and couples a behavioural decision to zone naming:
  an upstream rename of the `Etc/GMT` family would silently change which results count as ocean.
- **Fix:** precompute a boolean array indexed by zone id once at load and test that instead.
  Correct by construction, faster, and decoupled from naming. Size: ~15 lines.
- **Take the ceiling before the before/after.** `prototypes/query_stage_profile.py` prices the
  stage on the `on_land` stratum in one run; that number is the most this can ever win, and it
  decides whether the full before/after in a no-numba environment (`uv sync --group test`, then
  `make benchmark-noise`) is worth taking at all. Expect it at or below the noise floor, for the
  reason the next bullet gives, in which case this ships as a correctness-and-clarity change or not
  at all and is ranked there. It also adds a small per-instance array, which `make memory` would
  show. **Neither number has been taken yet** — record both here when you do.
- **Value:** low to moderate. `timezone_at_land` is public and the packaged data covers the oceans,
  so the branch is taken constantly — but the regex runs on the *result*, after the lookup that
  dominates the query.
- **Status:** open.
- **Last touched:** 2026-08-13 — found by a wide-angle review.

### BIG-1 — `_iter_boundary_ids_of_zone` re-opens `zone_positions.npy` on every call

- **Location:** `timezonefinder/timezonefinder.py`, `_iter_boundary_ids_of_zone`.
- **Defect:** calls `np.load(..., mmap_mode="r")` per invocation, under a comment reading *"load
  only on demand"*. Off the `timezone_at` hot path but on `certain_timezone_at`'s and
  `get_geometry`'s.
- **Why it is not a straight refactor:** caching it is a memory/latency trade, and `CLAUDE.md` is
  explicit that the memory-mapped path must stay viable for constrained containers. Needs a
  decision plus a benchmark, not just an edit.
- **Status:** needs a decision.
- **Last touched:** 2026-08-07 — re-verified, unchanged.

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
  alone. Confirm with `make benchmark-noise` in a no-numba environment if you want the number on
  record, but do not gate the change on it.
- **Status:** open.
- **Last touched:** 2026-08-07 — re-verified, unchanged.

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
- **Ranked on simplicity, not on the timing.** A 6 % ceiling on one stratum is the same order as the
  machine's own noise, so the benchmark suite cannot demonstrate it and it must not be sold as a
  speed-up; what carries it is that a scalar loop over three elements is also the simpler code. Take
  the before/after with `prototypes/query_stage_profile.py` on both backends anyway, and record it
  here — it is the only place the number will exist.
- **Status:** open.
- **Last touched:** 2026-08-20 — from #497's finding 6, which reached no entry when the rest of that
  profiling did.

---

## Public API and behaviour

### BUG-1 — a negative zone or boundary id silently returns the wrong zone

- **Location:** `timezonefinder/timezonefinder.py`, `AbstractTimezoneFinder.zone_id_of` and
  `zone_name_from_id`.
- **Defect:** both index a Python list / numpy array directly, so a negative id is a valid index
  counting from the end rather than an error. Measured against the packaged data:
  `zone_name_from_id(-1)` returns `Etc/GMT+12` and `zone_id_of(-1)` returns `443`, with
  `nr_of_zones == 444`. `zone_name_from_id` explicitly range-checks in its `except IndexError`
  handler, which a negative id never reaches, so the guard reads as complete and is not.
- **Value:** a caller propagating a `-1` sentinel — the conventional "not found" from an index
  lookup — gets a plausible timezone name back instead of an exception. Both are public API.
- **Fix:** reject `< 0` explicitly in both, alongside the existing upper-bound check. Size: ~6
  lines. **This is a behaviour change** (a call that returns today would raise), so it wants a
  maintainer decision and a changelog bullet in the main list.
- **Status:** needs a decision.
- **Last touched:** 2026-08-08 — found and measured while correcting the `:raises:` lines of the
  same two methods.

### GH-502 — first-class `zoneinfo` / UTC-offset helpers

- **Tracks:** issue #502.
- **Why here:** moves the two most common downstream steps into the library. See DOC-3 for the
  Windows caveat any such helper inherits.
- **Status:** needs a decision on the API surface.
- **Last touched:** 2026-08-20 — migrated from the roadmap issue, rank 9 there.

### API-1 — `AbstractTimezoneFinder.__init__` takes an `in_memory` it never uses

- **Location:** `timezonefinder/timezonefinder.py`, `AbstractTimezoneFinder.__init__`.
- **Defect:** the parameter is accepted and then not read; `TimezoneFinder.__init__` applies its
  *own* copy of the argument to the two `PolygonArray` constructors after calling `super()`. The
  base class loads only data it always keeps in memory, so there is nothing for it to select.
- **Fix:** either drop it from the base signature (subclasses stop forwarding it) or have the base
  store it for subclasses to read. Size: ~10 lines.
- **Why it is not a straight refactor:** `AbstractTimezoneFinder` is importable from the package
  root, so a signature change is public API surface, and `TimezoneFinderL` accepts `in_memory`
  purely to forward it. Needs a decision on whether that parameter should exist at all.
- **Status:** needs a decision.
- **Last touched:** 2026-08-08 — documented accurately rather than changed.

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
  first. Same shape as API-1.
- **Status:** needs a decision.
- **Last touched:** 2026-08-13 — found by a wide-angle review; verified by running
  `dir(timezonefinder)`.

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
- **Status:** needs a decision.
- **Last touched:** 2026-08-20 — migrated from the roadmap issue, where it was ranked 3 as "#446
  decision 2". Ranked above GH-449 here because the list is walked top-down and GH-449 is
  blocked by it.

### GH-501 — guardrails on the automated data update pipeline

- **Tracks:** issue #501.
- **What it is:** the weekly pipeline auto-merges and auto-tags a PyPI release from an unpinned,
  unchecksummed, undiffed 64 MB upstream drop. The release-notes half shipped in #519 — a data
  release is now withheld whenever anything else is pending. What remains is that nothing knows
  what the 64 MB actually changed. Its one prerequisite is met: #523 exposed the dataset version at
  runtime (`timezonefinder_data.__version__`), so a diff report has something to name.
- **Decisions still open:** which thresholds block an automated release, and what happens when one
  trips.
- **Preventive, not corrective:** no timezone-boundary-builder release has ever been bad. That
  lowers the urgency and not the value — the argument never rested on a past incident, it rests on
  the pipeline auto-merging and auto-tagging with no human diff review.
- **Status:** needs decisions.
- **Last touched:** 2026-08-20 — migrated from the roadmap issue, rank 5 there.

### GH-317 — reduce the release artifact count

- **Tracks:** issue #317.
- **What it is:** the PyPI project storage quota (10 GB, already hit, old releases deleted to
  recover space), driven by *artifact count × artifact size*. GH-449 owns size; this owns count.
- **Largely answered by the distribution split:** the data is no longer one of the artifacts. A code
  release now ships three platform wheels plus an sdist of a few hundred KB each instead of ~65 MB
  each, and the data ships once per data release as a single `py3-none-any` wheel with no sdist.
  What is left is whether three near-identical platform wheels are worth shipping at all — they are
  **99.995 % identical**, differing only in a 2,915-byte `.so`.
- **Status:** open.
- **Last touched:** 2026-08-20 — migrated from the roadmap issue.

### GH-332 — reduced timezone dataset as a second distribution

- **Tracks:** issue #332 (and GH-334 for the mapping).
- **The reframing:** 92 zones instead of 444. It reads as a build-time switch and is really a second
  published data distribution the user installs instead — which turns a hard problem into a
  packaging decision.
- **Now unblocked:** the distribution split shipped the machinery it needs — a workspace member, a
  `DATA_DIR` indirection and a version scheme — and it no longer depends on DATA-BINARIES.
- **Status:** needs a decision on whether to publish a second data distribution at all.
- **Last touched:** 2026-08-20 — migrated from the roadmap issue.

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
- **Status:** needs a decision.
- **Last touched:** 2026-08-19 — found on the first read of the module.

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
- **Why it needs a decision:** either fix changes where a file is written for anyone calling
  `parse_data(output_path=...)`, which is a behaviour change. In the meantime `make testparse`
  carries a comment saying to restore the file.
- **Status:** needs a decision.
- **Last touched:** 2026-08-14 — found immediately after making `make testparse` runnable again;
  before that the target could not reach the report-writing code at all, which is why no earlier
  pass saw it.

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
- **Fix:** raise, or state the absence in the report. Size: ~8 lines. **Check first whether this is
  a behaviour change** — if any caller compiles data without holes, it is, and the entry belongs
  under *Behaviour and public API* instead.
- **Value:** low-moderate, and narrower than when this entry was first written. It originally also
  covered the function being 37 statements with a function-local import mid-body; PR #509 rewrote
  the loads through `PolygonArray`/`HoleArray`, taking it to 24 statements with no local import, so
  only the silent-empty branch is left.
- **Status:** open.
- **Last touched:** 2026-08-14 — re-verified after rebasing onto #509; the size complaint it was
  written about is gone.

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
- **Status:** needs a decision.
- **Last touched:** 2026-08-19 — annotation half shipped, deletion still open.

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
  point-in-polygon work, and draft PR #348, still open and implementing it. #497 sizes what it
  removes: `get_last_change_idx` is 149 ns on numba and 283 ns on clang of a ~13.3 µs ambiguous
  query, and nothing at all on a unique-shortcut one — 1–2 %, below the 3–9 % noise of the machine
  that would have to demonstrate it. What it costs is a shortcut-layout version bump, therefore a
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
