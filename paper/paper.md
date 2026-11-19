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
NOTE (archive authors): JOSS editors check that the archive deposited after acceptance lists
  the paper's authors ("In most situations, the two author lists should match ... any
  differences need to be explained", editing.html, Post-review). Decided in #780: the archive
  keeps the single author from CITATION.cff, and the maintainer explains the difference to the
  editor in person (reason and fallback recorded in #780). Nothing to change in this paper.
TODO(authors, trimming pass): the paper is about 2,870 words; JOSS asks for 750-1750 and "may
  ask [authors] to reduce the length". Section sizes: Summary ~210, Statement of need ~430,
  State of the field ~690, Software design ~770, Research impact ~360, AI disclosure ~260,
  Acknowledgements ~160. The text that repeated other sections is cut, and Statement of need,
  State of the field, Software design and Research impact are trimmed; the remaining
  candidates are marked with "TRIM CANDIDATE" comments below.
-->

# Summary

The time shown on a clock depends on where it hangs. Each place belongs to a time zone, and the rules of that zone, its offset from Coordinated Universal Time (UTC) and when daylight saving time begins and ends, are recorded in the IANA Time Zone Database [@iana_tzdb] under names such as `Europe/Berlin`. Instruments, GPS receivers and computer models usually record when and where something happened as a UTC timestamp and a pair of coordinates. To recover the local time, such as the hour of day, the local date or whether it was dark, one first has to know which time zone contains each coordinate.

`timezonefinder` is a Python package that answers this question without an internet connection. Given a latitude and a longitude, it returns the name of the time zone that contains the point. It reads the zone boundaries published by the timezone-boundary-builder project [@tzbb], which derives them from OpenStreetMap [@osm; @haklay2008osm], and it uses these boundaries exactly as published, without simplifying their shape. Since its first release in April 2016 it has had 86 releases across nine major versions, at least two in every year, which added among other things the ocean zones (version 5, 2020), a separately versioned data package (version 8.3, 2026) and batch lookups (version 9, 2026).

# Statement of need

Research data often records *when* and *where* something happened as a UTC timestamp and a pair of coordinates: measurements at monitoring stations, GPS tracks, geotagged posts, the points of a model grid. Many research questions depend on local time instead: the hour of the day at which an exposure occurred, the local date, whether an event happened after dark, or how many working hours two places share. Once the IANA time zone of a coordinate is known, standard libraries such as Python's `zoneinfo` [@pep615] apply its rules, including daylight saving time and historical changes. Finding the zone is the step those libraries leave open.

`timezonefinder` closes this gap for researchers who need local time at recorded coordinates, and for the developers of research software that offers this to its own users. The Research impact statement describes this use. It sets four requirements, and the package is designed around them.

**Accuracy at zone borders.** In several published studies, the zone feeds directly into the main variable: the hour at which a forecast input is taken [@worsnop2021fire], whether a walk counts as a night walk [@vellimana2023walking], the time difference between two places [@bahar2023innovation]. A tool that simplifies the zone polygons makes its errors along borders and coastlines, which biases exactly the analyses that compare regions across a border. `timezonefinder` uses the polygons without simplification, so its accuracy is limited only by the source data. The guarantee is fidelity to that data, not ground truth: where OpenStreetMap places a border wrongly, `timezonefinder` answers wrongly in the same way.

**Offline and reproducible lookups.** Compute nodes of research clusters often have no internet access, and a web service can fail, impose quotas or change its answers without notice; one study chose `timezonefinder` over a web API for this reason [@perezparedes2023athletics]. A lookup in `timezonefinder` is a pure function of the coordinates and the installed boundary data, which ships as a separately versioned package and reports the timezone-boundary-builder release it comes from. A study that pins and reports both versions can repeat its lookups exactly.

**Coverage of the whole globe.** Buoys, ships, aircraft and remote stations need an answer too. The boundary data includes the nautical zones over the oceans, so every coordinate receives a zone, and researchers who need to tell land from sea can ask for land zones only.

**Whole datasets at once.** Research datasets often contain millions of points. One call returns the zones of whole arrays of coordinates, which fits the column-oriented workflows of NumPy [@numpy] and pandas [@pandas], and the answers are identical whether or not an optional compiled backend is installed.

# State of the field

Researchers who need the time zone at a coordinate take one of four routes.

**Approximations** derive the offset from the longitude, one hour per 15 degrees, or take one zone per country. Both fail where it matters: zone borders do not follow meridians, many large countries span several zones, and an offset derived from the longitude has no daylight saving time and no history.

**Online services** such as the Google Maps Time Zone API [@google_tz_api], TimeZoneDB [@timezonedb] or GeoNames [@geonames] need network access, accounts and quotas, and they neither state nor fix the boundary data behind an answer, so a result cannot be repeated later.

**General-purpose GIS tools** such as GeoPandas [@geopandas] or the spatial database PostGIS [@postgis] can join points against the published boundaries [@tzbb] exactly. They leave the researcher to obtain the data and record its version, to load and index hundreds of megabytes of geometry, and to decide what happens where zones overlap, where a spatial join returns every match or an arbitrary one. `timezonefinder` packages these steps, as described under Software design.

**Dedicated lookup libraries** answer the question from the timezone-boundary-builder data: 26 libraries in 15 programming languages [@tzbb_libs]. In Python, `pytzwhere` [@pytzwhere] reads the outdated `tz_world` dataset [@tz_world], which has no ocean zones, and has had no release since 2017. `tzfpy` [@tzfpy], a binding of the Rust crate `tzf-rs` [@tzfrs] first released in 2022, is today the main alternative to `timezonefinder`.

**Comparison with `tzfpy`.** The two packages read the same timezone-boundary-builder releases but make opposite trade-offs. The build of `tzfpy` on PyPI ships simplified polygons, so its wheels are about a tenth of the size (about 3 MB, against about 33 MB for `timezonefinder` and its data package), and a single lookup is faster by a small single-digit factor. We measured the price with both packages on the same boundary release (`tzfpy` 2.1.2, timezone-boundary-builder 2026f). Uniformly random points, which lie far from any border, never receive different answers. Near land-zone borders, the packages disagree on at least one side of about nine in ten sampled border locations at 1 cm, two thirds at 1 m and almost half at 10 m, and the disagreement vanishes at about 100 m, in line with the maximum displacement of about 111 m that the maintainer of `tzfpy` states for the simplification [@tzfpy]. An analysis of points far from borders can use either package; an analysis whose points cluster near borders, such as a comparison of neighbouring regions or a lookup for every cell of a grid, gets different answers from the simplified polygons. `timezonefinder` also looks up whole NumPy arrays in one call, faster per point than a loop of single `tzfpy` calls, ships its data as a separately versioned package, and runs without a compiler. An experimental `tzfpy` variant with unsimplified polygons, distributed outside PyPI, was not measured. The comparisons run both packages on the same points on the same machine, and their reports are part of the documentation ([border accuracy](https://timezonefinder.readthedocs.io/en/latest/border_accuracy_vs_tzfpy.html), [speed](https://timezonefinder.readthedocs.io/en/latest/benchmark_results_vs_tzfpy.html)), which also [lists the use cases](https://timezonefinder.readthedocs.io/en/latest/alternatives.html) for which `tzfpy` is the better choice.

<!--
Speed is stated qualitatively on purpose: the factors are measured on one machine and move with
  the hardware; the speed report in the documentation gives them with the machine they come from.
  The border-accuracy shares come from docs/border_accuracy_vs_tzfpy.rst (tzfpy 2.1.2, boundary
  release 2026f). The wheel sizes are the current PyPI wheels (tzfpy 2.1.2: 2.9-3.2 MB;
  timezonefinder 9.2.0: 0.2 MB plus timezonefinder-data 4.2026.6: 32.9 MB).
OPEN QUESTION: a reviewer may ask for a measurement against the unsimplified tzfpy variant.
-->

**Why a separate package.** `timezonefinder` started in 2016 from `pytzwhere`, which then parsed a large text file and rebuilt its search structures at every start, at a cost of hundreds of megabytes of memory before the first answer. Making lookups cheap needed a new data format and lookup algorithm, which replaced the existing ones rather than amending them, so they were released as a new package. Contributions upstream went on in parallel: the first author's report of wrong results near nested polygons ([#34](https://github.com/pegler/pytzwhere/issues/34)) was fixed upstream, and the updated boundary data the first author proposed ([#36](https://github.com/pegler/pytzwhere/pull/36)) was not merged. The data of `pytzwhere` was never updated ([#42](https://github.com/pegler/pytzwhere/issues/42)), and it has had no commit since 2018. Its last release [needs an order of magnitude more memory](https://timezonefinder.readthedocs.io/en/latest/alternatives.html#comparison-to-pytzwhere) than `timezonefinder`, starts and answers more slowly, and answers for under a third of the globe. `tzfpy` appeared six years later with a deliberately different trade-off. Neither design can absorb the other without giving up the property it is built around, so the two packages coexist, and the maintainer of `tzfpy` has contributed to `timezonefinder`.

<!--
NOTE: the upstream-contribution sentence rests on the public pytzwhere tracker and history,
  checked 2026-11-19: #34 (opened 2016-04-13 by jannikmi; cstich reported a fix in the
  development branch on 2016-05-16; still open), PR #36 (opened 2016-04-27, closed unmerged by its
  author 2016-06-08, no review), #42 (2017-05-25; cstich: "We are still using the old data"),
  releases 2.3 (2016-03) to 3.0.3 (2017-08), last commit 2018-02. There was no other contact
  with the pytzwhere maintainers (confirmed by the maintainer, 2026-11-19), so the public record
  is complete.
-->

# Software design

<!--
TODO(authors): the repository links point to `master`; pin them to the release archived for
  the submission once it exists.
-->

The design of `timezonefinder` follows from one decision: the boundary polygons are never simplified. Every vertex and every hole is stored as timezone-boundary-builder publishes it, and most of the remaining design makes this full-resolution geometry affordable in time and memory. This section gives the trade-offs and the alternatives that were rejected; the [architecture documentation](https://timezonefinder.readthedocs.io/en/latest/architecture.html) describes the implementation.

**No simplification.** Simplification is the obvious way to make a geometric lookup smaller and faster, and it is proposed regularly. It is rejected because of where its error falls. A simplification algorithm such as Douglas–Peucker [@douglas1973] bounds how far the simplified line departs from the original. For a lookup, this bound is not a small error spread over all queries. It is a possibly wrong answer for every query within the tolerance of a border, and those are the only queries whose answer is in doubt at all. The size and speed that simplification would buy are instead bought with the lossless means described below. The price that remains is accepted: the distribution is about an order of magnitude larger than a simplified one, and a single lookup near a border is slower.

**Exact integer geometry.** Polygon vertices and query points are stored as 32-bit integers in units of 10^-7^ degrees, about 1.1 cm at the equator and ten times finer than the precision at which timezone-boundary-builder publishes its boundaries. This halves the storage compared with 64-bit floating point and makes the geometric test exact integer arithmetic, so an answer does not depend on floating-point rounding.

**A precomputed spatial index.** A grid aligned with longitude and latitude, refined only where zones meet, maps every point to the few polygons that can contain it. Most points, in the oceans and the interiors of countries, are answered from the index without touching any geometry, and the rest are tested against a handful of candidate polygons out of the dataset's thousands. Alignment with the meridians matters because the ocean zones share borders along every 7.5° meridian, and grids not aligned with them test markedly more polygons per lookup. A cell is found with integer arithmetic alone, which vectorises with NumPy [@numpy], so a batch lookup resolves most of its points in a few array operations.

**Memory mapping.** The polygon data is stored in the FlatBuffers format [@flatbuffers] and memory-mapped rather than read at start-up. Only the pages a lookup touches become resident, and the operating system can reclaim them under memory pressure, which keeps the package usable in memory-constrained containers and in many parallel worker processes. Users can instead read all data into memory, which is faster, or use a lighter variant that answers from the index alone where an approximate answer near borders is acceptable.

**Accelerators that never decide correctness.** The point-in-polygon test exists as a C extension, as a Numba [@numba] compilation and as plain Python, and the package binds one of them at import time. All three return identical answers: an accelerator makes the package fast but never makes it correct, so without a compiler and without Numba the package still installs and answers correctly, only more slowly. The test suite runs against each configuration.

**Overlapping zones.** The source data contains places that more than one zone claims. Returning a set from every lookup would complicate every lookup for a rare case, so ordinary lookups return one zone by a documented rule: the smaller zone, the one enclaved in the other, wins. A separate lookup returns every zone that contains the point. The rule depends only on the zones, not on the index or the order of the data, so it does not change when the index is rebuilt.

**A separately versioned data package.** The boundaries change several times a year with each timezone-boundary-builder release, while the code changes on its own schedule. Shipping both in one package would mean that pinning a dataset pins old code. The data therefore ships as its own distribution, `timezonefinder-data`, whose version names both the binary format generation and the upstream release. The code accepts any upstream release in the format generation it reads, so a data update needs no code release, and data the installed code cannot read is refused by the package installer rather than failing at the first lookup. A weekly workflow builds each new upstream release and publishes it once the test suite passes on it.

**Recorded decisions.** The design decisions, including the options that were measured and rejected, are recorded in the repository under [`contributing/improvements/decisions/`](https://github.com/jannikmi/timezonefinder/tree/master/contributing/improvements/decisions). Each record states the measurement and the reasoning that decided it, so that a rejected option is not proposed again without new evidence.

# Research impact statement

A literature search across full-text indexes, publisher sites and institutional repositories found 40 publications from 2018 onwards that name `timezonefinder` in their text: 20 journal articles, conference papers, books and reports, 5 preprints and 15 theses. For 39 of them, the passage naming the package was read in the full text. The search method and the evidence for each entry are recorded in the repository under [`paper/references/`](https://github.com/jannikmi/timezonefinder/tree/master/paper/references).

The publications span atmospheric emission modelling [@guevara2019hermes] and atmospheric chemistry [@bowdalo2024ghost; @patel2023lightning], fire-weather forecasting [@worsnop2021fire], ionospheric physics [@dinsmore2021griti; @chakraborty2026pynasonde], ocean remote sensing [@macchi2025milky], solar and building energy [@agyeiagyemang2026solar; @omoyele2026ethos; @john2021thermostat], public health [@romero2022runners], transport safety [@vellimana2023walking; @carey2027darkness], economics and management [@bahar2023innovation; @ramirez2023essays], scientometrics [@manchin2025collaboration], computational social science [@dellanegra2026reddit] and radio-spectrum measurement [@sanders2026cbrs]. Every described use maps coordinates to a zone, which then serves to convert timestamps between UTC and local time, to compute the position of the sun or the times of twilight in local time, or to take the time difference between places. Besides the studies named in the Statement of need, the zone enters the main variable of the analysis in deciding whether a fatal pedestrian crash took place at night [@carey2027darkness], in the time-zone difference between the co-authors of about 20 million articles [@manchin2025collaboration], and in the reference against which a method is evaluated [@dellanegra2026reddit].

Research software depends on `timezonefinder` too, so its users rely on the answers without calling the package themselves: among others the HERMESv3 emission model [@guevara2019hermes], the solar-irradiance downscaling package ETHOS.TISED [@omoyele2026ethos], the ionosonde library pynasonde [@chakraborty2026pynasonde] and the measurement tooling of a NIST technical note [@sanders2026cbrs]. GitHub's [dependency graph](https://github.com/jannikmi/timezonefinder/network/dependents) listed about 5,000 repositories and 260 published packages that depend on `timezonefinder` on 18 November 2026, among them projects of CERN, Sandia National Laboratories, the US National Laboratory of the Rockies (formerly NREL), the US EPA, NOAA and NASA JPL ([list](https://github.com/jannikmi/timezonefinder#used-by)).

<!--
TODO(authors): refresh the dependency-graph counts and the access date at submission (GitHub
  states that the counts are approximate).
OPEN QUESTION: the government and research projects are named by institution only, with the
  projects behind the README's "Used by" list, to save words. A reviewer may ask for each
  project to be cited. If so, add a paper.bib entry per project (title, owning institution as
  author, repository URL, year of the version checked) and cite it after the institution:
  CERN's CAiMIRA (gitlab.cern.ch/caimira/caimira), Sandia National Laboratories' pvOps
  (github.com/sandialabs/pvOps), the National Laboratory of the Rockies' HOPP
  (github.com/NatLabRockies/HOPP), the US EPA's sensortoolkit (github.com/USEPA/sensortoolkit),
  NOAA's monetio (github.com/noaa-oar-arl/monetio) and NASA JPL OPERA's next_pass
  (github.com/OPERA-Cal-Val/next_pass). The README link points to master; pin it with the other
  repository links at submission.
-->

These figures are a lower bound. Only three of the publications list the package in their references, so citation databases miss nearly all of them, and theses and paywalled full texts are only partly indexed. The project provides a Zenodo DOI [@tzf_zenodo] and a citation file, and this paper adds a peer-reviewed reference.

# AI usage disclosure

Generative AI has been used in the development of `timezonefinder` since September 2025. All earlier development, including the original design of the package, its data format and a first spatial index, was done without it. The current, optimised implementation of the spatial index was developed with AI assistance. The tools used were Anthropic's Claude Code with the models Claude Opus 5, Claude Opus 5.5, Claude Sonnet 5 and Claude Sonnet 5.5, OpenAI Codex with GPT-5.6 Terra, and GitHub Copilot, whose underlying models changed over the period of use and were not recorded. The assistance covered code generation and refactoring, tests, benchmark and report scripts, continuous-integration configuration, documentation, the contributor guide, pull-request review and the survey of publications that reference the package. The co-authors also used AI assistants, including Claude Code, for their contributions. This paper was drafted and revised with Claude Code, using Claude Opus 5.5 and Claude Sonnet 5.5, and edited by the authors; no other AI tool was used for it.

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
