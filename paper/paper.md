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
    affiliation: 3
affiliations:
  - name: Independent Researcher
    index: 1
  - name: Affiliation to be confirmed
    index: 2
  - name: Affiliation to be confirmed
    index: 3
date: 17 November 2026
bibliography: paper.bib
---

<!--
JOSS review notes (see paper/joss-review.md for the full assessment against the review criteria).
These comments do not appear in the compiled PDF.

TODO(authors): fill in the affiliations of Evgenii Seliverstov and Lucas Hemkemeier, and add
  ORCIDs if they have them. JOSS requires an affiliation for every author.
TODO(authors): ORCID of the co-authors (optional, but JOSS asks for it where one exists).
TODO(authors): set `date` to the submission date.
OPEN QUESTION (authorship): reviewers are asked whether the author list is "appropriate and
  complete". The co-authors' contributions (build and release pipeline; automated data updates)
  are credited in docs/5_contributing.rst but nowhere in the paper. Consider one sentence in the
  Acknowledgements or Software design naming each co-author's part, so a reviewer can check it
  against the commit history without digging. Each co-author must also agree to be listed.
TODO(authors): the paper was ~4,360 words before this review. JOSS asks for 750-1750 words and
  may ask longer papers to be cut. This revision condenses it to roughly 2,700 words (body text, comments excluded) by moving
  documentation-level detail (API names, index parameters, CI and wheel matrix, test strategy)
  out and linking to the documentation pages that already hold it. Decide whether to cut further
  (candidates: the Acknowledgements name list, the second State-of-the-field paragraph).
-->

# Summary

The time shown on a clock depends on where it hangs. Each place belongs to a time zone, and the rules of that zone, its offset from Coordinated Universal Time (UTC) and when daylight saving time begins and ends, are recorded in the IANA Time Zone Database [@iana_tzdb] under names such as `Europe/Berlin`. Instruments, GPS receivers and computer models usually record when and where something happened as a UTC timestamp and a pair of coordinates. To recover the local time, such as the hour of day, the local date or whether it was dark, one first has to know which time zone contains each coordinate.

`timezonefinder` is a Python package that answers this question without an internet connection. Given a latitude and a longitude, it returns the name of the time zone that contains the point. It reads the zone boundaries published by the timezone-boundary-builder project [@tzbb], which derives them from OpenStreetMap [@osm; @haklay2008osm], and it uses these boundaries exactly as published, without simplifying their shape. Because the data also covers the oceans, practically every coordinate on Earth receives an answer. The boundary data ships as a separately versioned package, so a lookup needs no online service, and pinning the data version makes its answers repeatable. One call can look up an entire array of coordinates, which suits whole datasets. The package has been developed in the open since 2016.

# Statement of need

Research data often records *when* and *where* something happened as a UTC timestamp and a pair of coordinates: measurements at monitoring stations, GPS tracks from wearables and phones, geotagged social-media posts, the points of a model grid. Many research questions, however, depend on local time: the hour of the day at which an exposure occurred, the local date, whether an event happened after dark, or how many working hours two places share. Once the IANA zone of a coordinate is known, standard libraries such as Python's `zoneinfo` [@pep615] apply its rules, including historical changes and daylight saving time. Finding the zone is the step those libraries leave open. It cannot be approximated from the longitude alone, because zone borders follow political boundaries rather than meridians: China spans about 60 degrees of longitude but uses a single zone.

`timezonefinder` closes this gap. Its target audience is researchers who need local time at recorded coordinates, and the developers of research software that offers this to its own users, such as emission models and instrument-processing libraries (see the Research impact statement). These uses set four requirements, and the package is designed around them.

**Accuracy at zone borders.** In several published studies, the zone feeds directly into the main variable of the analysis, such as the hour at which a forecast input is taken or whether a walk counts as a night walk [@worsnop2021fire; @vellimana2023walking]. A tool that simplifies the zone polygons makes its errors along borders and coastlines, which biases exactly the analyses that compare regions across a border. `timezonefinder` uses the polygons without simplification, so its accuracy is limited only by the source data. The guarantee is fidelity to that data, not ground truth: where OpenStreetMap places a border wrongly, `timezonefinder` answers wrongly in the same way, and such errors are corrected upstream.

