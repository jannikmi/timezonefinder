# GH-317 — reduce the release artifact count


## Related memory

- [Data distribution, packaging, and release decisions](../../decisions/data-distribution-packaging-and-release-decisions.md)
- **Tracks:** issue #317, **closed as answered 2026-08-21**; the closing comment carries the figures.
- **Withdrawn.** Its question — *"do we really need 10 wheels?"* — was about artifact count when an artifact was ~55 MB of packaged data. A release is now **1.02 MB across 4 files**, so dropping two of the three platform wheels saves ~0.17 MB and costs manylinux2014 or musl users their wheel.
- **The storage half was the real driver and continues as PYPI-1.**
- **Status:** withdrawn — superseded by the distribution split.
- **Last touched:** 2026-08-21 — figures re-measured, withdrawn, issue closed.
