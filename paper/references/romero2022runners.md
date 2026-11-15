# COVID-19 and physical-activity habits of competitive runners (Romero & Lv, 2022)

- **BibTeX key:** `romero2022runners`
- **Venue:** International Journal of Environmental Research and Public Health 19(19), 12933, 2022
- **DOI:** [10.3390/ijerph191912933](https://doi.org/10.3390/ijerph191912933) (open access, CC BY 4.0; PubMed 36232233)
- **Preprint:** Preprints.org, [10.20944/preprints202209.0068.v1](https://doi.org/10.20944/preprints202209.0068.v1) — same text, not counted separately
- **Field:** public health / wearable-sensor data analysis
- **Verification:** full text read via Europe PMC; one mention.

## How timezonefinder is referenced

In the data-preprocessing description:

> GPS coordinates were used to map activities to country and time zone with the Python packages timezonefinder and reversegeocode. Timestamps were converted from UTC time zone to the local time zone.

No reference-list entry.

## Role of timezonefinder

Running activities recorded by Stryd foot-pod devices worldwide carry UTC timestamps; the start coordinates are mapped to a time zone so that time-of-day and weekday habits can be compared before and during the pandemic in local time.

## Notes

- Activities without GPS (18.3 % in 2019, 0.7 % in 2020) could not be localised, which illustrates that the package is only as useful as the coordinates fed to it.
