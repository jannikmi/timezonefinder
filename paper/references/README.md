# Scientific publications referencing timezonefinder

This directory records scientific publications that name the `timezonefinder` Python package directly in their text. [`../references.bib`](../references.bib) holds one BibTeX entry per publication, and each entry has a note here, named after its key, with the quoted passage, how the package is cited and what it is used for. The automated search ran on 2026-11-15. The maintainer supplied two Google Scholar result lists on 2026-11-16, and those hits were added and checked the same way. The same day the maintainer supplied the publisher PDFs of `worsnop2021fire`, `bahar2023innovation` and `chakraborty2026pynasonde` and asked for eleven further Google Scholar searches, which were run in the Claude desktop app's built-in browser; open full texts of further entries were read in that browser too.

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
| Google Scholar, sorted by date | `"timezonefinder"` | 1 hit ([`panteleev2026validation`](panteleev2026validation.md)). Date sorting only lists recently added records, so there is no page 3 |
| Google Scholar | `"from timezonefinder import"` | 4 hits, all recorded: `srijon2021covid`, `pandey2025water`, `josephs2021pbl`, `hennessy2025solar` |
| Google Scholar | `"timezone_at"` | 7 hits, all recorded: `patel2023lightning`, `kolluri2025panchang`, `steinertthrelkeld2018twitter`, `srijon2021covid`, `josephs2021pbl`, `hennessy2025solar`, `pandey2025water` |
| Google Scholar | `"timezonefinderL"` | No hits |
| Google Scholar | `"pypi.org/project/timezonefinder"` | 3 hits, all recorded: `worsnop2021fire`, `perezparedes2023athletics`, `timosenco2026flight`. `bahar2023innovation` and `chakraborty2026pynasonde` print the URL too but are not returned |
| Google Scholar | `"jannikmi/timezonefinder"` | No hits |
| Google Scholar | `"timezonefinder.readthedocs"` | 1 hit, recorded: `dinsmore2021griti` |
| Google Scholar | `"Michelfeit" timezone` | 17 hits. Only `bowdalo2024ghost` refers to the package; the others cite a different Michelfeit (corpus-linguistics tooling) or acknowledge one, and mention time zones in passing |
| Google Scholar | `"Kissinger" "timezonefinder"` | No hits |
| Google Scholar | `"zenodo.23579731"` | No hits |
| Google Scholar | `"time zone finder" python` | 2 hits: `hosseinabad2021twitter` (published version) and a sister paper that does not name the package (excluded below) |

Each hit was then checked against the full text for a literal mention of the package. The notes record the evidence in one of three grades:

- **full text read** (36): the passage was read in the publication itself, or for `ramirez2023betting` in the thesis chapter with the same text, or for `steinertthrelkeld2018twitter` in the author-hosted copy of the Cambridge Core PDF. The maintainer downloaded the SSRN PDF of `kolluri2025panchang`. Open-access repository PDFs (UDC, Charles University, Carleton, UNLP, Reading, Politecnico di Milano, UPC, Utrecht, NIST, CMAS, the Siberian journal, Concordia, CUNY, UT Austin, Oklahoma State, LMU, Brno) made most theses verifiable, and the maintainer supplied the publisher PDFs of `worsnop2021fire`, `bahar2023innovation` and `chakraborty2026pynasonde` and the published texts of `omoyele2026ethos`, `manchin2025collaboration` and `carey2027darkness`. Some repository PDFs could only be read in the browser, with pdf.js, because the repository refuses command-line downloads;
- **quoted search snippet** (2): the passage is quoted from a search-engine or Google Scholar extract because the publisher blocked access (ScienceDirect and SSRN refuse the browser too, and ACM and ProQuest are paywalled). These are `benetka2019context` and `srijon2021covid`;
- **index match only** (2): Google Scholar's full-text index matches the term, but the passage has not been seen. These are `talafha2026sharjah` and `babar2026franchising`, both on SSRN, whose bot check refuses command-line access and offers no other copy. For `talafha2026sharjah` the first author's public code repository imports and calls the package, which rules out a false match, though the paper's passage is still unread.

Check the last two grades against the full text before quoting them.

### Excluded candidates

