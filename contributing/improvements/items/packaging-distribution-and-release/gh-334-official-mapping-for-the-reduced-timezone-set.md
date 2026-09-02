# GH-334 — official mapping for the reduced timezone set


## Related memory

- [Data distribution, packaging, and release decisions](../../decisions/data-distribution-packaging-and-release-decisions.md)
- [Improvement sequencing and preconditions](../../improvement-sequencing-and-preconditions.md)
- **Tracks:** issue #334.
- **Unblocked, 2026-09-02.** The upstream request, evansiroky/timezone-boundary-builder#195, was closed on 2026-01-08 by commit `f5e798b` ("output lookups of merged zones"), which added a `writeCombinedZoneLookup` step to `index.js`. The mapping has shipped in every release since: the 2026c assets carry `timezone-names-Now.json` and `timezone-names-1970.json` plus their `-with-oceans-` variants, each a representative zone → merged IANA zones lookup (`"Africa/Abidjan": ["Africa/Abidjan", "Africa/Accra", …, "Etc/UTC"]`). The park was recorded 2026-08-20, seven months after the block lifted; the issue body had already said so.
- **What the work is.** Mechanical and test-side, as issue #334 spells out: download the mapping alongside the boundary data in `parse_data.sh`, vendor it into `tests/`, and read it in `tests/auxiliaries.py:convert_to_reduced_timezone` instead of deriving a table. It stays the *only* source of a reduced-zone mapping — see the settled decision that such a mapping comes from upstream or not at all.
- **Status:** free — an S-sized pass can take it. GH-332 is sequenced behind it.
- **Last touched:** 2026-09-02 — verified the upstream close and the released assets; unparked.
