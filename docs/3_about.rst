=====
About
=====

``timezonefinder`` is a Python package providing offline timezone lookups for WGS84 coordinates.

:doc:`architecture` walks through the lookup pipeline end to end, the three point-in-polygon backends and the trade-offs that were deliberately *not* taken.
:doc:`data_format` documents the binary layouts it reads, and :doc:`alternatives` compares this package against the other options.


Statement of need
-----------------

Much research data records *when* and *where* something happened as a UTC timestamp and a WGS84 coordinate: sensor networks and field stations, GPS and animal tracking, photo and social-media metadata, satellite overpasses.
Questions about human activity or daily cycles need the local time instead - the hour of day, the date in the local calendar, whether daylight saving time applied - and recovering it means knowing the IANA timezone at each coordinate.
``timezonefinder`` answers that offline, from the coordinates alone.
Three properties matter for that use:

* **Accuracy at borders.** The boundary polygons are never simplified (:doc:`why_no_simplification`), so accuracy is limited only by the source dataset.
  The errors a simplified boundary makes are not random noise: they cluster along borders and coastlines, which biases exactly the analyses that compare regions across them.
* **Reproducibility.** A lookup needs no network access and no online service, so it runs on clusters without internet access and is subject to neither quotas nor data that changes without notice.
  The boundary data ships as a separately versioned package: pin it and report ``TimezoneFinder.data_version``, the timezone-boundary-builder release the answers come from, and the lookups can be repeated exactly (:doc:`result_stability`).
* **Whole datasets in one call.** ``timezone_names_at()`` takes one array per axis, and every backend, including pure Python on a machine without a compiler, returns identical answers.
  :ref:`Localizing timestamps in a dataset <localize_dataset>` shows the pattern.


License
-------

``timezonefinder`` is licensed under the `MIT license <https://github.com/jannikmi/timezonefinder/blob/master/LICENSE>`__.

The data ships in the separate ``timezonefinder-data`` distribution and is licensed under the `ODbL license <https://github.com/jannikmi/timezonefinder/blob/master/packages/timezonefinder-data/DATA_LICENSE>`__, following the base dataset from `evansiroky/timezone-boundary-builder <https://github.com/evansiroky/timezone-boundary-builder>`__.

Used by
-------

GitHub's `dependency graph <https://github.com/jannikmi/timezonefinder/network/dependents>`__ lists thousands of repositories and hundreds of published packages that depend on ``timezonefinder``, among them:

* industry: Google's `data-science-on-gcp <https://github.com/GoogleCloudPlatform/data-science-on-gcp>`__, Posit's `Shiny for Python <https://github.com/posit-dev/py-shiny>`__
* research and government: CERN's `CAiMIRA <https://gitlab.cern.ch/caimira/caimira>`__, Sandia National Laboratories' `pvOps <https://github.com/sandialabs/pvOps>`__, the National Laboratory of the Rockies' (formerly NREL) `HOPP <https://github.com/NatLabRockies/HOPP>`__, the US EPA's `sensortoolkit <https://github.com/USEPA/sensortoolkit>`__, NOAA's `monetio <https://github.com/noaa-oar-arl/monetio>`__, NASA JPL OPERA's `next_pass <https://github.com/OPERA-Cal-Val/next_pass>`__
* open source: `LibrePhotos <https://github.com/LibrePhotos/librephotos>`__, `RocketPy <https://github.com/RocketPy-Team/RocketPy>`__, Bellingcat's `ShadowFinder <https://github.com/bellingcat/ShadowFinder>`__, Catalyst Cooperative's `PUDL <https://github.com/catalyst-cooperative/pudl>`__


Citing
------

To cite ``timezonefinder``, use the DOI `10.5281/zenodo.23579731 <https://doi.org/10.5281/zenodo.23579731>`__, which Zenodo resolves to the latest release, or the "Cite this repository" button on GitHub, which reads `CITATION.cff <https://github.com/jannikmi/timezonefinder/blob/master/CITATION.cff>`__.
