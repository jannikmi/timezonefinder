=========
Changelog
=========



X.X.X (unreleased)
------------------

Internal:

* ``timezonefinder`` is now published to PyPI by Trusted Publishing (OIDC) rather than with a long-lived API token, matching how ``timezonefinder-data`` already publishes. The upload job runs in the ``pypi`` deployment environment and exchanges its OIDC identity for a short-lived, project-scoped upload token, so no publishing credential exists in repository secrets to leak or rotate, and each stream's identity is bound to an environment the other does not use. This requires a trusted publisher configured for the ``timezonefinder`` project on PyPI; without it the release upload fails.


8.3.0 (2026-08-19)
------------------

* the dataset version is now exposed at runtime. ``TimezoneFinder().data_version`` (and ``TimezoneFinderL().data_version``) return the timezone-boundary-builder release the packaged data was built from, read from a ``data_version.txt`` stamp that ``scripts/file_converter.py`` writes into the data directory it generates and that ships in the wheel. Previously an installed ``timezonefinder`` could not state it at all: the release tag lived only in a repo-root file that is not packaged. Which release a parse is stamped with comes from the input's filename (``combined-with-oceans-2026c.json``, which ``update_data.sh`` now produces), or from ``scripts/file_converter.py --data-version`` for an input that cannot carry it; your own GeoJSON is stamped ``"unknown"``, and an unpacked release archive that lost its tag is refused rather than compiled into data that could never say where it came from. ``timezonefinder.__version__`` is now exposed as well, read from the installed distribution metadata. Solves issue #498
* fixed a ``BufferError: cannot close exported pointers exist`` raised during resource cleanup in file mode (``in_memory=False``). A coordinate array obtained from ``coords_of()`` is a zero-copy view onto the memory-mapped file, and ``mmap.close()`` refuses to unmap while one is alive, so an array outliving its ``TimezoneFinder`` raised on cleanup. The mapping now stays valid instead of leaving the views dangling, and ``FileCoordAccessor.cleanup()`` releases its own references so the deferred close happens as soon as the last view is dropped. The accessor must not be used after ``cleanup()``
* polygon coordinates are now stored one axis at a time in the packaged ``coordinates.bin`` files - all x values followed by all y values per polygon, instead of interleaved. The point in polygon test scans a single axis per iteration, so contiguous per-axis blocks halve the cache lines it touches: ~1.6x faster on a median polygon and ~2.5x faster on the largest ones via the C extension, 14-25% faster via Numba. The bundled data was regenerated accordingly, and the layout is described in the `data format documentation <https://timezonefinder.readthedocs.io/en/latest/data_format.html>`__
* every packaged FlatBuffers file now carries a file identifier and a layout version, and ``TimezoneFinder`` raises a ``ValueError`` naming the offending file when either does not match - previously such a directory was read without complaint and produced wrong timezones. For ``coordinates.bin`` the version records how the coordinates are encoded and which polygons the file holds. The hybrid shortcut binaries get an identifier that differs per zone id width, because the uint8 and uint16 schemas differ only in the width of a zone id and each parses cleanly as the other; the width is now read from the buffer instead of being guessed from the file name, so a renamed or mispaired shortcut file fails loudly rather than returning wrong zones. If you compile your own data and point ``bin_file_location`` at it, regenerate it once with ``scripts/file_converter.py``, since the coordinate layout, the hole storage, the shortcut container and the file names all changed in this release. The markers track what a file holds rather than the package version, so this is not a per-release obligation. Solves issue #458
* the memory footprint of every finder configuration is now measured and published in a new `memory report <https://timezonefinder.readthedocs.io/en/latest/benchmark_results_memory.html>`__, separating what a configuration allocates (``tracemalloc``) from what it makes resident (RSS, which additionally counts memory-mapped pages). The distinction is the point: the default mode maps the coordinate data instead of reading it, so it allocates an order of magnitude less than the in-memory mode, and only the pages a lookup actually touches become resident. This replaces documentation claiming a 40MB process ceiling and a 41MB data directory, both long out of date
* restructured the two entry points a reader actually arrives at - ``README.rst`` and the `documentation landing page <https://timezonefinder.readthedocs.io/en/latest/>`__ - so both state what the package is and how it works instead of only what it is called. The README opens with the project banner and a one-sentence statement of what the package is for, then the badges, then the quick guide - and adds three short sections that were missing entirely: *How it works* (the lookup pipeline and the no-simplification trade-off), *Performance* (a concrete throughput figure with its configuration named, the three point-in-polygon backends and the pure-Python fallback), and *Engineering notes* linking the architecture, data format and benchmarking methodology pages. The maintainers-wanted notice moves from the first heading after the intro into a new ``Contributing`` section at the bottom, which also links ``CONTRIBUTING.md`` for the first time. The badge block is corrected along the way: the ``code style: black`` badge named a formatter this project has never used and is replaced by ``ruff``, and a supported-Python-versions badge was added. The banner is referenced by absolute URL, since PyPI serves the long description without the repository and a ``docs/…`` path renders as a broken image there. The landing page gains the same *How it works* summary, the no-simplification trade-off and the ocean-zone consequence for ``timezone_at()``, and its flat seventeen-entry table of contents is grouped into *Using it*, *Design*, *Performance* and *Project*, so the sidebar says what kind of project this is rather than listing pages in the order they were written
* rewrote the `package comparison <https://timezonefinder.readthedocs.io/en/latest/alternatives.html>`__ page. It now states its position in prose before the first table - border correctness is what this package optimises for, speed is the constraint that work happens under - and says plainly when ``tzfpy`` is the better choice. Every quantitative cell names what it measures and links its source, and the speed row is deliberately qualitative on both sides, with a note explaining that the two packages have never been benchmarked under one harness. The decision table drops the rows on which the two packages do not differ
* two new documentation pages: `Architecture <https://timezonefinder.readthedocs.io/en/latest/architecture.html>`__ describes the lookup pipeline, the three point-in-polygon backends and the memory modes, and states the ceilings this package deliberately does not exceed - unsimplified geometry, ~1 cm coordinate resolution, no general-purpose spatial code. It also documents how the package is built and shipped, which was previously described nowhere outside the workflow YAML: why one abi3 wheel per target replaces one wheel per Python version and what ``abi3audit`` is guarding, why three libc targets are built, why the end-to-end job installs the built wheel and asserts the C extension loaded rather than merely importing the package, and why a tag pushed from outside ``master`` aborts the release. The testing section gained the property-based suite and the reason the tox matrix is a matrix - the acceleration paths are bound at import time, so a passing run describes one configuration only. Both sections are linked from the README's *Engineering notes*. `Benchmarking Methodology <https://timezonefinder.readthedocs.io/en/latest/benchmarking_methodology.html>`__ documents how the published numbers are produced and what they can and cannot tell you: ``ubuntu-latest`` pins the runner image and not the CPU, which is why a pull request is measured against its own merge base on the same runner and why every alert threshold is derived from measured noise. It was previously addressed only to contributors, in the second half of ``CONTRIBUTING.md``, which now keeps the operational instructions and links to it
* the H3 resolution choice in the `data format documentation <https://timezonefinder.readthedocs.io/en/latest/data_format.html>`__ is no longer asserted to "offer a good balance" but reports the study behind it (``prototypes/single_resolution_bench.py``): resolution 3 keeps the hybrid index at a small fraction of the packaged polygon data, while resolution 4 would exceed 10 % of it for gains that do not justify the increase
* the hand-written documentation no longer restates exact figures that belong to the generated pages - dataset vertex, polygon and hole counts, index and distribution sizes, memory footprints, lookup throughput. Those change with every data update and with code that shifts a footprint, which silently left the copies wrong: the memory figures had already gone stale in four places. The prose now states the magnitude that survives a data update and links `the data report <https://timezonefinder.readthedocs.io/en/latest/data_report.html>`__ or the relevant `benchmark report <https://timezonefinder.readthedocs.io/en/latest/7_performance.html>`__, which are regenerated from the packaged data and are always current
* the three weakest hand-written documentation pages no longer answer a question by pointing at a file the reader has to open. The `performance page <https://timezonefinder.readthedocs.io/en/latest/7_performance.html>`__ now opens with the four benchmark reports and the trend chart instead of a bullet list of adjectives about the binary format, and its C extension and Numba sections are cut to what a user does - which call reports the active backend - with the explanation left to the architecture page that already carried a more precise version of it. *Getting started* lists the four runtime dependencies and what each is for, where it previously said to consult ``pyproject.toml``, which remains linked as the authoritative source for version ranges. The use case pages carry runnable snippets for building an aware ``datetime`` and reading a UTC offset, with the ``examples/`` scripts as the follow-up rather than the whole answer; the snippets use the standard library's ``zoneinfo``, so neither needs an optional dependency
* the shortcut entry distributions in the `data report <https://timezonefinder.readthedocs.io/en/latest/data_report.html>`__ no longer report three quarters of all H3 cells as holding ``0`` polygons, which is impossible for data whose ocean zones cover the globe. Those cells are covered by a single timezone and store its id directly, so a lookup there needs no point-in-polygon test at all - the column is now *Polygons to test* and the row reads *none (unique zone)*. The tables are introduced by a sentence on what they measure, including why no cell ever needs exactly one test
* the hybrid shortcut loader no longer keeps the entire shortcut binary in memory. The polygon id arrays it returns were zero-copy views onto the ~1.5 MB file buffer, so ~47 KB of live data pinned the whole thing for the lifetime of every ``TimezoneFinder`` / ``TimezoneFinderL`` instance. They are now disjoint read-only slices of a single compact array, cutting the shortcut mapping's footprint from ~7.4 MB to ~4.7 MB per instance, and every finder's resident set by ~2 MB, at unchanged initialisation time - which matters most for concurrent workloads, where the recommended one-instance-per-thread pattern multiplied the waste
* the usage examples in ``README.rst`` and the `usage documentation <https://timezonefinder.readthedocs.io/en/latest/1_usage.html>`__ now show the result the packaged data actually returns. Every snippet queries the same Berlin coordinates and annotated the answer as ``'Europe/Paris'``, which is the value from the reduced ``timezones-now`` dataset, where ``Europe/Berlin`` is merged into ``Europe/Paris`` - not from the full dataset the package ships by default. All eleven annotations now read ``'Europe/Berlin'``, verified against the packaged data for each of ``timezone_at()``, ``timezone_at_land()``, ``certain_timezone_at()``, ``unique_timezone_at()`` and ``TimezoneFinderL``, and the ``get_geometry()`` call in the opening example asks for that same zone instead of a different one. ``tests/test_documented_contracts.py`` now re-runs each of those documented lookups, so a data update that moves the example coordinate's zone fails there rather than leaving every snippet on both pages quietly wrong again

