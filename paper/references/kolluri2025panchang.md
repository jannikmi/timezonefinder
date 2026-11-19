# Timezone-aware traditional calendar systems: Hindu Panchang with DST support (Kolluri, 2025)

- **BibTeX key:** `kolluri2025panchang`
- **Venue:** SSRN preprint 5347331, 2025
- **DOI:** [10.2139/ssrn.5347331](https://doi.org/10.2139/ssrn.5347331)
- **Field:** calendar computation / applied astronomy software
- **Verification:** weak. Google Scholar returns it for "timezonefinder" and for the method name "timezone_at", which means its indexed full text contains both, most likely in code. Neither the snippet nor any text read here shows the passage, because SSRN blocks automated access. Crossref has no reference list or abstract for it. Confirm before quoting.
- **Access attempts (2026-11-19):** the SSRN abstract and PDF URLs return a Cloudflare challenge (HTTP 403) to command-line requests. OpenAlex lists SSRN as the only location, Semantic Scholar has no record, and web searches found no other copy and no code repository by the author. The SSRN author page lists two further panchang papers by him. Reading it needs a person in a browser on SSRN.

## How timezonefinder is referenced

Not seen. The Scholar snippet only gives the abstract: "a comprehensive solution for implementing traditional Hindu calendar systems (panchang) with full timezone awareness and Daylight Saving Time (DST) support".

## Role of timezonefinder (inferred)

Panchang elements (tithi, sunrise-based day boundaries) depend on local civil time at the observer's location, so the package most likely maps the user's coordinates to an IANA zone, with DST handled by the tz database. This is an inference from the topic, not something read in the text.
