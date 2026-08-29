# Developer tooling and packaging checks

Do not re-raise these findings without new evidence.

- **Report calculations and typing:** `calculate_shortcut_index_stats`'s `naive_storage_bytes` conditional covers the whole parenthesized expression, so a zero entry count yields `0 * 0` rather than `ZeroDivisionError`; this is correct despite being easy to misread. `generate_metrics_rows`'s non-numeric `str(value)` fallback remains reachable through `Mapping[str, object]` rather than being deleted to satisfy an artificially narrow annotation.

- **Corrected output-redirection finding:** `scripts/reporting.py`'s two redirectors—`redirect_output_to_file`, opening `"a"`, and `redirect_output_to_file_contextmanager`, opening `"w"`—were once judged non-duplicates because callers depended on append versus truncate. That answered the wrong question: neither should exist. TOOL-6's decision has renderers return strings, after which append mode and both redirectors have no callers. Do not treat the original distinction as evidence that the current design is sound.
