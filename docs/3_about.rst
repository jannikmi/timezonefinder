=====
About
=====

``timezonefinder`` is a python package for looking up the corresponding timezone for given coordinates on earth entirely offline.

:doc:`architecture` walks through the lookup pipeline end to end, the three point-in-polygon backends and the trade-offs that were deliberately *not* taken.
:doc:`data_format` documents the binary layouts it reads, and :doc:`alternatives` compares this package against the other options.


LICENSE
-------

``timezonefinder`` is licensed under the `MIT license <https://github.com/jannikmi/timezonefinder/blob/master/LICENSE>`__.

The data ships in the separate ``timezonefinder-data`` distribution and is licensed under the `ODbL license <https://github.com/jannikmi/timezonefinder/blob/master/packages/timezonefinder-data/DATA_LICENSE>`__, following the base dataset from `evansiroky/timezone-boundary-builder <https://github.com/evansiroky/timezone-boundary-builder>`__.


Contact
-------

Tell me if and how you are using this package.
This encourages me to develop and test it further.

Most certainly there is stuff I missed, things I could have optimized even further or explained more clearly, etc.
I would be really glad to get some feedback.

If you encounter any bugs, have suggestions etc. do not hesitate to **open an Issue** or **add a Pull Request** on Git.
Please refer to the :ref:`contribution guidelines <contributing>`.
