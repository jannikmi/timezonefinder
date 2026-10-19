.. _data_report:



Data Report
===========

**Timezone Data Version**: 2026e



Data Statistics
---------------


.. list-table::
   :header-rows: 1
   :widths: 79 21

   * - General Metric
     - Value
   * - Total coordinate values (2 per point)
     - 16,567,350



Boundary Polygon Statistics
~~~~~~~~~~~~~~~~~~~~~~~~~~~


.. list-table::
   :header-rows: 1
   :widths: 82 18

   * - Boundary Metric
     - Value
   * - Total boundary polygons
     - 1,358
   * - Total boundary coordinates
     - 8,021,069
   * - Total boundary coordinate values (2 per point)
     - 16,042,138
   * - Average coordinates per boundary polygon
     - 5,906.53
   * - Maximum coordinates in one boundary polygon
     - 193,006
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
     - 795
   * - Total hole coordinates
     - 262,606
   * - Total hole coordinate values (2 per point)
     - 525,212
   * - Average coordinates per hole polygon
     - 330.32
   * - Maximum coordinates in one hole polygon
     - 24,023
   * - Minimum coordinates in one hole polygon
     - 3
   * - Number of boundary polygons with holes
     - 99
   * - Percentage of boundary polygons with holes
     - 7.29%
   * - Average holes per boundary polygon (with holes)
     - 8.03



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
     - 3.06
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
     - 281
     - 63.29%
     - Africa/Abidjan
   * - 2 polygons
     - 40
     - 9.01%
     - Africa/Cairo
   * - 3 polygons
     - 29
     - 6.53%
     - Africa/Blantyre
   * - 4 polygons
     - 24
     - 5.41%
     - America/Anchorage
   * - 5 polygons
     - 14
     - 3.15%
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
   :widths: 54 46

   * - Shortcut Index Metric
     - Value
   * - Grid
     - 480 root columns, 4x4 blocks
   * - Total shortcut entries
     - 319,275
   * - Zone entries (direct lookup)
     - 253,548
   * - Polygon entries (require testing)
     - 65,727
   * - Empty entries
     - 0
   * - Total polygon references
     - 133,620
   * -
     -
   * - Root cells
     - 115,200
   * - Root cells refined into blocks
     - 13,605
   * - Cells in the tree
     - 319,275
   * - Cells stored
     - 319,275
   * - Cells missing
     - 0
   * - Coverage ratio
     - 1.000
   * -
     -
   * - Unique entry fraction
     - 0.794
   * - Unique surface fraction
     - 0.794
   * - Zone distribution efficiency
     - 0.794
   * - Avg polygons per polygon entry
     - 2.03
   * -
     -
   * - Zone storage (KB)
     - 2228.4
   * - Polygon storage (KB)
     - 774.5
   * - Total estimated storage (KB)
     - 3002.9
   * - Storage compression ratio
     - 0.92x



Shortcut Entry Distributions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

How much work a lookup in one cell costs. A cell covered by a single timezone stores that zone id directly and needs no point-in-polygon test at all; the rest store the candidate polygons a lookup has to test.

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
     - 253548
     - 79.41%
     - 79.41%
     - 20.59%
   * - 2
     - 63848
     - 20.0%
     - 99.41%
     - 0.59%
   * - 3
     - 1780
     - 0.56%
     - 99.97%
     - 0.03%
   * - 4
     - 66
     - 0.02%
     - 99.99%
     - 0.01%
   * - 5
     - 16
     - 0.01%
     - 99.99%
     - 0.01%
   * - 6
     - 2
     - 0.0%
     - 100.0%
     - 0.0%
   * - 7
     - 2
     - 0.0%
     - 100.0%
     - 0.0%
   * - 8
     - 1
     - 0.0%
     - 100.0%
     - 0.0%
   * - 10
     - 2
     - 0.0%
     - 100.0%
     - 0.0%
   * - 12
     - 1
     - 0.0%
     - 100.0%
     - 0.0%
   * - 14
     - 3
     - 0.0%
     - 100.0%
     - 0.0%
   * - 15
     - 1
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
   * - 22
     - 1
     - 0.0%
     - 100.0%
     - 0.0%
   * - 27
     - 1
     - 0.0%
     - 100.0%
     - 0.0%
   * - 35
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
     - 253548
     - 79.41%
     - 79.41%
     - 20.59%
   * - 2
     - 64127
     - 20.09%
     - 99.5%
     - 0.5%
   * - 3
     - 1560
     - 0.49%
     - 99.99%
     - 0.01%
   * - 4
     - 40
     - 0.01%
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
     - 30.61
     - 97.60%
   * - hole polygon data
     - 0.09
     - 0.29%
   * - shortcut index
     - 0.66
     - 2.11%
   * - Total
     - 31.36
     - 100.00%
