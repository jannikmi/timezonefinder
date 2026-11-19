# Collaboration across the globe: time zone differences and citations (Manchin, 2025)

- **BibTeX key:** `manchin2025collaboration`
- **Venue:** Research Policy 54(8), 105296, 2025 (received 19 July 2024, accepted 24 June 2025, online 2 August 2025; open access, CC BY 4.0)
- **DOI:** [10.1016/j.respol.2025.105296](https://doi.org/10.1016/j.respol.2025.105296)
- **Working paper:** SSRN, [10.2139/ssrn.4903262](https://doi.org/10.2139/ssrn.4903262)
- **Field:** economics of science / scientometrics
- **Verification:** full text read, from the published article supplied by the maintainer (ScienceDirect refuses automated access). The reference list has no timezonefinder entry, so the package is cited in a footnote only.

## How timezonefinder is referenced

Footnote 3, attached to Section 3.1 (data preparation), lists the tools: "most of data processing work was done in Python", with `dask` for cleaning and merging, the `geocoder` package for geocoding, and "timezone calculations were done with 'timezonefinder' package", followed by the documentation URL (`timezonefinder.readthedocs.io`). Regressions were done in Stata. Section 3.1 itself says the affiliation locations were geocoded with the Google Maps API and that "the geographical coordinates were used to calculate the corresponding time zone for each location". The two statements about the geocoder differ (Google Maps API in the text, the `geocoder` package in the footnote); the package is probably used as the client.

## Role of timezonefinder

The study uses Scopus records of about 20.5 million co-authored journal articles from 1995 to 2016. Each author affiliation is geocoded, and the coordinates give a time zone. The time-zone difference between co-authors (the average of all bilateral differences in the team, in hours; sample mean 0.54 h, maximum 12 h) is the key explanatory variable for citation counts. Authors with affiliations in several time zones weight each zone inversely to their number. The paper reports that one extra hour of average difference goes with about 4 % more citations, with the largest effect (about 15 %) at 5–6 h.

## Notes

- A use where timezonefinder output is not just preprocessing but defines the treatment variable of the study, at the scale of tens of millions of articles. Zone errors at borders would propagate directly into the estimates, although most affiliations are institutions in cities, away from borders.
- The paper does not say how a zone name becomes an hour difference, for example at which date the UTC offsets are taken, which matters in zones with daylight-saving time.
- Table 1 reports 20,562,571 observations; about 470,000 articles (2 %) with missing author information were dropped, and the paper says dropping them leaves the results almost unchanged.
