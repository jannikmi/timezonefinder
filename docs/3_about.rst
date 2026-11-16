=====
About
=====

``timezonefinder`` is a Python package providing offline timezone lookups for WGS84 coordinates.

:doc:`architecture` walks through the lookup pipeline end to end, the three point-in-polygon backends and the trade-offs that were deliberately *not* taken.
:doc:`data_format` documents the binary layouts it reads, and :doc:`alternatives` compares this package against the other options.


Statement of need
-----------------

Much research data records *when* and *where* something happened as a UTC timestamp and a WGS84 coordinate: monitoring stations, GPS tracks from wearables, geotagged social-media posts, points of a model grid.
Questions about human activity or daily cycles need the local time instead - the hour of day, the date in the local calendar, whether it was dark, whether daylight saving time applied - and recovering it means knowing the IANA timezone at each coordinate.
``timezonefinder`` answers that offline, from the coordinates alone.

Published research uses it this way in fields from atmospheric chemistry, fire-weather forecasting and ionospheric physics to public health, transport safety, economics and radio-spectrum measurement.
It converts monitoring-station records between local time and UTC (`Bowdalo et al., 2024 <https://doi.org/10.5194/essd-16-4417-2024>`__), takes every fire-danger input at local noon on a forecast grid (`Worsnop et al., 2021 <https://doi.org/10.1175/WAF-D-21-0075.1>`__), and measures the time-zone distance between cities linked by nonstop flights (`Bahar et al., 2023 <https://doi.org/10.1287/mnsc.2023.4682>`__).
Research software such as the HERMESv3 emission model (`Guevara et al., 2019 <https://doi.org/10.5194/gmd-12-1885-2019>`__) and pynasonde (`Chakraborty et al., 2026 <https://doi.org/10.1016/j.softx.2026.102617>`__) ships it as a dependency, so their users inherit its answers.
Three properties matter for that use:

* **Accuracy at borders.** The boundary polygons are never simplified (:doc:`why_no_simplification`), so accuracy is limited only by the source dataset.
  The errors a simplified boundary makes are not random noise: they cluster along borders and coastlines, which biases exactly the analyses that compare regions across them.
  This is measured, not assumed: against ``tzfpy``, which ships simplified polygons built from the same release, a uniform global sample shows no disagreement at all, while most sampled land-zone border locations are affected within metres of the border and the disagreement reaches out to about a hundred metres (:doc:`border_accuracy_vs_tzfpy`).
  Studies like those above feed the zone straight into their main variable - the hour a fire-danger input is taken at, whether a walk happened after dark, the time-zone distance between two places - so a wrong zone near a border moves a published result.
  The guarantee is fidelity to the source, not ground truth: the boundaries come from OpenStreetMap via timezone-boundary-builder, and where OpenStreetMap is wrong this package is wrong the same way (:doc:`why_no_simplification`).
  A lookup also answers only for the exact point passed, so a study that looks up grid-cell centres assigns a cell straddling a border wholly to the zone at its centre.
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
* research and government: CERN's `CAiMIRA <https://gitlab.cern.ch/caimira/caimira>`__, the Barcelona Supercomputing Center's `HERMESv3 <https://earth.bsc.es/gitlab/es/hermesv3_gr>`__ emission model, Forschungszentrum Jülich's `ETHOS.TISED <https://github.com/FZJ-IEK3-VSA/ETHOS.TISED>`__, Sandia National Laboratories' `pvOps <https://github.com/sandialabs/pvOps>`__, the National Laboratory of the Rockies' (formerly NREL) `HOPP <https://github.com/NatLabRockies/HOPP>`__, the US EPA's `sensortoolkit <https://github.com/USEPA/sensortoolkit>`__, NOAA's `monetio <https://github.com/noaa-oar-arl/monetio>`__, NASA JPL OPERA's `next_pass <https://github.com/OPERA-Cal-Val/next_pass>`__
* open source: `LibrePhotos <https://github.com/LibrePhotos/librephotos>`__, `RocketPy <https://github.com/RocketPy-Team/RocketPy>`__, Bellingcat's `ShadowFinder <https://github.com/bellingcat/ShadowFinder>`__, Catalyst Cooperative's `PUDL <https://github.com/catalyst-cooperative/pudl>`__


Citing
------

To cite ``timezonefinder``, use the DOI `10.5281/zenodo.23579731 <https://doi.org/10.5281/zenodo.23579731>`__, which Zenodo resolves to the latest release, or the "Cite this repository" button on GitHub, which reads `CITATION.cff <https://github.com/jannikmi/timezonefinder/blob/master/CITATION.cff>`__.
As BibTeX:

.. code-block:: bibtex

    @software{kissinger_timezonefinder,
      author = {Kissinger, Jannik and Seliverstov, Evgenii and Hemkemeier, Lucas},
      title = {timezonefinder},
      url = {https://github.com/jannikmi/timezonefinder},
      doi = {10.5281/zenodo.23579731}
    }

In a methods section, also state the ``timezonefinder`` and ``timezonefinder-data`` versions you used: a data release can move answers, and ``TimezoneFinder.data_version`` names the boundary release a finder answers from (see :doc:`result_stability`).
