# Prototypes

Exploratory studies that produced committed design decisions. They are kept because the decision
is easier to trust — and to revisit — when the measurement behind it is still readable.

These scripts are **not part of the package and not part of the test suite**. Nothing imports them,
CI never runs them, and the ruff linter and mypy both skip this directory (see
`.pre-commit-config.yaml`); only the formatter still applies. They are run by hand, against the
data in the checkout, and each one records its conclusion in a `FINDINGS` block at the top of the
file. Expect them to need adjustment before they run again.

| Script | What it established |
|---|---|
| `single_resolution_bench.py` | H3 **resolution 3** as the shortcut index resolution — the central algorithmic parameter of the package. Builds a separate index per resolution and measures the size/throughput trade-off; resolution 4 would push the index past 10% of the polygon data for gains that do not justify it. Cited from `docs/data_format.rst`. |
| `shortcut_split_bfs_bench.py` | That a **hierarchical** index is not worth building. Multi-resolution indices are larger than the single-resolution equivalent (the maximum resolution dominates the size), cells do not nest cleanly so parents must be retained anyway, and checking several resolutions costs more than it saves. The idea was dropped on this evidence. |
| `visualize_resolution_metrics.py` | Nothing on its own — an interactive Plotly view over the CSV `shortcut_split_bfs_bench.py` emits, used to read the result above. |

They need the `proto` dependency group:

```bash
uv sync --group proto
```
