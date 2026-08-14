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
| `hole_boundary_redundancy.py` | That **96.4% of hole rings are a verbatim copy of some zone's boundary polygon** (release 2026c), which is what holes being stored as references rests on — see the *Holes as Boundary References* section of `docs/data_format.rst`. Also that the holes matching nothing are not geometric outliers but are fully covered by other zones, so they are an *ordering* question; the zone-precedence engine explored for them was rejected, because making timezone answers depend on hand-maintained political configuration is a real accuracy liability for a case that needs no resolution at all. Reads the upstream GeoJSON, so re-running it against a new release re-verifies the assumption. |
| `hole_removal_impact.py` | That **hole polygons cannot be dropped**, which is the natural next step after the deduplication above and looks safe until measured. Rewrites the hole files of a mirrored data directory and diffs `timezone_at`: dropping only the holes with no boundary twin changes 160 of 6,048 hole-interior answers, dropping all of them changes 1,703 — wrongly (`Asia/Hebron` → `Asia/Jerusalem`, `America/Argentina/Cordoba` → `America/Asuncion`). The companion script's finding that every hole is fully *covered* by other zones is true and insufficient: coverage says the right zone is among the shortcut candidates, ordering decides whether it is reached first. See issue #513. |
| `visualize_resolution_metrics.py` | Nothing on its own — an interactive Plotly view over the CSV `shortcut_split_bfs_bench.py` emits, used to read the result above. |

They need the `proto` dependency group:

```bash
uv sync --group proto
```
