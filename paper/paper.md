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
  - name: Affiliation to be confirmed
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

<!-- Next step: the research purpose and target audience, adapted from the statement of need in docs/3_about.rst. -->

# State of the field

<!-- Comparison with tzfpy and the other approaches in docs/alternatives.rst, with the build-vs-contribute justification. -->

# Software design

<!-- The trade-offs: unsimplified polygons, integer coordinates, the shortcut grid, interchangeable point-in-polygon backends, the separately versioned data package. -->

# Research impact statement

<!-- Evidence from the publications recorded in paper/references/, verified against their full text. -->

# AI usage disclosure

<!-- The statement drafted in paper/ai-usage-disclosure.md, once its open points are settled. -->

# Acknowledgements

<!-- Contributors from docs/5_contributing.rst, funding through GitHub Sponsors, and the statement on the sponsorship by the author of tzfpy. -->

# References
