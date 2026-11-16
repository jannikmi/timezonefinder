# Automated solar panel for the LMU campus (Hennessy et al., 2025)

- **BibTeX key:** `hennessy2025solar`
- **Venue:** honors thesis, Loyola Marymount University, 2025
- **URL:** <https://digitalcommons.lmu.edu/honors-thesis/580/>
- **Field:** engineering / solar tracking
- **Verification:** Google Scholar snippet only (a code listing). The PDF is behind a bot challenge. The author list is as Scholar gives it and may be truncated.

## How timezonefinder is referenced

> … geopy.geocoders import Nominatim from timezonefinder import TimezoneFinder import pytz … def get_utc_offset(lat, lon): tf = TimezoneFinder() timezone_name = tf.timezone_at(lat=lat, …

Cited as: code listing.

## Role of timezonefinder

A sun-tracking panel computes the solar position. The UTC offset of the installation site is derived from its coordinates.

## Notes

- The listing builds a new `TimezoneFinder()` on every call to `get_utc_offset`. That reloads the data each time; documentation on reusing one instance or using the module-level functions would prevent this.
