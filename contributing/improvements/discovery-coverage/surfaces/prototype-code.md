# Prototype code discovery coverage

## Baseline

- **Delta anchor:** `0141e4b`, advanced by the 2026-09-07 record audit below; the previous anchor was `72678a1`.
- **Coverage state:** the exploratory *code* stays deliberately outside improvement-pass scope; each script's `FINDINGS` block and `prototypes/README.md` do not, because the register cites them as decision evidence.

## Covered subjects

- All seven scripts and `README.md` were read end to end on 2026-09-07 for **record accuracy only** — dangling item ids, dead links, questions stated as open after the work answering them shipped, and named repair sites the follow-up disproved. Everything found was corrected in that pass; nothing was read for exploratory code quality.
- Every script still imports against the current tree, checked by importing all seven modules.
- `prototypes/query_stage_profile.py`'s `FINDINGS` were reconciled with the query measurement baseline.

## Known uncovered deltas

- Exploratory lint debt is intentionally not discovery work for an ordinary pass.
- The prototypes' own *numbers* were not re-measured. A `FINDINGS` table is pinned to the commit it was taken at, and only `query_stage_profile.py` has a rule requiring a re-run when the query path moves.

## Next useful gap

- Re-read the records whenever a decision they carry is retired or reversed, rather than sweeping this surface on a schedule: no drift found here was caused by a study being edited on its own merits. Both mechanisms are a shipping pull request — one that never opened the file naming its id (#574), and one that rewrote the file and wrote the dangling handle into it (#633). The second is why "did the shipping pull request touch `prototypes/`?" is not the question to ask.
