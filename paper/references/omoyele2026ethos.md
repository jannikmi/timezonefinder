# ETHOS.TISED: a Python package for temporal downscaling of solar irradiance (Omoyele et al., 2026)

- **BibTeX key:** `omoyele2026ethos`
- **Venue:** SoftwareX 34, 102688, 2026 (received 24 February 2026, accepted 26 April 2026, online 12 May 2026; open access, CC BY 4.0)
- **DOI:** [10.1016/j.softx.2026.102688](https://doi.org/10.1016/j.softx.2026.102688); preprint SSRN [10.2139/ssrn.6357987](https://doi.org/10.2139/ssrn.6357987)
- **Field:** energy systems modelling / solar resource software (Forschungszentrum Jülich, ETHOS suite)
- **Verification:** full text read. ScienceDirect refused the built-in browser with HTTP 403, so the maintainer supplied the text of the published article. The Crossref reference list (49 entries) has no timezonefinder entry, which the full text confirms: the package is cited in a footnote only. The call is also confirmed in the package's source code.

## How timezonefinder is referenced

Twice. The code metadata table (C6, "Software code languages, tools and services used") lists `timezonefinder` among the dependencies, next to Pandas, NumPy, pvlib, sklearn, SciPy and kgcpy. Section 2.2, sub-method (2) "Setting Time Zone", explains why it is needed:

> The class utilizes the timezonefinder³ package through the latitude and longitude to obtain the location's time zone.

Footnote 3 gives the repository URL, `https://github.com/jannikmi/timezonefinder`. There is no reference-list entry.

## Role of timezonefinder

The package downscales a year of hourly global horizontal irradiance (GHI) to one-minute resolution for a given location, by matching daily variability indicators against a database of non-dimensional minute-resolution profiles. The user supplies only the hourly series, latitude, longitude and year. Section 2.2 describes six sub-methods; the second turns the year into start and end times at hourly and minute resolution, and the paper states that these "require the time zone of the location". The zone therefore fixes the local-time axis on which the extraterrestrial irradiance, the solar angles, sunrise and sunset and the output series are computed.

The repository ([FZJ-IEK3-VSA/ETHOS.TISED](https://github.com/FZJ-IEK3-VSA/ETHOS.TISED), commit `fe4fb70`) shows the call: `ethos_tised/model.py` `_get_timezone_and_range()` runs `TimezoneFinder().timezone_at(lat=self.lat, lng=self.lon)`, falls back to `"UTC"` when the result is `None`, and builds time-zone-aware start and end timestamps of the year from the zone. `pyproject.toml` lists `timezonefinder` as a required dependency without a version constraint.

## Notes

- The `"UTC"` fallback for a `None` result is a workaround of the same kind as GHOST's ([`bowdalo2024ghost`](bowdalo2024ghost.md)). With the default dataset `timezone_at` never returns `None`, so the branch is dead code there; the paper does not mention it.
- A second solar or pvlib use, after [`agyeiagyemang2026solar`](agyeiagyemang2026solar.md). Here timezonefinder is a runtime dependency of another published research package, as in HERMESv3 ([`guevara2019hermes`](guevara2019hermes.md)), so its users inherit it. The paper names one such user: Mantuano et al. applied ETHOS.TISED for data imputation.
- The paper reports that downscaling a full year takes about 20–45 s on a desktop computer; one zone lookup per run is negligible in that budget.
