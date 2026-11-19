# Unequal darkness: disparities in nighttime pedestrian fatality risk in the United States (Carey & Beeram, 2027)

- **BibTeX key:** `carey2027darkness`
- **Venue:** Journal of Transport & Health 52, 102440, 2027 (received 20 March 2026, accepted 14 September 2026, online 30 September 2026; all rights reserved, not open access)
- **DOI:** [10.1016/j.jth.2026.102440](https://doi.org/10.1016/j.jth.2026.102440)
- **Field:** transport safety / public health
- **Verification:** full text read, from the published article supplied by the maintainer (ScienceDirect refuses automated access). The supplied text ends with the conclusions, before the reference list. The Crossref reference list (23 entries) has no timezonefinder entry, so the package is named in the text only, without a footnote, URL or reference.

## How timezonefinder is referenced

Section 3.1 (data sources), describing the outcome variable `IS_DARK`:

> A crash was classified as occurring in darkness if the crash timestamp, localized to the crash's time zone using timezonefinder, occurred after civil dusk—the moment when the sun is 6° below the horizon.

The same paragraph names the `astral` library (v3) for the twilight times and `geopandas` for the census-tract join. None of the three has a reference.

## Role of timezonefinder

The study links 53,353 US pedestrian fatalities (FARS, 2015–2023) to census-tract demographics and satellite night-time radiance. For each crash with a timestamp and coordinates (58,662 of 58,666 had a valid time), the timestamp is localised to the zone at the crash coordinates, and `astral` computes civil dusk and dawn there. A crash after dusk or before dawn counts as dark (`IS_DARK`), which is the outcome of every regression: the share of fatalities in darkness is 47.8 %, and it rises with tract poverty (odds ratio 1.07 per standard deviation) and minority share (1.08). The paper tests alternative darkness definitions (nautical twilight, the 0–120 min after sunset, and the FARS lighting field) but does not vary the zone lookup.

## Notes

- Like [`manchin2025collaboration`](manchin2025collaboration.md), the lookup feeds the study's key variable directly. A wrong zone would shift a crash by an hour relative to dusk, which matters most in the evening hours when most dark crashes happen. The risk is largest near US time-zone borders (for example split counties in Indiana, Kentucky, Tennessee, Florida or the Dakotas), where this use is sensitive to border accuracy.
- The same pattern as [`vellimana2023walking`](vellimana2023walking.md): coordinates and a timestamp, the zone, then the position of the sun. Both are transport-safety studies that label the dark.
- The text calls the twilight computation "astronomical" once but uses civil twilight throughout; this does not concern the zone lookup.
