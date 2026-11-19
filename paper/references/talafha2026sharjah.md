# Sharjah criterion for lunar crescent visibility (Talafha, Al-Wardat & Al-Naimiy, 2026)

- **BibTeX key:** `talafha2026sharjah`
- **Venue:** SSRN preprint 6911299, 2026
- **DOI:** [10.2139/ssrn.6911299](https://doi.org/10.2139/ssrn.6911299)
- **Field:** observational astronomy / calendar applications
- **Verification:** index match for the paper, use confirmed in the authors' code. Google Scholar returns the paper for "timezonefinder", which means its indexed full text contains the term. The passage is not shown in the snippet, SSRN blocks automated access, and the 16 Crossref references contain no timezonefinder entry. The first author's public repository for the criterion, [mtalafha90/Sharjah_Criterion](https://github.com/mtalafha90/Sharjah_Criterion) (MIT, `CITATION.cff` version 1.0.0 released 2026-06-19), imports and calls the package (checked on 2026-11-19 at commit `fb05612`). The paper's own passage is still unread, so confirm it before quoting.

## How timezonefinder is referenced

In the paper: not seen.

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

The criterion is fitted on 4,470 crescent-sighting reports from many sites, using relative altitude, elongation and moon lag time. The feature script geocodes each observing site with Nominatim, looks up its zone with the package, and skips the report if no zone is found. With `zoneinfo` it then places the observation, the local sunset and the conjunction in the site's local time, which gives the moon's age at the observation. This is read from the code. That the paper describes the same step is an inference from the Scholar match.
