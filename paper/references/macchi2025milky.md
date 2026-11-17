# Milky Seas events: satellite observation, prediction and planning (Macchi, 2025)

- **BibTeX key:** `macchi2025milky`
- **Venue:** master thesis (Space Engineering), Politecnico di Milano, academic year 2024–25 (Scholar lists 2024)
- **URL:** <https://www.politesi.polimi.it/handle/10589/247235>
- **Field:** space engineering / ocean remote sensing
- **Verification:** full text read; one mention.

## How timezonefinder is referenced

> Observation times have been standardized to UTC using the TimezoneFinder library, which infers the local time zone from each event's geographic position and converts the start and end times accordingly.

Cited as: inline name.

## Role of timezonefinder

Historical ship reports of bioluminescent "milky sea" events give local times at sea. The package assigns a zone so they can be converted to UTC and matched with satellite overpasses.

## Notes

- An ocean use. Points at sea get the nautical `Etc/GMT±N` zones, which are only an approximation of the ship's clock. Remote and offshore points are also the subject of the GHOST follow-up (issue #773).
