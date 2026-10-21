# timezonefinder

<p align="center">
  <a href="https://timezonefinder.readthedocs.io/en/latest/"><img src="https://raw.githubusercontent.com/jannikmi/timezonefinder/master/docs/hero_banner.jpeg" alt="Coordinate to IANA timezone lookup"></a>
</p>

**Offline timezone lookup for WGS84 coordinates, with no polygon simplification - so the answer stays correct at timezone borders.**

<!-- The badges are duplicated in docs/badges.rst, which the docs include and which stays reStructuredText: an include does not render on PyPI, so sync the two by hand. -->

[![build status](https://github.com/jannikmi/timezonefinder/actions/workflows/build.yml/badge.svg?branch=master)](https://github.com/jannikmi/timezonefinder/actions?query=branch%3Amaster)
[![documentation status](https://readthedocs.org/projects/timezonefinder/badge/?version=latest)](https://timezonefinder.readthedocs.io/en/latest/?badge=latest)
[![wheel](https://img.shields.io/pypi/wheel/timezonefinder.svg)](https://pypi.python.org/pypi/timezonefinder)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![total PyPI downloads](https://pepy.tech/badge/timezonefinder)](https://pepy.tech/project/timezonefinder)
[![used by thousands of GitHub repositories](https://img.shields.io/badge/used%20by-thousands%20of%20repositories-blue?logo=github)](https://github.com/jannikmi/timezonefinder/network/dependents)
[![latest version on PyPI](https://img.shields.io/pypi/v/timezonefinder.svg)](https://pypi.python.org/pypi/timezonefinder)
[![latest version on conda-forge](https://img.shields.io/conda/vn/conda-forge/timezonefinder.svg)](https://anaconda.org/conda-forge/timezonefinder)
[![supported python versions](https://img.shields.io/pypi/pyversions/timezonefinder.svg)](https://pypi.python.org/pypi/timezonefinder)
[![linted and formatted with ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

In comparison to other alternatives this package aims at maximum accuracy around timezone borders while offering fast lookup performance and compatibility with many (Python) runtime environments.
It combines preprocessed polygon data, grid-based spatial shortcuts, and optional acceleration via Numba or a clang-backed point-in-polygon routine.


## Quick Guide

```console
pip install timezonefinder
```

This compiles a small C extension for the point-in-polygon test.
Where no compiler is available the optional [Numba](https://numba.pydata.org/) extra (`pip install timezonefinder[numba]`) JIT-compiles the same routine instead;
the extension wins wherever it loaded.
The [acceleration path comparison](https://timezonefinder.readthedocs.io/en/latest/benchmark_results_acceleration_paths.html) measures all three against each other and is regenerated with every report;
where it is the kernel, the extra also costs a process more resident memory than the packaged data;
where the extension loaded, it is never even imported.

The timezone boundary data is installed automatically as the separate `timezonefinder-data` distribution, so that a new dataset ships without a new `timezonefinder` release.
Pin it to hold a deployment to one dataset - the [release history](https://pypi.org/project/timezonefinder-data/#history) lists the versions to choose from: `pip install timezonefinder "timezonefinder-data==<version>"`.
A dataset update can change the answer for a coordinate, so pin it when a result has to stay reproducible across deployments - [result stability](https://timezonefinder.readthedocs.io/en/latest/result_stability.html) covers what can change and what cannot.

```python
# use the global function for convenience:
from timezonefinder import timezone_at

tz = timezone_at(lng=13.358, lat=52.5061)  # 'Europe/Berlin'


# For improved performance and control, reuse one instance for the whole job.
# The context manager releases its coordinate data even if the job raises:
from timezonefinder import TimezoneFinder

with TimezoneFinder(in_memory=True) as tf:
    tz = tf.timezone_at(lng=13.358, lat=52.5061)  # 'Europe/Berlin'

    # Many coordinates at once, one array per axis - ids for a caller that maps
    # them itself, names for one that does not:
    lngs = [13.358, 2.3522]
    lats = [52.5061, 48.8566]
    zone_ids = tf.timezone_ids_at(lngs=lngs, lats=lats)
    names = tf.timezone_names_at(lngs=lngs, lats=lats)
    # ['Europe/Berlin', 'Europe/Paris']
```

**Note:** This library uses the full original timezone dataset with all >440 timezone names, providing full localization capabilities and historical timezone accuracy.
For applications that prefer a smaller memory footprint, the reduced "timezones-now" dataset is available via the `update_data.sh` script (cf. [Documentation](https://timezonefinder.readthedocs.io/en/latest/data_format.html#alternative-dataset-options)).


## How it works

A lookup scales the coordinates to 32-bit integers (x 10^7, ~1.1 cm steps),
finds the point's cell in an aligned grid tree - 0.75-degree cells, refining to 0.1875 degrees where several zones meet - by one integer division per axis,
and reads a precomputed shortcut for that cell.
Most cells are covered by a single timezone, so the answer is returned immediately with no geometry touched at all.
Only an ambiguous cell falls through to the polygons it lists: bounding-box rejection first, then a ray-casting point-in-polygon test - holes before the outer ring, since holes are smaller and can reject the polygon outright.

The central trade-off: **the boundary polygons are never simplified**, so border accuracy is limited only by the source dataset.
The shortcut index is what makes carrying full-resolution geometry affordable.

Since the dataset includes ocean zones, every coordinate on earth matches some timezone - use `timezone_at_land()` when you need to tell land from sea.

The dataset also contains genuinely overlapping zones, so a coordinate can match *more than one* - `timezone_at()` picks the smaller one, and `timezones_at()` returns all of them.


## Performance

**Hundreds of thousands of lookups per second on a single core** for uniformly random query points.
The exact figure depends on the acceleration backend, the machine and the dataset version, so the benchmark reports below carry it - each states the configuration it was measured in - rather than this page, which would go stale.

The point-in-polygon routine has three interchangeable backends, selected at import time in this order:
a clang-compiled C extension (built automatically when a compiler is available),
Numba JIT compilation (used only where the C extension is unavailable and the optional `numba` dependency is installed),
and pure Python.
All three return identical answers - a missing compiler costs speed, never results.
Which is fastest is measured, not assumed: see the [acceleration path comparison](https://timezonefinder.readthedocs.io/en/latest/benchmark_results_acceleration_paths.html).

* [benchmark trend chart](https://jannikmi.github.io/timezonefinder/dev/bench/) - appended to on every push to `master`
* [benchmark reports](https://timezonefinder.readthedocs.io/en/latest/7_performance.html) - lookup, point-in-polygon, initialization and memory
* [benchmarking methodology](https://timezonefinder.readthedocs.io/en/latest/benchmarking_methodology.html) - how these numbers are produced and what they can and cannot tell you


## Engineering notes

* [Architecture](https://timezonefinder.readthedocs.io/en/latest/architecture.html) - the lookup pipeline, the acceleration backends, and the ceilings this package deliberately does not exceed
* [Data Format](https://timezonefinder.readthedocs.io/en/latest/data_format.html) - binary layouts, coordinate scaling and the shortcut index
* [Benchmarking Methodology](https://timezonefinder.readthedocs.io/en/latest/benchmarking_methodology.html) - the measurement design and where every threshold comes from
* [Testing philosophy](https://timezonefinder.readthedocs.io/en/latest/architecture.html#tests-that-protect-guarantees-not-behaviour) - the tests that exist because a rule needed a failure mode, plus the property-based suite and the version/backend matrix
* [How it ships](https://timezonefinder.readthedocs.io/en/latest/architecture.html#how-it-ships) - abi3 wheels, three libc targets, and the checks that stop a broken wheel reaching PyPI
* [Alternatives](https://timezonefinder.readthedocs.io/en/latest/alternatives.html) - the trade-offs against `tzfpy`, and when to choose it instead
* [Changelog](https://github.com/jannikmi/timezonefinder/blob/master/CHANGELOG.rst)

**Alternative:** Need maximum speed at the cost of accuracy?
Check out [tzfpy](https://github.com/ringsaturn/tzfpy) - a fast and lightweight alternative based on Rust.


## Contributing

**Looking for maintainers. Reach out if you want to contribute!**

Contribution guidelines, the development workflow and the testing/benchmarking gates are documented in [CONTRIBUTING.md](https://github.com/jannikmi/timezonefinder/blob/master/CONTRIBUTING.md).


## References

* [Documentation](https://timezonefinder.readthedocs.io/en/latest/)
* [PyPI](https://pypi.python.org/pypi/timezonefinder/)
* [conda-forge feedstock](https://github.com/conda-forge/timezonefinder-feedstock)
* [download stats](https://pepy.tech/project/timezonefinder)
* [online GUI and API](https://timezonefinder.michelfe.it)
* [GUI repository](https://github.com/jannikmi/timezonefinder_gui)
* [ruby port](https://github.com/gunyarakun/timezone_finder)


## LICENSE

`timezonefinder` is licensed under the [MIT license](https://github.com/jannikmi/timezonefinder/blob/master/LICENSE).

The data ships in the separate `timezonefinder-data` distribution and is licensed under the [ODbL license](https://github.com/jannikmi/timezonefinder/blob/master/packages/timezonefinder-data/DATA_LICENSE), following the base dataset from [evansiroky/timezone-boundary-builder](https://github.com/evansiroky/timezone-boundary-builder).
