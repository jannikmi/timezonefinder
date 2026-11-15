# Solar-plus-storage capacity sizing for Winnipeg (Agyei-Agyemang & Bibeau, 2026)

- **BibTeX key:** `agyeiagyemang2026solar`
- **Venue:** Energies 19(17), 4149, 2026
- **DOI:** [10.3390/en19174149](https://doi.org/10.3390/en19174149) (open access)
- **Field:** renewable energy systems / photovoltaic modelling
- **Verification:** full text **not** retrieved (publisher blocks automated access). The mention is taken from a search-engine extract of the methods section: "Local time zones required by pvlib, were automatically assigned from station coordinates using the TimeZoneFinder library." The Crossref reference list (79 entries) contains no timezonefinder entry. Re-check against the full text before quoting.

## Role of timezonefinder

Hourly meteorological records from a weather station (Winnipeg International Airport) are fed into `pvlib`, which needs a local time zone for solar-position calculations; timezonefinder supplies it from the station coordinates.

## Notes

- Spelled "TimeZoneFinder" in the text.
- Typical pvlib pairing; the open-access framework presumably lets other sites be modelled by changing the coordinates only.