- *Prediction of Customer Purchase Intention using Social Media Data* (Kale et al., IJARSCT, 2022, doi:10.48175/IJARSCT-4003). A search result described it as using the package in preprocessing. The full text (four pages, from the journal site) contains no time-zone handling at all, in the text or the figures, so the search result was wrong.
- *Crowdsourcing for Machine Learning in Public Health Surveillance: Lessons Learned From Amazon Mechanical Turk* (Shakeri Hossein Abad et al., J Med Internet Res 24(1), e28749, 2022, doi:10.2196/28749). The same group and dataset as [`hosseinabad2021twitter`](hosseinabad2021twitter.md). The full text says only "we used a time zone finder in Python" and never names the package.
- *Scale-invariant time registration of 24-hour accelerometric rest-activity profiles* (McDonnell et al., bioRxiv 2020 / Biological Rhythm Research 2021). It came up in a combined search, but nothing showed that it mentions the package.
- *Exploring Scientists' Working Timetable: A Global Survey* (arXiv:1310.5777, 2013). It converts coordinates to time zones but predates the package.
- *catalyst-cooperative/pudl: PUDL v2025.7.0* (Zenodo). A software release whose changelog mentions moving an expensive `TimezoneFinder` call. It is not a scientific publication. It is still noteworthy as a downstream report about lookup cost.
- A Scholar "[CITATION]" record by Харсун & Бекирова (*Информационно-компьютерные технологии в экономике, образовании и социальной сфере*). There is no identifiable work, full text or passage behind it.
- Google Scholar hits for `"Michelfeit" timezone` other than GHOST: they cite or thank people of that name for unrelated work and mention time zones in passing.
- Repository copies of already recorded papers (the UPCommons versions of both HERMESv3 parts) are not counted separately.
- Publications about time zones that do not use the package (trade economics, collaboration across time zones, RFC 7808, etc.).


### Still to check

Candidates and gaps that were not fully checked, with what blocked them.

