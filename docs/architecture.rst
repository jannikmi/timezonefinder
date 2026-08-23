.. _architecture:

============
Architecture
============

``timezonefinder`` answers one question - *which IANA timezone contains this coordinate?* - and is
built around one trade-off: **the polygon data is never simplified.** Border accuracy is the
product; everything else in this document exists to make that affordable.

This page describes how the lookup works, what was deliberately not built, and how the test suite
defends the guarantees rather than only the behaviour. For the binary layouts see
:doc:`data_format`; for the measured numbers see :doc:`7_performance`.


The lookup pipeline
-------------------

A single ``timezone_at()`` call runs this sequence:

1. **Validate and scale.** Longitude and latitude are validated, then multiplied by 10\ :sup:`7` and
   truncated to ``int32``. The polygon data is stored the same way, so the whole geometric path is
   integer arithmetic - no floating point, and no conversion per candidate polygon.
2. **H3 shortcut.** The cell id's own bits index a precomputed table - one ``int16`` per H3 cell at
   resolution 3 (~41k cells worldwide), with no keys stored and no search. If every polygon
   intersecting that cell belongs to one timezone, the table holds the zone id and the answer is
   returned immediately, with no geometry touched at all. This is the majority case and it is why
   the package is fast despite carrying full-resolution polygons.
3. **Candidate list.** Otherwise the table names the list of polygons that intersect the cell - a
   handful, out of the thousand-odd the dataset contains. Their zone ids are fetched, and the scan
   stops at the last zone change: once no *other* zone can still be matched, the remaining polygons
   need not be tested. Where that is depends only on the candidate list, so it is precomputed and
   stored beside it rather than derived per query.
4. **Bounding-box rejection.** Each candidate's precomputed bbox is checked first, which rejects most
   of them for the cost of four integer comparisons.
5. **Holes before the outer ring.** Holes are far smaller than the boundary they sit in, so testing
   them first is cheaper and can reject the polygon outright. Only then is the outer ring
   ray-cast.

Two consequences worth knowing:

- Because the dataset includes **ocean zones** (``Etc/GMT±XX``), every coordinate on earth matches
  some timezone. ``timezone_at()`` therefore effectively never returns ``None``; use
  ``timezone_at_land()`` when you need to distinguish land from sea. (The polygons include
  territorial waters, so a land match does not mean dry land - see :doc:`data_format`.)
- The final candidate is returned **without** a point-in-polygon check. If every other zone has been
  excluded and some zone must match, testing the last one can only confirm what is already known.


Module map
----------

Most modules are self-describing. The ones that carry the design:

``timezonefinder.py``
    The two finder classes and the lookup above. ``AbstractTimezoneFinder`` holds what both tiers
    share; ``TimezoneFinder`` and ``TimezoneFinderL`` differ in how far they are willing to go for
    an answer.

``configs.py``
    Central types and runtime constants - coordinate scaling, the H3 resolution, FlatBuffers layout.
    Declared once here so the runtime and the data converter cannot drift apart.

``utils.py`` / ``utils_numba.py`` / ``utils_clang.py``
    Polygon math and the acceleration backends. ``utils.py`` binds the point-in-polygon
    implementation **at import time** (see below).

``polygon_array.py``
    Bounding boxes and point-in-polygon over the packaged polygon data, for boundaries and holes
    alike.

``coord_accessors.py``
    The one place that knows whether coordinates are memory-mapped or resident. Swapping the two
    memory modes is swapping the accessor.

``flatbuf/``
    Readers and writers for the FlatBuffers coordinate and shortcut files, plus the ``flatc``\
    -generated bindings. The only generated code in the package.

``global_functions.py`` / ``command_line.py``
    Convenience wrappers for one-off use. They are *not* thread-safe - concurrent workloads should
    build a per-thread ``TimezoneFinder(in_memory=True)``.


Three point-in-polygon backends, chosen once
--------------------------------------------

The ray-casting inner loop exists in three forms:

- **clang C extension** - compiled by ``cffi`` at install time if a compiler is available.
- **Numba JIT** - the Python implementation, compiled on first use when the optional ``numba``
  dependency is installed. Preferred over the C extension when both are present.
- **pure Python** - the same source, uncompiled. Roughly **400x slower** than the alternatives, and
  correct.

``utils.py`` picks one of them at **import time**, not per call. That has two implications that
surface throughout this documentation:

- The three are entirely separate code paths, so **their timings are not comparable** and must never
  share a benchmark name. CI tracks one configuration (clang, no Numba - what a plain
  ``pip install timezonefinder`` gives you) and *asserts* the active path rather than assuming it;
  see :doc:`benchmarking_methodology`.
