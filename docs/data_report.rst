.. _data_report:



Data Report
===========

**Timezone Data Version**: 2026c



Data Statistics
---------------


.. list-table::
   :header-rows: 1
   :widths: 79 21

   * - General Metric
     - Value
   * - Total coordinate values (2 per point)
     - 16,375,460



Boundary Polygon Statistics
~~~~~~~~~~~~~~~~~~~~~~~~~~~


.. list-table::
   :header-rows: 1
   :widths: 82 18

   * - Boundary Metric
     - Value
   * - Total boundary polygons
     - 1,322
   * - Total boundary coordinates
     - 7,925,313
   * - Total boundary coordinate values (2 per point)
     - 15,850,626
   * - Average coordinates per boundary polygon
     - 5,994.94
   * - Maximum coordinates in one boundary polygon
     - 192,960
   * - Minimum coordinates in one boundary polygon
     - 3



Hole Polygon Statistics
~~~~~~~~~~~~~~~~~~~~~~~


.. list-table::
   :header-rows: 1
   :widths: 87 13

   * - Hole Metric
     - Value
   * - Total hole polygons
     - 756
   * - Total hole coordinates
     - 262,417
   * - Total hole coordinate values (2 per point)
     - 524,834
   * - Average coordinates per hole polygon
     - 347.11
   * - Maximum coordinates in one hole polygon
     - 24,019
   * - Minimum coordinates in one hole polygon
     - 3
   * - Number of boundary polygons with holes
     - 97
   * - Percentage of boundary polygons with holes
     - 7.34%
   * - Average holes per boundary polygon (with holes)
     - 7.79



Timezone Statistics
~~~~~~~~~~~~~~~~~~~


.. list-table::
   :header-rows: 1
   :widths: 86 14

   * - Timezone Metric
     - Value
   * - Total timezones
     - 444
   * - Average boundary polygons per timezone
     - 2.98
   * - Maximum polygons in one timezone
     - 96
   * - Minimum polygons in one timezone
     - 1
   * - Median polygons per timezone
     - 1



Polygons per Timezone Distribution
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


.. list-table::
   :header-rows: 1
   :widths: 25 26 14 35

   * - Number of Polygons
     - Number of Timezones
     - Percentage
     - Example Timezone
   * - 1 polygon
     - 280
     - 63.06%
     - Africa/Abidjan
   * - 2 polygons
     - 42
     - 9.46%
     - Africa/Cairo
   * - 3 polygons
     - 32
     - 7.21%
     - Africa/Blantyre
   * - 4 polygons
     - 23
     - 5.18%
     - America/Anchorage
   * - 5 polygons
     - 12
     - 2.7%
     - America/Asuncion
   * - 6 polygons
     - 8
     - 1.8%
     - Africa/Ceuta
   * - 7 polygons
     - 6
     - 1.35%
     - America/Adak
   * - 8 polygons
     - 15
     - 3.38%
     - America/Caracas
   * - 9 polygons
     - 4
     - 0.9%
     - America/Bogota
   * - 10 polygons
     - 6
     - 1.35%
     - Europe/Moscow
   * - 11 polygons
     - 2
     - 0.45%
     - Atlantic/South_Georgia
   * - 12 polygons
     - 1
     - 0.23%
     - Pacific/Honolulu
   * - 13 polygons
     - 1
     - 0.23%
     - Etc/GMT-1
   * - 14 polygons
     - 2
     - 0.45%
     - America/Costa_Rica
   * - 18 polygons
     - 1
     - 0.23%
     - Etc/GMT-2
   * - 21 polygons
     - 1
     - 0.23%
     - Asia/Taipei
   * - 22 polygons
     - 1
     - 0.23%
     - Europe/Brussels
   * - 23 polygons
     - 2
     - 0.45%
     - Asia/Pyongyang
   * - 24 polygons
     - 1
     - 0.23%
     - Asia/Tokyo
   * - 25 polygons
     - 1
     - 0.23%
     - Australia/Brisbane
   * - 28 polygons
     - 1
     - 0.23%
     - Europe/Athens
   * - 49 polygons
     - 1
     - 0.23%
     - Pacific/Tahiti
   * - 96 polygons
     - 1
     - 0.23%
     - America/Argentina/Cordoba



