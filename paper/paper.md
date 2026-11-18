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

# Summary

The time shown on a clock depends on where it hangs. Each place belongs to a time zone, and the rules of that zone, its offset from Coordinated Universal Time (UTC) and when daylight saving time begins and ends, are recorded in the IANA Time Zone Database [@iana_tzdb] under names such as `Europe/Berlin`. Instruments, GPS receivers and computer models usually record when and where something happened as a UTC timestamp and a pair of coordinates. To recover the local time, such as the hour of day, the local date or whether it was dark, one first has to know which time zone contains each coordinate.

`timezonefinder` is a Python package that answers this question without an internet connection. Given a latitude and a longitude, it returns the name of the time zone that contains the point. It reads the zone boundaries published by the timezone-boundary-builder project [@tzbb], which derives them from OpenStreetMap [@osm], and it uses these boundaries exactly as published, without simplifying their shape. Because the data also covers the oceans, practically every coordinate on Earth receives an answer. The boundary data ships as a separately versioned package, so a lookup needs no online service, and pinning the data version makes its answers repeatable. One call can look up an entire array of coordinates, which suits whole datasets. The package has been developed in the open since 2016.

# Statement of need

Research data often records *when* and *where* something happened as a UTC timestamp and a pair of coordinates: measurements at monitoring stations, GPS tracks from wearables and phones, geotagged social-media posts, the points of a model grid. Many research questions, however, depend on local time rather than on UTC: the hour of the day at which an exposure occurred, the date in the local calendar, whether an event happened after dark, whether daylight saving time applied, or how many working hours two places share. Recovering local time needs the IANA time zone at each coordinate. Once the zone is known, standard libraries such as Python's `zoneinfo` apply its rules, including historical changes and daylight saving time. Finding the zone is the step those libraries leave open. It cannot be approximated from the longitude alone, because zone borders follow political boundaries rather than meridians: China spans about 60 degrees of longitude but uses a single zone, and much of western Europe keeps a zone an hour ahead of its solar time.

`timezonefinder` closes this gap. Its target audience is researchers who need local time at recorded coordinates, and the developers of research software that offers this to its own users. Published work uses it in fields as different as atmospheric chemistry, fire-weather forecasting, ionospheric physics, public health, transport safety and the economics of innovation. A harmonised global dataset of surface atmospheric composition measurements uses it to assign a zone to each monitoring station, so that measurements reported in local time can be shifted to UTC [@bowdalo2024ghost]. A week-two fire-danger forecast uses it to find the UTC hour of local noon at every point of its forecast grid, the time at which the fire-danger inputs are taken [@worsnop2021fire]. A study of walking exposure uses it to decide whether a trip started before sunrise or after sunset [@vellimana2023walking], and a study of firm innovation uses it to measure the working-hour overlap between airports linked by nonstop flights [@bahar2023innovation]. Research software ships it as a dependency, among them the HERMESv3 emission model [@guevara2019hermes] and the ionosonde processing library pynasonde [@chakraborty2026pynasonde], so the users of these tools rely on its answers without calling it themselves. The Research impact statement below lists the use in more detail.

These uses set four requirements, and the package is designed around them.

**Accuracy at zone borders.** In several of the studies above, the zone feeds directly into the main variable: the hour at which a forecast input is taken, whether a walk counts as a night walk, the time difference between two places. A wrong zone near a border therefore changes a published result. Lookup errors are not random noise either. A tool that simplifies the zone polygons to save space or time makes its errors along borders and coastlines, which biases exactly the analyses that compare regions across a border. `timezonefinder` uses the boundary polygons without simplification, so its accuracy is limited only by the source data. The guarantee is fidelity to that data, not ground truth: where OpenStreetMap places a border wrongly, `timezonefinder` answers wrongly in the same way, and such errors are corrected upstream. The State of the field section quantifies how far a simplifying alternative departs from the source near borders.

**Offline and reproducible lookups.** Web services such as the Google Maps Time Zone API answer the same question, but they need network access and an account, impose quotas and costs, and can change their answers without notice. Compute nodes of research clusters often have no internet access at all. A study that chose `timezonefinder` over a web API names this reason: an offline lookup cannot fail because an external service does [@perezparedes2023athletics]. A lookup in `timezonefinder` is a pure function of the coordinates and the installed boundary data. The data ships as the separately versioned `timezonefinder-data` package, and `TimezoneFinder.data_version` names the timezone-boundary-builder release the answers come from. A study that pins both packages and reports these versions can repeat its lookups exactly, and readers can tell which boundary release a result is based on.

**Coverage of the whole globe.** Instruments are not confined to land. Buoys, ships, aircraft, offshore platforms and remote stations need an answer too. The boundary data includes the nautical zones (`Etc/GMT±N`) over the oceans, so every coordinate receives a zone. Researchers who need to tell land from sea can ask for land zones only.

**Whole datasets at once.** Research datasets often contain millions of points. One call takes an array of longitudes and an array of latitudes and returns the zone of every point, which fits the column-oriented workflows of NumPy and pandas. Optional compiled backends make such batch lookups fast, but they are not required: on a machine without a compiler the package falls back to pure Python and returns identical answers, so a result does not depend on which backend happened to be installed.

# State of the field

Researchers who need the time zone at a coordinate take one of four routes.

