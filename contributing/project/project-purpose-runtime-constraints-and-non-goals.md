# Project purpose, runtime constraints, and non-goals

`timezonefinder` provides offline timezone lookups by WGS84 coordinates, prioritising accuracy at timezone borders (no geometry simplification) over raw speed.

Constraints that shape design decisions:

- Primary users are latency-sensitive services doing high-volume, possibly concurrent lookups (plus one-off CLI/script use)
- Must run in **containerised deployments with constrained CPU/memory** — don't assume abundant RAM or many cores; the `in_memory=False` (memory-mapped) path must stay a viable low-memory option
- Must degrade gracefully without Numba/C-extension — the pure-Python path stays correct, just slower
- **The shortcut index binary is capped at 800 KB in total** (`shortcuts.bin`, header, table, blocks and candidate lists together; the shipped grid tree is ~513 KB). The index exists to spare the ~30 MB of unsimplified polygons work, and past that cap its storage overhead stops being small next to them, so an index design over it is refused however fast it measures, and a sweep compares only designs within it

Non-goals: sub-centimeter precision (the ~1.1 cm coordinate scaling is a deliberate ceiling, not a bug), and general-purpose geometry — spatial code exists only in service of timezone lookup.

## Mission & Expectations

- timezonefinder provides accurate offline timezone lookups across platforms. Every change should preserve numerical correctness at timezone borders and remain friendly to constrained runtimes.
- Assume your work will ship immediately. Submit only production-ready code: defensive error handling, predictable behaviour across Python versions we support, and clear fallbacks when optional accelerators (Numba, clang-based polygon checks) are missing.
- Be explicit about trade-offs. Document assumptions in code comments or pull request notes when optimisations or heuristics change behaviour.
