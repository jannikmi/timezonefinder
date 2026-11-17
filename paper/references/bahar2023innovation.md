# Innovation on wings: nonstop flights and firm innovation (Bahar et al., 2023)

- **BibTeX key:** `bahar2023innovation`
- **Venue:** Management Science 69(10), 6202–6223, 2023 (open access, CC BY 4.0)
- **DOI:** [10.1287/mnsc.2023.4682](https://doi.org/10.1287/mnsc.2023.4682)
- **Field:** management / economics of innovation
- **Verification:** full text read (PDF supplied by the maintainer); mentioned in the main text, Sect. 2.2 "Characteristics of Firms and Firm Locations", p. 6206, with footnote 8. The online appendix was not read.

## How timezonefinder is referenced

> First, we collect data on temporal distance, measured by the extent of working hour overlap between two firm/subsidiary locations (proxied by the airport location). For each airport, we obtained the time zone using its latitude and longitude coordinates and the timezonefinder package in Python.⁸ Using the time zones, we calculate the time difference between the origin airport and the destination airport and then calculate the working hour overlap to be from zero to eight hours.⁹

Cited as: footnote 8, `More information can be accessed at https://pypi.org/project/timezonefinder/.` No reference-list entry, no author and no version.

## Role of timezonefinder

Assigns a time zone to every airport in the flight data. The time difference between airport pairs defines *temporal distance* (working-hour overlap, footnote 9), one of the two moderators the paper's second prediction is about: Table 6, columns (1)–(4), split airport pairs into high and low temporal distance ("greater than one hour apart in time zone difference" versus "one hour or less"), and Online Sections D1–D3 vary the cutoff and test pairs 8+ hours apart. It is a heterogeneity split, not a control: the main regressions absorb country-level time-zone differences with country-pair–year fixed effects. Table 8 also controls for an airport's "Time zone difference from GMT"; the paper does not say how that variable was computed.

## Notes

- The most-cited publication in the record (69 Scholar citations), in a top management journal.
- Crossref's 71 parsed references contain no entry for the package because the citation is a footnote URL.
