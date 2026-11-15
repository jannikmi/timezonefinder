# Scientific publications referencing timezonefinder

This directory records scientific publications that name the `timezonefinder` Python package directly in their text. [`../references.bib`](../references.bib) holds one BibTeX entry per publication, and each entry has a note here, named after its key, with the quoted passage, how the package is cited and what it is used for. The search ran on 2026-11-15.

## Search method

| Source | Query | Outcome |
|---|---|---|
| Europe PMC REST API, full-text search | `"timezonefinder"` | 3 hits: [`dinsmore2021griti`](dinsmore2021griti.md), [`romero2022runners`](romero2022runners.md) and its preprint |
| arXiv API | `all:timezonefinder` | No hits. The API searches metadata only, not full text |
| Crossref API | `timezonefinder` | No hits. Metadata only. Used afterwards for bibliographic data and reference lists |
| Zenodo API | `timezonefinder` | Only the package's own software record |
| Web search, unrestricted and restricted to arXiv, MDPI, Nature, PLOS, Frontiers, BMC, ScienceDirect, Springer, Wiley, IEEE, ACM, Taylor & Francis, bioRxiv/medRxiv, Copernicus, JOSS, ResearchGate, OSF, PubMed Central and the ACL Anthology | `"timezonefinder"`, plus combinations with field terms (solar/pvlib, air quality, sleep/wearables, mobility/social media, ionosphere/astronomy, energy) | The remaining hits |
| Semantic Scholar snippet search, OpenAlex | `timezonefinder` | Not usable: both refused with rate limits during the search |

Each hit was then checked against the full text for a literal mention of the package. Open-access full text was read for six publications. For two, the publisher blocked automated access, and the mention rests on a search-engine extract of the methods section. Their notes say so.

### Excluded candidates

- *Prediction of Customer Purchase Intention using Social Media Data* (Kale et al., IJARSCT, 2022, doi:10.48175/IJARSCT-4003). A search result described it as using the package in preprocessing. No full text could be read and none of its 10 Crossref references names the package, so it is unconfirmed and left out.
- *Scale-invariant time registration of 24-hour accelerometric rest-activity profiles* (McDonnell et al., bioRxiv 2020 / Biological Rhythm Research 2021). It came up in a combined search, but nothing showed that it mentions the package.
- *Exploring Scientists' Working Timetable: A Global Survey* (arXiv:1310.5777, 2013). It converts coordinates to time zones but predates the package.
- Publications about time zones that do not use the package (trade economics, collaboration across time zones, RFC 7808, etc.).

## Findings

Eight publications reference timezonefinder directly (2019–2026):

| Key | Year | Venue | Field | Use of timezonefinder | Cited how |
|---|---|---|---|---|---|
| [`guevara2019hermes`](guevara2019hermes.md) | 2019 | Geosci. Model Dev. | emission modelling | dependency (>= 2.1.0) for local-time emission profiles | dependency list |
| [`guevara2020hermes`](guevara2020hermes.md) | 2020 | Geosci. Model Dev. | emission modelling | dependency (> 2.1.0), bottom-up module | dependency list |
| [`dinsmore2021griti`](dinsmore2021griti.md) | 2021 | MethodsX | ionospheric physics | building block of research code | acknowledgement + docs URL |
| [`romero2022runners`](romero2022runners.md) | 2022 | IJERPH | public health, wearables | GPS start point → local time of running activities | inline name |
| [`bowdalo2024ghost`](bowdalo2024ghost.md) | 2024 | Earth Syst. Sci. Data | atmospheric chemistry | station coordinates → IANA zone, local time → UTC | reference-list entry (PyPI) |
| [`manchin2025collaboration`](manchin2025collaboration.md) | 2025 | Research Policy | scientometrics | geocoded affiliations → time-zone differences between co-authors | docs reference (full text not read) |
| [`dellanegra2026reddit`](dellanegra2026reddit.md) | 2026 | arXiv (cs.SI) | computational social science | geocoded places → ground-truth time zones | inline name |
| [`agyeiagyemang2026solar`](agyeiagyemang2026solar.md) | 2026 | Energies | solar energy | weather-station coordinates → time zone for pvlib | inline name (full text not read) |

### Observations

- **One usage pattern dominates.** Where the use is described, the package converts coordinates into an IANA time-zone name. Most do it to turn UTC timestamps into local time or local time into UTC (HERMESv3, GHOST, runners, solar). The others use it to compute time-zone differences (Research Policy) or to build an evaluation baseline (Reddit). None evaluates or benchmarks the package itself, and no dedicated paper about timezonefinder exists.
- **The fields are broad**: atmospheric sciences, space physics, public health, scientometrics, social media research and energy systems. The common need is local time at a location.
- **Citation practice is weak.** Only GHOST has a reference-list entry (`Michelfeit, J.: timezonefinder, PyPI`). The others mention the package inline, in a dependency list or in acknowledgements, so citation databases do not count it. A citable record now exists ([`CITATION.cff`](../../CITATION.cff), Zenodo DOI 10.5281/zenodo.23579731), but none of the publications found uses it.
- **The coordinates often come from geocoding.** In Research Policy and Reddit they are geocoded place names, and in the runners study they are device GPS points. Lookup accuracy at borders matters less there than the accuracy of the coordinates.
- **Results are treated as ground truth, with one exception.** The Reddit and Research Policy studies take the result as given. GHOST flags measurements converted with an inferred zone as "Timezone Doubt" and adds its own expanding-radius search for remote stations where no zone was found. This user-side workaround is worth knowing when documenting `timezone_at` versus `timezone_at_land` and the ocean-zone coverage.
- **Coverage is a lower bound.** Mentions inside paywalled full text, in theses, or in code-only artefacts are not found by the sources available here. Semantic Scholar snippet search or Google Scholar would be the next sources to query.
