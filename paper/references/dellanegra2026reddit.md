# Reddit's globalization: inferring community time zone from activity timestamps (Della Negra et al., 2026)

- **BibTeX key:** `dellanegra2026reddit`
- **Venue:** arXiv preprint [2605.04371](https://arxiv.org/abs/2605.04371) (cs.SI), 2026
- **Field:** computational social science
- **Verification:** full text (arXiv HTML) read; one mention.

## How timezonefinder is referenced

In the construction of the ground-truth set:

> We leverage RedditLists' taxonomy, which includes the Nation/State and name of a location, to compose descriptive strings that we pass to the Nominatim geocoder service. Then, we use the timezonefinder Python package to attribute time zones based on the inferred latitude and longitude of each location.

No reference-list entry.

## Role of timezonefinder

Produces the reference ("ground-truth") time zone of location-specific subreddits, against which the paper's activity-rhythm-based time-zone inference methods are evaluated.

## Notes

- timezonefinder serves as the trusted baseline for evaluation, i.e. its answers are assumed correct.
- Coordinates come from geocoding place names, so the lookup sits downstream of geocoding uncertainty.
