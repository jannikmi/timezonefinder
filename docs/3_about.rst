=====
About
=====

``timezonefinder`` is a Python package providing offline timezone lookups for WGS84 coordinates.

:doc:`architecture` walks through the lookup pipeline end to end, the three point-in-polygon backends and the trade-offs that were deliberately *not* taken.
:doc:`data_format` documents the binary layouts it reads, and :doc:`alternatives` compares this package against the other options.


License
-------

``timezonefinder`` is licensed under the `MIT license <https://github.com/jannikmi/timezonefinder/blob/master/LICENSE>`__.

The data ships in the separate ``timezonefinder-data`` distribution and is licensed under the `ODbL license <https://github.com/jannikmi/timezonefinder/blob/master/packages/timezonefinder-data/DATA_LICENSE>`__, following the base dataset from `evansiroky/timezone-boundary-builder <https://github.com/evansiroky/timezone-boundary-builder>`__.

Used by
-------

``timezonefinder`` is the most downloaded offline timezone lookup package for Python - see :doc:`alternatives` for how it compares.
GitHub's `dependency graph <https://github.com/jannikmi/timezonefinder/network/dependents>`__ lists thousands of repositories and hundreds of published packages that depend on it, among them:

* industry: Google's `data-science-on-gcp <https://github.com/GoogleCloudPlatform/data-science-on-gcp>`__, Posit's `Shiny for Python <https://github.com/posit-dev/py-shiny>`__
* research and government: CERN's `CAiMIRA <https://gitlab.cern.ch/caimira/caimira>`__, Sandia National Laboratories' `pvOps <https://github.com/sandialabs/pvOps>`__, the National Laboratory of the Rockies' (formerly NREL) `HOPP <https://github.com/NatLabRockies/HOPP>`__, the US EPA's `sensortoolkit <https://github.com/USEPA/sensortoolkit>`__, NOAA's `monetio <https://github.com/noaa-oar-arl/monetio>`__, NASA JPL OPERA's `next_pass <https://github.com/OPERA-Cal-Val/next_pass>`__
* open source: `LibrePhotos <https://github.com/LibrePhotos/librephotos>`__, `RocketPy <https://github.com/RocketPy-Team/RocketPy>`__, Bellingcat's `ShadowFinder <https://github.com/bellingcat/ShadowFinder>`__, Catalyst Cooperative's `PUDL <https://github.com/catalyst-cooperative/pudl>`__


Citing
------

To cite ``timezonefinder``, use the DOI `10.5281/zenodo.23579731 <https://doi.org/10.5281/zenodo.23579731>`__, which Zenodo resolves to the latest release, or the "Cite this repository" button on GitHub, which reads `CITATION.cff <https://github.com/jannikmi/timezonefinder/blob/master/CITATION.cff>`__.
