# Query performance measurement baseline

Every timing quoted in this file comes from one run of `prototypes/query_stage_profile.py`, whose `FINDINGS` block holds the full per-stage breakdown. Repeated here is only what the ranking needs: the denominators, and how to tell whether they still describe the tree.

- **Taken at** `590e21b`, 2026-08-23 (**this SHA is an operand, not a citation** — the freshness command below diffs against it, so GH-522's history rewrite invalidates it and the baseline has to be re-anchored and re-measured in the same pass) — Apple arm64, Python 3.14.2, data 2026c, fixture set v3, both acceleration backends, both coordinate-access modes. Re-measured wholesale when the H3 shortcut index moved from resolution 3 to 4, which re-labels the strata as well as re-weighting them; the previous anchor predates that move, and figures from the two runs are not comparable stage by stage.
- **The denominators.** A unique-shortcut query is ~1.0 µs and contains no geometry at all; an ambiguous one is ~11.2-11.7 µs on the default mapped mode and ~10.4-11.0 µs with `in_memory=True`. The two backends differ by under 9 % on both. Every share below is a share of one of these, and the entry says which — a share of an ambiguous query is not a share of a workload.
- **Freshness check**, before ranking anything on one of them:

  ```
  git diff --stat 590e21b..HEAD -- timezonefinder/ packages/timezonefinder-data/timezonefinder_data/data
  ```

Empty ⇒ the numbers describe the current tree. Non-empty ⇒ classify what changed. A docstring, an `__all__` list or a rename leaves them standing and is worth recording here so the next pass does not re-derive it; a change to the lookup flow, the polygon math, the coordinate accessors, the shortcut reader or the packaged data does not.

Read the [query-path change-classification log](query-path-change-classification-log.md) only when the freshness diff is non-empty or when adding a new classification.
- **One machine took these, so rank on what survives leaving it.** In descending order of how well a figure travels:

  1. **Counts, which are exact and machine-independent** — a line's hit count does not depend on the hardware, only on the code. 1.05 candidate polygons per ambiguous query, 0.11 per uniformly random one; one FFI crossing and one buffer acquisition per candidate on the clang/mapped path; two numpy calls per ambiguous query. State what a change removes as a count first, and use time only to size it.
  2. **Shares within one query**, which travel but not uniformly: the stages are bound by different things — memory latency for the mapped accessor, interpreter dispatch for the Python prologue, floating-point throughput for the kernel — so another machine re-weights them against each other. Read a share as an order of magnitude, never to one percentage point.
  3. **Absolute nanoseconds, which are this machine's alone.** Never rank on one, and never compare one to a figure from CI or from a report page.
- **Rank the `clang` / `in_memory=False` column, not the development machine's.** A dev checkout runs numba on whatever laptop is to hand; a plain `pip install` in a constrained container runs the C extension against memory-mapped data, which is why `docs/benchmarking_methodology.rst` makes that the tracked configuration for CI too. Both are measured, so this costs nothing but the discipline of reading the right column.
- **A share of a stratum is not a share of a workload.** Uniformly random points are ~11 % ambiguous (that page again), and an ambiguous query costs ~11x a unique one on the mapped path, so ambiguous work is ~57 % of a realistic mixed wall clock and unique work ~43 %. Multiply the stratum share through before comparing two items that live on different strata — that multiplication is a property of the fixtures, not of the machine, so it survives the move.
- **A stage's share bounds its upside and says nothing about its downside, so a small stage is a constraint rather than an opportunity.** The shortcut lookup is 117-145 ns — **13-15 % of a unique query, ~1 % of an ambiguous one, ~7 % of the uniformly random stratum**. Making it infinitely fast wins at most ~7 %. Making it slower is not bounded that way: the `searchsorted` layout refused for it measured **+93 % of a unique query**, and resolution 4 sharpened that asymmetry rather than softening it — ~89 % of a random workload is now answered on the unique path, so a unique-path regression is amplified where it used to be diluted. For any stage the ladder puts in single digits — `zone_name_from_id` at 4-6 % is the other one — ask whether a change keeps it free, never whether it makes it faster, and settle it on a whole-query A/B rather than on a microbenchmark of the stage. `docs/benchmarking_methodology.rst` carries the three A/B designs that got this wrong before it was settled.
- **Where a unique query's time actually is, and therefore where a real win has to come from:** `validate_coordinates` ~34 % and `h3.latlng_to_cell` ~49 % — **83 % in two calls before any lookup logic runs.** The batch lookups hit the same wall from the other side: they hoist validation and the table read out of the loop and are left paying one scalar `latlng_to_cell` per point, which is why they buy ~1.6x on the unique stratum and not more. Neither is a shortcut-side optimisation.
- **A second machine class exists for the shortcut format change, and it is CI's.** The benchmark workflow measured base and head in one job on an **AMD EPYC 7763** (Linux, the C extension, no numba - the tracked configuration), which is the cross-check this section asks for and the only figures here not taken on one laptop. The shortcut-format change's branch head against its merge base - which is the format change alone, before the H3 resolution moved to 4 and traded part of the footprint win back for query speed, so read the memory rows as what the format bought rather than as where the branch landed:

  | | base | head | |
  |---|---:|---:|---|
  | `timezone_at[unique_shortcut-in_memory]` | 4.305 ms | 3.832 ms | **-11.0 %** |
  | `timezone_at[random-in_memory]` | 13.500 ms | 12.943 ms | -4.1 % |
  | `timezone_at[ambiguous_shortcut-in_memory]` | 40.086 ms | 39.258 ms | -2.1 % |
  | `TimezoneFinderL::init_heap` | 4.47 MiB | 175 KiB | **-96.2 %** |
  | `TimezoneFinderL::init_rss` | 13.3 MiB | 244 KiB | **-98.2 %** |
  | `TimezoneFinder[file_based]::init_heap` | 4.53 MiB | 246 KiB | **-94.7 %** |
  | `TimezoneFinder[file_based]::init_rss` | 13.8 MiB | 860 KiB | **-93.9 %** |
  | `TimezoneFinder[in_memory]::init_rss` | 74.9 MiB | 62.0 MiB | -17.3 % |

Two things to read from it. The **memory figures are `tracemalloc` heap and near-deterministic**, so `-96 %` is signal and not jitter, unlike the query rows where a few percent is the runner's own noise. And the `-11 %` on the unique stratum is the branch *whole*, not the format change: that was measured neutral on its own, and the slot-arithmetic reduction accounts for ~5 % of it. **Attribute a combined number to its parts before quoting it**, which is why the changelog says the format change buys memory and load rather than speed.
- **The 2x rule, for what none of the above fixes.** Act on a difference only if it survives any single stage turning out 2x cheaper or 2x more expensive elsewhere. It keeps the large calls (a 37 % workload share stays large at half the size) and refuses the ones that only exist on this laptop. An item that fails the rule and still matters needs a second machine class — the profiler is one script over committed fixtures, so a run in a Linux x86 container is the cheap way to get one; record it as a second column here, described the way `scripts/describe_benchmark_machine.py` describes a benchmark run's machine.
- **Re-measuring belongs to the change that invalidates it**, not to a follow-up pass. A pull request that moves the critical path re-runs the profiler on both backends (a few minutes each), and updates the `FINDINGS` block, this anchor and every share it moved, in that same pull request. Numbers left behind do not announce themselves: an entry ranked on a share that is no longer true reads exactly like one that is, which is the failure this file exists to prevent.

---
