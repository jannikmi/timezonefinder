.. _data_report:



Data Report
===========

**Timezone Data Version**: 2026d



Data Statistics
---------------


.. list-table::
   :header-rows: 1
   :widths: 79 21

   * - General Metric
     - Value
   * - Total coordinate values (2 per point)
     - 16,505,010



Boundary Polygon Statistics
~~~~~~~~~~~~~~~~~~~~~~~~~~~


.. list-table::
   :header-rows: 1
   :widths: 82 18

   * - Boundary Metric
     - Value
   * - Total boundary polygons
     - 1,355
   * - Total boundary coordinates
     - 7,990,706
   * - Total boundary coordinate values (2 per point)
     - 15,981,412
   * - Average coordinates per boundary polygon
     - 5,897.2
   * - Maximum coordinates in one boundary polygon
     - 193,003
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
     - 791
   * - Total hole coordinates
     - 261,799
   * - Total hole coordinate values (2 per point)
     - 523,598
   * - Average coordinates per hole polygon
     - 330.97
   * - Maximum coordinates in one hole polygon
     - 24,023
   * - Minimum coordinates in one hole polygon
     - 3
   * - Number of boundary polygons with holes
     - 99
   * - Percentage of boundary polygons with holes
     - 7.31%
   * - Average holes per boundary polygon (with holes)
     - 7.99



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
     - 3.05
   * - Maximum polygons in one timezone
     - 95
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
     - 30
     - 6.76%
     - Africa/Blantyre
   * - 4 polygons
     - 23
     - 5.18%
     - America/Anchorage
   * - 5 polygons
     - 13
     - 2.93%
     - America/Asuncion
   * - 6 polygons
     - 7
     - 1.58%
     - Asia/Anadyr
   * - 7 polygons
     - 7
     - 1.58%
     - Africa/Ceuta
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
     - 2
     - 0.45%
     - Asia/Hong_Kong
   * - 14 polygons
     - 1
     - 0.23%
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
   * - 35 polygons
     - 1
     - 0.23%
     - Asia/Shanghai
   * - 49 polygons
     - 1
     - 0.23%
     - Pacific/Tahiti
   * - 95 polygons
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
     - 256,732
   * - Polygon entries (require testing)
     - 31,390
   * - Empty entries
     - 0
   * - Total polygon references
     - 65,241
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
     - 372.7
   * - Total estimated storage (KB)
     - 2629.1
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
     - 256732
     - 89.11%
     - 89.11%
     - 10.89%
   * - 2
     - 29368
     - 10.19%
     - 99.3%
     - 0.7%
   * - 3
     - 1836
     - 0.64%
     - 99.94%
     - 0.06%
   * - 4
     - 135
     - 0.05%
     - 99.98%
     - 0.02%
   * - 5
     - 25
     - 0.01%
     - 99.99%
     - 0.01%
   * - 6
     - 9
     - 0.0%
     - 99.99%
     - 0.01%
   * - 7
     - 5
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
   * - 36
     - 1
     - 0.0%
     - 100.0%
     - 0.0%
   * - 50
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
     - 256732
     - 89.11%
     - 89.11%
     - 10.89%
   * - 2
     - 29641
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
     - 30.50
     - 97.82%
   * - hole polygon data
     - 0.09
     - 0.29%
   * - shortcut index
     - 0.59
     - 1.89%
   * - Total
     - 31.18
     - 100.00%
