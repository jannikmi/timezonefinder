# Scientific publications referencing timezonefinder

This directory records scientific publications that name the `timezonefinder` Python package directly in their text. [`../references.bib`](../references.bib) holds one BibTeX entry per publication, and each entry has a note here, named after its key, with the quoted passage, how the package is cited and what it is used for. The automated search ran on 2026-11-15. The maintainer supplied two Google Scholar result lists on 2026-11-16, and those hits were added and checked the same way.

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
| Google Scholar, second result list from the maintainer | `"timezonefinder"` | 24 new publications, most of them theses and reports from institutional repositories (see the table below), plus duplicates of existing entries and the excluded items below |

Each hit was then checked against the full text for a literal mention of the package. The notes record the evidence in one of three grades:

- **full text read** (21): the passage was read in the publication itself, or for `ramirez2023betting` in the thesis chapter with the same text. Open-access repository PDFs (UDC, Charles University, Carleton, UNLP, Reading, Politecnico di Milano, UPC, Utrecht, NIST, CMAS, the Siberian journal) made most of the second Scholar round verifiable;
- **quoted search snippet** (7): the passage is quoted from a search-engine or Google Scholar extract because the publisher or repository blocked automated access. These are `manchin2025collaboration`, `agyeiagyemang2026solar`, `benetka2019context`, `omoyele2026ethos`, `carey2027darkness`, `srijon2021covid` and `hennessy2025solar`;
- **index match only** (11): Google Scholar's full-text index matches the term, but the passage has not been seen. These are `kolluri2025panchang`, `talafha2026sharjah`, `steinertthrelkeld2018twitter`, `worsnop2021fire`, `john2021thermostat`, `josephs2021pbl`, `bahar2023innovation`, `vellimana2023walking`, `pandey2025water`, `chakraborty2026pynasonde` and `babar2026franchising`.

Check the last two grades against the full text before quoting them.

### Excluded candidates