**Offline and reproducible lookups.** Web services answer the same question, but they need network access and an account, impose quotas, and can change their answers without notice; compute nodes of research clusters often have no internet access at all. One study chose `timezonefinder` over a web API for exactly this reason [@perezparedes2023athletics]. A lookup in `timezonefinder` is a pure function of the coordinates and the installed boundary data, and the data package names the timezone-boundary-builder release it was built from, so a study can pin, report and repeat its lookups.

**Coverage of the whole globe.** Buoys, ships, aircraft and remote stations need an answer too. The boundary data includes the nautical zones over the oceans, so every coordinate receives a zone; land zones alone can be requested.

**Whole datasets at once.** Research datasets often contain millions of points. The package looks up arrays of coordinates in one call, which fits the column-oriented workflows of NumPy [@numpy] and pandas [@pandas].

# State of the field

Researchers who need the time zone at a coordinate take one of four routes.

**Approximations.** Deriving the offset from the longitude, one hour per 15 degrees, or taking one zone per country both fail where it matters: borders do not follow meridians, and countries such as the United States, Russia, Brazil and Australia span several zones. An offset from the longitude also carries no daylight saving time or history.

**Online services.** Web APIs such as the Google Maps Time Zone API [@google_tz_api], TimeZoneDB [@timezonedb] or GeoNames [@geonames] return a zone name for a coordinate. They need network access, accounts and quotas, and the boundary data behind an answer is neither stated nor fixed, so a result cannot be repeated later.

**General-purpose GIS tools.** The timezone-boundary-builder boundaries can be loaded into GeoPandas [@geopandas] or PostGIS [@postgis] for a spatial join. This gives exact answers, but it leaves the researcher to obtain and version the data, to load and index hundreds of megabytes of geometry, and to decide what happens where the dataset's polygons genuinely overlap, where a spatial join returns every match or an arbitrary one. `timezonefinder` packages these steps: the data arrives as a versioned dependency, the index is precomputed, the geometry is memory-mapped, and an overlap is resolved by a documented rule.

**Dedicated lookup libraries.** The timezone-boundary-builder project lists more than twenty libraries in over a dozen languages that answer this question from its data. In Python, `pytzwhere` [@pytzwhere] reads the outdated `tz_world` dataset [@tz_world], which has no ocean zones, and has had no release since 2017. `tzfpy` [@tzfpy], first released in 2022 as a binding of the Rust crate `tzf-rs` [@tzfrs], is today the main alternative.

<!--
TODO(authors): "more than twenty libraries in over a dozen languages" needs a citation or URL
  (the "Lookup Libraries" list in the timezone-boundary-builder README), with an access date.
-->

`tzfpy` and `timezonefinder` read the same boundary releases but make opposite trade-offs. The PyPI build of `tzfpy` ships simplified polygons, so its wheels are an order of magnitude smaller and a single lookup is faster by a small factor. The price is accuracy near borders. We measured both packages on the same boundary release: over points drawn uniformly from the globe they never disagree, but one centimetre from a land-zone border they answer differently on at least one side of about nine in ten sampled border locations, two thirds at one metre and almost half at ten metres, with no disagreement observed beyond a hundred metres. For analyses whose points cluster near borders, such as studies of neighbouring regions or every cell of a regular grid, the simplified polygons change answers. `timezonefinder` also ships its data as a separately versioned package, looks up whole arrays in one call (about twice as fast per point as a loop of `tzfpy` calls on the benchmark points), and runs without a compiler, falling back to pure Python with identical answers. The measurements come from harnesses in the repository that run both packages on the same points in the same process; their reports are part of the documentation, which also lists the use cases for which `tzfpy` is the better choice.

<!--
TODO(authors): pin the numbers above to a version and a citable source. Suggested: name the
  tzfpy and boundary-release versions and the date (currently tzfpy 1.3.3, release 2026c,
  2026-08-30, per docs/border_accuracy_vs_tzfpy.rst; tzfpy is at 2.1.x on PyPI now, so consider
  re-running `make tzfpy-agreement` before submission), and link the documentation pages
  border_accuracy_vs_tzfpy and benchmark_results_vs_tzfpy by URL so a reader of the PDF can
  reproduce them.
