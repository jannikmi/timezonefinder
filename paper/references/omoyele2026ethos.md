# ETHOS.TISED: a Python package for temporal downscaling of solar irradiance (Omoyele et al., 2026)

- **BibTeX key:** `omoyele2026ethos`
- **Venue:** SoftwareX 34, 102688, 2026
- **DOI:** [10.1016/j.softx.2026.102688](https://doi.org/10.1016/j.softx.2026.102688); preprint SSRN [10.2139/ssrn.6357987](https://doi.org/10.2139/ssrn.6357987)
- **Field:** energy systems modelling / solar resource software (Forschungszentrum Jülich, ETHOS suite)
- **Verification:** found through Google Scholar. The passages below are Scholar's full-text snippet. The publisher full text was not retrieved (ScienceDirect refused the built-in browser with HTTP 403), and the Crossref reference list (49 entries) has no timezonefinder entry, which fits a footnote citation. The role below is confirmed from the package's source code.

## How timezonefinder is referenced

> … used Python ≥ 3.13.0, Pandas, NumPy, pvlib, sklearn, SciPy, timezonefinder, kgcpy … The class utilizes the timezonefinder³ package through the latitude and longitude to obtain …

Listed as a dependency and cited in footnote 3.

## Role of timezonefinder

The package downscales hourly or daily irradiance to finer time steps for a given location. The repository ([FZJ-IEK3-VSA/ETHOS.TISED](https://github.com/FZJ-IEK3-VSA/ETHOS.TISED), commit `fe4fb70`) shows the call: `ethos_tised/model.py` `_get_timezone_and_range()` runs `TimezoneFinder().timezone_at(lat=self.lat, lng=self.lon)`, falls back to `"UTC"` when the result is `None`, and builds time-zone-aware start and end timestamps of the year from the zone; the solar-position calculation used for gap-filling depends on them. `pyproject.toml` lists `timezonefinder` as a required dependency without a version constraint.

## Notes

- The `"UTC"` fallback for a `None` result is a workaround of the same kind as GHOST's ([`bowdalo2024ghost`](bowdalo2024ghost.md)). With the default dataset `timezone_at` never returns `None`, so the branch is dead code there; whether the authors met a `None` is not documented.

- A second solar or pvlib use, after [`agyeiagyemang2026solar`](agyeiagyemang2026solar.md). Here timezonefinder is a runtime dependency of another published research package, as in HERMESv3 ([`guevara2019hermes`](guevara2019hermes.md)), so its users inherit it.
