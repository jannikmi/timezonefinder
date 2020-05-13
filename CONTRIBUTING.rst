=======================
Contribution Guidelines
=======================

Contributions are welcome, and they are greatly appreciated! Every little bit
helps, and credit will always be given.

You can contribute in many ways:

Types of Contributions
----------------------

Report Bugs
~~~~~~~~~~~

Report bugs via `Github Issues`_.

If you are reporting a bug, please include:

* Your version of this package, python and Numba (if you use it)
* Any other details about your local setup that might be helpful in troubleshooting, e.g. operating system.
* Detailed steps to reproduce the bug.
* Detailed description of the bug (error log etc.).


Fix Bugs
~~~~~~~~

Look through the GitHub issues for bugs. Anything tagged with "bug" is open to whoever wants to implement it.

Implement Features
~~~~~~~~~~~~~~~~~~

Look through the GitHub issues for features. Anything tagged with "help wanted"
and not assigned to anyone is open to whoever wants to implement it - please
leave a comment to say you have started working on it, and open a pull request
as soon as you have something working, so that Travis starts building it.

Issues without "help wanted" generally already have some code ready in the
background (maybe it's not yet open source), but you can still contribute to
them by saying how you'd find the fix useful, linking to known prior art, or
other such help.

Write Documentation
~~~~~~~~~~~~~~~~~~~

Probably for some features the documentation is missing or unclear. You can help with that!


Submit Feedback
~~~~~~~~~~~~~~~

The best way to send feedback is to file an issue via `Github Issues`_.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement. Create multiple issues if necessary.
* Remember that this is a volunteer-driven project, and that contributions  are welcome :)


Get Started!
------------

Ready to contribute? Here's how to set up this package for local development.

*  Fork this repo on GitHub.
*  Clone your fork locally

* To make changes, create a branch for local development:

   .. code-block:: sh

       $ git checkout -b name-of-your-bugfix-or-feature



* Check out the instructions and notes in ``publish.py``
* Install ``tox`` and run the tests:

   .. code-block:: sh

       $ pip install tox
       $ tox

   The ``tox.ini`` file defines a large number of test environments, for
   different Python etc., plus for checking codestyle. During
   development of a feature/fix, you'll probably want to run just one plus the
   relevant codestyle:

   .. code-block:: sh

       $ tox -e codestyle


* Commit your changes and push your branch to GitHub:

   .. code-block:: sh

       $ git add .
       $ git commit -m "Your detailed description of your changes."
       $ git push origin name-of-your-bugfix-or-feature

* Submit a pull request through the GitHub website. This will trigger the Travis CI build which runs the tests against all supported versions of Python.



.. _Github Issues: https://github.com/MrMinimal64/timezonefinder/issues