- The fallback contract is *correct but slower, never broken*. If the C extension fails to compile
  and Numba is absent, the package still works. Ask which path is live with
  ``TimezoneFinder.using_clang_pip()`` and ``TimezoneFinder.using_numba()``.


Two accuracy tiers, two memory modes
------------------------------------

These are independent choices, and both are about what a deployment can afford.

**Accuracy tier.** ``TimezoneFinder`` runs the full pipeline: shortcut, then geometry when the
shortcut is ambiguous. ``TimezoneFinderL`` consults *only* the shortcut index and gives up when the
cell is ambiguous - no polygon data is loaded at all. It is right when an approximate answer near a
border is acceptable and the footprint is not.

**Memory mode.** By default the coordinate data is **memory-mapped**: only the pages a lookup
actually touches become resident, and the kernel can reclaim them under pressure. Passing
``in_memory=True`` reads everything up front, which is faster but holds an order of magnitude more
on the heap. The measured figures are in :doc:`benchmark_results_memory`; the speed they buy is in
:doc:`benchmark_results_timezonefinding`.

The mapped mode is not a curiosity to be optimised away later - it is what keeps the package viable
in a memory-constrained container, and any change that makes the library hold data it previously
mapped is a regression whether or not a timing moves.


Tests that protect guarantees, not behaviour
--------------------------------------------

Most of the suite is ordinary regression testing. A handful of tests exist for a different reason:
each one enforces an invariant that had **no failure mode at all** before it was written. They are
listed together here because as separate files they read as unrelated, and as a category they read
as a practice.

``tests/test_mypy_config.py``
    Keeps mypy's ``ignore_errors`` list restricted to generated code. ``ignore_errors = true``
    silences *every* type error in the modules it names, so the cheapest way to make a real error go
    away is to append the offending module to that list - and nothing would fail. Silencing a module
    is now a reviewed decision rather than a one-line edit.

``tests/test_benchmark_workflows.py``
    Parses both benchmark workflow YAMLs and asserts that the constants they duplicate actually
    agree. Workflows cannot import from each other, so those literals were held together only by a
    "must match" comment; a one-sided edit would have made the comparison job download an artifact
    that no longer existed and compare against nothing, silently.

``tests/test_benchmark_names.py`` / ``tests/test_memory_metric_names.py``
    Pin the exact set of benchmark node ids and memory metric names. These are the join keys of the
    trend charts: a rename does not move a metric's history, it starts a new empty one beside the
    orphaned old chart. Renaming is still allowed - it just cannot happen by accident.

``test_declared_slots_are_assigned`` (``tests/test_resource_management.py``)
    Asserts that every declared ``__slots__`` entry is actually assigned by some finder. Four
    leftovers had survived a refactor, and an unassigned slot is worse than dead code: it re-permits
    the very attribute ``__slots__`` exists to forbid, punching a hole in the guarantee while
    looking like it enforces it.

``tests/test_package_contents.py``
    Builds both distributions and asserts that no unwanted file is in either - which passes just as
    readily when a pattern matches nothing at all, as ``.github`` (lacking the trailing slash a
    directory pattern needs) and ``Agents.*`` (after the file became ``AGENTS.md``) each did. Two
    tests now hold that pattern list and ``MANIFEST.in`` to each other: one fails on a pattern
    naming no path in the checkout, the other on an exclusion that no pattern covers. They are two
    hand-written statements of one intent, and had drifted in both directions.

Two further layers sit beside those invariants.

**Property-based tests.** ``tests/test_property_validation.py`` and ``tests/test_property_api.py``
drive coordinate validation and the public lookup API with ``hypothesis``. The input space is two
floats with hard bounds, which is exactly the shape fuzzing is good at: the interesting cases are the
bounds themselves, the region just outside them, and ``NaN``/``Inf`` - all of which an example-based
test only covers where somebody thought to write the example down. The properties asserted are
invariants rather than values (a returned zone name is always one of the known names, a rejected
coordinate always raises rather than returning something plausible), so they hold across a data
update that changes every individual answer.

The generator these tests draw from is uniform in *latitude*, which oversamples the poles by roughly
2.5x. That bias is deliberate and it is why the same sampler must not be used for benchmarks - see
:doc:`benchmarking_methodology`, where the opposite choice is made and justified. Correctness tests
want more edge cases per draw; a benchmark wants the query mix a real caller has.

