# Timezone-aware traditional calendar systems: Hindu Panchang with DST support (Kolluri, 2025)

- **BibTeX key:** `kolluri2025panchang`
- **Venue:** SSRN preprint 5347331, 2025 (paper dated June 30, 2025)
- **DOI:** [10.2139/ssrn.5347331](https://doi.org/10.2139/ssrn.5347331)
- **Field:** calendar computation / applied astronomy software
- **Verification:** full text read on 2026-11-19, in the SSRN PDF the maintainer downloaded (12 pages). Two mentions: a code listing in Section 3.3 (page 4) and a bullet in the appendix (page 11). SSRN refuses command-line access, so the copy came from the maintainer's browser.

## How timezonefinder is referenced

Section 3.3, "DST-Aware Timezone Resolution", page 4, code listing:

```text
class TimezoneService:
    def __init__(self):
        self.timezone_finder = TimezoneFinder()
        self.dst_database = DSTTransitionDatabase()

    def get_timezone_info(self, coordinates, date):
        """
        Get complete timezone information including DST status
        """
        # Get timezone identifier
        timezone_str = self.timezone_finder.timezone_at(
            lat=coordinates['lat'],
            lng=coordinates['lng']
        )
```

The listing then builds a `pytz` time zone from the name and returns its UTC offset, DST offset and abbreviation for the date.

Appendix, "A.3 Technical Implementation Highlights", page 11:

> TimezoneFinder Integration: Automatic timezone detection from coordinates using offline database

Cited as: code and an appendix bullet. The paper names the class `TimezoneFinder`, but not the package itself or its import. Its six references do not include the package.

## Role of timezonefinder

The paper describes a production panchang service (Shubhamastu, 31,300+ cities). The service geocodes a location with a GeoNames SQLite database and falls back to OpenCage. The package then gives the location's IANA zone, and `pytz` gives that date's UTC and DST offsets. Sunrise-based panchang times are computed in UTC with the Swiss Ephemeris and converted to local time with that zone.

## Notes

- Section 6.2, "Timezone Boundary Edge Cases", treats points within 10 km of a zone border as uncertain. Near a border it uses the user's location string to choose between nearby zones, and it may override the coordinate lookup. The helpers in that listing (`get_timezone_at_coordinates`, `calculate_distance_to_nearest_timezone_boundary`, `get_nearby_timezones`) are not shown, so the paper does not say whether they use the package. This is a downstream user handling border uncertainty in its own code.
