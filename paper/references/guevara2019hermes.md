# HERMESv3 Part 1: global and regional module (Guevara et al., 2019)

- **BibTeX key:** `guevara2019hermes`
- **Venue:** Geoscientific Model Development 12(5), 1885–1907, 2019
- **DOI:** [10.5194/gmd-12-1885-2019](https://doi.org/10.5194/gmd-12-1885-2019) (open access, CC BY 4.0)
- **Field:** atmospheric emission modelling
- **Verification:** full text read; one mention.

## How timezonefinder is referenced

Listed as a required dependency of the HERMESv3_GR emission model, in Sect. 2.6 "Technical implementation":

> HERMESv3_GR is coded using Python 2.7.X and requires numpy (>= 1.9.1), … holidays (>= 0.4.1), pytz (>= 2017.2), timezonefinder (>= 2.1.0), mpi4py (>= 3.0.0) and pytest (>= 3.6.1) Python libraries.

No reference-list entry; the package is named only in the dependency list.

## Role of timezonefinder

Emission inventories are temporally disaggregated with local-time profiles (hour of day, weekday, holidays). Determining the local time zone of each grid cell from its coordinates is what the dependency (together with `pytz` and `holidays`) provides.

## Notes

- Earliest scientific reference found; pins a minimum version (2.1.0).
- Same group (Barcelona Supercomputing Center) as [`guevara2020hermes`](guevara2020hermes.md) and [`bowdalo2024ghost`](bowdalo2024ghost.md).
