.. _contributing:

Contribution
============

Contribution guidelines are documented in `CONTRIBUTING.md on GitHub <https://github.com/jannikmi/timezonefinder/blob/master/CONTRIBUTING.md>`_

If you encounter a bug or have a suggestion, `open an issue <https://github.com/jannikmi/timezonefinder/issues/new/choose>`__ or a `pull request <https://github.com/jannikmi/timezonefinder/compare>`__ on GitHub.


Contact
-------

Tell me if and how you are using this package - it encourages me to develop and test it further.

Most certainly there is something I missed, could have optimized further, or explained more clearly.
I would be really glad to get some feedback.


Acknowledgements
----------------

Thanks to:

- `theirix <https://github.com/theirix>`__ for the build and release pipeline: packaging the C extension into wheels with cibuildwheel, the uv and setuptools-based build, the universal abi3 wheel and the end-to-end wheel tests.
- `Lucas Hemkemeier <https://github.com/hemkdev>`__ for the automated data updates: detecting new timezone-boundary-builder releases and opening, merging and releasing the update pull requests.
- `Adam <https://github.com/adamchainz>`__ for adding organisational features to the project and for helping me with publishing and testing routines.
- `ringsaturn <https://github.com/ringsaturn>`__ for valuable feedback, sponsoring this project, creating the ``tzfpy`` package and adding the ``pytz`` compatibility extra.
- `ARYAN RAJ <https://github.com/a-ryanraj>`__ for the auto-generated data report, the GeoJSON validation, example scripts and updating Python version support.
- `Pratyush Kumar <https://github.com/pratyushkumar211>`__ for refactoring the data converter.
- `Lu Yicheng <https://github.com/01luyicheng>`__ for the property-based tests.
- `Marco Barbosa <https://github.com/aureliobarbosa>`__ for modernising the type hints and fixing packaging inconsistencies.
- `sefiotonomo <https://github.com/sefiotonomo>`__ for the original ``in_memory`` mode.
- `joshuadavidthomas <https://github.com/joshuadavidthomas>`__ for the first GitHub Actions CI workflow.
- `badhope <https://github.com/badhope>`__ for the ``--stdin`` streaming mode of the command line script and the ``Etc/GMT`` sign convention documentation.
- `Nice6042 <https://github.com/Nice6042>`__ for guarding data-only releases against shipping pending work.
- `MsfPablo <https://github.com/MsfPablo>`__ for exposing the packaged dataset version at runtime.
- `Pxli9130 <https://github.com/Pxli9130>`__ for the musllinux wheels.
- `Kristian Sloth Lauszus <https://github.com/Lauszus>`__ for making ``setuptools`` a build-only dependency.
- `Chase Horton <https://github.com/Chase-Horton>`__ for the ``slow`` test marker.
- `Dave Tapley <https://github.com/davetapley>`__ and `David Park <https://github.com/daphtdazz>`__ for making resource cleanup robust at interpreter shutdown.
- `WestonReed <https://github.com/WestonReed>`__ for updating the timezone data.
- `Tyler Huntley <https://github.com/Ty1776>`__ for adding docstrings.
- `Greg Meyer <https://github.com/gmmeyer>`__ for updating h3 to >4.
- `Romain Girard <https://github.com/romaingd-spi>`__ for fixing unwanted test content.
- `synapticarbors <https://github.com/synapticarbors>`__ for fixing Numba import with py27.
- `snowman2 <https://github.com/snowman2>`__ for creating the conda-forge recipe.
- `xylar <https://github.com/xylar>`__ for co-maintaining the `timezonefinder <https://github.com/conda-forge/timezonefinder-feedstock>`__ and `timezonefinder-data <https://github.com/conda-forge/timezonefinder-data-feedstock>`__ conda-forge feedstocks.
- `zedrdave <https://github.com/zedrdave>`__ for valuable feedback.
- everyone else who contributed fixes, reported issues or reviewed changes - see the `contributors page <https://github.com/jannikmi/timezonefinder/graphs/contributors>`__ and the :doc:`changelog <6_changelog>`.
