# Franchising defrosts: ownership structure and service availability (Babar et al., 2026)

- **BibTeX key:** `babar2026franchising`
- **Venue:** SSRN preprint 6504158, 2026 (PDF built 31 March 2026; Reject and Resubmit at *Management Science*, according to the authors' pages)
- **DOI:** [10.2139/ssrn.6504158](https://doi.org/10.2139/ssrn.6504158)
- **Field:** operations management / economics
- **Verification:** full text read on 2026-11-19, in the SSRN PDF the maintainer downloaded (44 pages). One mention, in Appendix B, "McBroken Data Collection" (PDF page 44). SSRN refuses command-line access, and OpenAlex, the Tilburg research portal and the authors' pages led back to SSRN only, so the copy came from the maintainer's browser.

## How timezonefinder is referenced

> To accurately determine the precise local time of each status check, we first identified the local time zone for every restaurant. This was achieved using the Python package timezonefinder, which converted the restaurant's geographical coordinates into its corresponding time zone. Following this, for each UTC commit timestamp, we converted it to the restaurant's local time zone. From this newly localized commit time, we then subtracted the "minutes ago" value of the "last check" to derive the exact local time at which the check was performed.

Cited as: inline name, in the data appendix. No reference-list entry.

## Role of timezonefinder

The study measures ice-cream machine availability at about 11,900 US McDonald's restaurants from 2021 to 2025, using the McBroken archive on GitHub. The archive commits a JSON snapshot every 30 minutes with UTC commit times and relative "last check" times. The package gives each restaurant's zone, and each check is converted to the restaurant's local time. Section 3.2.1 then keeps only checks within each restaurant's opening hours, to remove machine status carried over from closing. So every observation behind the two outcomes, the share of unavailable checks and the duration of unavailability, passes through the local time the lookup supplies.

## Notes

- The appendix's worked example is a restaurant in Trotwood, OH (UTC−4): a commit at 15:01 UTC with a check 16 minutes earlier gives a local check time of 10:45.
