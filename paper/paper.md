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

# Summary

Each place belongs to a time zone, whose rules, its offset from Coordinated Universal Time (UTC) and its daylight saving time, are recorded in the IANA Time Zone Database [@iana_tzdb] under names such as `Europe/Berlin`. To convert a timestamp to local time, one first has to know which time zone contains the place.

`timezonefinder` is a Python package that answers this question without an internet connection. Given a latitude and a longitude, it returns the name of the time zone that contains the point, using the boundaries of the timezone-boundary-builder project [@tzbb], derived from OpenStreetMap [@osm; @haklay2008osm], without simplifying them. Since its first release in April 2016 it has had 86 releases across nine major versions, at least two in every year.

# Statement of need

Research data often records *when* and *where* something happened as a UTC timestamp and a pair of coordinates, but many research questions depend on local time: the hour at which an exposure occurred, the local date, whether an event happened after dark. Once the IANA time zone of a coordinate is known, standard libraries such as Python's `zoneinfo` [@pep615] apply its rules, including daylight saving time and historical changes. Finding the zone is the step those libraries leave open.

`timezonefinder` closes this gap for researchers who need local time at recorded coordinates, and for the developers of research software that offers this to its own users. This use sets four requirements, and the package is designed around them.

**Accuracy at zone borders.** In several published studies, the zone feeds directly into the main variable: the hour at which a forecast input is taken [@worsnop2021fire], whether a walk counts as a night walk [@vellimana2023walking], the time difference between two places [@bahar2023innovation]. A tool that simplifies the zone polygons makes its errors along borders and coastlines, which biases exactly the analyses that compare regions across a border. `timezonefinder` uses the polygons without simplification, so its accuracy is limited only by the source data. The guarantee is fidelity to that data, not ground truth: where OpenStreetMap places a border wrongly, `timezonefinder` answers wrongly in the same way.

**Offline and reproducible lookups.** Compute nodes of research clusters often have no internet access, and a web service can fail, impose quotas or change its answers without notice; one study chose `timezonefinder` over a web API for this reason [@perezparedes2023athletics]. A lookup in `timezonefinder` is a pure function of the coordinates and the installed boundary data, which ships as a separately versioned package and reports the timezone-boundary-builder release it comes from. A study that pins and reports both versions can repeat its lookups exactly.

**Coverage of the whole globe.** Buoys, ships, aircraft and remote stations need an answer too. The boundary data includes the nautical zones over the oceans, so every coordinate receives a zone, and researchers who need to tell land from sea can ask for land zones only.

**Whole datasets at once.** Research datasets often contain millions of points. One call returns the zones of whole arrays of coordinates, which fits the column-oriented workflows of NumPy [@numpy] and pandas [@pandas].

# State of the field

Researchers who need the time zone at a coordinate take one of four routes.

**Approximations**, one hour per 15 degrees of longitude or one zone per country, fail where zone borders leave the meridians and in countries that span several zones.

**Online services** such as the Google Maps Time Zone API [@google_tz_api], TimeZoneDB [@timezonedb] or GeoNames [@geonames] need network access, accounts and quotas, and they neither state nor fix the boundary data behind an answer, so a result cannot be repeated later.

**General-purpose GIS tools** such as GeoPandas [@geopandas] or the spatial database PostGIS [@postgis] can join points against the published boundaries [@tzbb] exactly. They leave the researcher to obtain the data and record its version, to load and index hundreds of megabytes of geometry, and to decide what happens where zones overlap, where a spatial join returns every match or an arbitrary one. `timezonefinder` packages these steps.

**Dedicated lookup libraries** answer the question from the timezone-boundary-builder data: 26 libraries in 15 programming languages [@tzbb_libs]. In Python, `pytzwhere` [@pytzwhere] reads the outdated `tz_world` dataset [@tz_world], which has no ocean zones, and has had no release since 2017. `tzfpy` [@tzfpy], a binding of the Rust crate `tzf-rs` [@tzfrs] first released in 2022, is today the main alternative to `timezonefinder`.