TODO(authors): replace "an order of magnitude smaller" and "faster by a small factor" with the
  measured figures (wheel sizes; single-lookup ratio from benchmark_results_vs_tzfpy).
OPEN QUESTION: the earlier draft said "the maximum displacement the maintainer of tzfpy states
  for the simplification" (about 100 m). If kept, it needs a citation to that statement.
OPEN QUESTION: the earlier draft mentioned an experimental unsimplified tzfpy variant outside
  PyPI that was not measured. A reviewer may ask for a comparison against it; consider measuring
  it or keeping the sentence that says it was not measured.
-->

**Why a separate package.** `timezonefinder` started in 2016 from `pytzwhere`, which then parsed a large text file into memory and rebuilt its search structures at every start, costing hundreds of megabytes before the first answer. Making lookups cheap needed a different data layer and lookup algorithm, replacing both rather than amending them, so the work was released as a new package. `tzfpy` appeared six years later with a Rust core and a deliberately different trade-off. Neither design can absorb the other without giving up the property it is built around, so the two packages coexist, and the maintainer of `tzfpy` has contributed to `timezonefinder`.

<!--
TODO(authors): the earlier draft claimed "an order of magnitude less memory and faster start-up
  and single lookups" than the last pytzwhere release. Restore it only with a link to the
  measurement; otherwise it reads as an unsupported claim.
OPEN QUESTION: was contributing upstream to pytzwhere attempted or discussed in 2016 (issue,
  PR, contact with its maintainer)? JOSS asks for an explicit "build vs. contribute"
  justification; one sentence of evidence would strengthen it.
-->

# Software design

The design follows from one decision: the boundary polygons are never simplified. Most of the remaining design exists to make full-resolution geometry affordable in time and memory. The reasoning is documented in more detail in the package documentation, including the options that were measured and rejected.

**No simplification.** A simplification algorithm such as Douglas–Peucker [@douglas1973] bounds how far the simplified line strays from the original. For a lookup this bound is not a small error spread over all queries: it is a possibly wrong answer for every query within the tolerance of a border, and those are the only queries whose answer is in doubt at all. The benefits simplification would buy, a smaller distribution and fewer edge tests, are bought instead by the lossless means below. The price that remains is accepted: a distribution about an order of magnitude larger than a simplified one, and slower single lookups near borders.

**Exact integer geometry.** Coordinates are stored as 32-bit integers on a grid of about 1.1 cm, ten times finer than the precision at which timezone-boundary-builder publishes its boundaries. This halves storage compared with 64-bit floats and makes the point-in-polygon test exact integer arithmetic, so an answer never depends on floating-point rounding.

**A precomputed spatial index.** The globe is divided into a grid of cells aligned with longitude and latitude. For each cell, a table built with the data stores which zones it touches. Most cells lie inside a single zone, and the table answers them without touching any geometry. Cells where zones meet are refined, and only where a refined cell is still shared does the lookup test a handful of candidate polygons. The alignment with meridians matters, because the ocean zones share borders along every 7.5° meridian, and the cell of a point is found with integer arithmetic alone, which vectorises over a batch of points.

**Memory mapping and optional accelerators.** The polygon data is stored in binary FlatBuffers [@flatbuffers] files that are memory-mapped rather than read at start-up, so only the pages a lookup touches become resident. This keeps the package usable in memory-constrained containers and in many parallel worker processes; reading all data into memory is an option. The inner point-in-polygon loop exists as a C extension, as a Numba [@numba] compilation, and as pure Python. They return identical answers and differ only in speed: an accelerator makes the package fast but never makes it correct, and the test suite runs against each configuration.

**Overlapping zones.** The source data contains places that two zones claim. Returning a set from every lookup would complicate the interface for a rare case, so single-answer lookups apply a documented rule that depends only on the zones: the smaller zone, the one enclaved in the other, wins. A separate lookup returns every zone at the point.

