# Automated solar panel for the LMU campus (Hennessy et al., 2025)

- **BibTeX key:** `hennessy2025solar`
- **Venue:** honors thesis (final design review), Loyola Marymount University, 2025
- **URL:** <https://digitalcommons.lmu.edu/honors-thesis/580/> (open access)
- **Field:** engineering / solar tracking
- **Verification:** full text read (repository PDF, read in the browser); the package appears only in the Python listing that computes the panel's tilt angles, pp. 26–27. The prose and the bibliography do not name it. The repository lists five authors, the same as Scholar.

## How timezonefinder is referenced

```python
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
import pytz

...


def get_utc_offset(lat, lon):
    tf = TimezoneFinder()
    timezone_name = tf.timezone_at(lat=lat, lng=lon)
    if timezone_name is None:
        return "Time zone not found"
    timezone = pytz.timezone(timezone_name)
    now = datetime.datetime.now(timezone)
    utc_offset = now.utcoffset().total_seconds() / 3600
    return utc_offset
```

Cited as: code listing only. No reference-list entry, URL or version.

## Role of timezonefinder

A sun-tracking panel computes the solar hour angle. The script derives the site's UTC offset from its coordinates and uses it for the local standard time meridian (`LSTM = 15 * get_utc_offset(lat, lon)`) in the equation-of-time correction.

## Notes

- The listing builds a new `TimezoneFinder()` on every call to `get_utc_offset`. That reloads the data each time; documentation on reusing one instance or using the module-level functions would prevent this.
- The offset is taken for the current moment (`datetime.datetime.now`), not for the day being computed, so the standard-time meridian shifts by 15° whenever daylight saving time is in effect at run time. This is the user's handling of the zone, not a lookup error.
