# API-1 — `AbstractTimezoneFinder.__init__` takes an `in_memory` it never uses


## Related memory

- [Public API and runtime-loading decisions](../../decisions/public-api-compatibility-and-runtime-loading-decisions.md)
- [Improvement sequencing and preconditions](../../improvement-sequencing-and-preconditions.md)
- **Location:** `timezonefinder/timezonefinder.py`, `AbstractTimezoneFinder.__init__`.
- **Defect:** the parameter is accepted and then not read; `TimezoneFinder.__init__` applies its *own* copy of the argument to the two `PolygonArray` constructors after calling `super()`. The base class loads only data it always keeps in memory, so there is nothing for it to select.
- **Fix:** either drop it from the base signature (subclasses stop forwarding it) or have the base store it for subclasses to read. Size: ~10 lines. Note the base cannot store it as things stand — `in_memory` is not in `__slots__`, so option two costs a slot.
- **The premise this entry was written on is wrong, and that changes how much it touches.** `AbstractTimezoneFinder` is **not** importable from the package root: `from timezonefinder import AbstractTimezoneFinder` raises `ImportError`. It is reachable only as `timezonefinder.timezonefinder.AbstractTimezoneFinder` — which is public solely because API-2 is unresolved. So how much public surface a signature change here touches is decided by API-2, not by this entry, and the two want answering in that order.
- **`TimezoneFinderL` is the user-visible half.** Its `__init__` is a pure pass-through that could be deleted outright, and it accepts `in_memory=True` in silence while loading no polygon data. **The repository already made this call in the opposite direction:** `command_line.py` *refuses* `--in-memory` with `-f 3`/`-f 4`, under the comment that accepting it "would promise a speedup it cannot deliver, which is worse than refusing it". The Python API and its own CLI disagree, which is the sharpest form of the question.
- **Decided, 2026-08-21 — drop it everywhere.** From `AbstractTimezoneFinder.__init__` and from `TimezoneFinderL.__init__`, which is a pure pass-through and goes with it. `TimezoneFinderL( in_memory=True)` becomes a `TypeError`, which is what the CLI already does for the same call and is the whole point: a parameter that cannot do anything should say so. **This is a breaking change**, so it ships in a major — see the release-strategy decision below, which is why this entry no longer moves on its own.
- **Status:** open — decision taken, held for the next major.
- **Last touched:** 2026-08-21 — decided, and bound to the batched-major decision.
