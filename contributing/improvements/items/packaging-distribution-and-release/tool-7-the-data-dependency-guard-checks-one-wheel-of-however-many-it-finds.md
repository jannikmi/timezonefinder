# TOOL-7 — the data-dependency guard checks one wheel of however many it finds


## Related memory

- [Data distribution, packaging, and release decisions](../../decisions/data-distribution-packaging-and-release-decisions.md)
- **Location:** `scripts/check_data_dependency.py`, `find_wheel`.
- **Defect:** `sorted(dist_dir.glob(f"{prefix}-*.whl"))[0]` and no word about the rest. The release job runs this over a `dist/` that cibuildwheel has filled with one wheel per platform target, so the discarded majority is the normal case, not the edge one. It is correct today because every wheel of a build carries the same `Requires-Dist`; it stops being correct the moment `dist/` holds two versions, and the guard would then pass on the wrong one — silently, in the one script whose entire job is to not pass vacuously (its own `read_requirement` raises rather than let a missing requirement do that).
- **Fix:** read the requirement from every matching wheel and raise `UndeterminedError` if they disagree. Size: ~10 lines.
- **Why it needs a decision:** it changes when the script exits `2`, for an input that exits `0` today, in the gate ahead of an irreversible publish.
- **Decided, 2026-08-21 — assert that `dist/` holds exactly one version, and refuse otherwise.** Stricter than reading every wheel and comparing their requirements, and chosen over it: a `dist/` holding two versions is not a disagreement to adjudicate, it is a staging accident, and the guard cannot tell which version is the one being released. It also catches the case reading-and-comparing misses entirely — a stale wheel of an *older* version left behind, whose `Requires-Dist` agrees with the new one and so passes a comparison while proving nothing about what is about to be published.
- **What implementing it means:** `find_wheel` returns all matches; raise `UndeterminedError` naming the versions found when the set has more than one. Exit 2 already means "could not be carried out" and already blocks, so no new failure mode reaches the release job — only a new reason to reach an existing one. **Add a test**: this is the guard nothing else covers, and no pull request ever exercises it, since it runs on tag refs only. Changelog bullet in the **Internal** list.
- **Status:** open — decision taken, implementation not started.
- **Last touched:** 2026-08-21 — decided; found on the first read of the module.

---
