# GH-332 — reduced timezone dataset as a second distribution


## Related memory

- [Data distribution, packaging, and release decisions](../../decisions/data-distribution-packaging-and-release-decisions.md)
- [Improvement sequencing and preconditions](../../improvement-sequencing-and-preconditions.md)
- **Tracks:** issue #332, which carries the reframing and the costs.
- **Why it is ranked here:** 63 zones instead of 444 on the 2026c release — counted from the vendored table rather than remembered; "~90" was in the entry and in `docs/data_format.rst` until it was checked — and the distribution split turned it from a build-time switch into a packaging decision.
- **Decided, 2026-08-21 — no hand-maintained mapping.** Shipping with one was declined: until the official table exists it is the same liability the zone-precedence engine was rejected for. That decision stands and is unaffected by what follows; only its precondition changed.
- **Unparked, 2026-09-02; unblocked, 2026-09-03.** The official table exists and is now in the tree: `tests/fixtures/reduced_zones/mapping.json` holds the release asset verbatim, `source.txt` beside it records the release and digest it was verified against, `update_data.sh` re-takes it with every data update, and `tests/auxiliaries.py:convert_to_reduced_timezone` converts a location expectation through it whenever the packaged data is the reduced variant. So the mapping half is done and this entry no longer waits on anything.
- **Status:** open — nothing sequences it any more. Note what the vendored mapping does *not* cover: it converts a zone name, so the expectations reached through `single_location_test` hold on either dataset, while the ocean cases in `TEST_LOCATIONS_AT_LAND` do not — under the reduced data an ocean zone merges into a *land* representative, which changes what `timezone_at_land` returns rather than what it is called. That is this item's work, not a gap in the mapping. The costs on the issue are unchanged; they were never the reason for the park.
- **Last touched:** 2026-09-03 — unblocked when the official mapping was vendored and consumed.
