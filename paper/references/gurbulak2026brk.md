# BRK-Astronomical Tools: a multilingual astronomy tool for observation preparation (Gürbulak & Nasıroğlu, 2026)

- **BibTeX key:** `gurbulak2026brk`
- **Venue:** Osmaniye Korkut Ata Üniversitesi Fen Bilimleri Enstitüsü Dergisi 9(1), 183–195, 2026
- **DOI:** [10.47495/okufbed.1664438](https://doi.org/10.47495/okufbed.1664438) (open access via DergiPark)
- **Field:** observational astronomy software
- **Verification:** full text (PDF) read; three mentions.

## How timezonefinder is referenced

In the description of the libraries used:

> Timezonefinder; It is a Python package that allows you to find the time zone corresponding to the given coordinates on the globe, completely offline (Lutz, 2010).

In the methods:

> Geolocation-based calculations were performed using the Geopy library, and time zone management was supported by Pytz and TimezoneFinder.

In the discussion:

> In particular, modules such as Astral and Timezonefinder facilitate accurate and reliable results in timing calculations.

## Role of timezonefinder

The tool plans telescope observations (visibility windows, sunrise and sunset, twilight) for a user-chosen site. timezonefinder supplies the site's time zone, so the tool can show times in local civil time next to UTC and sidereal time.

## Notes

- **Wrong citation.** The package is cited as "(Lutz, 2010)", i.e. Mark Lutz's *Learning Python* book, which predates the package (first released 2016). The paper also uses that reference for pytz and Astral. Valid citation metadata (`CITATION.cff`, Zenodo DOI) would help prevent this.
- The paper credits the package with part of the timing accuracy.
