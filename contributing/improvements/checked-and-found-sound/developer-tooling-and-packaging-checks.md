# Developer tooling and packaging checks

Do not re-raise these findings without new evidence.

- Pass 8: `calculate_shortcut_index_stats`'s `naive_storage_bytes`, whose conditional covers the whole
  parenthesised expression rather than just the division, so a zero entry count yields `0 * 0` and
  not a `ZeroDivisionError` — correct, and confusing enough to re-derive rather than re-raise;
  `generate_metrics_rows`'s non-numeric `str(value)` fallback, kept reachable by annotating the
  parameter `Mapping[str, object]` rather than deleted to satisfy a narrower annotation.

- Pass 8, **superseded 2026-08-21 — kept with the correction rather than deleted**, because the site
  still looks defensible and the next pass would otherwise re-derive it: `scripts/reporting.py`'s two
  output redirectors, `redirect_output_to_file` (a decorator, opening `"a"`) and
  `redirect_output_to_file_contextmanager` (opening `"w"`), were recorded as *not* duplicates,
  differing in append-vs-truncate with callers depending on which they got. That was true, and it
  answered the wrong question: neither should exist. TOOL-6's decision has the renderers return
  strings, after which append mode has no caller and both redirectors have none. Do not conclude
  from the original note that they are fine as they are.