**Comparison with `tzfpy`.** The two packages read the same timezone-boundary-builder releases but make opposite trade-offs. The build of `tzfpy` on PyPI ships simplified polygons, so its wheels are about a tenth of the size (about 3 MB, against about 33 MB for `timezonefinder` with its data) and a single lookup is faster by a small single-digit factor. Measured on the same boundary release (`tzfpy` 2.1.2, timezone-boundary-builder 2026f), uniformly random points, which lie far from any border, never receive different answers. Near borders, they often disagree, and the disagreement vanishes at about 100 m (\autoref{fig:agreement}), in line with the maximum displacement of about 111 m that the maintainer of `tzfpy` states for the simplification [@tzfpy]. An analysis of points far from borders can use either package; an analysis whose points cluster near borders, such as a comparison of neighbouring regions or a lookup for every cell of a grid, gets different answers from the simplified polygons. An experimental `tzfpy` variant with unsimplified polygons, distributed outside PyPI, was not measured. The documentation gives the [border-accuracy](https://timezonefinder.readthedocs.io/en/latest/border_accuracy_vs_tzfpy.html) and [speed](https://timezonefinder.readthedocs.io/en/latest/benchmark_results_vs_tzfpy.html) reports and [the use cases](https://timezonefinder.readthedocs.io/en/latest/alternatives.html) for which `tzfpy` is the better choice.

![Share of sampled border locations at which `tzfpy` and `timezonefinder` answer differently on at least one side of the border, by distance from it; 20,000 locations per distance.\label{fig:agreement}](tzfpy_agreement_by_distance.pdf)

**Why a separate package.** `timezonefinder` started in 2016 from `pytzwhere`, which then rebuilt its search structures from a large text file at every start, at a cost of hundreds of megabytes of memory before the first answer. Fixing this needed a new data format and lookup algorithm, which replaced the existing ones rather than amending them, so they became a new package. Upstream, the first author's bug report was fixed ([#34](https://github.com/pegler/pytzwhere/issues/34)), but the proposed data update was not merged ([#36](https://github.com/pegler/pytzwhere/pull/36)) and the data of `pytzwhere` was never updated ([#42](https://github.com/pegler/pytzwhere/issues/42)). `tzfpy` appeared six years later with a deliberately different trade-off. Neither design can absorb the other without giving up the property it is built around, so the two packages coexist, and the maintainer of `tzfpy` has contributed to `timezonefinder`.

# Software design

The design follows from the four requirements, above all from never simplifying the polygons; most of it makes full-resolution geometry affordable in time and memory. The trade-offs and rejected alternatives are recorded with their measurements in [`contributing/improvements/decisions/`](https://github.com/jannikmi/timezonefinder/tree/master/contributing/improvements/decisions), and the [architecture documentation](https://timezonefinder.readthedocs.io/en/latest/architecture.html) describes the implementation.

**No simplification.** The bound that an algorithm such as Douglas–Peucker [@douglas1973] guarantees is not a small error spread over all queries but a possibly wrong answer for every query within the tolerance of a border, the only queries in doubt at all. The size and speed simplification would buy are bought losslessly instead, as described below. The remaining price is accepted: a distribution about an order of magnitude larger, and slower single lookups near borders.

**Exact integer geometry.** Polygon vertices and query points are stored as 32-bit integers in units of 10^-7^ degrees, about 1.1 cm at the equator and ten times finer than the precision at which timezone-boundary-builder publishes its boundaries. This halves the storage compared with 64-bit floating point and makes the geometric test exact integer arithmetic, so an answer does not depend on floating-point rounding.

**A precomputed spatial index.** A grid aligned with longitude and latitude, refined only where zones meet, maps every point to the few polygons that can contain it. Most points, in the oceans and the interiors of countries, are answered from the index without touching any geometry, and the rest are tested against a handful of candidate polygons out of the dataset's thousands. Alignment with the meridians matters because the ocean zones share borders along every 7.5° meridian, and grids not aligned with them test markedly more polygons per lookup. A cell is found with integer arithmetic alone, which vectorises over the arrays of a batch lookup.

**Memory mapping.** The polygon data is stored in the FlatBuffers format [@flatbuffers] and memory-mapped rather than read at start-up. Only the pages a lookup touches become resident, and the operating system can reclaim them under memory pressure, which keeps the package usable in memory-constrained containers and in many parallel worker processes. Users can instead read all data into memory, which is faster, or use a lighter variant that answers from the index alone where an approximate answer near borders is acceptable.

**Accelerators that never decide correctness.** The point-in-polygon test exists as a C extension, as a Numba [@numba] compilation and as plain Python, and the package binds one of them at import time. All three return identical answers: an accelerator makes the package fast but never makes it correct, so without a compiler and without Numba the package still installs and answers correctly, only more slowly. The test suite runs against each configuration.

**Overlapping zones.** Some places are claimed by more than one zone. Rather than burden every lookup with a set for this rare case, ordinary lookups return the smaller, enclaved zone, a rule that depends only on the zones and so survives a rebuilt index; a separate lookup returns every zone.

**A separately versioned data package.** The boundaries change several times a year, the code on its own schedule, so the data ships separately. Its version names the binary format generation and the upstream release; the code accepts any upstream release in the format generation it reads, so a data update needs no code release, and the package installer refuses data the installed code cannot read. A weekly workflow publishes each new upstream release once the test suite passes on it.

# Research impact statement

A literature search across full-text indexes, publisher sites and institutional repositories found 40 publications from 2018 onwards that name `timezonefinder` in their text: 20 journal articles, conference papers, books and reports, 5 preprints and 15 theses. For 39 of them, the passage naming the package was read in the full text. The search method and the evidence for each entry are recorded in the repository under [`paper/references/`](https://github.com/jannikmi/timezonefinder/tree/master/paper/references).

The publications span atmospheric emission modelling [@guevara2019hermes] and atmospheric chemistry [@bowdalo2024ghost; @patel2023lightning], fire-weather forecasting [@worsnop2021fire], ionospheric physics [@dinsmore2021griti; @chakraborty2026pynasonde], ocean remote sensing [@macchi2025milky], solar and building energy [@agyeiagyemang2026solar; @omoyele2026ethos; @john2021thermostat], public health [@romero2022runners], transport safety [@vellimana2023walking; @carey2027darkness], economics and management [@bahar2023innovation; @ramirez2023essays], scientometrics [@manchin2025collaboration], computational social science [@dellanegra2026reddit] and radio-spectrum measurement [@sanders2026cbrs]. Every described use maps coordinates to a zone, which then serves to convert timestamps between UTC and local time, to compute the position of the sun or the times of twilight in local time, or to take the time difference between places.

Research software depends on `timezonefinder` too, so its users rely on the answers without calling the package themselves: among others the HERMESv3 emission model [@guevara2019hermes], the solar-irradiance downscaling package ETHOS.TISED [@omoyele2026ethos], the ionosonde library pynasonde [@chakraborty2026pynasonde] and the measurement tooling of a NIST technical note [@sanders2026cbrs]. GitHub's [dependency graph](https://github.com/jannikmi/timezonefinder/network/dependents) listed about 5,000 repositories and 260 published packages that depend on `timezonefinder` on 18 November 2026, among them projects of CERN, Sandia National Laboratories, the US National Laboratory of the Rockies (formerly NREL), the US EPA, NOAA and NASA JPL ([list](https://github.com/jannikmi/timezonefinder#used-by)).

These figures are a lower bound. Only three of the publications list the package in their references, so citation databases miss nearly all of them, and theses and paywalled full texts are only partly indexed. The project provides a Zenodo DOI [@tzf_zenodo] and a citation file, and this paper adds a peer-reviewed reference.

# AI usage disclosure

Generative AI was used for the code, tests, documentation and paper text. The tools were Anthropic's Claude Code with Claude Opus 5, Claude Opus 5.5, Claude Sonnet 5 and Claude Sonnet 5.5; OpenAI Codex with GPT-5.6 Terra; and GitHub Copilot. The co-authors also used AI assistants, including Claude Code. The models behind GitHub Copilot and the co-authors' assistants were not recorded. The assistance covered code generation and refactoring, tests, benchmark scripts, documentation, pull-request review, the literature survey, and drafting and revising this paper, which used only Claude Code with Claude Opus 5.5 and Claude Sonnet 5.5. The human authors reviewed, edited and validated all AI-assisted output and made the core design decisions.

# Acknowledgements

We thank [Evan Siroky](https://github.com/evansiroky) and the contributors of timezone-boundary-builder [@tzbb] and OpenStreetMap [@osm; @haklay2008osm], whose boundary data `timezonefinder` is built on, and everyone [listed in the documentation](https://timezonefinder.readthedocs.io/en/latest/5_contributing.html) who contributed to `timezonefinder`.

The development of `timezonefinder` is supported by the first author's sponsors through GitHub Sponsors. Han Xiao, the author of `tzfpy`, which this paper compares against, has sponsored the project in the past, without influence on the software or on this paper beyond that of any other contributor. The authors declare no other competing interests.

# References
