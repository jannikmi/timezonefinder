# Shortcut ordering and fallback semantics

## Coverage and the two lookup contracts

Settled by the maintainer, 2026-09-09: the full dataset including ocean timezones may be treated as covering the globe for `timezone_at()`. Uncovered slivers are not a blocker for shortcut ordering, and proving coverage cell by cell is not required to justify its untested final-zone fallback. This is an accepted dataset assumption, not a claim that a geometric overlay proves exact coverage.

Users who want to avoid that fallback use `certain_timezone_at()`, which checks containment and can return `None`. Do not require the main lookup to adopt that contract. The full-coverage assumption is specific to the dataset with oceans; it is not evidence that an arbitrary custom or land-only dataset covers the globe.

## Overlap ties

When compared spherical zone areas are equal, use the timezone identifier string as the secondary key, in ascending lexicographic order. This maintainer decision replaces leaving equal-area precedence unresolved. Use the identifier, not a numeric zone index or iteration order. Equality means equality of the computed area values; no near-equality tolerance was requested. This completes the tie rule, without making a polygon's area clipped to an H3 cell a semantic precedence rule. Holes remain excluded from their owning polygons.

## Precedence is independent of the index

- **A correctness property is never expressed in terms of the H3 shortcut index.** Settled 2026-08-21, while removing shortcut-candidate ordering as GH-513's blocker. Zone precedence — which zone a query should reach first where several cover a point — is a property of the zones and their geometry. Stating it per H3 cell would make correctness depend on the spatial index, whose resolution, layout and hybrid unique-zone encoding are implementation details the package is free to change; a future resolution change would then silently move answers rather than only performance. The index is a candidate *filter* and may be reordered, rebuilt or replaced freely, which is exactly why nothing load-bearing may be derived from its structure. It is what forced GH-513's question into the zone-level form that turned out to be cyclic, and it binds any future argument that reaches for the shortcuts to prove something about answers.
