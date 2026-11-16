# US walking distances and pedestrian safety outcomes (Vellimana, 2023)

- **BibTeX key:** `vellimana2023walking`
- **Venue:** master's thesis, The University of Texas at Austin, 2023 (supervisor Kara M. Kockelman)
- **URL:** <https://repositories.lib.utexas.edu/items/c374c5fd-304f-412e-9a47-689d7f41c955> (open access)
- **Field:** transport safety
- **Verification:** full text read (repository PDF, read in the browser); mentioned once, in Sect. 1.2 "Datasets Assembled", pp. 8–9. The bibliography has no entry for it.

## How timezonefinder is referenced

> Python's 'Suntime' library was used to find sunset and sunrise in Coordinated Universal Time (UTC), given trip starting coordinates and date (with NHTS sampling trips from April 2016 through April 2017). UTC time was converted to the local time of trip location with the help of a Python package called 'TimezoneFinder', to determine whether respondent-reported walk-trip start times were before sunrise or after sunset (and labeled "night" or "nighttime").

Cited as: named inline only, by its class name. No reference-list entry, URL or version.

## Role of timezonefinder

Part 1 models daily walk-miles travelled (WMT) and nighttime WMT from the 2016/17 National Household Travel Survey. timezonefinder gives the zone of each walk trip's origin (a block-group centroid), so the UTC sunrise and sunset times can be compared with the locally reported trip start time. That comparison labels a trip as night or day, which defines nighttime WMT, one of the two dependent variables.

## Notes

- The same darkness classification as in [`carey2027darkness`](carey2027darkness.md), applied to walking exposure rather than to crashes.
