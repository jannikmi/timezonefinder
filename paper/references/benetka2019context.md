# Understanding context for tasks and activities (Benetka, Krumm & Bennett, 2019)

- **BibTeX key:** `benetka2019context`
- **Venue:** Proceedings of the 2019 Conference on Human Information Interaction and Retrieval (CHIIR '19), ACM, pp. 133–142
- **DOI:** [10.1145/3295750.3298929](https://doi.org/10.1145/3295750.3298929)
- **Field:** information retrieval / human–computer interaction
- **Verification:** full text read on 2026-11-19, in the authors' PDF on the Microsoft Research publication page (<https://www.microsoft.com/en-us/research/wp-content/uploads/2019/01/chiir-activity-benetka.pdf>, 10 pages, ACM `acmart` layout, built 16 January 2019). One mention, in Section 3.2.1, "Preprocessing" (page 4), with footnote 3. The ACM Digital Library refuses command-line access (HTTP 403), and OpenAlex lists no open copy.

## How timezonefinder is referenced

> Timezone inference - in order to calculate the local time of a tweet from its server publication time, we infer the tweet's timezone from its geo-coordinates using timezonefinder³ and apply the time difference to get the local time.

Footnote 3: "https://github.com/MrMinimal64/timezonefinder", the repository's address at the time, under the maintainer's former GitHub handle.

Cited as: inline name with a footnote URL. No reference-list entry, which matches the Crossref reference list (42 entries).

## Role of timezonefinder

The tweets are Foursquare check-ins shared to Twitter. The paper extracts the activities people tweet about and models them by time of day and venue category, and compares those temporal profiles with the American Time Use Survey. Each tweet's local time comes from its coordinates through the package, so the time-of-day profiles depend on the lookup.

## Notes

- Earliest use found outside atmospheric modelling, from Microsoft Research authors. Scholar lists 22 citations.
- Same usage pattern as [`hosseinabad2021twitter`](hosseinabad2021twitter.md): social-media timestamps converted to local time.