**The matrix.** ``tox.ini`` runs four Python versions against three configurations - plain, ``numba``
and ``pytz`` - plus separate ``slow`` and ``docs`` environments. It is a matrix rather than a single
run because of the import-time binding above: the acceleration paths are separate code paths, so
"the tests pass" is a statement about one configuration and says nothing about the other two. The
``pytz`` axis checks a different kind of claim - that every zone name the packaged data can return is
one ``pytz`` actually knows - which a data update can break without a line of this package's code
changing.

The shared shape: a rule that a reviewer would have to remember becomes a test that fails.


How it ships
------------

Packaging is where the "correct but slower, never broken" contract above is actually kept, so it is
part of the design rather than an afterthought. The operational side - how to cut a release - is in
`CONTRIBUTING.md <https://github.com/jannikmi/timezonefinder/blob/master/CONTRIBUTING.md>`__ and the
``Makefile``; this section is the *why*.

**One wheel per target, not one per Python version.** The C extension is built once against the
stable ABI (``py_limited_api``, ``cp311``), so a single wheel serves every later interpreter instead
of the build matrix growing a row per Python release. The saving is only real if the claim is true,
which is why every wheel goes through ``abi3audit --strict`` in the repair step: a wheel that
*declares* abi3 and links something version-specific installs happily and crashes at runtime on an
interpreter no CI job ever ran.

**Three libc targets.** manylinux2014, manylinux_2_28 and musllinux are built separately, so an
Alpine container and an old glibc host both get the compiled path rather than the ~400x pure-Python
fallback. Platforms without a published wheel install from the sdist and compile locally; if that
fails, ``fallible_build_ext`` in ``setup.py`` swallows the error and the install still succeeds -
slower, never broken.

**The end-to-end job is the interesting one.** It installs the *built wheel* on four Python versions
and asserts both a known lookup result and ``clang_extension_loaded``. A smoke test that only checked
``import timezonefinder`` would pass on a wheel whose extension had silently failed to build, which
is the one failure this package must not ship quietly - it would degrade to the pure-Python path
without a single red check. It doubles as the proof that the abi3 claim holds, since one cp311 wheel
is what all four interpreters install.

**Two distributions, one repository.** The boundary data ships as ``timezonefinder-data``, a
separate distribution built from the same checkout. Every release used to carry the whole ~65 MB
dataset in three platform wheels plus an sdist to distinguish a 3 KB ``.so``, which had already
exhausted the PyPI project quota once - and it coupled the two things that change on entirely
different cadences, so a dataset could only be pinned by pinning an old ``timezonefinder`` and
forfeiting every code fix since. The dependency is hard, so ``pip install timezonefinder`` behaves
as it always did.

What the split needs to stay honest is a version that carries *two* facts. An upstream release is
the frequent driver; a change to the binary format is the other, and that one breaks in both
directions at once, since the writer lives in ``scripts/`` and the reader in
``timezonefinder/flatbuf/io/``. So the data version reads ``<format>.<year>.<letter>`` -
``2.2026.3`` is format generation 2 built from release ``2026c`` - and ``timezonefinder`` requires
``timezonefinder-data>=…,<N+1``. No ceiling on the data axis, so an ordinary update still needs no
code release; a hard one on the format axis, so old code paired with a new format is refused by the
resolver rather than at the first lookup. The in-file identifier and ``layout_version`` markers stay
regardless: a ``bin_file_location`` directory has no distribution metadata to read, and only a
per-file marker catches a *mixed* directory.

**What the artifacts contain is asserted, not assumed.** ``tests/test_package_contents.py`` builds
every artefact each distribution publishes and checks them from both ends: every file the package
needs at runtime is in them, and nothing that should have stayed in the repository - the CI
configuration, ``docs/``, ``scripts/``, the agent instruction files - came along. The asymmetry is
why the second half is worth automating: a missing data file fails on first use and gets reported,
an extra one ships quietly. Since the split it also asserts that neither distribution carries the
other's payload, which is the difference between a layout convention and something that can fail.
That guard is easy to disarm by accident, so it is guarded in turn - see *Tests that protect
guarantees, not behaviour* above.

**A code release cannot outrun the data it declares.** The two distributions are versioned and
published independently, so on a data format change the order is fixed: the data first, then the
code requiring it. Backwards, the wheel is uninstallable until the data lands, and PyPI never
accepts a version number twice - the fix is a whole new release. The release job therefore reads
the data requirement out of the wheel it is about to publish and asks the index whether any released,
non-yanked version satisfies it, refusing to go on if none does. Reading the wheel rather than
``pyproject.toml`` is deliberate: the wheel is the artefact a resolver will read. The check runs
ahead of the GitHub Release rather than next to the PyPI upload, because that Release is the first
step of the two that cannot be taken back - and the upload job depends on this one, so one placement
covers both.

