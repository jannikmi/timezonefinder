# GH-542 — establish what coordinate precision is worth


## Related memory

- [Geometry, data-format, and validation decisions](../../decisions/geometry-data-format-and-validation-decisions.md)
- **Tracks:** issue #542, opened 2026-08-21 to unblock GH-449; it carries what has to be established
  and why.
- **Why it exists:** GH-449's two candidate encodings differ in whether they spend precision, and
  ~3 MB separates them. Nothing in the repository says what ~1.1 cm is worth, so that choice cannot
  be made — this produces the evidence, not a format change.
- **Value:** high as a decision unblocker, low as code. It decides an L-sized item that is otherwise
  stalled.
- **An unattended pass can produce half of it, and the half it cannot produce is the deciding one.**
  The competitor half is now cheap and has a home: `benchmarks/test_comparison.py` already runs this
  package and `tzfpy` over the same committed fixtures in one process, so the disagreement rate —
  uniform and, separately, near borders — is an addition to an existing harness rather than the
  prototype the issue proposed. The user half is not: the "0 of 200,000 changed at 1e-6" figure has
  to be re-taken **with the shortcut index rebuilt from the quantized geometry** — which a pass may
  now do, since regenerating the packaged data is no longer out of bounds. What it costs is a
  regeneration and the review of the binaries it moves, not a permission.
- **Half the question is now answered, and it needed no regeneration at all — the source carries
  six decimals, not seven.** Read off the committed binaries: across all 15,850,626 packaged
  coordinate values the last decimal digit is only ever `0` or `9`, never `1`-`8`. That is not a
  statistical argument — a genuinely seven-decimal source would spread the digit over 0-9 — and the
  `9`s are `coord2int` truncating toward zero (`133580000` stored as `133579999`) rather than a
  digit that means anything. So the stored 10^-7 step is exactly 10x finer than upstream's 10^-6,
  and **quantising to 10^-6 cannot change an answer, by construction**: information that was never
  there cannot be lost. That explains the "0 of 200,000 changed at 1e-6" figure rather than merely
  observing it, and retires the need to re-take it. `tests/test_coordinate_precision.py` pins the
  finding, so a future upstream that does publish a seventh digit fails loudly.
- **What it is worth, priced for GH-449's encodings.** Per-polygon deltas as varints over the
  packaged boundaries: **60.5 MiB** fixed-width today, **33.7 MiB** at 10^-7, **27.7 MiB** at
  10^-6. The redundant decimal is therefore ~6 MiB, **~18 % of the encoded size** — but only once
  the encoding is variable-width. In the current fixed layout it is worth nothing: `int32` is
  forced by the *range* (±180° at 10^-6 still needs 29 bits), no reachable precision brings the
  globe inside `int16` (65,536 steps over 360° is 610 m), and the ray-casting kernel's `int32`
  arithmetic does not care about magnitudes. **Do not propose relaxing the scale factor as a
  standalone performance change** — it is only ever a term in the encoding decision.
- **What still needs a regeneration** is the part below 10^-6, where real information starts to go:
  that is where the user-facing accuracy question actually lives. A pass may now do it — quantize
  the geometry, rebuild the shortcut index from it, and re-take the changed-answer rate against the
  committed fixtures. Worth pairing with GH-449 in one release, since both move the format.
- **Status:** open. Blocks GH-449, but the encoding choice can now be priced on the figures above.
- **Last touched:** 2026-08-24 — the source-precision half established from the committed data
  without a regeneration, with the delta+varint sizes at both scales; the remaining deciding
  question narrowed to resolutions finer than the source's own.
