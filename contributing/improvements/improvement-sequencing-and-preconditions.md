# Improvement sequencing and preconditions

Check these explicitly before taking an item, and name the blocking one when you skip it.

```
GH-542 (precision) ─→ GH-449 (encode) ─→ [data 2.x release] ─→ DATA-BINARIES ─→ GH-522
                                              (the held format-2 window)   (stop committing)  [strictly after]

GH-543 (cffi bump) ─→ GH-364's abi3t option

GH-500 (ordering invariant enforced) ─→ GH-513 (drop holes)   [GH-301 is NOT a blocker — rejected]

API-2 ─→ API-1   [same major; API-2 first, it decides how much surface API-1 touches]

GH-500 ←→ GH-428: one CLI design — SETTLED (subcommands), so neither waits on the other

PERF-1 (ocean check without a regex) ─→ BATCH-1 (batch `timezone_at_land`)

independent: GH-362, GH-524, PERF-2, GH-543
   GH-502 is independent too, but should ride the API major so the docs are rewritten once
```

- **Regenerating the packaged data is a normal thing for an item to do**, and no item is parked for needing it. Two things it has to respect: it must not collide with the weekly data-update pipeline, which opens *and auto-merges* its own pull requests, so rebase before the final gate; and it must not be incidental — the diff should list only binaries the change had a reason to move, since the cost is per *file* and a regeneration that leaves a file byte-identical costs nothing.
- **Format changes are cheaper in a row than spread out, so rank them together once one lands.** A `DATA_FORMAT_VERSION` bump numbers a release, not a change: while one sits unreleased on `master`, the next format change rides the same number and the ordered two-distribution release is paid once for both. The ranking prices each format item as if it paid that release alone, which is right for the first one and wrong for every one after it — so when a bump is pending, promote the other format items rather than reading their entries literally. GH-449 and GH-542 are the pair this applies to first, with GH-513 behind them.
- **DATA-BINARIES itself waits on a published `timezonefinder-data` 2.x.** Its bootstrap resolves the version the checkout pins, and the pending `DATA_FORMAT_VERSION` 2 bump has not been released, so today that resolves nothing. Its entry carries the one-command check.
- **GH-449 now sequences *before* DATA-BINARIES, not after — the maintainer held the 2.x release open so the encoding rides format 2.** The older ordering ran the other way, on the ground that uncommitting the binaries first makes every later regeneration cheap in history. That reasoning still holds and is simply outweighed: ~61 MiB of pack growth is recoverable by GH-522, whereas a second ordered two-distribution release is not, and waiting for DATA-BINARIES *guarantees* the extra release because DATA-BINARIES cannot start until the very publication that shuts the window. The [format-batching decisions](decisions/data-format-version-marker-and-release-batching-decisions.md) carry the mechanics and the exit condition.
- **Do not start GH-522 before DATA-BINARIES is in force.** A history rewrite followed by one more data update through the current pipeline re-adds ~61 MiB immediately, and the rewrite — which detaches every existing clone and fork — would have to be repeated. The distribution split does **not** satisfy this on its own: the binaries are still committed, only at a new path.
- **Publish the data distribution before the code release that requires it**, on every change that bumps `DATA_FORMAT_VERSION`. Since PR #529 this is *enforced*: the release job refuses to go on if no published `timezonefinder-data` satisfies the bound in the wheel it is about to publish. The rule stays stated because the guard blocks the wrong order without performing the right one — it tells you the data release is missing, it does not make it. Worth knowing: the guard runs only on tag refs, so **no pull request ever exercises it**, and the first time it can speak is the run that is already publishing. Dry-running it against a locally built wheel costs a minute and is the only way to learn its answer while the version is still spendable.
- **The candidate loop has already been made ~35 % cheaper once, so price against the current baseline and not against any figure you remember.** Fetching a candidate's coordinates fell from ~4.9 µs to ~0.83 µs when the coordinate accessors stopped re-walking the FlatBuffers structure per lookup, which moved the vertex count below which a candidate costs more to *fetch* than to test, and took the mapped mode from ~30 % slower than in-memory to within ~5 % of it. Anything ranked on the *time* in that loop — GH-364, GH-513 — inherits that: what is left may now sit inside the noise floor, in which case a native loop cannot be justified on speed at all. *The measured baseline* below is current as of its anchor; re-read it rather than an entry's prose. **A count is the exception, and it is the cheaper instrument.** What a change removes in candidates *tested* does not depend on what a candidate costs, so it can be enumerated over the packaged index today, and the answer survives a change to what a candidate costs, a new machine and a data update alike. That is what settled GH-301 without waiting: reach for the count first, and only price it in time if the count leaves the question open.
- **BATCH-1 waits for PERF-1 so that the batch form is not born with a regex per point.** The ocean check is the last step of `timezone_at_land`, and batching a lookup that ends in a `re.match` per answer reintroduces exactly the per-point work a batch exists to remove. After PERF-1 the check is a property of the *zone id*, which a batch can apply as one mask over the whole answer — cheaper per point than the scalar method, rather than merely equal to it.
- **GH-505 is gated on publicly voiced user interest.** Never implement it; only report whether interest has appeared.
- **Do not re-propose anything in the topic decision files linked from the [register rules](improvement-register-rules.md) without new evidence.**

---
