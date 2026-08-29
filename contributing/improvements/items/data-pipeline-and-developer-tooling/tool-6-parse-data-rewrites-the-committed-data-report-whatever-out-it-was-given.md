# TOOL-6 — `parse_data` rewrites the committed data report whatever `-out` it was given

- **Location:** `scripts/file_converter.py`, `parse_data`'s call to
  `write_data_report_from_binary`; `scripts/reporting.py`, `write_data_report_from_binary`, which
  writes to `DATA_REPORT_FILE` (`scripts/configs.py`, anchored at the checkout's `docs/`).
- **Defect:** the function's `data_path` selects which binaries to *read*; the destination is fixed.
  So `make testparse`, which parses `tests/test_input.json` into `tmp/parsed_data`, leaves the
  committed `docs/data_report.rst` describing the three-zone fixture — as does any user following
  `docs/2_use_cases.rst` with their own `-out`. Nothing warns, and the report is a generated file
  nobody re-reads, so the corruption is only caught by `git status`.
- **Fix:** write the report beside the parsed data when the output directory is not the packaged
  one, or have `parse_data` skip the report for a non-default `-out` and leave it to
  `make reports`. Size: ~10 lines.
- **Both fixes above were the wrong shape, and the better one is to delete the decorator.**
  `redirect_output_to_file` is applied exactly three times, all in `scripts/reporting.py`, all with
  the same constant, over three functions called consecutively from the one place. It is not an
  abstraction — it is the *reason* the destination cannot be a parameter, because a decorator binds
  its argument at import time. Removing it collapses the problem:

  ```python
  def write_data_report_from_binary(data_path=..., report_path=DATA_REPORT_FILE):
      data = load_binary_data(data_path)
      with redirect_output_to_file_contextmanager(report_path):  # opens "w"
          report_data_statistics(...)
          print_shortcut_statistics(...)
          report_file_sizes(...)
  ```

  The destination becomes an ordinary defaulted parameter, which is all `parse_data` ever needed.
  Four things fall out that neither earlier option got:
  - the `if DATA_REPORT_FILE.exists(): unlink()` dance goes, because the context manager opens
    `"w"` and truncates. The current code truncates then appends three times; one truncating block
    around all three is byte-identical output
  - the file is opened **once** instead of three times
  - the three functions become plain functions that `print`, testable with `capsys` instead of by
    writing a file and reading it back — none of them has a test today
  - `main()`'s `--data-path` gains a matching `--out`, closing the same defect in the CLI, which has
    it too
- **Interacts with a *Deliberately checked and found sound* entry**, which has to be updated rather
  than quietly contradicted: pass 8 recorded that the decorator and the context manager "look like
  duplicates but differ in append-vs-truncate, and both have callers that depend on which they got".
  That was true. It stops being true here — with one block around all three calls, append mode has
  no caller left and the decorator goes with it. `redirect_output_to_file_contextmanager` stays;
  `scripts/benchmark_utils.py` uses it.
- **Neutrality is provable in seconds**, which is what makes this safe: `uv run python -m
  scripts.reporting`, then confirm `git diff docs/data_report.rst` is empty. Verified 2026-08-21
  that the committed report already regenerates byte-identically from the packaged data, so the
  diff is a real signal rather than a coin toss.
- **Size:** ~40 lines, most of it deletion. **Still a behaviour change** for anyone calling
  `parse_data(output_path=...)` — they get their report next to their data instead of overwriting
  the checkout's — which is the change worth having.
- **Decided, 2026-08-21 — go further than deleting the decorator: the renderers return strings.**
  The decorator is a symptom; the defect is that these functions use **stdout as a return channel**,
  and redirection — decorator or context manager — is the workaround for that. Turning
  `print_rst_table` into `render_rst_table() -> str` and the three report functions into
  string-returning functions leaves `write_data_report_from_binary` as
  `report_path.write_text(render_report(data))`, with **no stdout redirection anywhere in
  `scripts/`**. Chosen over deleting only the decorator (~40 lines, keeps the workaround
  parameterised) and over threading a `file=` argument through every helper (~50 lines, puts I/O
  into pure formatting code).
- **What makes it reachable rather than a rewrite:**
  - the module is **already half-converted** — `rst_title` returns a string, `print_rst_table`
    prints. That one helper is the keystone, and it is imported by *both* report generators
  - `BenchmarkReporter` (`scripts/benchmark_utils.py`) already accumulates `(kind, …)` tuples and
    renders once, and still reaches for `redirect_output_to_file_contextmanager` in `write_report`
    **because** `print_rst_table` prints. Fixing the helper frees it too, so **both redirectors lose
    their last caller and are deleted** — not just the decorator
  - `main()` and `load_binary_data` also print, and that output is genuine console progress that
    must **not** reach `docs/data_report.rst`. Today it stays out only because of where those calls
    sit; afterwards the separation is structural. Moving one `print("Loading…")` inside a decorated
    function currently ships it in the committed docs page
  - `print_frequencies` and `print_polygon_distribution_table` are tested through `capsys` in
    `tests/utils_test.py`; they become plain return-value assertions
- **Size:** ~150 lines touched, **net deletion**. `main()` gains the `--out` it is missing, which
  closes the same defect in the CLI.
- **Verification, both halves confirmed available 2026-08-21:** `uv run python -m scripts.reporting`
  then an empty `git diff docs/data_report.rst`; and
  `uv run python -m scripts.render_benchmark_reports --benchmark-json=tmp/benchmark.json` then an
  empty diff on the three benchmark pages. **Omit `--memory-json`** — the stored `tmp/memory.json`
  is not the one behind the committed memory page and rewrites it.
- **Still a behaviour change** for anyone calling `parse_data(output_path=…)`: the report lands
  beside their data instead of overwriting the checkout's. Changelog bullet in the **Internal** list.
- **Status:** open — decision taken, implementation not started.
- **Last touched:** 2026-08-21 — re-scoped twice and decided. The decorator was not the defect
  either; stdout-as-return-channel is.
