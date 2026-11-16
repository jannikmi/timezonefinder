# Scientific publications referencing timezonefinder

This directory records scientific publications that name the `timezonefinder` Python package directly in their text. [`../references.bib`](../references.bib) holds one BibTeX entry per publication, and each entry has a note here, named after its key, with the quoted passage, how the package is cited and what it is used for. The automated search ran on 2026-11-15. The maintainer supplied a Google Scholar result list on 2026-11-16, and those hits were added and checked the same way.

## Search method

| Source | Query | Outcome |
|---|---|---|
| Europe PMC REST API, full-text search | `"timezonefinder"` | 3 hits: [`dinsmore2021griti`](dinsmore2021griti.md), [`romero2022runners`](romero2022runners.md) and its preprint |
| arXiv API | `all:timezonefinder` | No hits. The API searches metadata only, not full text |
| Crossref API | `timezonefinder` | No hits. Metadata only. Used afterwards for bibliographic data and reference lists |
| Zenodo API | `timezonefinder` | Only the package's own software record |
| Web search, unrestricted and restricted to arXiv, MDPI, Nature, PLOS, Frontiers, BMC, ScienceDirect, Springer, Wiley, IEEE, ACM, Taylor & Francis, bioRxiv/medRxiv, Copernicus, JOSS, ResearchGate, OSF, PubMed Central and the ACL Anthology | `"timezonefinder"`, plus combinations with field terms (solar/pvlib, air quality, sleep/wearables, mobility/social media, ionosphere/astronomy, energy) | The remaining hits |
| Semantic Scholar snippet search, OpenAlex | `timezonefinder` | Not usable: both refused with rate limits during the search |
| Google Scholar (full-text index), run by the maintainer | `timezonefinder` | 9 hits, 7 of them new: [`benetka2019context`](benetka2019context.md), [`hosseinabad2021twitter`](hosseinabad2021twitter.md), [`kolluri2025panchang`](kolluri2025panchang.md), [`gurbulak2026brk`](gurbulak2026brk.md), [`omoyele2026ethos`](omoyele2026ethos.md), [`talafha2026sharjah`](talafha2026sharjah.md), [`carey2027darkness`](carey2027darkness.md) |

Each hit was then checked against the full text for a literal mention of the package. The notes record the evidence in one of three grades:

- **full text read** (8): `guevara2019hermes`, `guevara2020hermes`, `dinsmore2021griti`, `romero2022runners`, `bowdalo2024ghost`, `dellanegra2026reddit`, `gurbulak2026brk`, and `hosseinabad2021twitter` (published version; the preprint passage comes from a snippet);
- **quoted search snippet** (5): the passage is quoted from a search-engine or Google Scholar extract because the publisher blocked automated access. These are `manchin2025collaboration`, `agyeiagyemang2026solar`, `benetka2019context`, `omoyele2026ethos` and `carey2027darkness`;
- **index match only** (2): Google Scholar's full-text index matches the term, but the passage has not been seen. These are `kolluri2025panchang` and `talafha2026sharjah`.

Check the last two grades against the full text before quoting them.

### Excluded candidates

- *Prediction of Customer Purchase Intention using Social Media Data* (Kale et al., IJARSCT, 2022, doi:10.48175/IJARSCT-4003). A search result described it as using the package in preprocessing. No full text could be read and none of its 10 Crossref references names the package, so it is unconfirmed and left out.
- *Scale-invariant time registration of 24-hour accelerometric rest-activity profiles* (McDonnell et al., bioRxiv 2020 / Biological Rhythm Research 2021). It came up in a combined search, but nothing showed that it mentions the package.
- *Exploring Scientists' Working Timetable: A Global Survey* (arXiv:1310.5777, 2013). It converts coordinates to time zones but predates the package.
- Publications about time zones that do not use the package (trade economics, collaboration across time zones, RFC 7808, etc.).

## Findings

Fifteen publications reference timezonefinder (2019–2027):