**A separately versioned data package.** Boundaries and code change at different speeds: the boundaries several times a year, the code on its own schedule. The data therefore ships as its own distribution, `timezonefinder-data`, whose version encodes both the binary format generation and the upstream release. The code accepts any upstream release of a compatible format, so an ordinary data update needs no code release, while an incompatible format is refused by the package installer rather than failing at the first lookup. A weekly workflow detects new upstream releases, regenerates the data and publishes it once continuous integration passes.

<!--
TODO(authors): add a link (URL) to the documentation pages that now carry the detail removed
  here: architecture, why_no_simplification, data_format, result_stability, and the decision
  records under contributing/improvements/decisions/. Relative repository paths do not resolve
  in the PDF.
OPEN QUESTION: the earlier draft described the CI wheel matrix (glibc/musl, stable ABI,
  free-threaded build) and the test strategy (Hypothesis property tests, packaging tests). This
  is good open-source practice evidence but is documentation-level detail for the paper; it is
  now left to the README/docs. Restore a single sentence if a reviewer asks about QA.
-->

# Research impact statement

`timezonefinder` is used in published research. A literature search across full-text indexes, publisher sites and institutional repositories found 40 publications from 2018 onwards that name the package in their text: 20 journal articles, conference papers, books and reports, 5 preprints and 15 theses. For 31 of them, the passage naming the package was read in the full text. The search method, the passages and the evidence for each entry are recorded in the repository.

<!--
TODO(authors): give the URL of paper/references/ (and pin it to a commit or the archived
  release) so the record is reachable from the PDF.
-->

The publications span a wide range of fields. They include atmospheric emission modelling [@guevara2019hermes] and atmospheric chemistry [@bowdalo2024ghost; @patel2023lightning], fire-weather forecasting [@worsnop2021fire], ionospheric physics [@dinsmore2021griti; @chakraborty2026pynasonde], ocean remote sensing [@macchi2025milky], solar and building energy [@agyeiagyemang2026solar; @john2021thermostat], public health [@romero2022runners], transport safety [@vellimana2023walking], economics and management [@bahar2023innovation; @ramirez2023essays], computational social science [@dellanegra2026reddit] and radio-spectrum measurement [@sanders2026cbrs]. Every described use maps coordinates to a zone name. The zone then serves to convert timestamps between UTC and local time, to compute the position of the sun or the times of twilight in local time, or to take the time difference between places. In several studies, the result enters the main variable of the analysis directly: the UTC hour at which every fire-danger input is taken [@worsnop2021fire], whether a walk took place at night [@vellimana2023walking], the working-hour overlap between two airports [@bahar2023innovation], or the reference against which a method is evaluated [@dellanegra2026reddit].

`timezonefinder` also reaches researchers indirectly, through research software that depends on it. Examples include the HERMESv3 emission model [@guevara2019hermes], the ionosonde library pynasonde [@chakraborty2026pynasonde] and the measurement tooling of a NIST technical note [@sanders2026cbrs]. GitHub's dependency graph lists thousands of repositories and hundreds of published packages that depend on `timezonefinder`. Among them are research and government projects such as CERN's CAiMIRA, the ETHOS.TISED model of Forschungszentrum Jülich, Sandia National Laboratories' pvOps, the HOPP model of the US National Laboratory of the Rockies (formerly NREL), the US EPA's sensortoolkit, NOAA's monetio and the next_pass tool of NASA JPL's OPERA project.

<!--
TODO(authors): "thousands of repositories and hundreds of packages" is vague; JOSS asks for
  evidence that is "compelling and specific". State the exact counts from the dependency graph
  with the access date (and optionally the monthly PyPI download count from a named source).
TODO(authors): each named project (CAiMIRA, ETHOS.TISED, pvOps, HOPP, sensortoolkit, monetio,
  next_pass) should have a reference or URL. ETHOS.TISED has a SoftwareX paper already recorded
  as omoyele2026ethos, but only at "search snippet" grade; cite it once the full text is checked.
TODO(authors): verify the "National Laboratory of the Rockies (formerly NREL)" naming against
  the lab's current official name at submission time.
-->

These figures are a lower bound. Most publications name the package only in the text, a footnote, a dependency list or a code listing, and only three include it in their reference list, so citation databases miss nearly all of them. To make citing easier, the project provides a Zenodo DOI [@tzf_zenodo] and a citation file, and this paper adds a peer-reviewed reference.