- **Recorded entries without full text.** Snippet grade: `benetka2019context` (ACM, paywalled, no open copy known) and `srijon2021covid` (ProQuest; institution not identified). Index-match grade: `talafha2026sharjah` and `babar2026franchising` (SSRN bot check; on 2026-11-19 OpenAlex, the Tilburg research portal and the authors' pages led back to SSRN only). A person in a browser on SSRN can read both; `talafha2026sharjah` is already confirmed in the authors' code.
- **Parts of recorded entries not read.** The online appendix of `bahar2023innovation` (how "time zone difference from GMT" in Table 8 was computed), and the code archive `appendix-1.zip` of `barton2024uwc` (how the zone is used).
- **Searches not completed.** Paging through the full relevance-sorted Google Scholar list for `"timezonefinder"` once more, to catch records added after the maintainer's two result lists (Scholar rate-limited the browser). Semantic Scholar snippet search and OpenAlex full-text search (both refused with rate limits). Scholar searches for the method names `"timezone_at_land"`, `"certain_timezone_at"` and `"TimezoneFinder()"`, which, like `"timezone_at"`, would surface code listings.
- **Excluded but reversible.** McDonnell et al. (bioRxiv 2020 / Biological Rhythm Research 2021): the full text was not searched for the package.

## Findings

Forty publications reference timezonefinder (2018–2027): 20 journal articles, conference papers, books and reports, 5 preprints and 15 theses.

| Key | Year | Venue | Field | Use of timezonefinder | Evidence |
|---|---|---|---|---|---|
| [`vilardell2018hermes`](vilardell2018hermes.md) | 2018 | CMAS Conference (abstract) | emission modelling | dependency, local-time emission profiles | full text |
| [`steinertthrelkeld2018twitter`](steinertthrelkeld2018twitter.md) | 2018 | Cambridge Elements (book) | social-science methods | tweet coordinates → local time; code listing calling `timezone_at` | full text |
| [`guevara2019hermes`](guevara2019hermes.md) | 2019 | Geosci. Model Dev. | emission modelling | dependency (>= 2.1.0) | full text |
| [`benetka2019context`](benetka2019context.md) | 2019 | CHIIR '19 (ACM) | information retrieval | tweet coordinates → local time | snippet |
| [`guevara2020hermes`](guevara2020hermes.md) | 2020 | Geosci. Model Dev. | emission modelling | dependency (> 2.1.0) | full text |
| [`dinsmore2021griti`](dinsmore2021griti.md) | 2021 | MethodsX | ionospheric physics | building block of research code (acknowledgement) | full text |
| [`hosseinabad2021twitter`](hosseinabad2021twitter.md) | 2021 | medRxiv → JMIR Public Health Surveill. | digital public health | tweet location → local time features | full text + snippet |
| [`worsnop2021fire`](worsnop2021fire.md) | 2021 | Weather and Forecasting | fire-weather forecasting | grid point → UTC hour of local noon for all index inputs; inline PyPI URL | full text |
| [`john2021thermostat`](john2021thermostat.md) | 2021 | Concordia University (M.A.Sc.) | building energy | home location → local sunrise/sunset to select night periods | full text |
| [`josephs2021pbl`](josephs2021pbl.md) | 2021 | CUNY (M.S.) | atmospheric science | profiler site → local time (code appendix only) | full text |
| [`srijon2021covid`](srijon2021covid.md) | 2021 | thesis (ProQuest) | social-media analysis | tweet timestamps → local time (`in_memory=True`) | snippet |
| [`romero2022runners`](romero2022runners.md) | 2022 | IJERPH | public health, wearables | GPS start point → local time | full text |
| [`ramirez2023betting`](ramirez2023betting.md) | 2023 | Int. J. Forecasting | sports economics | match city → time zone | full text (thesis) + snippet |
| [`bahar2023innovation`](bahar2023innovation.md) | 2023 | Management Science | economics of innovation | airport → zone for temporal distance (moderator); footnote URL | full text |
| [`vellimana2023walking`](vellimana2023walking.md) | 2023 | UT Austin (M.S.) | transport safety | trip origin → local time to label night walking (dependent variable) | full text |
| [`perezparedes2023athletics`](perezparedes2023athletics.md) | 2023 | Univ. da Coruña (bachelor) | sports analytics | venue → time-zone offset metric; chosen over a web API | full text |
| [`krsicka2023webcams`](krsicka2023webcams.md) | 2023 | Charles University (bachelor) | computer vision, meteorology | webcam location → zone for sun position | full text |
| [`patel2023lightning`](patel2023lightning.md) | 2023 | Carleton University (M.A.Sc.) | atmospheric chemistry | lightning flash → local time (`timezone_at`) | full text |
| [`ponteahon2023plates`](ponteahon2023plates.md) | 2023 | UNLP (Licenciatura) | astronomy, digital heritage | observatory → zone for plate metadata | full text |
| [`ramirez2023essays`](ramirez2023essays.md) | 2023 | University of Reading (PhD) | sports economics | as `ramirez2023betting` | full text |
| [`bowdalo2024ghost`](bowdalo2024ghost.md) | 2024 | Earth Syst. Sci. Data | atmospheric chemistry | station → zone, local time → UTC | full text |
| [`barton2024uwc`](barton2024uwc.md) | 2024 | Brno University of Technology (M.Sc.) | optical communication | dependency of link-budget software (appendix) | full text |
| [`manchin2025collaboration`](manchin2025collaboration.md) | 2025 | Research Policy | scientometrics | co-author time-zone differences from geocoded affiliations (key variable, ~20 million articles); footnote URL | full text |
| [`kolluri2025panchang`](kolluri2025panchang.md) | 2025 | SSRN | calendar computation | location → zone and DST offset for sunrise-based panchang times (code listing, appendix) | full text |
| [`macchi2025milky`](macchi2025milky.md) | 2025 | Politecnico di Milano (M.Sc.) | ocean remote sensing | ship reports at sea → UTC | full text |
| [`pandey2025water`](pandey2025water.md) | 2025 | Oklahoma State University (M.S.) | agricultural water management | field location → local time in a deployed forecast service | full text |
| [`hennessy2025solar`](hennessy2025solar.md) | 2025 | Loyola Marymount (honors) | solar tracking | site → UTC offset (code listing only) | full text |
| [`dellanegra2026reddit`](dellanegra2026reddit.md) | 2026 | arXiv (cs.SI) | computational social science | geocoded places → ground truth | full text |
| [`agyeiagyemang2026solar`](agyeiagyemang2026solar.md) | 2026 | Energies | solar energy | weather station → zone for pvlib | full text |
| [`gurbulak2026brk`](gurbulak2026brk.md) | 2026 | Osmaniye Korkut Ata Univ. J. | astronomy software | observing site → local time | full text |
| [`omoyele2026ethos`](omoyele2026ethos.md) | 2026 | SoftwareX | solar energy software | site → zone for the local-time axis of the downscaled year; runtime dependency; footnote URL | full text |
| [`talafha2026sharjah`](talafha2026sharjah.md) | 2026 | SSRN | astronomy, calendars | observing site → local time of sunset and conjunction (from the authors' code) | index; code confirmed |
| [`timosenco2026flight`](timosenco2026flight.md) | 2026 | UPC (bachelor) | aviation operations | aerodrome → local twilight times | full text |
| [`panteleev2026response`](panteleev2026response.md) | 2026 | Siberian J. Life Sci. Agric. | pharmacy marketing | preprocessing dependency | full text |
| [`panteleev2026validation`](panteleev2026validation.md) | 2026 | Siberian J. Life Sci. Agric. | pharmacy retail | preprocessing dependency (in abstract) | full text |
| [`sanders2026cbrs`](sanders2026cbrs.md) | 2026 | NIST Technical Note 2359 | radio-spectrum measurement | dependency (>= 6.0.2) | full text |
| [`chakraborty2026pynasonde`](chakraborty2026pynasonde.md) | 2026 | SoftwareX | ionospheric software | required dependency (v1.0.0); reference list, wrong author | full text |
| [`babar2026franchising`](babar2026franchising.md) | 2026 | SSRN | operations management | not seen | index |
| [`varjassy2026oss`](varjassy2026oss.md) | 2026 | Utrecht University (M.Sc.) | innovation studies | country time-zone difference (fixed reference date) | full text |
| [`carey2027darkness`](carey2027darkness.md) | 2027 | J. Transport & Health | transport safety | crash → local time vs. civil dusk (darkness outcome); named in the text only | full text |

### Observations

- **One usage pattern dominates.** Every described use maps coordinates to an IANA zone name. The zone is then used to convert timestamps between UTC and local time (most uses), to compute a sun or twilight position in local time (webcams, solar tracking, flight school, pedestrian darkness, walking at night, smart-thermostat night periods, fire-weather local noon, astronomy tools), or to take a time-zone difference between places (Management Science, Research Policy, Utrecht, the athletics thesis). None of the publications evaluates or benchmarks the package, and there is no dedicated paper about it.
- **The fields are broad.** They cover atmospheric sciences (emissions, air quality, lightning, boundary layer, fire weather), space physics and astronomy, ocean remote sensing, underwater optical communication, public health, transport safety, building energy, economics and management (sports betting, innovation, collaboration, franchising, pharmacy retail), social-media research, energy systems, agriculture, radio-spectrum measurement and aviation. The common need is local time at a location.
- **Theses are a large share.** 15 of the 40 publications are theses, most of them found only through Google Scholar's index of institutional repositories. The automated sources found none of them.
- **Scholar indexes code.** Six mentions sit only in code listings or appendices (`steinertthrelkeld2018twitter`, `kolluri2025panchang`, `josephs2021pbl`, `hennessy2025solar`, `srijon2021covid`, and the dependency list of `barton2024uwc`), and searching for the method name `"timezone_at"` returns them. A repository's extracted-text file can miss such an appendix: Brno's stops at 100,000 characters, before the page that names the package.
- **Some studies feed the result straight into their main variable.** This applies to time-zone differences (Management Science's temporal-distance moderator, Research Policy, Utrecht), the darkness classification (pedestrian crashes, nighttime walk-miles), night-period selection (smart thermostats), the UTC hour of local noon that every fire-danger input is taken at (Weather and Forecasting), and the ground truth (Reddit). An error near a zone border would move a result there, so accuracy at borders matters for published conclusions. The fire-weather study runs the lookup on a regular grid, where every border cell takes one zone or the other.
- **Research software ships it as a dependency.** HERMESv3 (three publications), ETHOS.TISED, pynasonde, the NIST CBRS tooling, the Brno link-budget program and the Oklahoma State forecast service do, and their users inherit timezonefinder. Only HERMESv3 (2.1.0) and NIST (6.0.2) state a minimum version in the publication. The pynasonde paper lists it as required for v1.0.0 without a version; its repository has since made it an optional extra pinned `>=6.5`.
- **Citation practice is weak and sometimes wrong.** Only GHOST, the UPC flight-school thesis and pynasonde have reference-list entries. Weather and Forecasting gives the PyPI URL inline, Management Science, Research Policy and ETHOS.TISED in footnotes; the rest name the package inline, in dependency lists, in footnotes or in code. Three attributions are wrong: pynasonde's reference [48] names "Müller F." as author (2021, accessed 9 October 2025), BRK-Astronomical Tools cites a Python textbook (Lutz, 2010), and the UPC budget annex names a non-existent author ("J. Janetzko"). The published version of the Twitter dataset dropped the name entirely, and a sister paper of the same group says only "a time zone finder in Python". None uses the Zenodo DOI in [`CITATION.cff`](../../CITATION.cff) (10.5281/zenodo.23579731).
- **Users report what the docs could address.**
  - GHOST added its own fallback for remote stations where no zone was found (issue #773), and ETHOS.TISED falls back to `"UTC"` when `timezone_at` returns `None`. With the default dataset that branch never runs, which the documentation could state. The Milky Seas thesis maps reports at sea, where the nautical `Etc/GMT±N` zones apply.
  - The Panchang service (`kolluri2025panchang`) treats points within 10 km of a zone border as uncertain and settles them with the user's location string, using its own boundary-distance helpers. The documentation could point such users to the lookup that returns every zone containing a point and to the documented overlap rule.
  - The LMU code and pynasonde build a new `TimezoneFinder()` on every call or object.
  - The LMU code takes the UTC offset of the current moment rather than of the date it computes, and the CUNY script keeps only the whole hours of the offset. Both are mistakes in handling the zone after the lookup, which a short example of converting a timestamp correctly could prevent.
  - The PUDL changelog (excluded above) moved an "expensive TimezoneFinder" call.
  - The athletics thesis is the one source that explains why it picked the package: offline lookups are not exposed to failures of an external service.
- **Coverage is still a lower bound.** Paywalled full text not indexed by Scholar, and code-only artefacts, remain uncovered. Two entries rest on a search snippet and two on an index match only; their publishers or SSRN refused access from here.
