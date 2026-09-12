
=====
About
=====


.. include:: ./badges.rst


``timezonefinder`` is a python package for looking up the corresponding timezone for given coordinates on earth entirely offline.

Timezones internally are being represented by polygons and the timezone membership of a given point (= lat lng coordinate pair) is determined by a point in polygon (PIP) check.
In many cases an expensive PIP check can be avoided.

For detailed information about the data format in use, see :doc:`data_format`.

Among other tweaks this index makes ``timezonefinder`` efficient (also check the :ref:`performance chapter <performance>`).

:doc:`architecture` walks through the lookup pipeline end to end, the three point-in-polygon backends and the trade-offs that were deliberately *not* taken.


References
----------

`GitHub <https://github.com/jannikmi/timezonefinder>`__

`PyPI <https://pypi.python.org/pypi/timezonefinder/>`__

`online GUI and API <http://timezonefinder.michelfe.it>`__

`conda-forge feedstock <https://github.com/conda-forge/timezonefinder-feedstock>`__

ruby port: `timezone_finder <https://github.com/gunyarakun/timezone_finder>`__

`download stats <https://pepy.tech/project/timezonefinder>`__


LICENSE
-------

``timezonefinder``  is licensed under the `MIT license <https://github.com/jannikmi/timezonefinder/blob/master/LICENSE>`__.

The data ships in the separate ``timezonefinder-data`` distribution and is licensed under the `ODbL license <https://github.com/jannikmi/timezonefinder/blob/master/packages/timezonefinder-data/DATA_LICENSE>`__, following the base dataset from `evansiroky/timezone-boundary-builder <https://github.com/evansiroky/timezone-boundary-builder>`__.


Alternative python packages
---------------------------

For detailed information about alternative packages and comparisons, see :doc:`alternatives`.


Contact
--------


Tell me if and how your are using this package. This encourages me to develop and test it further.

Most certainly there is stuff I missed, things I could have optimized even further or explained more clearly, etc.
I would be really glad to get some feedback.

If you encounter any bugs, have suggestions etc. do not hesitate to **open an Issue** or **add a Pull Requests** on Git.
Please refer to the :ref:`contribution guidelines <contributing>`
