---
title: 'timezonefinder: Offline time zone lookup for geographic coordinates'
tags:
  - Python
  - time zones
  - local time
  - geospatial
  - point-in-polygon
authors:
  - name: Jannik Kissinger
    orcid: 0000-0002-1819-6975
    affiliation: 1
  - name: Evgenii Seliverstov
    affiliation: 2
  - name: Lucas Hemkemeier
    orcid: 0009-0002-6127-717X
    affiliation: 1
affiliations:
  - name: Independent Researcher
    index: 1
  - name: Affiliation to be confirmed
    index: 2
date: 17 November 2026
bibliography: paper.bib
---

<!--
JOSS review notes (see paper/joss-review.md for the full assessment against the review criteria).
These comments do not appear in the compiled PDF. Search for TODO(authors) and OPEN QUESTION.

TODO(authors): fill in the affiliation of Evgenii Seliverstov (waiting on his employer's
  approval, #780) and his ORCID if he has one. JOSS requires an affiliation for every author.
OPEN QUESTION (archive authors): JOSS editors check that the archive deposited after acceptance
  lists the paper's authors ("In most situations, the two author lists should match ... any
  differences need to be explained", editing.html, Post-review). #780 keeps the software's
  single author in CITATION.cff, which Zenodo uses for the archive. Either add the co-authors to
  the archive metadata or prepare the explanation.
TODO(authors, trimming pass): the paper is about 4,560 words; JOSS asks for 750-1750 and "may
  ask [authors] to reduce the length". Section sizes: Summary ~280, Statement of need ~810,
  State of the field ~1,070, Software design ~1,560, Research impact ~400, AI disclosure ~260,
  Acknowledgements ~150. Candidates are marked with "TRIM CANDIDATE" comments below.
-->

# Summary

The time shown on a clock depends on where it hangs. Each place belongs to a time zone, and the rules of that zone, its offset from Coordinated Universal Time (UTC) and when daylight saving time begins and ends, are recorded in the IANA Time Zone Database [@iana_tzdb] under names such as `Europe/Berlin`. Instruments, GPS receivers and computer models usually record when and where something happened as a UTC timestamp and a pair of coordinates. To recover the local time, such as the hour of day, the local date or whether it was dark, one first has to know which time zone contains each coordinate.

`timezonefinder` is a Python package that answers this question without an internet connection. Given a latitude and a longitude, it returns the name of the time zone that contains the point. It reads the zone boundaries published by the timezone-boundary-builder project [@tzbb], which derives them from OpenStreetMap [@osm; @haklay2008osm], and it uses these boundaries exactly as published, without simplifying their shape. Because the data also covers the oceans, practically every coordinate on Earth receives an answer. The boundary data ships as a separately versioned package, so a lookup needs no online service, and pinning the data version makes its answers repeatable. One call can look up an entire array of coordinates, which suits whole datasets. The package has been developed in the open since 2016. Since its first release in April 2016 it has had 86 releases across nine major versions, at least two in every year, which added among other things the ocean zones (version 5, 2020), a separately versioned data package (version 8.3, 2026) and batch lookups (version 9, 2026).

# Statement of need

Research data often records *when* and *where* something happened as a UTC timestamp and a pair of coordinates: measurements at monitoring stations, GPS tracks from wearables and phones, geotagged social-media posts, the points of a model grid. Many research questions, however, depend on local time rather than on UTC: the hour of the day at which an exposure occurred, the date in the local calendar, whether an event happened after dark, whether daylight saving time applied, or how many working hours two places share. Recovering local time needs the IANA time zone at each coordinate. Once the zone is known, standard libraries such as Python's `zoneinfo` [@pep615] apply its rules, including historical changes and daylight saving time. Finding the zone is the step those libraries leave open. It cannot be approximated from the longitude alone, because zone borders follow political boundaries rather than meridians: China spans about 60 degrees of longitude but uses a single zone, and much of western Europe keeps a zone an hour ahead of its solar time.

`timezonefinder` closes this gap. Its target audience is researchers who need local time at recorded coordinates, and the developers of research software that offers this to its own users. Published work uses it in fields as different as atmospheric chemistry, fire-weather forecasting, ionospheric physics, public health, transport safety and the economics of innovation. A harmonised global dataset of surface atmospheric composition measurements uses it to assign a zone to each monitoring station, so that measurements reported in local time can be shifted to UTC [@bowdalo2024ghost]. A week-two fire-danger forecast uses it to find the UTC hour of local noon at every point of its forecast grid, the time at which the fire-danger inputs are taken [@worsnop2021fire]. A study of walking exposure uses it to decide whether a trip started before sunrise or after sunset [@vellimana2023walking], and a study of firm innovation uses it to measure the working-hour overlap between airports linked by nonstop flights [@bahar2023innovation]. Research software ships it as a dependency, among them the HERMESv3 emission model [@guevara2019hermes] and the ionosonde processing library pynasonde [@chakraborty2026pynasonde], so the users of these tools rely on its answers without calling it themselves. The Research impact statement below lists the use in more detail.

<!--
TRIM CANDIDATE: the examples in the paragraph above (GHOST, fire-danger forecast, walking,
  firm innovation, HERMESv3, pynasonde) repeat the Research impact statement almost word for
  word. JOSS: the statement of need covers problem, audience and relation to other work;
  the evidence of use belongs in the Research impact statement.
-->

These uses set four requirements, and the package is designed around them.

**Accuracy at zone borders.** In several of the studies above, the zone feeds directly into the main variable: the hour at which a forecast input is taken, whether a walk counts as a night walk, the time difference between two places. A wrong zone near a border therefore changes a published result. Lookup errors are not random noise either. A tool that simplifies the zone polygons to save space or time makes its errors along borders and coastlines, which biases exactly the analyses that compare regions across a border. `timezonefinder` uses the boundary polygons without simplification, so its accuracy is limited only by the source data. The guarantee is fidelity to that data, not ground truth: where OpenStreetMap places a border wrongly, `timezonefinder` answers wrongly in the same way, and such errors are corrected upstream. The State of the field section quantifies how far a simplifying alternative departs from the source near borders.

**Offline and reproducible lookups.** Web services such as the Google Maps Time Zone API [@google_tz_api] answer the same question, but they need network access and an account, impose quotas and costs, and can change their answers without notice. Compute nodes of research clusters often have no internet access at all. A study that chose `timezonefinder` over a web API names this reason: an offline lookup cannot fail because an external service does [@perezparedes2023athletics]. A lookup in `timezonefinder` is a pure function of the coordinates and the installed boundary data. The data ships as the separately versioned `timezonefinder-data` package, and the installed package reports the timezone-boundary-builder release the answers come from. A study that pins both packages and reports these versions can repeat its lookups exactly, and readers can tell which boundary release a result is based on.

**Coverage of the whole globe.** Instruments are not confined to land. Buoys, ships, aircraft, offshore platforms and remote stations need an answer too. The boundary data includes the nautical zones (`Etc/GMT±N`) over the oceans, so every coordinate receives a zone. Researchers who need to tell land from sea can ask for land zones only.

**Whole datasets at once.** Research datasets often contain millions of points. One call takes an array of longitudes and an array of latitudes and returns the zone of every point, which fits the column-oriented workflows of NumPy [@numpy] and pandas [@pandas]. Optional compiled backends make such batch lookups fast, but they are not required: on a machine without a compiler the package falls back to pure Python and returns identical answers, so a result does not depend on which backend happened to be installed.

# State of the field

Researchers who need the time zone at a coordinate take one of four routes.

**Approximations.** The simplest route derives the offset from the longitude, one hour per 15 degrees, or looks up the country of a point and takes a zone per country. Both fail where it matters. Zone borders follow political boundaries rather than meridians, as the Statement of need shows, and many large countries, among them the United States, Russia, Brazil and Australia, span several zones. An offset derived from the longitude also has no daylight saving time and no history, so it cannot localise a timestamp.

**Online services.** Web APIs such as the Google Maps Time Zone API [@google_tz_api], TimeZoneDB [@timezonedb] or GeoNames [@geonames] return a zone name for a coordinate. As discussed above, they need network access, accounts and quotas, and the boundary data behind an answer is neither stated nor fixed, so a result cannot be repeated later.

**General-purpose GIS tools.** The boundaries of timezone-boundary-builder [@tzbb] are published as a shapefile and as GeoJSON, so a researcher can load them into GeoPandas [@geopandas] or a spatial database such as PostGIS [@postgis] and run a spatial join. This gives exact answers, but it leaves the researcher to obtain the data and record its version, to load and index hundreds of megabytes of geometry, and to decide what happens at a point that lies inside two zones, where the dataset's polygons genuinely overlap. A spatial join returns every match there, or an arbitrary one. `timezonefinder` packages these steps: the data arrives as a versioned dependency, the index is precomputed, the geometry stays memory-mapped instead of loaded, and an overlap is resolved by a documented rule, in which the smaller zone, the one enclaved in the other, wins. A separate call returns every zone that contains the point.

**Dedicated lookup libraries.** The timezone-boundary-builder project lists 26 libraries in 15 programming languages that answer this question from its data [@tzbb_libs], among them C, Go, Java, JavaScript, Julia, R and Rust. In Python, three packages exist. `pytzwhere` [@pytzwhere] is the oldest. It reads the outdated `tz_world` dataset [@tz_world], which has no ocean zones, and its last release dates from 2017. `tzfpy` [@tzfpy], first released in 2022, is a Python binding of the Rust crate `tzf-rs` [@tzfrs] and today the main alternative to `timezonefinder`.

`tzfpy` and `timezonefinder` read the same timezone-boundary-builder releases but make opposite trade-offs. The build of `tzfpy` on PyPI ships simplified polygons. Its wheels are therefore an order of magnitude smaller (about 3 MB, against about 33 MB for `timezonefinder` and its data package), and a single lookup is faster by a small single-digit factor on a representative mix of points (2.6 times over uniformly random points in our benchmark). The price is accuracy near borders. We measured it with both packages on the same boundary release (`tzfpy` 1.3.3 and timezone-boundary-builder 2026c). Over points drawn uniformly from the globe, the two packages never disagree, because a random point lies hundreds of kilometres from the nearest border. Close to borders the picture reverses: within metres of a border, the two packages give different answers on at least one side of most sampled land-zone border locations (about nine in ten at 1 cm, two thirds at 1 m and almost half at 10 m), and the share falls with distance until it disappears at about a hundred metres, in line with the maximum displacement of about 111 m that the maintainer of `tzfpy` states for the simplification [@tzfpy]. For an analysis that looks up points far from any border, the two packages are interchangeable. For an analysis whose points cluster near borders, such as studies that compare neighbouring regions, cities on a border, or every cell of a regular grid, the simplified polygons change answers. `timezonefinder` uses the unsimplified polygons by default. The maintainer of `tzfpy` also publishes an experimental variant with unsimplified polygons, distributed outside PyPI, which we have not measured.

<!--
TODO(authors): the comparison figures come from docs/border_accuracy_vs_tzfpy.rst (2026-08-30)
  and docs/benchmark_results_vs_tzfpy.rst, both measured with tzfpy 1.3.3. tzfpy is at 2.1.2 on
  PyPI now; re-run `make tzfpy-agreement` and the comparison benchmarks before submission and
  update the version and figures above. The wheel sizes are the current PyPI wheels (tzfpy
  2.1.2: 2.9-3.2 MB; timezonefinder 9.2.0: 0.2 MB plus timezonefinder-data 4.2026.6: 32.9 MB).
OPEN QUESTION: a reviewer may ask for a measurement against the unsimplified tzfpy variant.
-->

Beyond border accuracy, the two packages differ in ways that matter for research use. `timezonefinder` ships its boundary data as a separately versioned PyPI package, so a study can pin and report the boundary release independently of the lookup code. It looks up whole NumPy arrays in one call, which outpaces a loop of single `tzfpy` calls on a representative mix of points (2.05 times per point over uniformly random points), since `tzfpy` has no batch interface. It can restrict answers to land zones, return every zone at a point in an overlap, return integer zone identifiers, and convert timestamps with the zone it finds. Finally, it can be built and run without a compiler at all, falling back to pure Python with identical answers, while a source build of `tzfpy` needs a Rust toolchain. All comparisons above come from harnesses in the repository that run both packages on the same points, in the same process and on the same machine. Their generated reports are part of the documentation ([border accuracy](https://timezonefinder.readthedocs.io/en/latest/border_accuracy_vs_tzfpy.html), [speed](https://timezonefinder.readthedocs.io/en/latest/benchmark_results_vs_tzfpy.html)), which also [lists the use cases](https://timezonefinder.readthedocs.io/en/latest/alternatives.html) for which `tzfpy` is the better choice.

**Why a separate package.** `timezonefinder` started in 2016 from `pytzwhere`. At that time, `pytzwhere` parsed a large text file into memory and rebuilt its search structures at every start, which cost hundreds of megabytes of memory before the first answer. Making lookups cheap needed a different data layer and lookup algorithm: polygons stored in binary files with 32-bit integer coordinates, read on demand, and a spatial index precomputed when the data is built. These changes replaced the data format and the lookup as a whole, rather than amending them, so they were released as a new package. Contributions upstream went on in parallel: the first author reported wrong results near nested polygons to `pytzwhere` ([#34](https://github.com/pegler/pytzwhere/issues/34), April 2016), which its maintainers traced and fixed, and proposed updated boundary data ([#36](https://github.com/pegler/pytzwhere/pull/36)), which was not merged. Its data was never updated ([#42](https://github.com/pegler/pytzwhere/issues/42)), and it has had no commit since 2018. A [side-by-side measurement](https://timezonefinder.readthedocs.io/en/latest/alternatives.html#comparison-to-pytzwhere) of its last release, 3.0.3, against `timezonefinder` today shows an order of magnitude less memory and faster start-up and single lookups, and an answer for every point, where `pytzwhere` answers for under a third of the globe. `tzfpy` appeared six years later with a Rust core and a deliberately different trade-off. Neither design can absorb the other without giving up the property it is built around, so the two packages coexist, and the maintainer of `tzfpy` has contributed to `timezonefinder`.

<!--
NOTE: the upstream-contribution sentence rests on the public pytzwhere tracker and history,
  checked 2026-11-19: #34 (opened 2016-04-13 by jannikmi; cstich reported a fix in the
  development branch on 2016-05-16; still open), PR #36 (opened 2016-04-27, closed unmerged by its
  author 2016-06-08, no review), #42 (2017-05-25; cstich: "We are still using the old data"),
  releases 2.3 (2016-03) to 3.0.3 (2017-08), last commit 2018-02. There was no other contact
  with the pytzwhere maintainers (confirmed by the maintainer, 2026-11-19), so the public record
  is complete.
TRIM CANDIDATE: the issue links could be cut to the single sentence of evidence.
-->

# Software design

<!--
TRIM CANDIDATE: JOSS says API functionality belongs in the documentation, not the paper. The
  API names were removed at the maintainer's request. Documentation-level detail a reviewer may
  still flag: the version-string scheme (`4.2026.5`),
  index parameters (0.75 degree cells, 4 x 4 refinement, 128-vertex blocks), the wheel/ABI
  matrix (Distribution), the test strategy (Tests that protect guarantees) and the decision
  records. Keep the trade-offs and their reasons; point to the documentation for the rest.
TODO(authors): the repository links point to `master`; pin them to the release archived for
  the submission once it exists.
-->

The design of `timezonefinder` follows from one decision: the boundary polygons are never simplified. Every vertex and every hole is stored as timezone-boundary-builder publishes it. Most of the remaining design exists to make this full-resolution geometry affordable in time and memory. The trade-offs are described below, together with the alternatives that were measured and rejected.

**No simplification.** Simplification is the obvious way to make a geometric lookup smaller and faster, and it is proposed regularly. It is rejected because of where its error falls. A simplification algorithm such as Douglas–Peucker [@douglas1973] guarantees that no removed vertex lies more than a tolerance away from the simplified line. For a lookup, this bound is not a small error spread over all queries. It is a possibly wrong answer for every query within the tolerance of a border, and those are the only queries whose answer is in doubt at all. The benefits simplification would buy, a smaller distribution and fewer edge tests, are instead bought with lossless means: the spatial index, the latitude block index, compact coordinate storage and memory mapping, all described below. The price that remains is accepted: the distribution is about an order of magnitude larger than a simplified one, and a single lookup near a border is slower. Users who prefer the opposite trade are pointed to `tzfpy` in the documentation.

**Integer coordinates.** Coordinates are multiplied by 10^7 and stored as 32-bit integers, both the polygon vertices and the query point. The resulting grid steps about 1.1 cm at the equator, ten times finer than the six decimal places, about 11 cm, at which timezone-boundary-builder publishes its boundaries. Finer storage would represent precision that the source does not have. The choice halves the storage of the polygon data compared with 64-bit floating point, and it makes the whole geometric path exact integer arithmetic, so that the answer at a point does not depend on floating-point rounding.

**A precomputed spatial index.** A naive lookup tests the query point against every polygon. `timezonefinder` instead divides the globe into a grid of 0.75° cells that is aligned with longitude and latitude, and a precomputed table stores for each cell which zones its polygons belong to. One integer division per axis locates the cell. Most cells lie inside a single zone, mostly in the oceans and the interiors of countries, and for these the table holds the answer directly, without touching any geometry. Where several zones meet, the cell refines into a block of 4 × 4 smaller cells, and only where a smaller cell is still shared by several zones does the lookup test geometry. Even then the index narrows the candidates to a handful of polygons out of the dataset's thousands, ordered so that the test can stop once only one zone remains possible. The last candidate is returned without a test, because it is the only remaining answer. Each candidate is first checked against its bounding box. Its holes are tested before its outer ring, because they are smaller and can rule the polygon out. Finally, the ray-casting test itself skips whole blocks of 128 vertices whose latitude range excludes the query point. This skip is exact, and it removes the large majority of edge tests.

Three properties of this index matter. Alignment with the meridians matters because the ocean zones share borders along every 7.5° meridian, and grids not aligned with them test markedly more polygons per lookup. A cell is found with integer arithmetic alone, which vectorises over a batch of points. And refining only the cells where zones meet spends a bounded index size where the borders are, rather than on every cell of the ocean.

**Memory mapping.** The polygon data is stored in binary files in the FlatBuffers format [@flatbuffers] and is memory-mapped rather than read at start-up. Only the pages a lookup touches become resident, and the operating system can reclaim them under memory pressure. By default the package therefore allocates only single-digit megabytes for its data structures, which keeps it usable in memory-constrained containers and in many parallel worker processes. An option reads all data into memory instead, which is faster and holds about an order of magnitude more memory. A lighter variant answers from the index alone and loads no polygon data at all, for applications that accept an approximate answer near borders.

**Interchangeable point-in-polygon backends.** The inner ray-casting loop exists in three implementations: a C extension, a Numba [@numba] compilation of the Python implementation, and the same Python implementation run uncompiled. The package binds one of them once, at import time: the C extension where it is available, otherwise Numba if it is installed, otherwise pure Python. The three return identical answers and differ only in speed. The rule is that an accelerator makes the package fast but never makes it correct: if the C extension fails to compile and Numba is absent, the package still installs and answers correctly, only more slowly. Because the three are separate code paths, the test suite runs against each configuration, and the benchmarks assert which path they measure instead of assuming it.

**Overlapping zones.** The source data contains places that more than one zone claims, such as the region around Ürümqi, where `Asia/Urumqi` and `Asia/Shanghai` overlap. Returning a set from every lookup would complicate every lookup for a rare case. Ordinary lookups therefore return one zone by a documented rule: the zone with the smaller area on the sphere, which is the one enclaved in the other, wins everywhere. A separate lookup returns every zone that contains the point, with the same answer always first. The rule depends only on the zones, not on the index or the order of the data, so it does not change when the index is rebuilt.

**Batch lookups.** Research data arrives as columns rather than single points. Batch lookups answer whole arrays of points at once. Locating the index cells is vectorised with NumPy [@numpy], so the points that the index answers directly are resolved in a few array operations, and only the remaining points go through the point-in-polygon test one by one. The batch path returns the same answers as the single-point path, which the test suite checks.

**A separately versioned data package.** The boundaries and the code change at different speeds: the boundaries change several times a year with each timezone-boundary-builder release, and the code changes on its own schedule. Shipping both in one package would mean that pinning a dataset pins old code. The data therefore ships as its own distribution, `timezonefinder-data`, built from the same repository. Its version carries two facts: the binary format generation and the upstream release, so that `4.2026.5` is format generation 4 built from release `2026e`. `timezonefinder` requires a fixed format generation but any upstream release, so an ordinary data update needs no code release, while a format change that old code cannot read is refused by the package installer rather than failing at the first lookup. A study can pin the data and report it, and the installed package reports the upstream release in use. Each data file also carries a format marker that the reader checks.

**Automated data updates.** A weekly workflow compares the packaged data version with the latest timezone-boundary-builder release. When a new release appears, it regenerates the binary data files and opens a pull request. When the continuous integration of that pull request passes, a second workflow merges it and publishes the new `timezonefinder-data` release. Code is never part of such a release, so data updates and code work cannot block each other.

**Distribution.** The build and release pipeline publishes Linux wheels with the compiled C extension, for older and newer glibc and for musl, so that both long-lived servers and minimal containers get the compiled path. The extension is built once per stable ABI of CPython, including the stable ABI of the free-threaded interpreter, rather than once per Python version, so a new Python release needs no new build. An end-to-end job installs each built wheel on every supported Python version and checks that the compiled extension is actually loaded and answers correctly. Without that check, a wheel whose extension had silently failed to build would fall back to pure Python and pass every other test. Platforms without a prebuilt wheel compile the extension during installation, and if that fails the installation still succeeds with the pure-Python fallback.

**Tests that protect guarantees.** Beyond ordinary regression tests, the suite contains property-based tests with Hypothesis [@hypothesis], which drive coordinate validation and the public interface with the boundary values, `NaN` and infinities that example-based tests tend to miss. A small group of tests turns rules a reviewer would otherwise have to remember into failures: for example, that the built distributions contain every file needed at run time and nothing else, and that benchmark names, which key the published performance history, do not change by accident. Performance claims come from benchmark harnesses that run competing implementations in the same process on the same committed query points, since figures from different machines vary too much to compare.

**Recorded decisions.** The design decisions behind the current version, including the options that were measured and rejected, are recorded in the repository under [`contributing/improvements/decisions/`](https://github.com/jannikmi/timezonefinder/tree/master/contributing/improvements/decisions). Each record states the measurement and the reasoning that decided it, so that a rejected option is not proposed again without new evidence.

# Research impact statement

`timezonefinder` is used in published research. A literature search across full-text indexes, publisher sites and institutional repositories found 40 publications from 2018 onwards that name the package in their text: 20 journal articles, conference papers, books and reports, 5 preprints and 15 theses. For 37 of them, the passage naming the package was read in the full text. The search method, the passages and the evidence for each entry are recorded in the repository under [`paper/references/`](https://github.com/jannikmi/timezonefinder/tree/master/paper/references).

The publications span a wide range of fields. They include atmospheric emission modelling [@guevara2019hermes] and atmospheric chemistry [@bowdalo2024ghost; @patel2023lightning], fire-weather forecasting [@worsnop2021fire], ionospheric physics [@dinsmore2021griti; @chakraborty2026pynasonde], ocean remote sensing [@macchi2025milky], solar and building energy [@agyeiagyemang2026solar; @omoyele2026ethos; @john2021thermostat], public health [@romero2022runners], transport safety [@vellimana2023walking; @carey2027darkness], economics and management [@bahar2023innovation; @ramirez2023essays], scientometrics [@manchin2025collaboration], computational social science [@dellanegra2026reddit] and radio-spectrum measurement [@sanders2026cbrs]. Every described use maps coordinates to a zone name. The zone then serves to convert timestamps between UTC and local time, to compute the position of the sun or the times of twilight in local time, or to take the time difference between places. In several studies, the result enters the main variable of the analysis directly: the UTC hour at which every fire-danger input is taken [@worsnop2021fire], whether a walk [@vellimana2023walking] or a fatal pedestrian crash [@carey2027darkness] took place at night, the working-hour overlap between two airports [@bahar2023innovation], the time-zone difference between the co-authors of about 20 million articles [@manchin2025collaboration], or the reference against which a method is evaluated [@dellanegra2026reddit].

`timezonefinder` also reaches researchers indirectly, through research software that depends on it. Examples include the HERMESv3 emission model [@guevara2019hermes], the solar-irradiance downscaling package [ETHOS.TISED](https://github.com/FZJ-IEK3-VSA/ETHOS.TISED) of Forschungszentrum Jülich, which takes the zone of the site to set the local time axis of the year it downscales [@omoyele2026ethos], the ionosonde library pynasonde [@chakraborty2026pynasonde] and the measurement tooling of a NIST technical note [@sanders2026cbrs]. GitHub's [dependency graph](https://github.com/jannikmi/timezonefinder/network/dependents) listed about 5,000 repositories and 260 published packages that depend on `timezonefinder` on 18 November 2026. Among them are research and government projects such as CERN's [CAiMIRA](https://gitlab.cern.ch/caimira/caimira), Sandia National Laboratories' [pvOps](https://github.com/sandialabs/pvOps), the [HOPP](https://github.com/NatLabRockies/HOPP) model of the US National Laboratory of the Rockies (formerly NREL), the US EPA's [sensortoolkit](https://github.com/USEPA/sensortoolkit), NOAA's [monetio](https://github.com/noaa-oar-arl/monetio) and the [next_pass](https://github.com/OPERA-Cal-Val/next_pass) tool of NASA JPL's OPERA project.

<!--
TODO(authors): refresh the dependency-graph counts and the access date at submission (GitHub
  states that the counts are approximate).
-->

These figures are a lower bound. Most publications name the package only in the text, a footnote, a dependency list or a code listing, and only three include it in their reference list, so citation databases miss nearly all of them. Theses in institutional repositories and paywalled full texts are only partly indexed. To make citing easier, the project provides a Zenodo DOI [@tzf_zenodo] and a citation file, and this paper adds a peer-reviewed reference.

# AI usage disclosure

Generative AI has been used in the development of `timezonefinder` since September 2025. All earlier development, including the original design of the package, its data format and a first spatial index, was done without it. The current, optimised implementation of the spatial index was developed with AI assistance. The tools used were Anthropic's Claude Code with the models Claude Opus 5, Claude Opus 5.5 and Claude Sonnet 5, OpenAI Codex with GPT-5.6 Terra, and GitHub Copilot, whose underlying models changed over the period of use and were not recorded. The assistance covered code generation and refactoring, tests, benchmark and report scripts, continuous-integration configuration, documentation, the contributor guide, pull-request review and the survey of publications that reference the package. The co-authors also used AI assistants, including Claude Code, for their contributions. This paper was drafted and revised with Claude Code and Claude Opus 5.5 and edited by the authors; no other AI tool was used for it.

The problem framing, the architecture and every design decision were made by the human authors, who reviewed, edited and validated all AI-assisted output before it was merged. Every change is checked by the continuous-integration test suite, and the design decisions, with the measurements and reasoning behind them, are recorded in the repository's contributor guide. Commits made with AI assistance carry co-author trailers in the version history. These trailers are a lower bound on AI use, since not every tool or merge records one. A detailed account compiled from the history is kept in the repository under [`paper/ai-usage-disclosure.md`](https://github.com/jannikmi/timezonefinder/blob/master/paper/ai-usage-disclosure.md).

<!--
TODO(authors): each author confirms the second paragraph for their own part (open point in
  paper/ai-usage-disclosure.md; this cannot be drafted on their behalf).
TRIM CANDIDATE (trim with care): JOSS treats an incomplete AI disclosure as an ethical breach,
  so keep everything it requires: the tools and models with versions, where they were used
  (code, documentation, paper text), the kind of assistance, and the statement that the human
  authors reviewed and validated all AI-assisted output and made the design decisions.
  Candidates that the detailed account in paper/ai-usage-disclosure.md already covers: the list
  of task types in the first paragraph, and the sentences on co-author trailers being a lower
  bound. Check every cut against the JOSS AI policy and ai-usage-disclosure.md.
-->

# Acknowledgements

We thank [Evan Siroky](https://github.com/evansiroky) and the contributors of timezone-boundary-builder [@tzbb], and the OpenStreetMap contributors [@osm; @haklay2008osm], whose boundary data `timezonefinder` is built on. We thank everyone who contributed code, reviews, issues and feedback to `timezonefinder`, in particular [Adam Johnson](https://github.com/adamchainz), [Han Xiao](https://github.com/ringsaturn), [Aryan Raj](https://github.com/a-ryanraj), [Pratyush Kumar](https://github.com/pratyushkumar211), [Lu Yicheng](https://github.com/01luyicheng), [Marco Barbosa](https://github.com/aureliobarbosa), [sefiotonomo](https://github.com/sefiotonomo), [joshuadavidthomas](https://github.com/joshuadavidthomas), [badhope](https://github.com/badhope), [Nice6042](https://github.com/Nice6042), [MsfPablo](https://github.com/MsfPablo), [Pxli9130](https://github.com/Pxli9130), [Kristian Sloth Lauszus](https://github.com/Lauszus), [Chase Horton](https://github.com/Chase-Horton), [Dave Tapley](https://github.com/davetapley), [David Park](https://github.com/daphtdazz), [WestonReed](https://github.com/WestonReed), [Tyler Huntley](https://github.com/Ty1776), [Greg Meyer](https://github.com/gmmeyer), [Romain Girard](https://github.com/romaingd-spi), [synapticarbors](https://github.com/synapticarbors) and [zedrdave](https://github.com/zedrdave), as well as [snowman2](https://github.com/snowman2) and [Xylar Asay-Davis](https://github.com/xylar) for creating and maintaining the conda-forge packages. A complete list is kept in the [documentation](https://timezonefinder.readthedocs.io/en/latest/5_contributing.html).

The development of `timezonefinder` is supported by the sponsors of the first author through GitHub Sponsors. Han Xiao (ringsaturn), the author of `tzfpy`, which this paper compares against, has sponsored the project in the past. The sponsorship gave no influence on the software or on this paper beyond that of any other contributor. The authors declare no other competing interests.

<!--
TODO(authors): each co-author confirms the competing-interests sentence above for their own
  part before submission.
TRIM CANDIDATE: the contributor name list could point to the documentation's complete list.
-->

# References
