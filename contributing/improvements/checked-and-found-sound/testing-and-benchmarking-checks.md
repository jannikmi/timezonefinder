# Testing and benchmarking checks

Do not re-raise these findings without new evidence.

- Pass 4: `scripts/describe_benchmark_machine.py` (read in full, nothing found); the three
  `benchmarks/test_*.py` suites (thin by design — parametrize tables plus a `_run_over` loop, and
  the shared `_run_over` in two of them is deliberately not hoisted into `conftest.py`, since an
  import would put a function call between the benchmark and the code it times);
  `render_benchmark_reports.py`'s four `render_*` functions sharing a load/headline/table/summary
  shape — extracting it would trade four readable functions for a framework, and the differences
  are exactly the report-specific parts.

- Pass 5: `scripts/measure_memory.py` (read in full, nothing found);
  `benchmarks/test_inside_polygon.py`'s `STRATA` list, which repeats the `PIP_STRATA` names as
  explicit `pytest.param` ids — deliberate, since the
  [benchmarking rules](../../development/benchmarking-and-performance-validation.md) require ids to be
  written out rather than derived, and deriving them from a data file would let a fixture
  regeneration silently reset chart history; `tests/main_test.py`'s `test_edge_shortcut_validity`,
  which asserts nothing beyond "does not raise" on the base class — that *is* its subject, and
  `test_edge_shortcut_result` covers the expected values for the class that has polygon data.

- Pass 6: `tests/test_benchmark_ci_tooling.py` and `tests/test_render_benchmark_reports.py` (both
  read in full, nothing found — each assertion names why it exists); `tests/auxiliaries.py`'s
  `matches_pattern`, whose `fnmatch` semantics (`*` crosses `/`, POSIX case sensitivity) are what
  the packaging patterns depend on and are correct as documented; the `.git/*` entry in
  `UNWANTED_DIST_PATTERNS`, which matches nothing in a working tree by design and is exempted
  rather than removed.
