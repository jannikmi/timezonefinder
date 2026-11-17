# Use of AI for operations and maintenance planning of a flight school (Timosenco, 2026)

- **BibTeX key:** `timosenco2026flight`
- **Venue:** bachelor thesis, Universitat Politècnica de Catalunya, examination session "Extension Autumn 2025" (Scholar and the repository list 2026); supervisor Luis Manuel Pérez Llera
- **URL:** <https://upcommons.upc.edu/entities/publication/ec82c6d0-a110-4ff5-9032-17a44bcbd42f>
- **Field:** aviation operations software
- **Verification:** full text read (report and budget annex); eleven mentions.

## How timezonefinder is referenced

> The UTC timestamps are converted to local aerodrome time using the timezonefinder library to resolve the IANA timezone from the aerodrome's coordinates and the Python zoneinfo module to perform the conversion.

Cited as: reference list, in the report ([37]) and the budget annex ([12]).

## Role of timezonefinder

Civil twilight times (UTC) from an API are converted to local aerodrome time to constrain flight-lesson scheduling.

## Notes

- **Wrong author:** the budget annex cites the package as `J. Janetzko, "timezonefinder," PyPI, 2024`. That name does not belong to the project; it looks like a guessed or generated attribution. Clear citation metadata would prevent this.