**A tag pushed from a non-master branch aborts the release.** Tags can be pushed from anywhere, so
the release job verifies that the tagged commit is contained in ``origin/master`` before publishing
rather than trusting the ref it was handed.

**The test matrix runs once per release, on master.** The tox matrix is the whole critical path -
four jobs of six to ten minutes each, against under a minute for every wheel, sdist and end-to-end
job put together - so running it on the master push *and* again on the tag that names the same
commit doubled the only expensive thing in the pipeline. It now runs on the master push and is
skipped on tag refs, and the release job publishes only from a tag: master tests, the tag releases.
That also removed a race the release procedure had to work around, since the release action is
handed a ``tag:`` and so master's own run used to create the tag itself, before the maintainer
could push it.

What makes skipping it sound is a check rather than an assumption. The ancestry check above proves
the tagged commit is on master; it does not prove the commit was ever green, since a commit can sit
on master with a red run or with none. So the release job asks the API whether a successful
``build`` run exists for that exact SHA on master, and refuses to go on if none does - one API call
standing in for ten minutes of matrix, ahead of the first irreversible step. The cost is that a tag
pushed before master's run finishes fails the release job instead of publishing; nothing is lost,
because the job can be re-run once master is green.

**The data pipeline releases itself.** A weekly workflow compares ``DATA_VERSION`` against the latest
timezone-boundary-builder release, regenerates the data and opens a pull request; when that pull
request's CI passes, a second workflow merges it and pushes a ``data-v*`` tag, which publishes
``timezonefinder-data`` and nothing else. That the two streams cannot block each other is the point:
a data update once had to wait for whatever code work sat unreleased, because it *was* a patch
release of ``timezonefinder`` and would have shipped that work under release notes describing only
the data. Now it releases a distribution containing no code, so the question does not arise.

The two namespaces share a branch, so what keeps them apart is enforced rather than conventional:
``build.yml`` excludes ``data-v*`` at its trigger, and again on the job that creates the GitHub
Release, because the ``release: types: [published]`` trigger consults no tag filter. Both
streams publish by PyPI Trusted Publishing rather than with a token: PyPI trusts one workflow file
per project, each gated on its own deployment environment, so neither holds a credential that could
upload the other's distribution and neither holds one that could leak. The tag is pushed with a GitHub App token because
a tag pushed with the default ``GITHUB_TOKEN`` does not trigger downstream workflows - the release
would be tagged and never built. The run reads ``master`` before the merge and checks the squash
commit's first parent against it afterwards, so a push that landed in between withholds the tag
rather than the merge, since the tag is what publishes. On failed CI or a ``master`` that moved
mid-merge, nothing is published: the pull request is labelled ``automation-failed`` and left for a
human, with one comment naming which of those happened. The merge is the one step that cannot be
undone, so a failure after it - a rejected tag push, say - is reported as its own cause: master
carries the new data, nothing was published, and only a tag pushed by hand still releases it.


Non-goals and deliberate ceilings
---------------------------------

What was **not** built matters as much as what was.

**~1.1 cm coordinate resolution is a chosen ceiling, not a defect.** Coordinates are scaled by
10\ :sup:`7` into ``int32``, which bounds the worst-case error at roughly 1 cm at the equator. That
is already far below the precision of the underlying boundary data, which is digitised from
OpenStreetMap. Spending 64-bit floats to represent uncertainty the source does not have would cost
memory and speed for no accuracy.

**No geometry simplification, ever.** This is the one line that is not negotiable, because it is the
entire reason to choose this package over a faster one. See :doc:`alternatives` for who should
choose otherwise.

**No general-purpose geometry.** The spatial code exists only in service of timezone lookup. There
is no polygon algebra, no reprojection, no spatial join. ``get_geometry()`` hands back the shapes
for callers who want them, and that is the extent of it.

**Sub-millisecond startup is not a goal.** ``TimezoneFinderL`` and the mapped mode exist for
processes that cannot afford construction cost; the full finder is built once and reused. The
package optimises steady-state lookup throughput, not process startup.

**Overlapping polygons are not resolved.** The upstream dataset contains coordinates claimed by more
than one timezone. The first match is returned rather than a set - supporting multiplicity would
change the return type of the entire public API for a rare case that has no obviously correct
answer.

**Correctness does not depend on optional dependencies.** Numba and a C compiler make the package
fast. Neither makes it right, and neither may become required.