# AI usage disclosure

Generative AI has been used in the development of `timezonefinder` since September 2025. All earlier development, including the original design of the package, its data format and a first spatial index, was done without it. The current, optimised implementation of the spatial index was developed with AI assistance. The tools used were Anthropic's Claude Code with the models Claude Opus 5, Claude Opus 5.5 and Claude Sonnet 5, OpenAI Codex with GPT-5.6 Terra, and GitHub Copilot, whose underlying models changed over the period of use and were not recorded. The assistance covered code generation and refactoring, tests, benchmark and report scripts, continuous-integration configuration, documentation, the contributor guide, pull-request review and the survey of publications that reference the package. The co-authors also used AI assistants, including Claude Code, for their contributions. This paper was drafted with Claude Code and Claude Opus 5.5, condensed during an internal review against the JOSS criteria with the same tool, and edited by the authors; no other AI tool was used for it.

The problem framing, the architecture and every design decision were made by the human authors, who reviewed, edited and validated all AI-assisted output before it was merged. Every change is checked by the continuous-integration test suite, and the design decisions, with the measurements and reasoning behind them, are recorded in the repository's contributor guide. Commits made with AI assistance carry co-author trailers in the version history. These trailers are a lower bound on AI use, since not every tool or merge records one. A detailed account compiled from the history is kept in the repository.

<!--
TODO(authors): each author confirms the second paragraph for their own part (open point in
  paper/ai-usage-disclosure.md; this cannot be drafted on their behalf).
TODO(authors): link paper/ai-usage-disclosure.md by URL.
-->

# Acknowledgements

We thank [Evan Siroky](https://github.com/evansiroky) and the contributors of timezone-boundary-builder [@tzbb], and the OpenStreetMap contributors [@osm; @haklay2008osm], whose boundary data `timezonefinder` is built on. We thank everyone who contributed code, reviews, issues and feedback to `timezonefinder`, in particular [Adam Johnson](https://github.com/adamchainz), [Han Xiao](https://github.com/ringsaturn), [Aryan Raj](https://github.com/a-ryanraj), [Pratyush Kumar](https://github.com/pratyushkumar211), [Lu Yicheng](https://github.com/01luyicheng), [Marco Barbosa](https://github.com/aureliobarbosa), [sefiotonomo](https://github.com/sefiotonomo), [joshuadavidthomas](https://github.com/joshuadavidthomas), [badhope](https://github.com/badhope), [Nice6042](https://github.com/Nice6042), [MsfPablo](https://github.com/MsfPablo), [Pxli9130](https://github.com/Pxli9130), [Kristian Sloth Lauszus](https://github.com/Lauszus), [Chase Horton](https://github.com/Chase-Horton), [Dave Tapley](https://github.com/davetapley), [David Park](https://github.com/daphtdazz), [WestonReed](https://github.com/WestonReed), [Tyler Huntley](https://github.com/Ty1776), [Greg Meyer](https://github.com/gmmeyer), [Romain Girard](https://github.com/romaingd-spi), [synapticarbors](https://github.com/synapticarbors) and [zedrdave](https://github.com/zedrdave), as well as [snowman2](https://github.com/snowman2) and [Xylar Asay-Davis](https://github.com/xylar) for creating and maintaining the conda-forge packages. A complete list is kept in the [documentation](https://timezonefinder.readthedocs.io/en/latest/5_contributing.html).

The development of `timezonefinder` is supported by the sponsors of the first author through GitHub Sponsors. Han Xiao (ringsaturn), the author of `tzfpy`, which this paper compares against, has sponsored the project in the past. The sponsorship gave no influence on the software or on this paper beyond that of any other contributor.

<!--
TODO(authors): JOSS requires every author to disclose potential conflicts of interest. Add an
  explicit sentence such as "The authors declare no other competing interests." once each
  author has confirmed it.
OPEN QUESTION: the co-authors are not named among the contributors here. If the author list is
  kept, consider stating each co-author's contribution in one sentence (see the note at the top).
-->

# References
