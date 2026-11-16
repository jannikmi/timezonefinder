# Timezone-aware traditional calendar systems: Hindu Panchang with DST support (Kolluri, 2025)

- **BibTeX key:** `kolluri2025panchang`
- **Venue:** SSRN preprint 5347331, 2025
- **DOI:** [10.2139/ssrn.5347331](https://doi.org/10.2139/ssrn.5347331)
- **Field:** calendar computation / applied astronomy software
- **Verification:** weak. Google Scholar returns it for "timezonefinder", which means its indexed full text contains the term. Neither the snippet nor any text read here shows the passage, because SSRN blocks automated access. Crossref has no reference list or abstract for it. Confirm before quoting.

## How timezonefinder is referenced

Not seen. The Scholar snippet only gives the abstract: "a comprehensive solution for implementing traditional Hindu calendar systems (panchang) with full timezone awareness and Daylight Saving Time (DST) support".

## Role of timezonefinder (inferred)

Panchang elements (tithi, sunrise-based day boundaries) depend on local civil time at the observer's location, so the package most likely maps the user's coordinates to an IANA zone, with DST handled by the tz database. This is an inference from the topic, not something read in the text.
