# GH-513 — drop hole polygons entirely

**Refused, 2026-09-01, on a proof rather than on a measurement.** The precedence relation a hole-free lookup would need is cyclic, so no candidate ordering satisfies it — not the size-derived rule proposed on the issue, not a maintained table, and not a per-cell order at any H3 resolution.

## Related memory

- [Geometry, data-format, and validation decisions](../../decisions/geometry-data-format-and-validation-decisions.md) — carries the refusal, so a re-proposal is answered there.
- **Tracks:** issue #513, which carries the original measurement and the coverage trap.
- **Status:** rejected — the zone precedence relation a hole-free lookup needs is cyclic, so no candidate ordering satisfies it and no ordering work would unblock this.
- **Last touched:** 2026-09-01 — refuted, with the prototypes re-run against the shipped dataset and the regression gate landed.

## What was asked and what was found

Dropping holes is answer-preserving only if, wherever two zones' rings overlap, the lookup reaches the right one first. Expressed as a relation over zones — which the [H3-independence decision](../../decisions/geometry-data-format-and-validation-decisions.md) requires, since the index is a candidate filter whose resolution and layout are free to change — that is `A ≺ B`: "where A and B both cover a point, A is the answer".

`prototypes/hole_precedence_relation.py` derives that relation from the geometry alone, by testing interior points of every hole against every boundary polygon whose bounding box admits them, with and without holes applied. On release `2026c` it needs **216 edges over 218 zones**, with all 756 holes needing at least one, and it contains **7 two-cycles**.

Every cycle is a second-order enclave — a zone inside a zone inside the first zone again:

| pair | what it is |
|---|---|
| `Europe/Amsterdam` / `Europe/Brussels` | Baarle-Hertog and its Dutch counter-enclaves |
| `Asia/Dubai` / `Asia/Muscat` | Nahwa inside Madha inside the UAE |
| `America/Denver` / `America/Phoenix` | the Hopi reservation inside the Navajo Nation |
| `America/Argentina/Cordoba` / `America/Asuncion` | |
| `Asia/Omsk` / `Asia/Yekaterinburg` | |
| `Europe/Astrakhan` / `Europe/Moscow` | |
| `Pacific/Tahiti` / `Etc/GMT+10` | a lagoon inside an atoll |

**Why this is structural and not a property of one release:** precedence is a relation between *zones*, containment is a relation between *rings*, and nesting two levels deep maps two opposite ring relations onto one zone pair. Nothing about the data release or the index enters. The Dubai/Muscat witnesses lie inside **the same hole** — hole 137 of boundary 471 — so not even a per-hole rule breaks the tie.

Three further findings, each of which would have been enough on its own:

- **The per-cell formulation the H3-independence decision forbids does not rescue it either.** All seven pairs have a shortcut cell at the shipped resolution whose single candidate list would have to order the pair both ways (`841fa4bffffffff` for Amsterdam/Brussels). The decision refuses that formulation on principle; here it is also unsatisfiable.
- **The size-derived rule fails separately, on 20 of 216 edges**, and the ocean zones are the systematic half. An `Etc/GMT±XX` polygon covers a hemisphere with a handful of vertices, so it is huge by area and *first* by the vertex-count key `optimise_shortcut_ordering` actually sorts on: `Etc/GMT-3` must precede `Africa/Djibouti` while being 583x its area. The composite case named on the issue is here too — `Asia/Shanghai` before `Asia/Ho_Chi_Minh`, 36x.
- **A partial drop is worse than doing nothing.** Keeping only the contradictory holes leaves 171 of 756, and leaves the entire subsystem with them: `HoleArray`, `hole_registry`, `poly_ref.npy`, the holes-before-boundary branch and the validator's hole checks are all still needed for those 171. It would add a precedence compiler to the build to buy a fraction of ~180 KB.

What the removal was buying, priced against the current tree so the trade is stated rather than assumed: ~180 KB of data, and on the query path 0.165 candidate polygon tests per query of which 38.6 % own holes — 0.59 hole bounding-box checks per query over 20,000 uniformly random points.

## Fresh measurements of the original experiment

Re-run before concluding anything, because which holes the ordering happens to get right is a property of the compiled data. Against `timezonefinder-data` 3.2026.3 — the dataset `DATA_BUILD_RUN` names, i.e. after the shortcut index was reshaped, the latitude block index landed and the frame-of-reference payload took the format to 3:

| variant | hole interior points changed | holes affected | random global points changed |
|---|---|---|---|
| drop only the 27 holes with no boundary twin | 159 / 6,048 | 20 of 27 | 0 / 20,000 |
| drop **all** holes | 1,404 / 6,048 | 188 of 756 | 2 / 20,000 |
| *(issue #513, older compilation)* | *160 / 1,703* | *20 / 224* | *0 / 16* |

Three compilations now agree on the conclusion and disagree on the details, which is the useful part: the reshaped index moved the totals ~18 % from the issue's figures, and format 3 then left every headline count identical and moved only the uniformly random tail, 6 changed points to 2 — the coordinate scale that rode format 3 shifts a handful of borderline points. **The precedence measurement below is identical on both formats**, down to the witnesses. `prototypes/hole_boundary_redundancy.py` reproduces its own figures exactly — 729 of 756 rings duplicate a boundary (96.4 %), 0 of 1,620 probed points fall outside every other zone.

`prototypes/hole_removal_impact.py` needed one fix to run at all, twice over: it symlinked the derived per-ring files while rewriting the rings they describe, so a variant addressed rings its directory did not have. It now writes the whole polygon collection — payload, coordinate frames, latitude index and vertex counts — through the converter's own `write_polygon_collection`, which is the only way that stays correct as the layout gains files.

## What was not built, and must not be re-proposed

The deletion itself — `data/holes/`, `hole_registry.json`, `HoleArray`, the holes-before-boundary branch, `poly_ref.npy` and #509's reference encoding, `HoleCollection` and the validator's hole checks. #509's encoding stands: it is the storage win that remains available, and it is now permanent rather than provisional.

Also refused with this: any restatement of the ordering guarantee that reaches for the shortcut index, and the zone-precedence engine, which was already [a recorded rejection](../../decisions/geometry-data-format-and-validation-decisions.md).

## What did ship

`tests/test_hole_lookup_regression.py` — interior points of every packaged hole, each answer checked against the geometry directly rather than against a committed fixture, so it survives a data update. It is the gate issue #513 asked for either way, and it fails on 1,404 of 6,048 points against hole-free data.
