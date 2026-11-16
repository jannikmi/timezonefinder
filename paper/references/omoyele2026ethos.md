# ETHOS.TISED: a Python package for temporal downscaling of solar irradiance (Omoyele et al., 2026)

- **BibTeX key:** `omoyele2026ethos`
- **Venue:** SoftwareX 34, 102688, 2026
- **DOI:** [10.1016/j.softx.2026.102688](https://doi.org/10.1016/j.softx.2026.102688); preprint SSRN [10.2139/ssrn.6357987](https://doi.org/10.2139/ssrn.6357987)
- **Field:** energy systems modelling / solar resource software (Forschungszentrum Jülich, ETHOS suite)
- **Verification:** found through Google Scholar. The passages below are Scholar's full-text snippet. The publisher full text was not retrieved, and the Crossref reference list (49 entries) has no timezonefinder entry, which fits a footnote citation.

## How timezonefinder is referenced

> … used Python ≥ 3.13.0, Pandas, NumPy, pvlib, sklearn, SciPy, timezonefinder, kgcpy … The class utilizes the timezonefinder³ package through the latitude and longitude to obtain …

Listed as a dependency and cited in footnote 3.

## Role of timezonefinder

The package downscales hourly or daily irradiance to finer time steps for a given location. One of its classes uses timezonefinder to get the site's time zone from latitude and longitude, presumably to align irradiance data with local solar time and pvlib's solar-position calculations.

## Notes

- A second solar or pvlib use, after [`agyeiagyemang2026solar`](agyeiagyemang2026solar.md). Here timezonefinder is a runtime dependency of another published research package, as in HERMESv3 ([`guevara2019hermes`](guevara2019hermes.md)), so its users inherit it.
