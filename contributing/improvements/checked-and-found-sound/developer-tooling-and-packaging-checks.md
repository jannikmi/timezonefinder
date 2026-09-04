# Developer tooling and packaging checks

Do not re-raise these findings without new evidence.

- **Report calculations and typing:** `calculate_shortcut_index_stats`'s `naive_storage_bytes` conditional covers the whole parenthesized expression, so a zero entry count yields `0 * 0` rather than `ZeroDivisionError`; this is correct despite being easy to misread. `generate_metrics_rows`'s non-numeric `str(value)` fallback remains reachable through `Mapping[str, object]` rather than being deleted to satisfy an artificially narrow annotation.

- **Corrected output-redirection finding, now settled:** `scripts/reporting.py` once held two redirectors—`redirect_output_to_file`, opening `"a"`, and `redirect_output_to_file_contextmanager`, opening `"w"`—judged non-duplicates because callers depended on append versus truncate. That answered the wrong question: neither should have existed. Both are deleted; every report renderer returns its RST and `join_lines` is the one place that turns blocks into text. Do not reintroduce stdout as a return channel here: it is what bound a report's destination to wherever the redirection was set up.