* holes that duplicate a timezone boundary polygon are no longer stored twice. Almost every hole is an enclave, cut into the surrounding zone with exactly the ring the upstream data also emits as the enclosed zone's own boundary polygon - the same geometry under two IDs. The packaged hole coordinate file now holds only the rings with no such twin (27 of 756 in the current data), and a new ``holes/poly_ref.npy`` records per hole which boundary polygon to read instead. Hole data drops from ~2.0 MiB to ~0.16 MiB, and ``in_memory=True`` saves the same amount of RAM, since those holes now resolve into the boundary arrays rather than materialising a second copy. Matching is exact - rings are compared as integer coordinates in a canonical form, with bounding boxes used only to narrow the search - so every timezone lookup returns what it did before. One visible consequence: ``get_geometry()`` may hand back a deduplicated hole ring starting at a different vertex or winding the other way than it used to, tracing the same closed path. The encoding is described in the `data format documentation <https://timezonefinder.readthedocs.io/en/latest/data_format.html>`__
* the command line script gained a ``--stdin`` streaming mode: it reads delimited rows from standard input and writes each back out with a ``timezone`` column appended, building the finder once instead of paying full initialisation per coordinate. Which columns hold the coordinates is read off the header by name, or stated with ``--lng-col``/``--lat-col``, and never inferred from their position - a swapped pair is still a valid coordinate for any longitude between -90 and 90, so guessing would answer with a real but wrong timezone instead of failing. Every input row produces exactly one output row, and a row that cannot be used warns on stderr and makes the run exit non-zero rather than ending the stream. Whether the first row is a header is worked out from the row, or stated with ``--header``/``--no-header``. New flags ``-d``/``--delimiter`` and ``--in-memory`` apply to the whole stream. See the `usage documentation <https://timezonefinder.readthedocs.io/en/latest/1_usage.html#looking-up-many-coordinates-at-once>`__. Solves issue #504. Thanks to `weed33834 <https://github.com/weed33834>`__ for the PR #516
* the timezone boundary data now ships as its own distribution, ``timezonefinder-data``. ``pip install timezonefinder`` is unchanged - it is a hard dependency and is installed automatically - but the dataset can now be pinned on its own (``pip install timezonefinder "timezonefinder-data==1.2026.3"``), where previously holding a dataset meant pinning an old ``timezonefinder`` and forfeiting every code fix since. Every release used to carry the whole ~65 MB dataset in three platform wheels plus an sdist to distinguish a few kilobytes of compiled code, which had already exhausted the PyPI project storage quota once. A data update is consequently no longer a ``timezonefinder`` release at all: it publishes ``timezonefinder-data`` under its own tag namespace and is recorded in that package's README rather than here. Its version reads ``<format>.<year>.<letter>`` - ``1.2026.3`` is data format generation 1 built from timezone-boundary-builder ``2026c`` - and ``timezonefinder`` requires ``timezonefinder-data>=…,<2``: no ceiling on the data axis, so a dataset update needs no code release, and a hard one on the format axis, so code paired with data it cannot read fails when resolving rather than at the first lookup. ``DATA_LICENSE`` moves with the database it covers and now ships inside the data wheel, and a compiled data directory additionally carries a ``schemas/`` copy of the FlatBuffers definitions its binaries were written by, so it can be read back without the package that wrote it. Solves the first part of issue #446
* the packaged FlatBuffers binaries are now named ``.bin`` rather than ``.fbs``: ``boundaries/coordinates.bin``, ``holes/coordinates.bin`` and ``hybrid_shortcuts_uint16.bin``. ``.fbs`` is the FlatBuffers *schema* extension, and the data directory now ships actual schemas next to the buffers, so one extension was naming two unrelated kinds of file. Each buffer already states what it is through the file identifier in its first bytes, which is what a rename or a mispaired copy cannot forge - the name never carried that meaning. The bytes are unchanged

Internal:

