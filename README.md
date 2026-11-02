# timezonefinder

<p align="center">
  <a href="https://timezonefinder.readthedocs.io/en/latest/"><img src="https://raw.githubusercontent.com/jannikmi/timezonefinder/master/docs/hero_banner.jpeg" alt="Coordinate to IANA timezone lookup"></a>
</p>

**Python package for offline timezone lookup of WGS84 coordinates, with no polygon simplification - so the answer stays correct at timezone borders.**

<!-- The badges are duplicated in docs/badges.rst, which the docs include and which stays reStructuredText: an include does not render on PyPI, so sync the two by hand. -->

[![build status](https://github.com/jannikmi/timezonefinder/actions/workflows/build.yml/badge.svg?branch=master)](https://github.com/jannikmi/timezonefinder/actions?query=branch%3Amaster)
[![documentation status](https://readthedocs.org/projects/timezonefinder/badge/?version=latest)](https://timezonefinder.readthedocs.io/en/latest/?badge=latest)
[![wheel](https://img.shields.io/pypi/wheel/timezonefinder.svg)](https://pypi.python.org/pypi/timezonefinder)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![total PyPI downloads](https://pepy.tech/badge/timezonefinder)](https://pepy.tech/project/timezonefinder)
[![monthly PyPI downloads](https://img.shields.io/pypi/dm/timezonefinder.svg)](https://pypistats.org/packages/timezonefinder)
[![latest version on PyPI](https://img.shields.io/pypi/v/timezonefinder.svg)](https://pypi.python.org/pypi/timezonefinder)
[![latest version on conda-forge](https://img.shields.io/conda/vn/conda-forge/timezonefinder.svg)](https://anaconda.org/conda-forge/timezonefinder)
[![supported python versions](https://img.shields.io/pypi/pyversions/timezonefinder.svg)](https://pypi.python.org/pypi/timezonefinder)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23579731.svg)](https://doi.org/10.5281/zenodo.23579731)
[![linted and formatted with ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Compared with the [alternatives](https://timezonefinder.readthedocs.io/en/latest/alternatives.html), it puts accuracy at timezone borders first while keeping lookups fast, and it runs with or without a C compiler.


## Quick Guide

```console
pip install timezonefinder
```

This builds a small C extension for the point-in-polygon test.
Without a compiler, install the [Numba](https://numba.pydata.org/) extra instead (`pip install timezonefinder[numba]`).
Free-threaded Python builds are supported: the GIL stays disabled, so lookups run on all threads at once ([concurrency](https://timezonefinder.readthedocs.io/en/latest/1_usage.html#global-functions)).

The boundary data comes as the separate `timezonefinder-data` package, so new datasets ship without a code release.
A dataset update can change results, so pin a [version](https://pypi.org/project/timezonefinder-data/#history) (`pip install timezonefinder "timezonefinder-data==<version>"`) when results must stay reproducible; see [result stability](https://timezonefinder.readthedocs.io/en/latest/result_stability.html).

```python
from timezonefinder import timezone_at

tz = timezone_at(lng=13.358, lat=52.5061)  # 'Europe/Berlin'

# For many lookups, reuse one instance (the context manager frees its data):
from timezonefinder import TimezoneFinder

with TimezoneFinder(in_memory=True) as tf:
    tz = tf.timezone_at(lng=13.358, lat=52.5061)  # 'Europe/Berlin'

    # Batch lookups take one array per axis:
    names = tf.timezone_names_at(lngs=[13.358, 2.3522], lats=[52.5061, 48.8566])
    # ['Europe/Berlin', 'Europe/Paris']
```

The full dataset with over 400 timezone names is used by default.
A smaller "timezones-now" dataset is available via `update_data.sh` ([details](https://timezonefinder.readthedocs.io/en/latest/data_format.html#alternative-dataset-options)).


## How it works

A lookup first finds the point's cell in a precomputed grid index.
Most cells lie inside a single timezone, so the index answers directly without touching any geometry.
Only where zones meet does the lookup run an exact point-in-polygon test against the few zones listed for that cell, on coordinates stored to about 1 cm.
The [architecture](https://timezonefinder.readthedocs.io/en/latest/architecture.html) page walks through the full pipeline, and [data format](https://timezonefinder.readthedocs.io/en/latest/data_format.html) documents the index and the binary layouts.

**The boundary polygons are never simplified**, so border accuracy is limited only by the source dataset; the grid index is what keeps full-resolution geometry fast.
[Why no simplification](https://timezonefinder.readthedocs.io/en/latest/why_no_simplification.html) explains the trade-off.

The dataset includes ocean zones, so every coordinate on earth gets a timezone - use `timezone_at_land()` to tell land from sea.
Where zones overlap, `timezone_at()` returns the smaller one and `timezones_at()` returns all of them.


## Performance

**Hundreds of thousands of lookups per second on a single core** for uniformly random query points.
The exact figure depends on the backend, the machine and the dataset version, so it lives in the benchmark reports, each stating the configuration it was measured in.

The point-in-polygon test has three backends - the C extension, Numba and pure Python - and all of them return identical answers: a missing compiler costs speed, never results.
The [acceleration path comparison](https://timezonefinder.readthedocs.io/en/latest/benchmark_results_acceleration_paths.html) measures which one is fastest.

**Low memory by default.** The boundary coordinates are memory-mapped, so only the pages a lookup reads become resident and the operating system can reclaim them under pressure.
`TimezoneFinder(in_memory=True)` trades memory for speed; the [memory report](https://timezonefinder.readthedocs.io/en/latest/benchmark_results_memory.html) measures both modes.

* [benchmark trend chart](https://jannikmi.github.io/timezonefinder/dev/bench/) - appended to on every push to `master`
* [benchmark reports](https://timezonefinder.readthedocs.io/en/latest/7_performance.html) - lookup, point-in-polygon, initialization and memory
* [benchmarking methodology](https://timezonefinder.readthedocs.io/en/latest/benchmarking_methodology.html) - how these numbers are produced and what they can and cannot tell you


## Engineering notes

* [Architecture](https://timezonefinder.readthedocs.io/en/latest/architecture.html) - the lookup pipeline, the acceleration backends, and the ceilings this package deliberately does not exceed
* [Data Format](https://timezonefinder.readthedocs.io/en/latest/data_format.html) - binary layouts, coordinate scaling and the shortcut index
* [Testing philosophy](https://timezonefinder.readthedocs.io/en/latest/architecture.html#tests-that-protect-guarantees-not-behaviour) - the tests that exist because a rule needed a failure mode, plus the property-based suite and the version/backend matrix
* [How it ships](https://timezonefinder.readthedocs.io/en/latest/architecture.html#how-it-ships) - abi3 wheels, three libc targets, and the checks that stop a broken wheel reaching PyPI
* [Result stability](https://timezonefinder.readthedocs.io/en/latest/result_stability.html) - which answers a dataset or code update can change, and which it cannot
* [Alternatives](https://timezonefinder.readthedocs.io/en/latest/alternatives.html) - the trade-offs against [tzfpy](https://github.com/ringsaturn/tzfpy), a faster Rust-based package, and when to choose it instead
* [Changelog](https://github.com/jannikmi/timezonefinder/blob/master/CHANGELOG.rst)


## Used by

GitHub's [dependency graph](https://github.com/jannikmi/timezonefinder/network/dependents) lists thousands of repositories and hundreds of published packages that depend on `timezonefinder`, among them:

* industry: Google's [data-science-on-gcp](https://github.com/GoogleCloudPlatform/data-science-on-gcp), Posit's [Shiny for Python](https://github.com/posit-dev/py-shiny)
* research and government: CERN's [CAiMIRA](https://gitlab.cern.ch/caimira/caimira), Sandia National Laboratories' [pvOps](https://github.com/sandialabs/pvOps), the National Laboratory of the Rockies' (formerly NREL) [HOPP](https://github.com/NatLabRockies/HOPP), the US EPA's [sensortoolkit](https://github.com/USEPA/sensortoolkit), NOAA's [monetio](https://github.com/noaa-oar-arl/monetio), NASA JPL OPERA's [next_pass](https://github.com/OPERA-Cal-Val/next_pass)
* open source: [LibrePhotos](https://github.com/LibrePhotos/librephotos), [RocketPy](https://github.com/RocketPy-Team/RocketPy), Bellingcat's [ShadowFinder](https://github.com/bellingcat/ShadowFinder), Catalyst Cooperative's [PUDL](https://github.com/catalyst-cooperative/pudl)


## Contributing

**Looking for maintainers. Reach out if you want to contribute!**

[CONTRIBUTING.md](https://github.com/jannikmi/timezonefinder/blob/master/CONTRIBUTING.md) is the entrypoint for human and AI coding-agent contributors alike.
Its routing table sends each task to the few files under `contributing/` it needs: coding and testing rules, the development and CI workflow, the benchmarking gates, step-by-step workflows for releases, reviews and improvement passes, and the recorded design decisions.


## References

* [Documentation](https://timezonefinder.readthedocs.io/en/latest/)
* [PyPI](https://pypi.python.org/pypi/timezonefinder/)
* [conda-forge feedstock](https://github.com/conda-forge/timezonefinder-feedstock)
* [download stats](https://pepy.tech/project/timezonefinder)
* [online GUI and API](https://timezonefinder.michelfe.it)
* [GUI repository](https://github.com/jannikmi/timezonefinder_gui)
* [ruby port](https://github.com/gunyarakun/timezone_finder)


## Citing

To cite `timezonefinder`, use the DOI [10.5281/zenodo.23579731](https://doi.org/10.5281/zenodo.23579731), which Zenodo resolves to the latest release, or the "Cite this repository" button on GitHub, which reads [`CITATION.cff`](https://github.com/jannikmi/timezonefinder/blob/master/CITATION.cff).


## LICENSE

`timezonefinder` is licensed under the [MIT license](https://github.com/jannikmi/timezonefinder/blob/master/LICENSE).

The data ships in the separate `timezonefinder-data` distribution and is licensed under the [ODbL license](https://github.com/jannikmi/timezonefinder/blob/master/packages/timezonefinder-data/DATA_LICENSE), following the base dataset from [evansiroky/timezone-boundary-builder](https://github.com/evansiroky/timezone-boundary-builder).
