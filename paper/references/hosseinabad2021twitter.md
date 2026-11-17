# Physical activity, sedentary behaviour and sleep on Twitter: a labelled dataset (Shakeri Hossein Abad et al., 2021)

- **BibTeX key:** `hosseinabad2021twitter`
- **Venue:** medRxiv preprint, 2021, [10.1101/2021.04.13.21255449](https://doi.org/10.1101/2021.04.13.21255449)
- **Published version:** JMIR Public Health and Surveillance 8(2), e32355, 2022, [10.2196/32355](https://doi.org/10.2196/32355) (open access, PMC8887637)
- **Field:** digital public health / social-media data
- **Verification:** the preprint passage comes from Google Scholar's full-text snippet. The published JMIR full text was read via Europe PMC and describes the same step without naming the package (see below).

## How timezonefinder is referenced

Preprint (Scholar snippet):

> … this timezone base on each tweet's location, we utilized the bounding box of coordinates, which enabled spatial mapping to tweets' respective city locations and used timezonefinder in …

Published JMIR version, "Time Adjustment":

> The Twitter API returns the date and time that a tweet is published in the Universal Time Coordinated. To adjust this time zone based on each tweet's location, we used the bounding box of coordinates, which enabled spatial mapping to tweets' respective city locations, and used a time zone finder in Python.

No reference-list entry in either version.

## Role of timezonefinder

Converts tweet timestamps to local time so that weekday, month and hour can be used as features when labelling tweets about physical activity, sedentary behaviour and sleep.

## Notes

- In peer review the package name became a generic description ("a time zone finder in Python"), so the published article would not be found by a search for the name. This is an example of the attribution being lost.
