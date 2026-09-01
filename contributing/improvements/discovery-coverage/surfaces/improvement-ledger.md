# Improvement ledger discovery coverage

## Baseline

- **Delta anchor:** `72678a1`.
- **Coverage state:** ranking anchors, issue states, and code premises are reverified during selection rather than trusted from earlier passes.

## Covered subjects

- Issue-state checks have caught work that shipped while its item remained open.
- Premise checks have caught both removed code anchors and items partially shipped by unrelated work.
- Recorded maintainer decisions are reconciled with the code before an item is ranked eligible.

## Durable evidence

- The canonical maintenance rules live in [improvement register rules](../../improvement-register-rules.md).

## Next useful gap

- Reverify an item's premise, issue state, claim, and open pull requests before ranking it, not after selecting it.
