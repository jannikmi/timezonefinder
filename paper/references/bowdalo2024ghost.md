# GHOST: globally harmonised surface atmospheric composition dataset (Bowdalo et al., 2024)

- **BibTeX key:** `bowdalo2024ghost`
- **Venue:** Earth System Science Data 16(10), 4417–4495, 2024
- **DOI:** [10.5194/essd-16-4417-2024](https://doi.org/10.5194/essd-16-4417-2024) (open access, CC BY 4.0)
- **Field:** atmospheric chemistry / observational data harmonisation
- **Verification:** full text read; mentioned in Sect. 3.2.3 and 3.4.5 and in the reference list.

## How timezonefinder is referenced

Formally cited as `Michelfeit, J.: timezonefinder, https://pypi.org/project/timezonefinder/, last access: 26 March 2024.`

> However, in the case where no local time zone information exists, this is obtained using the Python timezonefinder package (Michelfeit, 2024) as detailed in Sect. 3.4.5.

> This is done by passing a station longitude–latitude coordinate pair to the Python timezonefinder package (Michelfeit, 2024). This returns a local time zone string, referencing the IANA time zone database (IANA, 2024), which is saved to the station_timezone metadata variable. In some cases, if the station is extremely remote, the timezonefinder package will not be able to identify a local time zone. In these cases, the closest time zone is identified within a set radius around the station of initially 1°. If no time zones are identified within this initial radius, the radius size is increased iteratively by 1° until a time zone is found. This iteration is allowed to continue for 1 min before timing out, and the station time zone is left unset.

Measurements shifted from local time to UTC this way receive the GHOST QA flag "Timezone Doubt".

## Role of timezonefinder

Assigns IANA time zones to ~thousands of monitoring stations of 38 networks (7.3 billion measurements, 1970–2023) so local-time measurements can be shifted to UTC, and stores the zone as station metadata.

## Notes

- The most detailed scientific use found, and one of three reference-list entries (with the UPC flight-school thesis and pynasonde); the only one in a journal that names the author correctly.
- **Relevant feedback for the project:** the paper reports "no zone found" results for remote stations and works around them with its own expanding-radius search and time-out. The paper does not say which release or method it called. With the default dataset, which includes ocean zones, `timezone_at` returns a zone for every coordinate; `None` comes only from `timezone_at_land` or a dataset without ocean zones. The "Timezone Doubt" QA flag shows that users treat the lookup as a source of uncertainty for remote points.
- Same institution as [`guevara2019hermes`](guevara2019hermes.md).
