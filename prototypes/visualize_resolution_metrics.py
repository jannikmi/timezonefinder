"""Interactive visualisation for hierarchical shortcut benchmark metrics.

Reads the CSV emitted by ``prototypes/shortcut_split_bfs_bench.py`` (stored by
default under ``plots/hierarchical_metrics.csv``) and opens a few Plotly-based
figures to explore all metrics interactively:

* a scatter matrix across every recorded metric,
* a resolution grid scatter (``max_res`` vs ``min_res``) coloured by a selected
  metric,
* a parallel coordinates view to inspect trade-offs holistically.

Run with::

    uv run python prototypes/visualize_resolution_metrics.py

Adjust ``DEFAULT_CSV_PATH`` below if the metrics CSV lives elsewhere.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd
import plotly.express as px
import plotly.io as pio

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV_PATH = ROOT / "plots" / "hierarchical_metrics.csv"


BASE_METRIC_COLUMNS: tuple[str, ...] = (
    "mean_throughput_kpts",
    "median_ns",
    "max_ns",
    "binary_size_mib",
    "unique_surface_fraction",
    "unique_entry_fraction",
    "zone_entries",
    "polygon_entries",
    "polygon_ids",
    "total_entries",
    "coverage_ratio",
)


def ensure_metrics_present(df: pd.DataFrame, columns: Iterable[str]) -> None:
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise KeyError("Missing required columns in metrics CSV: " + ", ".join(missing))


def load_metrics(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Cannot find metrics CSV at {csv_path}. Run the benchmark first."
        )

    df = pd.read_csv(csv_path)
    ensure_metrics_present(df, ("min_res", "max_res", "binary_size_bytes"))
    df["binary_size_mib"] = df["binary_size_bytes"] / (1024**2)
    ensure_metrics_present(df, BASE_METRIC_COLUMNS)
    return df


def show_scatter_matrix(df: pd.DataFrame, metrics: list[str]) -> None:
    fig = px.scatter_matrix(
        df,
        dimensions=metrics,
        color="min_res",
        symbol="max_res",
        hover_data={col: True for col in df.columns},
        title="Metric scatter matrix",
    )
    fig.update_traces(diagonal_visible=False, showupperhalf=False)
    fig.update_layout(height=900, width=1200)
    fig.show()


def show_resolution_scatter(df: pd.DataFrame, metric: str) -> None:
    fig = px.scatter(
        df,
        x="max_res",
        y="min_res",
        color=metric,
        size="binary_size_mib",
        hover_data={col: True for col in df.columns},
        title=f"Resolution grid coloured by {metric}",
        color_continuous_scale="Viridis",
    )
    fig.update_layout(yaxis=dict(dtick=1), xaxis=dict(dtick=1))
    fig.show()


def show_parallel_coordinates(df: pd.DataFrame, metrics: list[str]) -> None:
    fig = px.parallel_coordinates(
        df,
        color="mean_throughput_kpts",
        dimensions=["min_res", "max_res", *metrics],
        color_continuous_scale=px.colors.sequential.Viridis,
        title="Parallel coordinates across metrics",
    )
    fig.show()


def main() -> None:
    csv_path = DEFAULT_CSV_PATH
    print(f"Loading metrics from {csv_path} ...")
    df = load_metrics(csv_path)
    print(f"Loaded {len(df)} (min_res, max_res) combinations. Opening figures...")

    res_check_cols = sorted(col for col in df.columns if col.startswith("res_checks_r"))
    metrics = list(BASE_METRIC_COLUMNS) + res_check_cols

    # Prefer opening in the browser if running from the CLI.
    if pio.renderers.default in {"notebook", "notebook_connected"}:
        pio.renderers.default = "browser"

    show_scatter_matrix(df, metrics)
    show_resolution_scatter(df, "mean_throughput_kpts")
    show_resolution_scatter(df, "median_ns")
    show_parallel_coordinates(df, metrics)


if __name__ == "__main__":
    main()
