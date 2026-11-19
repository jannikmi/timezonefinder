# Sharjah criterion for lunar crescent visibility (Talafha, Al-Wardat & Al-Naimiy, 2026)

- **BibTeX key:** `talafha2026sharjah`
- **Venue:** SSRN preprint 6911299, 2026
- **DOI:** [10.2139/ssrn.6911299](https://doi.org/10.2139/ssrn.6911299)
- **Field:** observational astronomy / calendar applications
- **Verification:** full text read on 2026-11-19, in the SSRN PDF the maintainer downloaded (32 pages, an unreviewed preprint dated June 2026). One mention, in Section 2.1, "Data" (page 6). The first author's public repository, [mtalafha90/Sharjah_Criterion](https://github.com/mtalafha90/Sharjah_Criterion) (MIT, `CITATION.cff` version 1.0.0 released 2026-06-19), which the paper's "Data and code availability" statement names, shows the call (checked on 2026-11-19 at commit `fb05612`).

## How timezonefinder is referenced

In the paper, Section 2.1, page 6:

> First, each report location was geocoded using OpenStreetMap Nominatim queries based on city, province, and country information, with the results cached locally to avoid repeated online requests. The local timezone was then inferred from the geocoded latitude and longitude using the timezonefinder Python library.

Cited as: inline name. No reference-list entry.

In the code, `Sharjah_Criterion/03_build_crescent_features.py`, which builds the feature table the criterion is fitted on, present since the first upload on 2026-05-12:

```text
from timezonefinder import TimezoneFinder
...
TF = TimezoneFinder(in_memory=True)
...
def timezone_from_latlon(lat: float, lon: float) -> str | None:
    return TF.timezone_at(lat=lat, lng=lon)
```

## Role of timezonefinder

The criterion is fitted on 4,470 crescent-sighting reports from many sites, using relative altitude, elongation and moon lag time. The feature script geocodes each observing site with Nominatim, looks up its zone with the package, and skips the report if no zone is found. With `zoneinfo` it then places the observation, the local sunset and the conjunction in the site's local time, which gives the moon's age at the observation. The paper describes this step, and the code shows it.
