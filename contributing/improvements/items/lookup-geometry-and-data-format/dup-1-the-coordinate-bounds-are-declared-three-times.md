# DUP-1 — the coordinate bounds are declared three times

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
  alone.
- **Which form, though, is not free — and one of the two is.** Measured per coordinate on the
  pure-Python validator: `-90.0 <= lat <= 90.0` at 127.3 ns, `-MAX_LAT_VAL <= lat <= MAX_LAT_VAL` at
  141.2 ns (~14 ns, two of them per query, ~3 % of a unique-shortcut query), and
  `MIN_LAT_VAL <= lat <= MAX_LAT_VAL` at **127.3 ns — indistinguishable from the literals**. The
  cost is the `UNARY_NEGATIVE`, not the global load, which 3.11's specialising interpreter makes
  free. **So declare `MIN_LAT_VAL` / `MIN_LNG_VAL` alongside the existing maxima and import both;
  do not negate at the call site.** With that, the substitution has no cost to weigh at all.
- **Decided, 2026-08-20 — import the constants, in the pre-negated form.** `MIN_LAT_VAL` and
  `MIN_LNG_VAL` are declared next to the existing maxima in `configs.py` and imported by both
  `utils.py`'s `validate_lat` / `validate_lng` and `utils_numba.py`'s `is_valid_lat` /
  `is_valid_lng`, so the validator, the message describing it and the canonical constant stop being
  three independent statements of the same fact.
- **What implementing it means.** Four sites read the constants and none of them negates. Two
  details that are easy to get wrong:
  - **Put the reason next to the constants, not in a commit message.** *Why* they are declared
    negative rather than derived with a `-` at each use is exactly the kind of fact the
    [core contract](../../../core-contributor-contract.md) says belongs at the point of decision —
    one comment on the `MIN_*` pair, saying the negation is what
    costs and the global load is not, so the next reader does not "simplify" them away.
  - **`MAX_LAT_VAL` / `MAX_LNG_VAL` are in `configs.__all__`, so the `MIN_*` pair joins them** —
    that widens the declared surface by two names while API-2 is about narrowing the *undeclared*
    one. No tension in practice: `configs` is reachable today only through the seam API-2 would
    close, and a constant that two modules import is exactly what `__all__` is for.
  - No changelog bullet in the main list — nothing observable changes; **Internal** is the place.
- **Status:** open — decision taken, implementation not started.
- **Last touched:** 2026-08-20 — measured, then decided. The bounded-exposure argument stands and is
  joined by a positive result: in the pre-negated form the change is free outright.

## Related memory

- [Geometry, data-format, and validation decisions](../../decisions/geometry-data-format-and-validation-decisions.md)
