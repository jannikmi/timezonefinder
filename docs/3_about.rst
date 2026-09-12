=====
About
=====

``timezonefinder`` is a python package providing offline timezone lookups for WGS84 coordinates.

:doc:`architecture` walks through the lookup pipeline end to end, the three point-in-polygon backends and the trade-offs that were deliberately *not* taken.
:doc:`data_format` documents the binary layouts it reads, and :doc:`alternatives` compares this package against the other options.


License
-------

``timezonefinder`` is licensed under the `MIT license <https://github.com/jannikmi/timezonefinder/blob/master/LICENSE>`__.

The data ships in the separate ``timezonefinder-data`` distribution and is licensed under the `ODbL license <https://github.com/jannikmi/timezonefinder/blob/master/packages/timezonefinder-data/DATA_LICENSE>`__, following the base dataset from `evansiroky/timezone-boundary-builder <https://github.com/evansiroky/timezone-boundary-builder>`__.