| Key | Year | Venue | Field | Use of timezonefinder | Cited how | Evidence |
|---|---|---|---|---|---|---|
| [`guevara2019hermes`](guevara2019hermes.md) | 2019 | Geosci. Model Dev. | emission modelling | dependency (>= 2.1.0) for local-time emission profiles | dependency list | full text |
| [`benetka2019context`](benetka2019context.md) | 2019 | CHIIR '19 (ACM) | information retrieval | tweet coordinates → local time | footnote | snippet |
| [`guevara2020hermes`](guevara2020hermes.md) | 2020 | Geosci. Model Dev. | emission modelling | dependency (> 2.1.0), bottom-up module | dependency list | full text |
| [`dinsmore2021griti`](dinsmore2021griti.md) | 2021 | MethodsX | ionospheric physics | building block of research code | acknowledgement + docs URL | full text |
| [`hosseinabad2021twitter`](hosseinabad2021twitter.md) | 2021 | medRxiv → JMIR Public Health Surveill. | digital public health | tweet location → local time features | inline name (preprint); generic "time zone finder" (published) | full text + snippet |
| [`romero2022runners`](romero2022runners.md) | 2022 | IJERPH | public health, wearables | GPS start point → local time of running activities | inline name | full text |
| [`bowdalo2024ghost`](bowdalo2024ghost.md) | 2024 | Earth Syst. Sci. Data | atmospheric chemistry | station coordinates → IANA zone, local time → UTC | reference-list entry (PyPI) | full text |
| [`manchin2025collaboration`](manchin2025collaboration.md) | 2025 | Research Policy | scientometrics | geocoded affiliations → time-zone differences between co-authors | docs reference | snippet |
| [`kolluri2025panchang`](kolluri2025panchang.md) | 2025 | SSRN | calendar computation | not seen (presumably observer location → zone) | not seen | index match |
| [`dellanegra2026reddit`](dellanegra2026reddit.md) | 2026 | arXiv (cs.SI) | computational social science | geocoded places → ground-truth time zones | inline name | full text |
| [`agyeiagyemang2026solar`](agyeiagyemang2026solar.md) | 2026 | Energies | solar energy | weather-station coordinates → time zone for pvlib | inline name | snippet |
| [`gurbulak2026brk`](gurbulak2026brk.md) | 2026 | Osmaniye Korkut Ata Univ. J. Nat. Appl. Sci. | astronomy software | observing site → local time | inline, mis-cited as (Lutz, 2010) | full text |
| [`omoyele2026ethos`](omoyele2026ethos.md) | 2026 | SoftwareX | solar energy software | site lat/lon → zone; runtime dependency | dependency list + footnote | snippet |
| [`talafha2026sharjah`](talafha2026sharjah.md) | 2026 | SSRN | astronomy, calendars | not seen (presumably sighting site → zone) | not seen | index match |
| [`carey2027darkness`](carey2027darkness.md) | 2027 | J. Transport & Health | transport safety | crash location → local time vs. civil dusk | inline name | snippet |

### Observations

- **One usage pattern dominates.** Where the use is described, the package converts coordinates into an IANA time-zone name. Most publications use it to turn UTC timestamps into local time or local time into UTC: HERMESv3, GHOST, the runners and both Twitter studies, the solar papers, the astronomy tool and the crash study. Two use it to compute a time-zone difference (Research Policy) or to build an evaluation baseline (Reddit). None evaluates or benchmarks the package itself, and no dedicated paper about timezonefinder exists.
- **The fields are broad**: atmospheric sciences, space physics, astronomy and calendars, public health, transport safety, scientometrics, social-media research, information retrieval and energy systems. The common need is local time at a location.
- **Three studies feed timezonefinder output straight into their main variable**: the time-zone difference in Research Policy, the darkness indicator in the crash study, and the ground truth in the Reddit study. In the crash study, an error near a US zone border would move a crash by an hour relative to dusk, which makes accuracy at borders matter for a published result.
- **Three research packages ship it as a runtime dependency**: HERMESv3 (both modules) and ETHOS.TISED. Their users depend on timezonefinder indirectly.
- **Citation practice is weak.** Only GHOST has a reference-list entry (`Michelfeit, J.: timezonefinder, PyPI`). The rest name the package inline, in a dependency list, in a footnote or in acknowledgements, so citation databases do not count it. BRK-Astronomical Tools attributes it to an unrelated Python textbook (Lutz, 2010). The published version of the Twitter dataset replaced the name with "a time zone finder in Python". A citable record exists ([`CITATION.cff`](../../CITATION.cff), Zenodo DOI 10.5281/zenodo.23579731), but none of the publications found uses it.
- **The coordinates often come from geocoding or devices.** In Research Policy and Reddit they are geocoded place names, the Twitter studies use tweet geotags or bounding boxes, and the runners study uses device GPS. There, the accuracy of the coordinates limits the result more than the lookup's accuracy at borders does.
- **Results are treated as ground truth, with one exception.** The other studies take the result as given. GHOST flags measurements converted with an inferred zone as "Timezone Doubt" and adds its own expanding-radius search for remote stations where no zone was found. Issue #773 tracks the follow-up.
- **Coverage is a lower bound.** The automated sources found 8 publications. One Google Scholar query added 7 more, mostly through footnotes and full text that the other sources do not index. Mentions in theses, paywalled text not indexed by Scholar, and code-only artefacts are still not covered.
