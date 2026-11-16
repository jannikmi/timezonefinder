# Estimation of the planetary boundary layer height from wind-profiler and ceilometer data (Josephs, 2021)

- **BibTeX key:** `josephs2021pbl`
- **Venue:** M.S. thesis, City University of New York (Hunter College, CUNY Academic Works), 2021
- **URL:** <https://academicworks.cuny.edu/hc_sas_etds/738/> (open access)
- **Field:** atmospheric science
- **Verification:** full text read (repository PDF, read in the browser). The package is named only in the code of Appendix B (scripts B.3 `addLocalTime.py` and B.4 `getFileStats2.py`, pp. 75–80). The main text, p. 18, describes the conversion without naming it.

## How timezonefinder is referenced

The main text describes the step:

> Finally, a Python script to convert the UTC (Coordinated Universal Time) timestamps of the data to the local timestamps based on the latitude/longitude coordinates of the associated RWP was applied to the remaining files

Appendix B.3, `addLocalTime.py`, does it with the package:

```python
from timezonefinder import TimezoneFinder

...
tf = TimezoneFinder()
...
mytz = tf.timezone_at(lng=lon, lat=lat)
```

Cited as: code only. No reference-list entry, URL or version.

## Role of timezonefinder

Assigns a zone to each radar wind profiler (RWP) site of a global network, read from the coordinates in the file name, and adds a local-time column to every profile. The boundary-layer height estimates are then analysed against local time, so the lookup sets the time axis of the diurnal analysis.

## Notes

- The script takes the UTC offset from the first three characters of the offset string (`int(str(offset)[19:22])`), so whole hours only: a site in a zone with a half-hour offset would get a local time 30 minutes off. Whether any such site is in the data is not stated.