Shortcut Mapping Statistics
---------------------------



Shortcut Index Overview
~~~~~~~~~~~~~~~~~~~~~~~


.. list-table::
   :header-rows: 1
   :widths: 82 18

   * - Shortcut Index Metric
     - Value
   * - H3 Resolution
     - 4
   * - Total shortcut entries
     - 288,122
   * - Zone entries (direct lookup)
     - 256,728
   * - Polygon entries (require testing)
     - 31,394
   * - Empty entries
     - 0
   * - Total polygon references
     - 65,214
   * -
     -
   * - H3 cells stored
     - 288,122
   * - H3 cells possible at resolution
     - 288,122
   * - H3 cells missing
     - 0
   * - H3 coverage ratio
     - 1.000
   * -
     -
   * - Unique entry fraction
     - 0.891
   * - Unique surface fraction
     - 0.891
   * - Zone distribution efficiency
     - 0.891
   * - Avg polygons per polygon entry
     - 2.08
   * -
     -
   * - Zone storage (KB)
     - 2256.4
   * - Polygon storage (KB)
     - 372.6
   * - Total estimated storage (KB)
     - 2629.0
   * - Storage compression ratio
     - 0.90x



Shortcut Entry Distributions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

How much work a lookup in one H3 cell costs. A cell covered by a single timezone stores that zone id directly and needs no point-in-polygon test at all; the rest store the candidate polygons a lookup has to test.

No cell needs exactly one test: a single candidate is unambiguous, so it is stored as a direct zone id instead.


.. list-table::
   :header-rows: 1
   :widths: 33 16 15 20 16

   * - Polygons to test
     - Frequency
     - Relative
     - Accumulated
     - Remaining
   * - none (unique zone)
     - 256728
     - 89.1%
     - 89.1%
     - 10.9%
   * - 2
     - 29372
     - 10.19%
     - 99.3%
     - 0.7%
   * - 3
     - 1838
     - 0.64%
     - 99.94%
     - 0.06%
   * - 4
     - 135
     - 0.05%
     - 99.98%
     - 0.02%
   * - 5
     - 24
     - 0.01%
     - 99.99%
     - 0.01%
   * - 6
     - 10
     - 0.0%
     - 99.99%
     - 0.01%
   * - 7
     - 4
     - 0.0%
     - 100.0%
     - 0.0%
   * - 9
     - 1
     - 0.0%
     - 100.0%
     - 0.0%
   * - 10
     - 2
     - 0.0%
     - 100.0%
     - 0.0%
   * - 13
     - 3
     - 0.0%
     - 100.0%
     - 0.0%
   * - 16
     - 1
     - 0.0%
     - 100.0%
     - 0.0%
   * - 17
     - 1
     - 0.0%
     - 100.0%
     - 0.0%
   * - 25
     - 1
     - 0.0%
     - 100.0%
     - 0.0%
   * - 31
     - 1
     - 0.0%
     - 100.0%
     - 0.0%
   * - 51
     - 1
     - 0.0%
     - 100.0%
     - 0.0%


.. list-table::
   :header-rows: 1
   :widths: 31 17 15 20 17

   * - Timezones in cell
     - Frequency
     - Relative
     - Accumulated
     - Remaining
   * - 1
     - 256728
     - 89.1%
     - 89.1%
     - 10.9%
   * - 2
     - 29645
     - 10.29%
     - 99.39%
     - 0.61%
   * - 3
     - 1657
     - 0.58%
     - 99.97%
     - 0.03%
   * - 4
     - 75
     - 0.03%
     - 99.99%
     - 0.01%
   * - 5
     - 13
     - 0.0%
     - 100.0%
     - 0.0%
   * - 6
     - 3
     - 0.0%
     - 100.0%
     - 0.0%
   * - 25
     - 1
     - 0.0%
     - 100.0%
     - 0.0%



Binary File Sizes
-----------------


.. list-table::
   :header-rows: 1
   :widths: 53 22 25

   * - File Type
     - Size (MB)
     - Percentage
   * - boundary polygon data
     - 60.49
     - 98.79%
   * - hole polygon data
     - 0.16
     - 0.26%
   * - shortcut index
     - 0.58
     - 0.95%
   * - Total
     - 61.23
     - 100.00%
