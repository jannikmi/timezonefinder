============================
timezonefinder
============================

.. include:: ./badges.rst


.. image:: hero_banner.jpeg
   :alt: Coordinate to IANA timezone lookup
   :align: center

This is a python package providing offline timezone lookups for WGS84 coordinates.
In comparison to other alternatives this package aims at maximum accuracy around timezone borders (no geometry simplifications) while offering fast lookup performance and compatibility with many (Python) runtime environments.
It combines preprocessed polygon data, H3-based spatial shortcuts, and optional acceleration via Numba or a clang-backed point-in-polygon routine.



References
----------

* `Documentation <https://timezonefinder.readthedocs.io/en/latest/>`__
* `PyPI <https://pypi.python.org/pypi/timezonefinder/>`__
* `conda-forge feedstock <https://github.com/conda-forge/timezonefinder-feedstock>`__
* `download stats <https://pepy.tech/project/timezonefinder>`__
* `online GUI and API <https://timezonefinder.michelfe.it>`__
* `benchmark trend chart <https://jannikmi.github.io/timezonefinder/dev/bench/>`__
* `GUI repository <https://github.com/jannikmi/timezonefinder_gui>`__
* `ruby port <https://github.com/gunyarakun/timezone_finder>`__



.. toctree::
   :maxdepth: 2
   :caption: Contents:

   Getting Started <0_getting_started>
   Usage <1_usage>
   Use Cases <2_use_cases>
   Performance <7_performance>
   Timezone Finding Benchmarks <benchmark_results_timezonefinding>
   Point-in-Polygon Benchmarks <benchmark_results_polygon>
   Initialization Benchmarks <benchmark_results_initialization>
   Memory Benchmarks <benchmark_results_memory>
   Data Format <data_format>
   Data Report <data_report>
   About <3_about>
   Alternatives <alternatives>
   API <4_api>
   Contributing <5_contributing>
   Changelog <6_changelog>

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
