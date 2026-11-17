# pynasonde: a Python library for ionosonde data processing (Chakraborty et al., 2026)

- **BibTeX key:** `chakraborty2026pynasonde`
- **Venue:** SoftwareX 34, 102617, 2026 (open access, CC BY-NC 4.0)
- **DOI:** [10.1016/j.softx.2026.102617](https://doi.org/10.1016/j.softx.2026.102617)
- **Field:** space physics software
- **Verification:** full text read (PDF supplied by the maintainer); listed in Table 2 (p. 4) and in the reference list as [48]. The text does not say what the package does inside pynasonde.

## How timezonefinder is referenced

Table 2, "Version v1.0.0 library dependencies.", lists `timezonefinder [48]` in the "Required" column, next to numpy, pandas, matplotlib, opencv-python-headless, SciencePlots, scipy and loguru. No version constraint is given.

Cited as reference [48]: `Müller F. Timezonefinder: Python library for fast and accurate timezone lookup; 2021. https://pypi.org/project/timezonefinder/[Accessed 9 October 2025].` The author name is wrong: no "Müller F." has authored the package; [`CITATION.cff`](../../CITATION.cff) names Jannik Kissinger.

## Role of timezonefinder

A required runtime dependency of pynasonde v1.0.0, so every installation of that release pulls it in. The paper does not describe the call. The repository ([shibaji7/pynasonde](https://github.com/shibaji7/pynasonde), commit `dcf3c5d`) shows it: `pynasonde/timeutils.py` defines `TimeZoneConversion`, which calls `TimezoneFinder().timezone_at(lng=long, lat=lat)` for the station coordinates and converts timestamps between UTC and the station's local zone with `pytz`. At that commit the package is no longer required but an optional extra (`time`, `digisonde` and `vipir`), pinned `timezonefinder>=6.5`.

## Notes

- A new `TimezoneFinder()` is built on every `TimeZoneConversion` instantiation, the same pattern as the LMU code in [`hennessy2025solar`](hennessy2025solar.md).
- A third research package that ships the dependency, after HERMESv3 and ETHOS.TISED, and the second ionospheric tool after GRITI.
- The third reference-list entry found, after GHOST and the UPC flight-school thesis, and the second wrong attribution in a reference list.
