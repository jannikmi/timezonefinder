
=====
About
=====


.. include:: ./badges.rst


``timezonefinder`` is a python package for looking up the corresponding timezone for given coordinates on earth entirely offline.

Timezones internally are being represented by polygons and the timezone membership of a given point (= lat lng coordinate pair) is determined by a point in polygon (PIP) check.
In many cases an expensive PIP check can be avoided.

For detailed information about the data format in use, see :doc:`data_format`.

Among other tweaks this index makes ``timezonefinder`` efficient (also check the :ref:`performance chapter <performance>`).


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

The data is licensed under the `ODbL license <https://github.com/jannikmi/timezonefinder/blob/master/DATA_LICENSE>`__, following the base dataset from `evansiroky/timezone-boundary-builder <https://github.com/evansiroky/timezone-boundary-builder>`__.


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


Acknowledgements
----------------

Thanks to:

- `Adam <https://github.com/adamchainz>`__ for adding organisational features to the project and for helping me with publishing and testing routines.
- `ringsaturn <https://github.com/ringsaturn>`__ for valuable feedback, sponsoring this project, creating the ``tzfpy`` package and adding the ``pytz`` compatibility extra
- `theirix  <https://github.com/theirix>`__ for adding support for cibuildwheel
- `snowman2 <https://github.com/snowman2>`__ for creating the conda-forge recipe.
- `synapticarbors <https://github.com/synapticarbors>`__ for fixing Numba import with py27.
- `zedrdave <https://github.com/zedrdave>`__ for valuable feedback.
- `Tyler Huntley <https://github.com/Ty1776>`__ for adding docstrings
- `Greg Meyer <https://github.com/gmmeyer>`__ for updating h3 to >4
- `ARYAN RAJ <https://github.com/nikkhilaaryan>`__ for providing example scripts and updating python version support
- `Romain Girard <https://github.com/romaingd-spi>`__ for fixing unwanted test  content
