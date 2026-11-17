# Energy balance of the UWC link (Bartoň, 2024)

- **BibTeX key:** `barton2024uwc`
- **Venue:** master's thesis (diplomová práce), Brno University of Technology, Faculty of Electrical Engineering and Communication, Department of Radio Electronics, 2024 (supervisor Lucie Hudcová); Czech title *Energetická bilance UWC spoje*, text in English
- **URL:** <http://hdl.handle.net/11012/245907> (open access; also listed on theses.cz)
- **Field:** underwater optical wireless communication
- **Verification:** full text read (repository PDF, read in the browser); mentioned once, in Appendix B "The source code", p. 61. The repository's extracted-text file stops at 100,000 characters, before Appendix B, which is why a search of that file finds nothing. The source code itself sits in the attached `appendix-1.zip`, which was not opened.

## How timezonefinder is referenced

> For the program to correctly work, python libraries "numpy", "scipy", "Tkinter", "Pandas", "Pillow", "netCDF4", "solarpy", "datetime", "timezonefinder", "pytz", "os", "sys" and "matplotlib" need to be installed. This program was tested and optimized with Python version 3.12.1, on computer running on Windows 10 and 11 with 8 GB of RAM.

Cited as: a dependency list in the appendix. No reference-list entry, URL or version.

## Role of timezonefinder

A required dependency of the thesis software, which computes the link budget of an underwater optical link. The user picks a location on a map and then a date and time of operation, from which the program calculates the solar irradiance at the water surface and the resulting solar noise at the receiver (p. 38). Converting that local date and time to UTC for `solarpy` with `timezonefinder` and `pytz` is the likely use; the text does not say so, so this is an inference from the dependency list.
