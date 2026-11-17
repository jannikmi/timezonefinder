# HERMESv3 Part 2: the bottom–up module (Guevara et al., 2020)

- **BibTeX key:** `guevara2020hermes`
- **Venue:** Geoscientific Model Development 13(3), 873–903, 2020
- **DOI:** [10.5194/gmd-13-873-2020](https://doi.org/10.5194/gmd-13-873-2020) (open access, CC BY 4.0)
- **Field:** atmospheric emission modelling
- **Verification:** full text read; one mention.

## How timezonefinder is referenced

Listed as a required dependency of HERMESv3_BU in Sect. 4 "Technical implementation":

> HERMESv3_BU is coded using Python 3.7.X and requires numpy (> 1.16.0), NetCDF4 (> 1.3.1) under HDF5 in parallel mode, pandas (> 0.22.0), … cf_units (> 1.1.3), timezonefinder (> 2.1.0), mpi4py (> 3.0.0), …

No reference-list entry.

## Role of timezonefinder

Bottom-up emission sectors (traffic, residential, industry, …) are distributed in time with local-time profiles; the package maps source locations to IANA time zones.

## Notes

- Follow-up to [`guevara2019hermes`](guevara2019hermes.md); same minimum version, now on Python 3.