**Approximations.** The simplest route derives the offset from the longitude, one hour per 15 degrees, or looks up the country of a point and takes a zone per country. Both fail where it matters. Zone borders follow political boundaries rather than meridians, as the Statement of need shows, and many large countries, among them the United States, Russia, Brazil and Australia, span several zones. An offset derived from the longitude also has no daylight saving time and no history, so it cannot localise a timestamp.

**Online services.** Web APIs such as the Google Maps Time Zone API, TimeZoneDB or GeoNames return a zone name for a coordinate. As discussed above, they need network access, accounts and quotas, and the boundary data behind an answer is neither stated nor fixed, so a result cannot be repeated later.

**General-purpose GIS tools.** The boundaries of timezone-boundary-builder [@tzbb] are published as a shapefile and as GeoJSON, so a researcher can load them into GeoPandas [@geopandas] or a spatial database such as PostGIS [@postgis] and run a spatial join. This gives exact answers, but it leaves the researcher to obtain the data and record its version, to load and index hundreds of megabytes of geometry, and to decide what happens at a point that lies inside two zones, where the dataset's polygons genuinely overlap. A spatial join returns every match there, or an arbitrary one. `timezonefinder` packages these steps: the data arrives as a versioned dependency, the index is precomputed, the geometry stays memory-mapped instead of loaded, and an overlap is resolved by a documented rule, in which the smaller zone, the one enclaved in the other, wins. A separate call returns every zone that contains the point.

**Dedicated lookup libraries.** The timezone-boundary-builder project lists more than twenty libraries in over a dozen languages that answer this question from its data, among them C, Go, Java, JavaScript, Julia, R and Rust. In Python, three packages exist. `pytzwhere` [@pytzwhere] is the oldest. It reads the outdated `tz_world` dataset [@tz_world], which has no ocean zones, and its last release dates from 2017. `tzfpy` [@tzfpy], first released in 2022, is a Python binding of the Rust crate `tzf-rs` and today the main alternative to `timezonefinder`.

`tzfpy` and `timezonefinder` read the same timezone-boundary-builder releases but make opposite trade-offs. The build of `tzfpy` on PyPI ships simplified polygons. Its wheels are therefore an order of magnitude smaller, and a single lookup is faster by a small single-digit factor on a representative mix of points. The price is accuracy near borders. We measured it with both packages on the same boundary release. Over points drawn uniformly from the globe, the two packages never disagree, because a random point lies hundreds of kilometres from the nearest border. Close to borders the picture reverses: within metres of a border, the two packages give different answers on at least one side of most sampled land-zone border locations, and the share falls with distance until it disappears at about a hundred metres, the maximum displacement the maintainer of `tzfpy` states for the simplification. For an analysis that looks up points far from any border, the two packages are interchangeable. For an analysis whose points cluster near borders, such as studies that compare neighbouring regions, cities on a border, or every cell of a regular grid, the simplified polygons change answers. `timezonefinder` uses the unsimplified polygons by default. The maintainer of `tzfpy` also publishes an experimental variant with unsimplified polygons, distributed outside PyPI, which we have not measured.

Beyond border accuracy, the two packages differ in ways that matter for research use. `timezonefinder` ships its boundary data as a separately versioned PyPI package, so a study can pin and report the boundary release independently of the lookup code. It looks up whole NumPy arrays in one call, which outpaces a loop of single `tzfpy` calls on a representative mix of points, since `tzfpy` has no batch interface. It can restrict answers to land zones, return every zone at a point in an overlap, return integer zone identifiers, and convert timestamps with the zone it finds. Finally, it can be built and run without a compiler at all, falling back to pure Python with identical answers, while a source build of `tzfpy` needs a Rust toolchain. All comparisons above come from harnesses in the repository that run both packages on the same points, in the same process and on the same machine. Their generated reports are part of the documentation, which also lists the use cases for which `tzfpy` is the better choice.

**Why a separate package.** `timezonefinder` started in 2016 from `pytzwhere`. At that time, `pytzwhere` parsed a large text file into memory and rebuilt its search structures at every start, which cost hundreds of megabytes of memory before the first answer. Making lookups cheap needed a different data layer and lookup algorithm: polygons stored in binary files with 32-bit integer coordinates, read on demand, and a spatial index precomputed when the data is built. These changes replaced the data format and the lookup as a whole, rather than amending them, so they were released as a new package. `pytzwhere` has had no release since. A side-by-side measurement of its last release against `timezonefinder` today shows an order of magnitude less memory and faster start-up and single lookups, and an answer for every point, where `pytzwhere` answers for under a third of the globe. `tzfpy` appeared six years later with a Rust core and a deliberately different trade-off. Neither design can absorb the other without giving up the property it is built around, so the two packages coexist, and the maintainer of `tzfpy` has contributed to `timezonefinder`.

# Software design

<!-- The trade-offs: unsimplified polygons, integer coordinates, the shortcut grid, interchangeable point-in-polygon backends, the separately versioned data package. -->

# Research impact statement

<!-- Evidence from the publications recorded in paper/references/, verified against their full text. -->

# AI usage disclosure

<!-- The statement drafted in paper/ai-usage-disclosure.md, once its open points are settled. -->

# Acknowledgements

<!-- Contributors from docs/5_contributing.rst, funding through GitHub Sponsors, and the statement on the sponsorship by the author of tzfpy. -->

# References
