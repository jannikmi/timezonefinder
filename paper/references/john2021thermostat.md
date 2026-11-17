# Building thermal dynamics from smart-thermostat data (John, 2021)

- **BibTeX key:** `john2021thermostat`
- **Venue:** M.A.Sc. thesis, Concordia University (Montréal), 2021
- **URL:** <https://spectrum.library.concordia.ca/id/eprint/988865/> (open access)
- **Field:** building energy / data science
- **Verification:** full text read (repository PDF); mentioned once, in Sect. 3.4.1 "Estimating the Thermal Time Constant of a Dwelling", under "Criteria for Selection of Analysis Periods", p. 38. The bibliography has no entry for it.

## How timezonefinder is referenced

> For each location, a monthly sunset and sunrise time are determined based on the longest day of the month. A reference CSV file of these sunrise and sunset times, according to location and month, is created using the Python function geopy.geocoders.Nominatim, Geopy, and a Python package for time zone identification, timezonefinder.

Cited as: named inline only. No reference-list entry, URL or version.

## Role of timezonefinder

The thesis estimates thermal time constants of homes from ecobee smart-thermostat data and restricts the analysis to night-time periods. timezonefinder gives the zone of each geocoded location so that the monthly sunset and sunrise times in the reference table are in local time. The lookup therefore decides which periods count as night and enter the estimate.
