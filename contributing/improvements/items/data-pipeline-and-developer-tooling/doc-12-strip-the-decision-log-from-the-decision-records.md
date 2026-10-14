# DOC-12 — strip the decision log from the decision records

- **Status:** open — scope is `contributing/improvements/decisions/`, excluding the parts a re-proposal needs.
- **Size:** M — ten files, prose only, no code and no generated artifact.
- **Location:** every file under `contributing/improvements/decisions/`.

## The finding

A decision record is read to learn **the rule in force and the dead ends**, and most of these files also carry the chronology of how the rule was arrived at: who decided, on what date, what a hold was waiting for, what has since shipped. That content answers no question a reader of the file has, ages on its own, and is in Git already. Nine of the ten files carry at least one such marker (`Decided <date> by the maintainer`, `Settled 2026-…`, `has since`, `it ended on`), several of them several.

It also hides the live content. The release-batching file's longest bullet was a closed episode wrapped around one transferable rule; the fallback-semantics file carried three worked witnesses naming H3 cells that no longer exist, for a tie rule that is still in force.

## What to do

Per file: state the decision in force in the present tense, keep the refused options with the reason each loses, keep a measurement only where it is what refuses a proposal, and delete the rest. The test for a sentence is whether a future pass would act differently without it. The [contributor-memory rules](../../../contributor-memory-rules.md) state the standard; this item applies it to the files written before it.

Two things not to do. Do not delete a refusal because its subject changed — rewrite it so it still refuses something, since the next proposal will arrive in new clothes. And do not merge files to save words: the one-subject-per-file split is what makes a route to them possible.

## Why it is an item rather than part of the change that found it

The pull request replacing the shortcut index corrected every decision line it touched, at the maintainer's request. The rest of these files were already in this state and are not that change's to rewrite.