* the release pipeline refuses to publish ``timezonefinder`` unless a compatible ``timezonefinder-data`` already exists on PyPI. The two distributions release independently, and on a data format change the order is fixed - data first, then the code requiring it - because a code wheel whose declared data version does not exist yet is uninstallable for everyone until it does, and the version number cannot be reused to fix it. The check reads the requirement out of the built wheel rather than out of ``pyproject.toml``, and asks the index the same question a user's resolver will, so a yanked release does not count as one that satisfies it. It runs before the GitHub Release, which is the first step of the release that cannot be taken back
* pull requests are opened against a template (``.github/pull_request_template.md``) prompting for the change, its motivation and the checks that were run
* ``update_data.sh`` resolves the timezone-boundary-builder release tag before downloading and fetches that release's asset, instead of fetching ``releases/latest/download/`` and separately asking the API what ``latest`` was - two independent questions that a release landing between them answered differently, attributing one release's data to the other. The tag now names the downloaded archive and the GeoJSON as well, so a leftover file from another release or another dataset variant cannot satisfy the "already downloaded" checks and be parsed in place of what was asked for
* names and docstrings now describe what the code does. ``TimezoneFinder.timezone_at`` documents the optimisation it actually performs: once no other zone can be matched the last remaining zone is returned *without* a point in polygon test, which is always correct against the packaged data - the ocean zones cover the globe, so every point lies within one of the candidate polygons - but not against custom data that leaves areas uncovered, where a point inside none of the candidates is still attributed to that zone and ``certain_timezone_at`` is the method that tests every candidate. Three tests were named after something other than what they do: ``test_rectify_coords_valid``/``_invalid`` were named for a ``rectify_coords`` that exists nowhere in the package and both call ``validate_coordinates``, and the first was subsumed entirely by ``test_validate_coordinates_accepts_finite_values``, which covers all four of its distinct corners and additionally asserts the return value where the older test asserted only "does not raise"; and ``test_single_element_arrays_should_not_occur`` asserted that they *do* occur (``assert single_element_count == 2``) under a triple-quoted string placed after the first statement, making it a discarded expression rather than a docstring - so it reached neither ``--collect-only`` nor a failure report, which is where the contradicting name was the only thing a reader saw. A stale comment duplicated across the last two lines of ``tests/main_test.py``, reading as a to-do for something ``TestTimezonefinderClassTestMEM`` already does, is gone
* added ``DATA_VERSION`` file tracking which timezone-boundary-builder release the packaged data was generated from, written automatically by the data update script after a successful parse. Thanks to `Lucas Hemkemeier <https://github.com/hemkdev>`__ for the PR #429
* the packaged data now updates itself: a weekly workflow compares ``DATA_VERSION`` against the latest timezone-boundary-builder release, regenerates the data and opens a ready-to-review update PR, which is merged and released automatically once its CI passes - the version tag is pushed with a GitHub App token, since the default one would not trigger the release pipeline. The tag lives in its own ``data-v*`` namespace, which the code release pipeline excludes at its trigger and again on the job that creates the GitHub Release, and the data stream publishes by PyPI Trusted Publishing from its own deployment environment rather than with a shared token. It refuses to release when the squash it produced did not land on the ``master`` it checked, so the tag names a tree that was actually built. Failed CI takes the same manual-attention path and falls back to the previous notification issue. Each cause labels the PR ``automation-failed`` and leaves one comment naming that cause and linking the run, deduplicated per cause so re-running CI neither repeats a notice nor hides a second one; a failure past the merge is a cause of its own, since that leaves master carrying the update with no tag pushed and only a hand-pushed tag still releases it. The manual release path drops the stop condition it carried for an out-of-order ``CHANGELOG.rst``: the automation can no longer produce one, and the test suite asserts the committed file's section order if anything else does (issues #273, #167 and #510). Thanks to `Lucas Hemkemeier <https://github.com/hemkdev>`__ for the PRs #434 and #436, and to `Nice6042 <https://github.com/Nice6042>`__ for the PR #518
* ``update_data.sh`` (renamed from ``parse_data.sh``) is CI-ready: interactive prompts replaced by flags (``--dataset=full|same-since-now``, ``--with-oceans``, ``--rm-tmp``), the release note for a data update written automatically into the data package's README, no redundant ``tox`` run, and a ``make reports`` at the end so the benchmark and data reports cannot go stale relative to the data an update PR ships. A standalone ``make parse``/``make testparse`` still needs a manual ``make reports`` (issues #167 and #510). Thanks to `Lucas Hemkemeier <https://github.com/hemkdev>`__ for the PRs #432 and #434
* added property-based tests (``hypothesis``) for coordinate validation (solves issue #143). Thanks to `Lu Yicheng <https://github.com/01luyicheng>`__ for the PRs #431 and #433
* consolidated the three overlapping coding-agent instruction files into one canonical source: ``CLAUDE.md`` now holds all guidance, ``Agents.md`` is renamed to ``AGENTS.md`` and reduced to a pointer stub, and the legacy ``.cursorrules`` is replaced by ``.cursor/rules/repo-instructions.mdc`` (also a pointer stub), removing the drift risk of maintaining three near-duplicate copies
* replaced the hand-rolled ``timeit`` timing in ``scripts/check_speed_*.py`` with ``pytest-benchmark`` suites under ``benchmarks/``, excluded from ``make test``/``make testall`` via ``testpaths``. Both they and the memory harness run over deterministic committed fixtures (``tests/fixtures/benchmarks/``), so two runs of the same commit execute the exact same workload; the loader rejects fixtures that no longer match the checkout. Measurement and rendering are decoupled, so ``docs/benchmark_results_*.rst`` can be regenerated from a stored JSON without re-measuring. Run via ``make speedtest``, ``make benchmarks``, ``make memory`` or ``make reports``
* memory is measured by its own harness (``scripts/measure_memory.py``, ``make memory``) rather than by ``pytest-benchmark``, which times code and would have its timings distorted by allocation tracking. It emits pytest-benchmark-shaped JSON, so the existing normalisation, noise and comparison tooling works on it unchanged given a ``--metric``. ``tests/test_memory_footprint.py`` fails if a mode's allocation leaves its order of magnitude - the regression that would make ``in_memory=False`` stop being the low-memory option
* added continuous benchmarking on CI (solves issue #150), deliberately kept out of the release pipeline in ``build.yml``: the tracked core subset and the memory harness run on every pull request and every push to ``master``, publishing `trend charts <https://jannikmi.github.io/timezonefinder/dev/bench/>`__ to ``gh-pages`` and posting a same-runner base/head comparison on the pull request. A pull request is measured against its own merge base in the same job rather than against a stored baseline, because ``runs-on: ubuntu-latest`` pins the runner image and not the CPU. The measurement design, the tracked estimator and every alert threshold are documented in the new `benchmarking methodology <https://timezonefinder.readthedocs.io/en/latest/benchmarking_methodology.html>`__ page. The measuring job holds no write permissions and no secrets, so branch and fork pull requests behave identically; the comment is posted by a separate, privileged workflow via ``workflow_run``
* guarded the benchmark plumbing against silent drift: ``tests/test_benchmark_names.py`` and ``tests/test_memory_metric_names.py`` pin the node ids and metric names that join a measurement to its chart history, so a rename fails loudly instead of starting an empty chart beside the orphaned old one; ``tests/test_benchmark_workflows.py`` asserts that the constants duplicated across the two workflows agree, where a one-sided edit previously had no failure mode at all, and that the cross-machine trend chart cannot creep back into the pull request comparison; and every generated report page states the inputs it describes - ``docs/benchmark_results_*.rst`` the fixture and timezone data versions they were measured against, ``docs/data_report.rst`` the timezone data version its figures were derived from. Both stamps are covered by tests: one renders each report and fails if a renderer stops emitting it, another checks the committed pages against the current fixture metadata and ``DATA_VERSION``, so regenerating fixtures or updating the data without re-rendering fails loudly instead of leaving a page whose numbers are all plausible and all stale
* every generator now emits output that is already pre-commit-clean, so regenerating and diffing compares like with like: ``write_json`` sorts keys the way ``pretty-format-json`` does, and neither ``scripts/reporting.py`` nor ``BenchmarkReporter`` emits trailing whitespace on empty cells or a trailing blank line. Previously every ``make parse``/``make reports`` left its outputs looking modified until the hooks had run, which masked whether a regeneration had actually changed anything
* every generated benchmark report now opens with its headline figure and the configuration behind it, above the tables: how long a lookup takes and how many per second, the per-check cost across polygon sizes, construction time, footprint per mode - all derived from the same parsed JSON as the tables, never hardcoded. The banner beneath states which acceleration path and platform produced the numbers, and says whether that is the configuration CI tracks: the committed reports are rendered from a developer machine with Numba enabled, while CI measures the C extension without Numba, so their figures were never comparable to the trend chart and now say so
* ``make flatbuf`` no longer overwrites hand-maintained ``__init__.py`` files. ``flatc`` derives its output path from the schema namespace and writes an empty ``__init__.py`` at every level of it, so generating in place wiped the ``__all__`` in ``timezonefinder/__init__.py`` - the whole public API. The target now generates into a scratch tree, copies back only the generated packages, and runs the formatters on the result so a regeneration diff shows the codegen change rather than formatting churn
* mypy now type-checks the whole package except the ``flatc``-generated bindings. ``ignore_errors`` previously covered roughly 800 lines of hand-written code as well, where a blatantly wrong return type still reported "Success"; they all pass once the exemption is lifted, bar two genuine findings now fixed. ``tests/test_mypy_config.py`` keeps the list restricted to generated code, so silencing a module is a reviewed decision rather than a one-line edit
* the hybrid shortcut reader and writer now select their FlatBuffers schema from a single registry (``SHORTCUT_SCHEMAS`` in ``timezonefinder/flatbuf/io/hybrid_shortcuts.py``) instead of dispatching on the zone id width in three places, each keyed differently. One ``ShortcutSchema`` per width owns the width, the file name, the ``uintN`` marker and the maximum zone id, which were previously written down across five places with nothing tying them together. Verified behaviour-preserving down to the bytes: re-writing the shipped shortcut binary produces a byte-identical file
* each distribution's build is now asserted to contain exactly what it should. The data wheel's payload is compared against the committed dataset as a set, in both directions: a missing binary fails on first use and gets reported, but an extra one ships silently - setuptools copies package data into ``build/lib`` and never prunes it, so a file renamed in the source tree keeps being zipped into every later wheel built from that checkout, which is how a 63 MB ``coordinates.fbs`` was still shipping next to the ``coordinates.bin`` that replaced it and doubling the wheel whose size is the reason the distribution was split out. The wheel builders clear that directory first, so a local build matches the fresh checkout CI builds from, and the code sdist's checks cover its grafted test fixtures again
* compiled data directories are now checked for integrity where they are produced and where they are reviewed, by one shared set of assertions in ``scripts/data_integrity.py``: the converter runs them over the files it just wrote, and the test suite runs them over the packaged binaries. They establish that the hole reference vector, the hole coordinate file and the hole bounding boxes agree with one another, and - the part with evidence independent of the references themselves - that every reference resolves to the geometry its bounding box was computed from, so a converter that mismatched a hole to the wrong boundary polygon fails loudly instead of shipping a plausible wrong timezone. Deliberately not run when a ``TimezoneFinder`` is constructed: whether a data directory is coherent is settled once, by the build, and re-deriving it in every user's process would spend startup time re-answering a question that already has an answer. Keeping it off that path is what allows the check to be thorough rather than cheap - it resolves every hole ring in the dataset
* the packaged data is additionally held to a floor on how much hole deduplication achieves - the test suite fails if fewer than 90% of its holes match a boundary polygon (96.4% currently), because a future upstream release that stopped emitting enclaves as shared rings would still compile and still return correct timezones, just with the shipped data quietly re-inflated. The floor applies to that dataset and nothing else: compiling your own GeoJSON with ``scripts/file_converter.py`` is a supported use case, holes that are ordinary interior rings rather than enclaves are stored inline and answer correctly, and the converter only reports the ratio rather than refusing to compile. ``prototypes/hole_boundary_redundancy.py`` is the study behind the threshold: it reads the upstream GeoJSON, so re-running it against a new release re-verifies the assumption rather than restating it. ``prototypes/hole_removal_impact.py`` is the study behind keeping the unmatched holes stored inline rather than dropping them, which is the obvious next step and does not work: dropping holes and re-running the lookups changes answers, wrongly, because being covered by another zone only puts that zone among the shortcut candidates and says nothing about it being tested first (issue #513)
* removed constructs that provably did nothing, and gave two vacuous tests real assertions. Most consequentially, four ``__slots__`` entries were declared but assigned by nothing, which silently re-permitted the very attributes ``__slots__`` is there to forbid - assigning those names now raises ``AttributeError``, and ``test_declared_slots_are_assigned`` keeps the list honest
* ``get_corrected_hex_boundaries`` exists once again. An earlier refactor left two verbatim copies of the antimeridian and pole clipping rules with nothing keeping them in sync; the copy without callers is deleted, and the survivor is now covered by ``tests/hex_utils_test.py`` - it previously had no direct tests at all. ``scripts/configs.py`` no longer declares ``MAX_LAT``/``MAX_LNG`` as a second pair of names for ``timezonefinder.configs``'s constants
* added a ``code-quality-pass`` coding-agent skill (``.claude/skills/``, the only tracked part of ``.claude/``) driving one autonomous internal-quality pass: triage, then the ledger's highest-priority findings fixed one at a time - none of which may change observable behaviour - until a diff budget of ~400 changed lines is spent, the full verification gate and a pull request against ``master``. The pass consumes the ledger in priority order rather than picking a single theme, so the ranking and not a common story is what holds the pull request together: each item lands as a commit of its own naming its ledger entry, the budget is measured against the merge base with the ledger excluded and checked between items rather than mid-item, and a ranking that runs dry ends the pass as legitimately as a spent budget - there is nothing to pad it with. Findings accumulate in ``potential-improvements.md``, a committed ledger every pass reads before touching a source file, so a candidate already rejected is not raised again and a pass that finds nothing worth changing still leaves its triage behind. Several passes can run concurrently: each takes its own worktree and claims ground by pushing the branch as soon as triage picks its first item and again after every item it finishes, since the remote branch list is the only coordination there is and a branch claims only what it already holds, and the skill names the two files that collide regardless (the changelog, where both bullets are kept) along with how to resolve them. The ledger is a to-do list rather than a history - an entry is deleted by the pull request that ships it, leaving only what is unfinished or deliberately declined, which is also what keeps concurrent passes from conflicting over it. Its header leads with what the file is and how its entries are ranked, with the mechanics of how a pass consumes and rewrites it moved below, since the file is read far more often by people than by passes
* ``prototypes/`` has a ``README.md`` saying what the three scripts there are: exploratory studies behind committed design decisions, run by hand, outside the package and the test suite. One of them is the measurement that chose H3 resolution 3 - the central algorithmic parameter of the package, already cited from the data format page - and another is the evidence for not building a hierarchical index. ``MANIFEST.in`` now excludes the whole directory from the source distribution rather than only its ``*.py`` files
* ``plans/`` is git-ignored alongside ``tmp/`` and ``.venv/``: implementation plans written while working on a change are local scratch, and leaving the directory untracked-but-unignored made it noise in every ``git status`` and a candidate for an over-broad ``git add``
* failing paths now report the input that failed. ``tests/auxiliaries.py``'s ``run_command`` assembled the child's stdout and stderr into a message and then raised a *fresh* ``CalledProcessError`` that never used it, with ``from None`` discarding the original too, so a packaging failure under ``make testint`` reported an exit code and nothing about the cause; it now echoes the captured streams and re-raises the original exception with its traceback intact. ``scripts/reporting.py`` passes the coordinate file paths into ``get_polygon_collection``, whose optional ``file_path`` exists precisely so an incompatible-layout ``ValueError`` can say which of the two files was stale - ``make reports`` against an outdated data directory previously could not. ``Boundaries.overlaps`` names the type it rejected instead of raising a bare ``TypeError``, and the ``RuntimeError`` for missing ``original_polygons`` names the polygon and resolution it was computing. The two re-raises ruff flags under ``B904`` now say ``from None`` explicitly, so a deliberately dropped exception chain is distinguishable from a forgotten one, and ``timezonefinder/command_line.py`` drops ``FileNotFoundError`` from an ``except`` tuple that already caught its base class ``OSError``. ``tests/test_error_diagnostics.py`` pins what each of these messages must contain
* the command line interface no longer routes its own output through a temporary file. ``main`` redirected stdout to a ``mkstemp`` file for the duration of the lookup and then, in verbose mode, reopened it to read back a string it still held in a local variable - nothing inside the redirected block ever wrote to stdout, since the lookup functions return their result rather than printing it. The context manager, the read-back, its warning path and the file cleanup are gone, and the lookup function is now resolved once per invocation instead of twice, so ``-f 3``/``-f 4`` under ``-v`` no longer construct a second ``TimezoneFinderL`` and reload its shortcut data just to read a function name. Output is unchanged character for character, across every function id in both modes. ``tests/cli_test.py`` gains the coverage that makes that checkable - verbose mode, the empty line printed when no timezone is found, and the rejected function id had none - and asserts the printed name verbatim instead of passing it through ``rstrip("\n\x1b[0m")``, which strips a *set* of characters rather than a suffix and so truncates 12 of the packaged zone names (``Europe/Amsterdam`` -> ``Europe/Amsterda``)
* docstrings now describe the code that exists. Six documented something the implementation contradicts: ``AbstractTimezoneFinder.__init__`` called ``in_memory`` inert and "kept for API compatibility" when it is what selects memory-mapped against in-memory coordinate access - the claim ``help(TimezoneFinder)`` surfaces, and the opposite of what the usage docs say; both ``get_geometry`` docstrings pointed at a ``timezone_names.json`` that does not exist under that name; ``read_zone_names`` promised an empty list where it raises ``FileNotFoundError``, and illustrated itself with a hardcoded zone count that the packaged data had since outgrown; and ``zone_id_of`` / ``zone_name_from_id`` each advertised an exception type they convert away, sending callers to write handlers that can never fire. Five further ``:param:``/``Args:`` entries in ``scripts/`` and ``tests/`` documented arguments that were removed along with the parallel shortcut compilation they belonged to. ``tests/test_documented_contracts.py`` pins the exception types and the coordinate access mode, so those promises now rest on something besides prose
* the test and benchmark suites no longer contain checks that cannot fail. Eighteen calls sat inside four shared ``pytest.raises`` blocks in ``tests/main_test.py``, and execution leaves such a block at the first statement to raise - so one out-of-range coordinate, one positional call shape and one rejected ``get_geometry`` input were verified while the remaining fifteen were unreachable. Each is a test case of its own now: every coordinate just outside the WGS84 range, every positional call shape of every keyword-only lookup method, and the unknown-zone-name, past-the-end and negative zone id rejections of ``get_geometry``. The ``__del__`` cleanup test binds its exception per iteration rather than closing over the loop variable, which decided what a garbage-collected instance would raise long after the loop had moved on. On the benchmark side, ``pip_inputs_by_stratum`` validated only the strata the fixture happened to contain, so one missing from it altogether passed and surfaced later as a bare ``KeyError`` inside a benchmark, and the points and their labels were paired from two files with a non-strict ``zip`` that truncates silently. That grouping now lives in ``tests/auxiliaries.py`` as ``group_pip_inputs_by_stratum``, checks against the declared ``PIP_STRATA`` - which the generator no longer keeps a second copy of - and has tests for each way the two fixture files can disagree
* both point-in-polygon acceleration paths are now covered by a local test run, whichever one the environment happens to bind. The implementation is selected at import time and Numba wins whenever it is importable - which the documented setup (``uv sync --all-groups``) makes it - so the C extension was reached only by direct-kernel tests on hand-built arrays, and everything about how real polygon buffers arrive at it, including the read-only memory-mapped views, was first exercised in CI's non-numba tox environments: the configuration a plain ``pip install timezonefinder`` produces. ``tests/test_acceleration_paths.py`` now rebinds ``utils.inside_polygon`` and drives the full lookup stack through both implementations, asserting that they agree across the real boundary data, that the C path returns the known-correct answers, and that the point-in-polygon stage was reached at all rather than short-circuited by the shortcut layer (issue #482)
* the packaging guard in ``tests/test_package_contents.py`` no longer names files that do not exist. It asserts that nothing in the built sdist and wheel matches a list of unwanted paths, which passes just as readily when a pattern matches nothing at all: ``.github`` lacked the trailing slash that directory patterns need, ``Agents.*`` stopped matching when the file was renamed to ``AGENTS.md``, and ``readthedocs.yaml`` never matched ``readthedocs.yml`` - so the CI configuration and both of those files were unguarded while the suite stayed green. The patterns are corrected, ``CLAUDE.md``, ``potential-improvements.md`` and ``.cursor/`` are added to match what ``MANIFEST.in`` excludes, and ``test_every_unwanted_pattern_matches_a_project_file`` now fails on any hand-written pattern that matches no path in the checkout, so the next rename cannot silently disarm one. It carries the ``unit`` marker rather than the module's former blanket ``integration`` mark, since it needs no build: a mistyped pattern surfaces in ``make test``. ``.gitignore`` re-include lines (``!…``) are also no longer read as exclusions, which had produced one more parametrised case that could never fail. The converse direction is checked too: ``test_every_manifest_exclusion_is_guarded`` parses the ``exclude``/``recursive-exclude``/``prune``/``global-exclude`` directives out of ``MANIFEST.in`` and fails when one of them keeps a path out of the build that no pattern here names - previously such a line was enforced by the build and verified by nothing, so deleting it would have shipped the file with the suite still green. The two lists are hand-maintained statements of one intent and had drifted before, in both directions. The `architecture page <https://timezonefinder.readthedocs.io/en/latest/architecture.html>`__ describes the guard from both sides: among the tests that exist to give an invariant a failure mode, and under *How it ships* as the check on what the built artifacts actually contain
* the distributions built by the test suite are now built for the interpreter running it. ``uv build`` was invoked without ``--python``, so it targeted the newest interpreter on the machine, while ``tests/test_integration.py`` creates its throwaway venv from ``sys.executable``: on a checkout whose ``.venv`` is older than the newest installed Python, ``make testint`` produced a ``cp314`` wheel and failed with pip's "not a supported wheel on this platform". Every tox environment offers a single interpreter, so the two agreed by accident in CI and the mismatch only ever hit developer machines, where the workaround was to pin ``UV_PYTHON``. ``test_build_commands_pin_the_running_interpreter`` keeps the pin in place; it needs no build, so it fails in ``make test`` rather than waiting on a CI environment that cannot reproduce the mismatch
* added a ``roadmap-pass`` coding-agent skill (``.claude/skills/``) advancing the structural work tracked by the roadmap issue #506 one pass at a time: select an eligible item, check the sequencing preconditions #506 records, put that item's open design decisions to the maintainer as concrete choices with a recommendation, and only then implement one slice, ending in at most one pull request against ``master``. It asks where its ``code-quality-pass`` sibling deliberately never does - a roadmap item's design choices outlive the pass and belong to the maintainer, so a pass whose entire deliverable is four recorded decisions is a success rather than a pass that failed to produce code. All state is derived from the tracker instead of a progress file, which is what makes repeated and concurrent passes idempotent: an item is claimed by pushing its ``roadmap/<issue>-<slug>`` branch before any editing, answered decisions are posted as a comment on the item's own issue so a later pass reads them instead of re-asking and getting a different answer, and a single log comment on #506, edited in place, records every pass including the ones that shipped nothing. A slice must leave ``master`` releasable on its own, an item whose preconditions are unmet is refused with the blocking gate named, and a triage-only mode reports what the next pass would pick while changing nothing at all. ``tests/test_agent_skills.py`` checks the frontmatter of every skill under ``.claude/skills/``, since a description is the whole of what makes a skill discoverable and an unquoted ``#`` in a plain YAML scalar starts a comment - ``roadmap issue #506 by one pass`` stored the seven words before the ``#`` and silently discarded every trigger phrase after it
* added a ``cut-release`` coding-agent skill (``.claude/skills/``) driving the manual release end to end, in two halves split by the maintainer's merge: it checks the ``X.X.X (unreleased)`` section is release-ready and complete against every commit since the last tag, applies the changelog rules that make a released section read as one step, then derives ``patch``/``minor``/``major`` from the strongest bullet in it, lands the bump as a release PR justifying that level, and - once the maintainer has merged it - pushes the tag. It stops once, at the tag: that is the publish, PyPI will not let a version take back, and nothing reviews it afterwards. The level is not asked, because the release PR puts it in front of the maintainer with the diff attached before anything ships, so the PR body must quote the bullet that drove the level and name the level it ruled out. It records what the pipeline makes non-obvious: the tag-push run re-reads ``pyproject.toml`` at the tagged commit, so the tag and the version must agree; the release commit is the bump and the changelog and nothing else, so ``make reports`` must not run in it; and the tag has to be pushed promptly after the merge, because the master push run's own ``release`` job creates the GitHub Release and with it the tag, after which a ``git push`` of that tag is a no-op that fires no webhook - which is why the automated data path tags immediately too. A boundary-data update is not on that table at all: it releases ``timezonefinder-data`` and never reaches this changelog
* two tests no longer leak numpy's global error state into whatever pytest collects next. ``np.seterr`` and the warning filters are process-global, and ``test_overflow`` (``tests/main_test.py``) plus ``test_inside_polygon`` (``tests/utils_test.py``, six parametrisations) each set them and never restored them - so every later test in the same process ran with ``under`` promoted from ``ignore`` to ``warn``, and which of the two modules pytest collected first decided the state the other ran under. The filters were undone only incidentally, by pytest's per-test ``catch_warnings()``, not by the tests themselves. ``benchmarks/conftest.py`` already had the correct pattern; it now lives in ``tests/auxiliaries.py`` as the ``strict_numpy_errors`` context manager plus a thin ``strict_numpy_warnings`` fixture, re-exported through the conftest of each suite, and both call sites request it. The context manager form is what makes the restore directly testable - a leaked global otherwise surfaces only as an unrelated later failure that depends on collection order, which is the hardest kind to attribute
* the zone id invariants in ``scripts/timezone_data.py`` are each enforced in exactly one place, and now have tests. ``ZoneCollection.validate_structure`` and ``zone_positions`` each walked ``poly_zone_ids`` element by element checking it was non-decreasing and each raised the same message built from its own locals; the scan moves into one ``_validate_non_decreasing`` helper and ``zone_positions`` drops its copy, which could only ever have fired if a caller mutated the array in place - the validator runs at construction and nothing writes to it afterwards. A ``if min_zone_id < 0`` branch is deleted as unreachable: the same method rejects any non-unsigned dtype a dozen lines earlier, so it read as the guard against negative zone ids while being incapable of firing. The class had no tests at all, so what it actually promises - the unsigned-dtype rejection that makes a negative id unrepresentable, the ordering and maximum-id rules, and the shape ``zone_positions`` returns - is now pinned by ``tests/timezone_data_test.py``
* the seven out-of-range coordinates - one representable step outside the valid WGS84 range, per axis and at every corner - are declared once in ``tests/locations.py`` instead of verbatim in both ``tests/main_test.py`` and ``tests/utils_test.py``, where only one copy carried the comment explaining what makes them interesting and adding a corner to it left the other testing a smaller set
* the shortcut compilation chain in ``scripts/shortcuts.py`` is annotated for what it is actually passed. Both annotations were the wrong way round: ``check_shortcut_sorting`` declared ``np.ndarray`` and only ever receives the ``list[int]`` that ``optimise_shortcut_ordering`` returns, and it hands the ``np.ndarray`` it derives to ``has_coherent_sequences(lst: list[int])``. Widened rather than swapped, since ``tests/shortcut_test.py`` calls the latter with real lists
* the supported Python versions are declared in five places that cannot read each other - ``requires-python`` and one classifier per minor version in ``pyproject.toml``, the ``py{...}`` factors of ``tox.ini``'s envlist, the test matrix and ``CIBW_BUILD_VERSIONS`` in ``build.yml``, and ``py_limited_api`` in ``setup.py`` - and two "must match" comments said so while nothing enforced them. ``tests/test_python_version_support.py`` fails when they drift, in either of the two directions that fail silently: a classifier added without a matrix entry ships a version the package claims to support and CI never runs, and a ``requires-python`` raised without moving the abi3 base builds wheels tagged for an interpreter that is no longer supported. Each assertion was checked against the specific one-sided edit it targets, and both comments now name the test
* the data report generator states figures it derives rather than ones it restates, and its annotations describe what it returns. ``calculate_shortcut_index_stats`` took the number of H3 cells existing at the shortcut resolution from a ladder of literals covering resolutions 0 to 4 and fell through, for anything else, to the number of cells actually stored - which reports coverage of exactly 100 % instead of failing - behind an ``except ImportError`` that cannot fire, since h3 is a runtime dependency rather than an optional one. It asks ``h3.get_num_cells``, which returns precisely the numbers that were tabulated. Running mypy over ``scripts/reporting.py``, which the pre-commit hook excludes, found seventeen further disagreements between the module and its own signatures: the statistics bag was typed as holding scalars while returning two distributions, ``load_binary_data``'s nine-key result was a bare ``dict`` indexed by string literal, the table renderer declared string rows while stringifying whatever it is handed, ``main`` was annotated ``None`` while returning exit codes to ``exit()``, and ``print_polygon_distribution_table`` documented a return value it never produced while its one caller discarded it. The two dict results are now ``TypedDict``\ s in ``scripts/configs.py``, carrying tests that assert their keys against what is really returned, since CI cannot type-check ``scripts/``. The polygon count that labels a distribution row is no longer formatted into that label and parsed back out of it to key the example lookup. ``docs/data_report.rst`` and the benchmark reports regenerate byte-identically throughout
* removed five definitions nothing referenced - three JSON/pickle helpers in ``scripts/utils.py`` and the ``import pickle`` they kept alive, the ``i8`` dtype shim in ``timezonefinder/_numba_replacements.py`` that the no-numba fallback never imports, and a test helper self-documented as kept for future reference - and a guard in ``scripts/hex_utils.py`` that could not fire. ``Hex.poly_candidates`` re-read its cache after initialising it and returned an empty set if it were still unset, which no path through ``_init_candidates`` leaves it: an empty set there means "no candidate polygons", so a converter bug would have surfaced as silently missing shortcuts rather than as a failure. The property had no direct test, being reached only through shortcut generation, and now has one. ``_memory_mode_label`` looks its two labels up in ``PARAM_LABELS`` instead of spelling them out, so renaming the display vocabulary can no longer leave the comparison bullets and the tables above them disagreeing
* ``make parse`` and ``make testparse`` run again. Both invoked ``scripts/file_converter.py`` by path, which puts ``scripts/`` on ``sys.path[0]`` instead of the repository root, so the converter's own ``from scripts.timezone_data import ...`` raised ``ModuleNotFoundError`` before any work started - a total failure that CI never sees, since it runs neither target. ``make testparse`` is the only cheap end-to-end exercise of the converter (``update_data.sh`` needs a ~55 MB download), and nothing under ``tests/`` covers ``parse_data()``, so while it was broken the converter had no smoke test at all. The invocation documented in the usage docs had the same defect and is now the ``python -m scripts.file_converter`` form that ``update_data.sh`` already used; ``tests/test_script_invocations.py`` fails if a by-path invocation returns. Note that ``parse_data()`` writes its report to the checkout's committed ``docs/data_report.rst`` whatever ``-out`` it is given, so ``make testparse`` leaves that file describing the three-zone fixture - the target now says so
* ``scripts/`` is type-checked by the mypy pre-commit hook instead of being excluded from it. The directory holds the data converter and the benchmark tooling - most of the repository's non-library Python - and with nothing running mypy over it the annotations had drifted to fifteen errors: two ``# type: ignore`` codes mypy no longer emits, so the ignore silenced nothing; two implicit ``Optional`` defaults that ``no_implicit_optional = true`` was already configured to reject; a dict annotated with a narrower value type than it is assigned; a bucket key and four bounding-box lists annotated ``int`` while ``Boundaries`` declares ``float``; and two missing variable annotations. All fixed as annotations, with no runtime change. Two of the four errors mypy reported in ``tests/auxiliaries.py``, which it reaches by following imports out of ``scripts/``, are fixed alongside. ``test_scripts_are_type_checked_by_the_hook`` guards the exclude, which is a quieter way to stop type-checking a directory than the ``ignore_errors`` list the neighbouring tests already cover: it takes no override entry and reports nothing
* the eight ``__del__`` cleanup tests that differed only in which exception ``cleanup()`` raised, and whether zero or one ``ResourceWarning`` was expected, are two parametrized tests over the suppressed and warned exception tuples. Each previously repeated the same subclass, the same ``catch_warnings`` block and the same filter, so adding a ninth exception to ``__del__``'s suppression list meant copying the block a ninth time and a copy asserting the wrong count would be invisible. Coverage rises rather than falls: the hand-rolled loop asserting that ``__del__`` never raises to user code now runs over all six exception types instead of four
* three leftovers in the converter that read as bugs are gone: ``has_coherent_sequences`` built an iterator solely to take its first element and then looped from the start anyway (correct, but it reads as an off-by-one), ``compile_bboxes`` unpacked a pair and immediately reassigned half of it, and ``process_single_hex`` returned the ``hex_id`` it was handed so its only caller reassigned the loop variable to itself. Two shadowed builtins (``dir`` as a loop variable, ``id`` as a parameter) are renamed and three bare generator signatures annotated. The benchmark renderer classifies its "other" group by name suffix, as the two lines above it do, rather than by deep-equality scan over lists of dicts; and the ``check-manifest`` ignore list drops two entries naming files that do not exist (``CONTRIBUTING.rst``, ``publish.py``). Every converter change was verified by parsing ``tests/test_input.json`` before and after and comparing the outputs byte for byte


8.2.5 (2026-07-11)
------------------

* updated the data to `2026c <https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2026c>`__


8.2.4 (2026-05-01)
------------------

* added ``manylinux_2_28_x86_64`` wheel to releases, fixing the fallback to version 6.0.1 when pip resolves with ``--platform manylinux_2_28_x86_64`` (Python 3.14 + numpy 2.4). . Thanks to `theirix <https://github.com/theirix>`__ for the PR #420


8.2.3 (2026-04-30)
------------------

* updated the data to `2026b <https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2026b>`__
* added examples and documentation for using parallel processing with the timezonefinder libary.

Internal:

* reduced code duplication in coordinate validators: extracted common validation logic into a reusable ``_validate_coordinate()`` helper function
* improved error handling and warning emission during ``__del__`` resource cleanup
* refactored ``command_line.py`` for improved maintainability:
    * decomposed monolithic ``main()`` function into focused, independently testable components: ``_parse_arguments()``, ``_lookup_timezone()``, and ``_print_lookup_details()``
    * reduced cyclomatic complexity and improved separation of concerns
* modernized codebase with Python 3.11+ features and best practices:
    * migrated from ``typing`` module imports to ``collections.abc`` for ``Iterable`` and ``Callable``
    * added ``Self`` type annotation for context manager protocol
    * replaced conditional dispatches with ``match/case`` statements for improved clarity and maintainability
* using python 3.10+ type hints. Thanks to `Marco Barbosa <https://github.com/aureliobarbosa>`__
* enhanced test coverage:
    * added 8 comprehensive thread safety tests for concurrent singleton initialization
    * added 37 coordinate validation tests covering edge cases (NaN, Inf, boundary values)
* comprehensive code quality improvements for production-grade stability:
    * improved exception handling: replaced bare ``except`` clauses with specific exception types (``FileNotFoundError``, ``OSError``, ``IOError``), added proper exception chaining via ``from e``
    * enhanced type hints: added complete type annotations to public APIs, resolved type checking issues with mypy
    * enriched documentation: added comprehensive module and function docstrings with parameter descriptions, return types, error documentation, and usage examples
    * explicit API exports: added ``__all__`` declarations to ``utils.py``, ``zone_names.py``, ``global_functions.py``, and ``configs.py`` for clearer public API surface
    * improved error messages: replaced vague errors with specific context including valid ranges, expected values, and data locations
    * fixed deprecated patterns: updated ``tempfile`` API usage to modern context managers, fixed import ordering (stdlib first)
    * enhanced validation: added type checking for string inputs, better coordinate validation with clear error messages


8.2.2 (2026-03-26)
------------------

* updated the data to `2026a <https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2026a>`__


8.2.1 (2026-01-10)
------------------

* updated the data to `2025c <https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2025c>`__
* require ``numpy >=2`` following the official `NumPy Deprecation Policy <https://numpy.org/neps/nep-0029-deprecation_policy.html#drop-schedule>`__
* dropped official support for Python 3.9 and 3.10, due to NumPy dropping support for these versions.

Internal:

* Introduced ``slow`` test marker for computationally expensive tests to improve CI performance and local development workflow.  Updated CI configuration, tox environments, Makefile targets, and documentation accordingly. Thanks to `Chase Horton <https://github.com/Chase-Horton>`__ for the PR.
* enabled `Numba` tests for Python 3.13 and 3.14.


8.2.0 (2025-12-23)
------------------

* **Reverted to the full timezone dataset**: Starting from this release, ``timezonefinder`` uses the full original ``timezones-with-oceans`` dataset instead of the reduced ``timezones-now`` dataset.  This restores access to all >440 original timezone names, providing full localization capabilities and historical timezone accuracy. The reduced dataset (with ~90 timezones) is still available via the ``parse_data.sh`` script for users who prefer the smaller memory footprint. Due to the discussion in `GitHub Issue #363 <https://github.com/jannikmi/timezonefinder/issues/363>`__
* Improved error handling for resource cleanup. Thanks to `Dave Tapley <https://github.com/davetapley>`__ for the PR #375.
* Bug fixed where on termination we may hit an exception attempting to close resources in ``FileCoordAccessor``. Thanks to `David Park <https://github.com/daphtdazz>`__ for the PR #377.
* Made CFFI extension builds fallible, allowing the build process to continue even if C extension compilation fails. Thanks to `theirix <https://github.com/theirix>`__ for the PR #369.
* Added Python 3.14 to the supported test matrix (tox + GitHub Actions).



8.1.0 (2025-09-22)
------------------

* add the support of using the TimeZonefinder class instances as context managers. added a basic usage examples
* note that the performance of certain_timezone_at() degraded drastically, since now many more polygons will be checked with an expensive point-in-polygon algorithm. consider using timezone_at() or timezone_at_land() instead.
* introduced hybrid shortcut index structure that combines the functionality of separate shortcuts and unique shortcuts into a single optimized data structure, improving performance and reducing memory usage
* zone id storage now defaults to ``uint8`` and can be overridden via ``--zone-id-dtype``/``TIMEZONEFINDER_ZONE_ID_DTYPE`` when recompiling binaries
* relax ``cffi`` upper bound to allow the 2.x series so downstream packages pinning ``cffi>=2.0`` resolve cleanly
* ``scripts/reporting.py`` can now be executed as a standalone script to generate data reports from binary files independent from ``file_converter.py``
* the ``check_speed_*.py`` scripts now generates a detailed performance reports in reStructuredText format automatically included into documentation


Internal:

* using abi3 (aka Python limited API) wheels to avoid a combinatory explosion with Python version. It allows the use of a single Python 3.9 base and building future-proof wheels. Thanks to `theirix <https://github.com/theirix>`__
* using pydantic to validating and parsing the GeoJSON dataset. Thanks to `ARYAN RAJ <https://github.com/nikkhilaaryan>`__ for the PR.
* refactored file_converter.py to improve code quality. Thanks to `Pratyush Kumar <https://github.com/pratyushkumar211>`__ for the PR.
* consolidated shortcut data structures: replaced ``shortcuts.fbs`` file with ``hybrid_shortcuts_uint8.fbs`` (or ``hybrid_shortcuts_uint16.fbs``) file that stores both polygon lists and direct zone IDs using the minimal dtype for zone IDs.


8.0.0 (2025-08-11)
------------------

* starting from this release, ``timezonefinder`` uses the reduced ``timezones-now`` dataset version (cf. `GitHub Discussion <https://github.com/jannikmi/timezonefinder/discussions/323>`__ )
* in this dataset version, all timezones which agree on timekeeping methods as of the release date of the dataset, are merged into one zone (cf. `Dataset Documentation <https://github.com/evansiroky/timezone-boundary-builder?tab=readme-ov-file#same-since-now>`__ ). This results in a reduced set of ~90 timezones instead of >440 timezones and a reduced memory footprint of the package.
* If you used ``timezonefinder`` for localisation beyond the timezone behavior, it might become necessary for you to individually parse the full original dataset version using the ``parse_data.sh`` script.
* extended the ``parse_data.sh`` script to support downloading the ``timezones-now`` Dataset
* adapted tests to the reduced dataset version


7.0.2 (2025-08-06)
------------------

* exclude `tests` package closing issue #330


7.0.1 (2025-07-24)
------------------

* hit PyPI project size limit. triggering re-upload to fix missing sdist in ``7.0.0`` release.
* deleted all PyPI releases up to version ``3.4.2`` (last version supporting python 2.7) to free up project space



7.0.0 (2025-07-21)
------------------

* Simplified API for end-users, reducing redundant code
* Added global functions that use a shared ``TimezoneFinder`` instance:
    * ``timezone_at``
    * ``timezone_at_land``
    * ``unique_timezone_at``
    * ``certain_timezone_at``
    * ``get_geometry``

* Documented usage and warned about thread safety considerations for global functions
* Updated command line interface to use global functions where appropriate
* breaking API Changes: clarified naming. renamed "boundary" to "bbox". renamed "polygon" to "boundary". boundaries (the outer polygon defining part of a timezone) and holes are both polygons so hence the name "polygon" is ambiguous.


6.6.3 (2025-07-21)
------------------

* when ``in_memory=True``, all polygon ``numpy`` arrays are constructed once during startup rather than repeatedly on demand. This should significantly improve performance for applications that make frequent polygons queries.
* Created a ``coord_accessors.py`` module for abstracting access to polygon coordinates, allowing for both in-memory and file-based access.
* added auto-generated data report to the documentation. thanks to `ARYAN RAJ <https://github.com/nikkhilaaryan>`__ for the PR.



6.6.2 (2025-07-19)
------------------

* hotfix missing `hole_registry.json` in the distributions
* added integration tests in CI/CD. Thanks to `theirix <https://github.com/theirix>`__


6.6.1 (2025-07-18)
------------------

* hotfix missing `flatbuf` module in the distributions
* added tests for checking the content of the distributions



6.6.0 (2025-07-17)
------------------

* major internal refactoring without breaking API changes. improvements for performance and code quality
* use `flatbuffer` binary files for storing the polygon coordinate data and the shorcuts (spatial h3 index) in binary format. removed any custom code for reading and writing binary files (e.g. seek operations)
* documented the binary format in the documentation
* grouping all data files into a single "data" folder
* added a new class PolygonArray to abstract away handling binary data of multiple polygons
* separate binary data storage folders for polygon boundaries and holes. handling both with the PolygonArray class
* parameterised location tests
* improved CLI code quality suppressing any output. added nicer output in verbose mode
* dropped support for python 3.8 (reached the end of life). thanks to `ARYAN RAJ <https://github.com/nikkhilaaryan>`__ for the PR.
* added support for official for python 3.12
* added usage example scripts
* switched from `poetry` to `uv` for dependency management and packaging. Thanks to `theirix <https://github.com/theirix>`__


6.5.9 (2025-03-25)
------------------

* updated the timezone boundary data to version `2025b <https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2025b>`__. Thanks to `WestonReed <https://github.com/WestonReed>`__



6.5.8 (2025-01-21)
------------------

* updated the data to `2025a <https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2025a>`__
* internal: updated ``file_converter.py`` for ``h3>=4``


6.5.7 (2024-12-02)
------------------

* improved error handling to catch ``ValueError: not enough values to unpack`` (`Issue #209 <https://github.com/jannikmi/timezonefinder/issues/209>`__)


6.5.6 (2024-12-02)
------------------

* add musllinux Wheels for Linux. Thanks to `Pxli9130 <https://github.com/Pxli9130>`__


6.5.5 (2024-11-20)
------------------

* using ``setuptools`` only as a build dependency. Thanks to `Kristian Sloth Lauszus <https://github.com/Lauszus>`__


6.5.4 (2024-10-22)
------------------

* using the dependency ``h3>4``. Thanks to `Greg Meyer <https://github.com/gmmeyer>`__


6.5.3 (2024-09-16)
------------------

* updated the data to `2024b <https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2024b>`__.
* refactored C lang point in polygon utils

6.5.2 (2024-06-17)
------------------

* added support for ``numpy>=2.0`` (fixes issue #234)


6.5.1 (2024-06-14)
------------------

* added support for ``cibuildwheel``: publish wheels including the native C extension. GHA CI/CD pipeline creates sdist (no binaries inside) and a bunch of binary wheels with a prebuilt clang-pip extension for each python version. Thanks to `theirix <https://github.com/theirix>`__



6.5.0 (2024-03-14)
------------------

* updated the data to `2024a <https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2024a>`__.

internal:

* use ruff linter in pre-commit hook
* make dependency specifications less strict


6.4.1 (2024-02-08)
------------------

* added official support for python 3.8 again, by specifying numba as multiple constraint dependency


internal:

* added unit tests for polygon boundary binary reading


6.4.0 (2024-02-02)
------------------

* added python 3.12 support (supported by numba since release 0.59.0), Closes #208
* dropped official support for python 3.8, because the optional dependency numba requires python 3.9. this package might still work with python 3.8, but it is not tested anymore.


6.3.0 (2024-02-01)
------------------

* updated the data to `2023d <https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2023d>`__.

internal:

* added docstrings. Thanks to `Tyler Huntley <https://github.com/Ty1776>`__
* automatically skip GitHub actions publishing when the version already exists. useful for minor improvements without publishing a version. build would always fail otherwise
* enable tests for python 3.11 with numba
* enable tests for python 3.12
* added tests for generating the documentation
* use poetry dependency group specification (closing #199)


6.2.0 (2023-03-26)
------------------

* updated the data to `2023b <https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2023b>`__.


6.1.10 (2023-03-22)
-------------------

* added a `pytz` extra for easily maintaining compatibility
* improved documentation

6.1.9 (2022-12-06)
------------------

* updated the data to `2022g <https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2022g>`__.


6.1.8 (2022-11-25)
------------------

* pumped ``h3`` dependency to ``>=3.7.6,<4`` to support python 3.11 (FIX #170)
* added python 3.11 tests (not yet supporting numba)


6.1.7 (2022-11-20)
------------------

* updated the data to `2022f <https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2022f>`__.
* pinning dependencies more strictly

6.1.6 (2022-10-30)
------------------

* updated the data to `2022d <https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2022d>`__.


6.1.5 (2022-10-25)
------------------

* updated the data to `2022b <https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2022b>`__.
* logging build failures with warnings


6.1.4 (2022-10-23)
------------------

* more permissive optional ``Numba`` dependency specification (FIX #162, impossible using latest numpy version)
* made all dependency specifications more permissive following the same rationale


6.1.3 (2022-09-23)
------------------

* bugfix broken package build in the case of a broken ``cffi`` installation (GitHub issue #155). Skip build process if ``cffi`` fails. For performance reasons using the C extension should remain the default behavior. Hence the ``cffi`` dependency should not be optional.


6.1.2 (2022-09-13)
------------------

* bugfix potentially broken pip install due to a mismatch in ``cffi`` versions (GitHub issue #151)


6.1.1 (2022-08-18)
------------------

internals:

* minimized and cleaned up installation footprint (addresses GitHub Issue #151):
    * excluded script, changelog etc. files
    * included C extension into the "timezonefinder" package folder
* added initialisation speed benchmark


6.1.0 (2022-08-15)
------------------

* included point-in-polygon implementation in C
* included build script to (optionally) build C point-in-polygon extension automatically during installation
* added ``cffi`` as a dependency to build and interact with the C extension
* improved initialisation speed: read timezone polygon id index (h3 mapping) with ``np.fromfile``
* improved CLI speed: construct TimezoneFinder() instances only on demand

internals:

* updated documentation: ``Numba`` installation is no longer recommended (it is a huge dependency and should be optional)
* clarified documentation: TimezoneFinder() instances should be reused
* added separate speed benchmark scripts for point in polygon algorithm implementations and the different timezone finding functions
* added separate section in the documentation for performance including speed benchmark results
* added checks if all timezone polygons are actually in use (appear in index) to the file conversion script
* added and improved utility functions as well as tests
* improved typing


6.0.2 (2022-07-08)
------------------

* bump numpy dependency version to ``1.22`` (vulnerability fix)
* officially supported python versions ``>=3.8,<3.11`` (due to numpy and numba constraints)
* packaging now completely based on pyproject.toml (poetry)


6.0.1 (2022-05-20)
------------------

* explicitly included ``py.typed`` in the package to allow mypy users to run static type checking


6.0.0 (2022-05-09)
------------------

breaking changes:

* new dependency: using `h3 <https://uber.github.io/h3-py/intro.html>`__ for indexing the timezone polygons to check ("shortcuts) instead of the previous own indexing implementation. technical details: storing all 41,162 hex cells at resolution 3 and the corresponding timezone polygons which appear in them in the ``shortcuts.bin`` (~500 KB).
* removed ``.closest_timezone_at()``: with the current data set with ocean zones in use, any point is included in some zone. it is therefore not meaningful to search for the closest boundary! Also the timezone polygons do NOT follow the shorelines. This makes the results of ``closest_timezone_at()`` somewhat less expressive. Maintaining the non-trivial distance computation algorithms is not really at the core responsibility of this package.
* officially only supporting ``python>=3.7`` (removed official support for ``python3.6``, since the ``numpy`` dependency did so)
* removed ``v`` from the github release/version tags

internals:

* updated the data to `2021c <https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2021c>`__. please note that timezone polygons might be overlapping (cf. e.g. `timezone-boundary-builder/issue/105 <https://github.com/evansiroky/timezone-boundary-builder/issues/105>`__) and that hence a query coordinate can actually match multiple time zones. ``timezonefinder`` does currently NOT support such multiplicity and will always only return the first found match.
* shortcuts: sorting according to size of polygons (amount of coordinates) instead of the count of zone ids. useful as optimisation: smaller polygons will be checked first and can hence be "ruled-out" faster
* "most common": now meaning the zone with the largest polygons in the shortcut (last in the shortcut sorting). please note that this does not necessarily mean the most area in the shortcut is covered by this zone. the polygon size is just an easier to compute heuristic.
* officially supporting python versions >=3.7,<3.11 (like ``numba``)
* using poetry for dependency management
* using GitHub actions for CI instead of travis
* some minor typing improvements
* pre-commit hook improvements

In case you have criticism or feedback please reach out by creating an issue, discussion or PR on GitHub.


5.2.0 (2021-02-09)
------------------

* added function ``unique_timezone_at()`` (based on the request in issue #112). Allows querying for the unique zone within the corresponding shortcut.


5.1.1 (2021-02-03)
------------------

* BUGFIX: get_geometry() now also works for the last zone
* add get_geometry() tests
* black code style
* pre-commit checks

5.1.0 (2021-01-14)
------------------

* update the command line interface. the package can now directly be called with ``timezonefinder``
* added the new query functions to the command line interface (to match the online API)


5.0.0 (2020-12-23)
------------------

MAJOR CHANGES:

Due to multiple user requests the ocean timezones ("Etc/GMT+-XX") are now included in the data files per default. fix #88. Since ocean timezones span the whole globe, now every point lies within a timezone!

API changes:
* added ``timezone_at_land()``: replaces the previous ``timezone_at()`` and returns ``None`` in case of a matched ocean timezone.

* deprecated ``certain_timezone_at()``. only meaningful in the case of timezone data WITHOUT oceans. Has equal results as  ``timezone_at()``, but is more expensive to use.
* also looking a single closest timezone boundary with ``closest_timezone_at()`` is not really meaningful, since every point lies within a zone!
* refactored tests. new test cases for ocean timezones


4.5.0 (2020-11-06)
------------------

BUGFIX: handle output destination for data files correctly in file_converter.py (FIX #107)

* updated the data to `2020d <https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2020d>`__
* disable a test case for an Uzbek enclave. tests fail at this coordinate, possibly a bug. issue filed here: https://github.com/evansiroky/timezone-boundary-builder/issues/94
* update parse_data.sh script to properly handle new data format


4.4.1 (2020-08-04)
------------------

BUGFIX: a longitude of 180 equals -180 (not 0.0 as previously implemented)


4.4.0 (2020-05-14)
------------------

* added new class TimezonefinderL for using JUST shortcuts (without timezone polygon data)
* therefore included the most common timezone of each shortcut stored in the binary file ``shortcuts_direct_id.bin``
* introduced typing
* included API documentation
* read hole registry directly from json, ``hole_poly_ids.bin`` not required any more
* added the ``parse_data.sh`` shell script for downloading the latest timezone data, also with oceans


improvements of file_converter.py:

* added command line arguments for specifying the input and output directories
* read binary names from ``global_settings.py``
* read data types from ``global_settings.py``
* use with statement for writing binaries
* automatically detect overflow for each data type in use
* cleanup code, remove redundancies, improve codestyle
* fixing #101: make imports work for local and remote execution




4.3.1 (2020-04-29)
------------------

* BUGFIX #99: include the correct timezone_names.json in build
* wheel specific for the supported python versions (3.6, 3.7, 3.8)

4.3.0 (2020-04-28)
------------------

* updated the data to `2020a <https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2020a>`__
* added "extra" simplifying the installation of Numba
* added minimal required python version
* added minimal required version of the dependencies
* simplified and updated settings (e.g. reading current version from file)
* also testing python 3.8 now
* loading version from file

4.2.0 (2019-12-15)
------------------

* added option to specify the location of the binary data files to use. making it possible to easily point to own compiled data. also load timezone names json from this location
* make timezone names a class attribute (instead of a global variable)
* simplify code for opening and closing multiple binary files
* added tests for a specified path to the data
* testing multiple python3 versions automatically
* pinned new requirements
* importlib_resources removed from the dependencies
* added a documentation at: https://timezonefinder.readthedocs.io/en/latest/
* added contribution guidelines


4.1.0 (2019-07-07)
------------------

* updated the data to `2019b <https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2019b>`__
* added description of using vectorized input in readme



4.0.3 (2019-06-23)
------------------

* clarification of readme: referenced latest `timezonefinderL` release, better rst headlines, updated shield.io banner syntax
* clarification of speedup times (exponential notation)
* removed `six` and py2 dependency from tests
* minor updates to publishing routine
* minor improvement in timezone_at(): conversion coordinates to int later only when required


4.0.2 (2019-04-01)
------------------

* updated the data to `2019a <https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2019a>`__


4.0.1 (2019-03-12)
------------------

* BUGFIX: fixing #77 (missing dependency in setup.py)


4.0.0 (2019-03-12)
------------------

* ATTENTION: Dropped Python2 support (#72)! `six` dependency no longer required.
* BUGFIX: fixing #74 (broken py3 with numba support)
* added `in_memory`-mode (adapted unit tests to test both modes, added speed tests and explanation to readme)
* use of timeit in speed tests for more accurate results
* dropped use of kwargs_only decorator (can be implemented directly with python3)

3.4.2 (2019-01-15)
------------------

* BUGFIX: fixing #70 (broken py2.7 with numba support)
* added automatic tox tests for py2.7 py3 environments with numba installed
* fixed coverage report

3.4.1 (2019-01-13)
------------------

* added test cases for the Numba helpers (#55)
* added more polygon tests to test the function inside_polygon()
* added global data type definitions (format strings) to ``global_settings.py``
* removed tzwhere completely from the main tests (no comparison any more).
* removed code drafts for ahead of time compilation (#40)

3.4.0 (2019-01-06)
------------------

* updated the data to `2018i <https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2018i>`__
* introduced ``global_settings.py`` to globally define settings and get rid of "magic numbers".


3.3.0 (2018-11-17)
------------------

* updated the data to `2018g <https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2018g>`__



3.2.1 (2018-10-30)
------------------

* ATTENTION: the package ``importlib_resources`` is now required
* fixing automatic Conda build by exchanging ``pkg_resources.resource_stream`` with ``importlib_resources.open_binary``
* added tests for overflow in helpers.py/inside_polygon()


3.2.0 (2018-10-23)
------------------

* ATTENTION: the package `kwargs_only <https://github.com/adamchainz/kwargs-only>`__ is not a requirement any more!
* fixing #63 (kwargs_only not in conda) enabling automatic conda forge builds by directly providing the kwargs_only functionality again
* added example.py with the code examples from the readme
* fixing #62 (overflow happening because of using numpy.int32): forcing int64 type conversion



3.1.0 (2018-09-27)
------------------

* fixing typo in requirements.txt
* updated publishing routine: reminder to include all direct dependencies and to compile the requirements.txt with python 2 (pip-tools)


3.0.2 (2018-09-26)
------------------

* ATTENTION: the package `kwargs_only <https://github.com/adamchainz/kwargs-only>`__ is now required! This functionality has previously been implemented by the author directly within this package, but some code features got deprecated.
* updated build/testing/publishing routine
* fixing issue #61 (six dependency not listed in setup.py)
* no more default arguments for timezone_at() and certain_timezone_at()
* no more comparison to (py-)tzwhere in the tests (test_it.py)
* updated requirements.txt (removed tzwhere and dependencies)
* prepared helpers_test.py for also testing helpers_numba.py
* exchanged deprecated inspect.getargspec() into .getfullargspec() in functional.py


3.0.1 (2018-05-30)
------------------

* fixing minor issue #58 (readme not rendering in pyPI)


3.0.0 (2018-05-17)
------------------

* ATTENTION: the package six is now required! (was necessary because of the new testing routine. improves compatibility standards)
* updated build/testing/publishing routine
* updated the data to `2018d <https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2018d>`__
* fixing minor issue #52 (shortcuts being out of bounds for extreme coordinate values)
* the list of polygon ids in each shortcut is sorted after freq. of appearance of their zone id.
    this is critical for ruling out zones faster (as soon as just polygons of one zone are left this zone can be returned)
* using argparse package now for parsing the command line arguments
* added option of choosing between functions timezone_at() and certain_timezone_at() on the command line with flag -f
* the timezone names are now being stored in a readable JSON file
* adjusted the main test cases
* corrections and clarifications in the readme and code comments


2.1.2 (2017-11-20)
------------------

* bugfix: possibly uninitialized variable in closest_timezone_at()


2.1.1 (2017-11-20)
------------------

* updated the data to `2017c <https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2017c>`__
* minor improvements in code style and readme
* include publishing routine script


2.1.0 (2017-05-19)
------------------

* updated the data to `2017a <https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2017a>`__ (tz_world is not being maintained any more)
* the file_converter has been updated to parse the new format of .json files
* the new data is much bigger (based on OSM Data, +40MB). I am sorry for this but its still better than small outdated data!
* in case size and speed matter more you than actuality, you can still check out older versions of timezonefinder(L)
* the new timezone polygons are not limited to the coastlines, but they are including some large parts of the sea. This makes the results of closest_timezone_at() somewhat meaningless (as with timezonefinderL).
* the polygons can not be simplified much more and as a consequence timezonefinderL is not being updated any more.
* simplification functions (used for compiling the data for timezonefinderL) have been deleted from the file_converter
* the readme has been updated to inform about this major change
* some tests have been temporarily disabled (with tzwhere still using a very old version of tz_world, a comparison does not make too much sense atm)

2.0.1 (2017-04-08)
------------------

* added missing package data entries (2.0.0 didn't include all necessary .bin files)


2.0.0 (2017-04-07)
------------------

* ATTENTION: major change!: there is a second version of timezonefinder now: `timezonefinderL <https://github.com/jannikmi/timezonefinderL>`__. There the data has been simplified
    for increasing speed reducing data size. Around 56% of the coordinates of the timezone polygons have been deleted there. Around 60% of the polygons (mostly small islands) have been included in the simplified polygons.
    For any coordinate on landmass the results should stay the same, but accuracy at the shorelines is lost.
    This eradicates the usefulness of closest_timezone_at() and certain_timezone_at() but the main use case for this package (= determining the timezone of a point on landmass) is improved.
    In this repo timezonefinder will still be maintained with the detailed (unsimplified) data.
* file_converter.py has been complemented and modified to perform those simplifications
* introduction of new function get_geometry() for querying timezones for their geometric shape
* added shortcuts_unique_id.bin for instantly returning an id if the shortcut corresponding to the coords only contains polygons of one zone
* data is now stored in separate binaries for ease of debugging and readability
* polygons are stored sorted after their timezone id and size
* timezonefinder can now be called directly as a script (experimental with reduced functionality, cf. readme)
* optimisations on point in polygon algorithm
* small simplifications in the helper functions
* clarification of the readme
* clarification of the comments in the code
* referenced the new conda-feedstock in the readme
* referenced the new timezonefinder API/GUI



1.5.7 (2016-07-21)
------------------


* ATTENTION: API BREAK: all functions are now keyword-args only (to prevent lng lat mix-up errors)
* fixed a little bug with too many arguments in a @jit function
* clarified usage of the package in the readme
* prepared the usage of the ahead of time compilation functionality of Numba. It is not enabled yet.
* sorting the order of polygons to check in the order of how often their zones appear, gives a speed bonus (for closest_timezone_at)


1.5.6 (2016-06-16)
------------------

* using little endian encoding now
* introduced test for checking the proper functionality of the helper functions
* wrote tests for proximity algorithms
* improved proximity algorithms: introduced exact_computation, return_distances and force_evaluation functionality (s. Readme or documentation for more info)

1.5.5 (2016-06-03)
------------------

* using the newest version (2016d, May 2016) of the `tz world data`_
* holes in the polygons which are stored in the tz_world data are now correctly stored and handled
* rewrote the file_converter for storing the holes at the end of the timezone_data.bin
* added specific test cases for hole handling
* made some optimizations in the algorithms

1.5.4 (2016-04-26)
------------------

* using the newest version (2016b) of the `tz world data`_
* rewrote the file_converter for parsing a .json created from the tz_worlds .shp
* had to temporarily fix one polygon manually which had the invalid TZID: 'America/Monterey' (should be 'America/Monterrey')
* had to make tests less strict because tzwhere still used the old data at the time and some results were simply different now


1.5.3 (2016-04-23)
------------------

* using 32-bit ints for storing the polygons now (instead of 64-bit): I calculated that the minimum accuracy (at the equator) is 1cm with the encoding being used. Tests passed.
* Benefits: 18MB file instead of 35MB, another 10-30% speed boost (depending on your hardware)


1.5.2 (2016-04-20)
------------------

* added python 2.7.6 support: replaced strings in unpack (unsupported by python 2.7.6 or earlier) with byte strings
* timezone names are now loaded from a separate file for better modularity


1.5.1 (2016-04-18)
------------------

* added python 2.7.8+ support:
    Therefore I had to change the tests a little bit (some operations were not supported). This only affects output.
    I also had to replace one part of the algorithms to prevent overflow in Python 2.7


1.5.0 (2016-04-12)
------------------

* automatically using optimized algorithms now (when numba is installed)
* added TimezoneFinder.using_numba() function to check if the import worked


1.4.0 (2016-04-07)
------------------

* Added the ``file_converter.py`` to the repository: It converts the .csv from pytzwhere to another ``.csv`` and this one into the used ``.bin``.
    Especially the shortcut computation and the boundary storage in there save a lot of reading and computation time, when deciding which timezone the coordinates are in.
    It will help to keep the package up to date, even when the timezone data should change in the future.


    .. _tz world data: <http://efele.net/maps/tz/world/>
