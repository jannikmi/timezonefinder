# PYPI-1 — the PyPI project holds 11.37 GB of pre-split releases


## Related memory

- [Data distribution, packaging, and release decisions](../../decisions/data-distribution-packaging-and-release-decisions.md)
- **Location:** not the repository — the `timezonefinder` project on PyPI. Split out of GH-317,
  which was about artifact *count* and is answered; this is what was actually driving that issue.
- **The numbers, read off the index 2026-08-20:** 11.37 GB across **241 files and 57 versions**,
  against a 10 GB project quota that was already hit once (a support request and the deletion of
  every release up to 3.4.2 recovered the space). Current releases are not the cause and cannot
  become it: `timezonefinder` 8.3.0 is 1.02 MB and `timezonefinder-data` 1.2026.3 is 51.94 MB in a
  project of its own with its own quota — order 190 data releases of headroom.
- **Fix:** a one-off deletion of the pre-8.x releases, which are the ~55 MB-per-file ones. It is a
  maintainer action against PyPI, not a code change, which is why it is an entry here and not an
  issue anybody else could take.
- **Weigh before deleting**, because it is irreversible and PyPI never re-accepts a version number:
  a deleted release breaks any pin to it and any lockfile hash referencing it. Yanking is the
  reversible half-measure and **does not free storage**, so it does not solve this. The honest
  framing is that old releases of a package whose whole payload was a since-superseded dataset have
  little archival value, but that is a judgement about this package's users, not a general rule.
- **Value:** moderate and non-urgent — nothing breaks until the quota is hit again, and the split
  has made that far slower to arrive.
- **Status:** open.
- **Last touched:** 2026-08-21 — split out of GH-317 when its artifact-count half was answered.
