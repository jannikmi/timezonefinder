# Probabilistic week-two fire-danger forecasting with GEFF (Worsnop et al., 2021)

- **BibTeX key:** `worsnop2021fire`
- **Venue:** Weather and Forecasting 36(6), 2113–2125, 2021
- **DOI:** [10.1175/WAF-D-21-0075.1](https://doi.org/10.1175/WAF-D-21-0075.1)
- **Field:** fire-weather forecasting
- **Verification:** full text read (PDF supplied by the maintainer); mentioned once, in Sect. 4 "Preprocessing steps", p. 2116. The term does not appear in the reference list.

## How timezonefinder is referenced

> The tier 3 data are based on instantaneous quantities at local noon today. This local noon adjustment is part of the requirements to calculate the components of the NFDRS and is considered the time with the most favorable wildfire conditions. We determine the UTC corresponding to local noon at each grid point using the TimeZoneFinder Python package (https://pypi.org/project/timezonefinder/). Over the CONUS domain, local noon ranges from 1600 to 1900 UTC (1700–2000 UTC) within four possible daylight (standard) time zones.

Cited as: an inline URL in the text, `TimeZoneFinder Python package (https://pypi.org/project/timezonefinder/)`. No reference-list entry, no author and no version.

## Role of timezonefinder

Maps every forecast grid point over the contiguous United States to its time zone, so the UTC hour of local noon is known per point. That hour decides which reanalysis and reforecast steps form the 24-h windows (tier 2 inputs) and the instantaneous local-noon values (tier 3 inputs) of the GEFF fire-danger indices. The lookup therefore shapes every input to the forecasts the paper evaluates.

## Notes

- NOAA/ECMWF authors with 19 Scholar citations.
- A gridded use: the lookup runs over a regular grid rather than over station or event coordinates, so grid points near a zone border take one zone's noon hour or the other's.
- The capitalisation "TimeZoneFinder" follows the class name rather than the package name.