- *Prediction of Customer Purchase Intention using Social Media Data* (Kale et al., IJARSCT, 2022, doi:10.48175/IJARSCT-4003). A search result described it as using the package in preprocessing. No full text could be read and none of its 10 Crossref references names the package, so it is unconfirmed and left out.
- *Scale-invariant time registration of 24-hour accelerometric rest-activity profiles* (McDonnell et al., bioRxiv 2020 / Biological Rhythm Research 2021). It came up in a combined search, but nothing showed that it mentions the package.
- *Exploring Scientists' Working Timetable: A Global Survey* (arXiv:1310.5777, 2013). It converts coordinates to time zones but predates the package.
- *Energetická bilance UWC spoje* (Bartoň, master's thesis, Brno University of Technology, 2024; Scholar lists it twice, from dspace.vut.cz and theses.cz). The thesis text in the repository contains neither the package name nor any time-zone handling, so the Scholar match probably comes from attached code. Left out until the passage is found.
- *catalyst-cooperative/pudl: PUDL v2025.7.0* (Zenodo). A software release whose changelog mentions moving an expensive `TimezoneFinder` call. It is not a scientific publication. It is still noteworthy as a downstream report about lookup cost.
- A Scholar "[CITATION]" record by Харсун & Бекирова (*Информационно-компьютерные технологии в экономике, образовании и социальной сфере*). There is no identifiable work, full text or passage behind it.
- Repository copies of already recorded papers (the UPCommons versions of both HERMESv3 parts) are not counted separately.
- Publications about time zones that do not use the package (trade economics, collaboration across time zones, RFC 7808, etc.).

## Findings

Thirty-nine publications reference timezonefinder (2018–2027): 20 journal articles, conference papers, books and reports, 5 preprints and 14 theses.

| Key | Year | Venue | Field | Use of timezonefinder | Evidence |
|---|---|---|---|---|---|
| [`vilardell2018hermes`](vilardell2018hermes.md) | 2018 | CMAS Conference (abstract) | emission modelling | dependency, local-time emission profiles | full text |
| [`steinertthrelkeld2018twitter`](steinertthrelkeld2018twitter.md) | 2018 | Cambridge Elements (book) | social-science methods | not seen | index |
| [`guevara2019hermes`](guevara2019hermes.md) | 2019 | Geosci. Model Dev. | emission modelling | dependency (>= 2.1.0) | full text |
| [`benetka2019context`](benetka2019context.md) | 2019 | CHIIR '19 (ACM) | information retrieval | tweet coordinates → local time | snippet |
| [`guevara2020hermes`](guevara2020hermes.md) | 2020 | Geosci. Model Dev. | emission modelling | dependency (> 2.1.0) | full text |
| [`dinsmore2021griti`](dinsmore2021griti.md) | 2021 | MethodsX | ionospheric physics | building block of research code (acknowledgement) | full text |
| [`hosseinabad2021twitter`](hosseinabad2021twitter.md) | 2021 | medRxiv → JMIR Public Health Surveill. | digital public health | tweet location → local time features | full text + snippet |
| [`worsnop2021fire`](worsnop2021fire.md) | 2021 | Weather and Forecasting | fire-weather forecasting | not seen (probably reference list) | index |
| [`john2021thermostat`](john2021thermostat.md) | 2021 | Concordia University (thesis) | building energy | not seen | index |
| [`josephs2021pbl`](josephs2021pbl.md) | 2021 | CUNY (M.S. thesis) | atmospheric science | not seen | index |
| [`srijon2021covid`](srijon2021covid.md) | 2021 | thesis (ProQuest) | social-media analysis | tweet timestamps → local time (`in_memory=True`) | snippet |
| [`romero2022runners`](romero2022runners.md) | 2022 | IJERPH | public health, wearables | GPS start point → local time | full text |
| [`ramirez2023betting`](ramirez2023betting.md) | 2023 | Int. J. Forecasting | sports economics | match city → time zone | full text (thesis) + snippet |
| [`bahar2023innovation`](bahar2023innovation.md) | 2023 | Management Science | economics of innovation | not seen | index |
| [`vellimana2023walking`](vellimana2023walking.md) | 2023 | UT Austin (thesis) | transport safety | not seen | index |
| [`perezparedes2023athletics`](perezparedes2023athletics.md) | 2023 | Univ. da Coruña (bachelor) | sports analytics | venue → time-zone offset metric; chosen over a web API | full text |
| [`krsicka2023webcams`](krsicka2023webcams.md) | 2023 | Charles University (bachelor) | computer vision, meteorology | webcam location → zone for sun position | full text |
| [`patel2023lightning`](patel2023lightning.md) | 2023 | Carleton University (M.A.Sc.) | atmospheric chemistry | lightning flash → local time (`timezone_at`) | full text |
| [`ponteahon2023plates`](ponteahon2023plates.md) | 2023 | UNLP (Licenciatura) | astronomy, digital heritage | observatory → zone for plate metadata | full text |
| [`ramirez2023essays`](ramirez2023essays.md) | 2023 | University of Reading (PhD) | sports economics | as `ramirez2023betting` | full text |
| [`bowdalo2024ghost`](bowdalo2024ghost.md) | 2024 | Earth Syst. Sci. Data | atmospheric chemistry | station → zone, local time → UTC | full text |
| [`manchin2025collaboration`](manchin2025collaboration.md) | 2025 | Research Policy | scientometrics | co-author time-zone differences | snippet |
| [`kolluri2025panchang`](kolluri2025panchang.md) | 2025 | SSRN | calendar computation | not seen | index |
| [`macchi2025milky`](macchi2025milky.md) | 2025 | Politecnico di Milano (M.Sc.) | ocean remote sensing | ship reports at sea → UTC | full text |
| [`pandey2025water`](pandey2025water.md) | 2025 | dissertation (ProQuest) | agricultural water management | not seen | index |
| [`hennessy2025solar`](hennessy2025solar.md) | 2025 | Loyola Marymount (honors) | solar tracking | site → UTC offset | snippet |
| [`dellanegra2026reddit`](dellanegra2026reddit.md) | 2026 | arXiv (cs.SI) | computational social science | geocoded places → ground truth | full text |
| [`agyeiagyemang2026solar`](agyeiagyemang2026solar.md) | 2026 | Energies | solar energy | weather station → zone for pvlib | snippet |
| [`gurbulak2026brk`](gurbulak2026brk.md) | 2026 | Osmaniye Korkut Ata Univ. J. | astronomy software | observing site → local time | full text |
| [`omoyele2026ethos`](omoyele2026ethos.md) | 2026 | SoftwareX | solar energy software | site → zone; runtime dependency | snippet |
| [`talafha2026sharjah`](talafha2026sharjah.md) | 2026 | SSRN | astronomy, calendars | not seen | index |
| [`timosenco2026flight`](timosenco2026flight.md) | 2026 | UPC (bachelor) | aviation operations | aerodrome → local twilight times | full text |
| [`panteleev2026response`](panteleev2026response.md) | 2026 | Siberian J. Life Sci. Agric. | pharmacy marketing | preprocessing dependency | full text |
| [`panteleev2026validation`](panteleev2026validation.md) | 2026 | Siberian J. Life Sci. Agric. | pharmacy retail | preprocessing dependency (in abstract) | full text |
| [`sanders2026cbrs`](sanders2026cbrs.md) | 2026 | NIST Technical Note 2359 | radio-spectrum measurement | dependency (>= 6.0.2) | full text |
| [`chakraborty2026pynasonde`](chakraborty2026pynasonde.md) | 2026 | SoftwareX | ionospheric software | not seen | index |
| [`babar2026franchising`](babar2026franchising.md) | 2026 | SSRN | operations management | not seen | index |
| [`varjassy2026oss`](varjassy2026oss.md) | 2026 | Utrecht University (M.Sc.) | innovation studies | country time-zone difference (fixed reference date) | full text |
| [`carey2027darkness`](carey2027darkness.md) | 2027 | J. Transport & Health | transport safety | crash → local time vs. civil dusk | snippet |

### Observations

- **One usage pattern dominates.** Every described use maps coordinates to an IANA zone name. The zone is then used to convert timestamps between UTC and local time (most uses), to compute a sun or twilight position in local time (webcams, solar tracking, flight school, pedestrian darkness, astronomy tools), or to take a time-zone difference between places (Research Policy, Utrecht, the athletics thesis). None of the publications evaluates or benchmarks the package, and there is no dedicated paper about it.
- **The fields are broad.** They cover atmospheric sciences (emissions, air quality, lightning, boundary layer, fire weather), space physics and astronomy, ocean remote sensing, public health, transport safety, economics and management (sports betting, innovation, collaboration, franchising, pharmacy retail), social-media research, energy systems, radio-spectrum measurement and aviation. The common need is local time at a location.
- **Theses are a large share.** 14 of the 39 publications are theses, most of them found only through Google Scholar's index of institutional repositories. The automated sources found none of them.
- **Some studies feed the result straight into their main variable.** This applies to time-zone differences (Research Policy, Utrecht), the darkness indicator (pedestrian crashes) and the ground truth (Reddit). An error near a zone border would move a result there, so accuracy at borders matters for published conclusions.
- **Research software ships it as a dependency.** HERMESv3 (three publications), ETHOS.TISED, pynasonde and the NIST CBRS tooling do, and their users inherit timezonefinder. Only HERMESv3 (2.1.0) and NIST (6.0.2) state a minimum version.
- **Citation practice is weak and sometimes wrong.** Only GHOST and the UPC flight-school thesis have reference-list entries, and possibly Weather and Forecasting. The rest name the package inline, in dependency lists, in footnotes or in code. Two attributions are wrong: BRK-Astronomical Tools cites a Python textbook (Lutz, 2010), and the UPC budget annex names a non-existent author ("J. Janetzko"). The published version of the Twitter dataset dropped the name entirely. None uses the Zenodo DOI in [`CITATION.cff`](../../CITATION.cff) (10.5281/zenodo.23579731).
- **Users report what the docs could address.**
  - GHOST added its own fallback for remote stations where no zone was found (issue #773). The Milky Seas thesis maps reports at sea, where the nautical `Etc/GMT±N` zones apply.
  - The LMU code builds a new `TimezoneFinder()` on every call.
  - The PUDL changelog (excluded above) moved an "expensive TimezoneFinder" call.
  - The athletics thesis is the one source that explains why it picked the package: offline lookups are not exposed to failures of an external service.
- **Coverage is still a lower bound.** Paywalled full text not indexed by Scholar, and code-only artefacts, remain uncovered. 11 entries rest on an index match only and need the full text checked.
