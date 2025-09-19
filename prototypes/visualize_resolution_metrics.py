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
import numpy as np
import seaborn as sns
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV_PATH = ROOT / "plots" / "hierarchical_metrics.csv"

try:
    from prototypes.shortcut_split_bfs_bench import RESOLUTIONS as BENCHMARK_RESOLUTIONS
except ImportError:  # pragma: no cover - fallback for standalone usage
    BENCHMARK_RESOLUTIONS = None


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
    if BENCHMARK_RESOLUTIONS is not None:
        allowed = set(BENCHMARK_RESOLUTIONS)
        # Filtering here keeps existing CSVs usable when the benchmark's resolution window shrinks,
        # so there is no need to rerun the benchmark just to regenerate metrics.
        df = df[df["min_res"].isin(allowed) & df["max_res"].isin(allowed)]
        expected_pairs = {
            (min_res, max_res)
            for min_res in allowed
            for max_res in allowed
            if max_res >= min_res
        }
        present_pairs = set(zip(df["min_res"], df["max_res"]))
        missing_pairs = sorted(expected_pairs - present_pairs)
        if missing_pairs:
            formatted = ", ".join(f"({a}, {b})" for a, b in missing_pairs[:10])
            suffix = "" if len(missing_pairs) <= 10 else ", ..."
            print(
                "Warning: metrics CSV is missing "
                f"{len(missing_pairs)} expected (min_res, max_res) pairs "
                f"({formatted}{suffix})."
            )
            print(
                "         Rerun 'uv run python prototypes/shortcut_split_bfs_bench.py' "
                "to refresh the metrics."
            )
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
    raw_sizes = df["binary_size_mib"].fillna(0.0).to_numpy()
    if raw_sizes.size == 0:
        return

    max_size = raw_sizes.max()
    if max_size <= 0:
        raw_sizes = np.ones_like(raw_sizes)
        max_size = 1.0

    positive_sizes = raw_sizes[raw_sizes > 0]
    min_positive = positive_sizes.min() if positive_sizes.size else max_size
    sizes = np.where(raw_sizes > 0, raw_sizes, min_positive)

    size_max = 40
    sizeref = 2.0 * max_size / (size_max**2)

    fig = px.scatter(
        df,
        x="max_res",
        y="min_res",
        color=metric,
        size=sizes,
        size_max=size_max,
        hover_data={col: True for col in df.columns},
        title=f"Resolution grid coloured by {metric}",
        color_continuous_scale="Viridis",
    )

    fig.update_traces(
        marker=dict(sizemode="area", sizeref=sizeref), selector=dict(mode="markers")
    )

    if max_size > 0:
        sample_values = np.linspace(min_positive, max_size, num=4)
        sample_values = np.unique(np.round(sample_values, 3))
        for value in sample_values:
            fig.add_scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(
                    size=[value],
                    sizemode="area",
                    sizeref=sizeref,
                    color="rgba(0, 0, 0, 0.45)",
                ),
                showlegend=True,
                name=f"{value:.3f} MiB",
                legendgroup="size",
            )

    fig.update_layout(
        yaxis=dict(dtick=1),
        xaxis=dict(dtick=1),
        legend=dict(title="Marker size = binary size (MiB)", itemsizing="constant"),
    )
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


def show_size_throughput_scatter(
    df: pd.DataFrame, *, x: str, y: str, title: str
) -> None:
    fig = px.scatter(
        df,
        x=x,
        y=y,
        color="min_res",
        symbol="max_res",
        size="coverage_ratio",
        hover_data={col: True for col in df.columns},
        title=title,
    )
    fig.update_layout(legend=dict(title="min_res / max_res", itemsizing="constant"))
    fig.show()


def save_heatmaps(df: pd.DataFrame, output_dir: Path) -> None:
    heatmap_specs = [
        ("mean_throughput_kpts", "Average throughput (random queries; k/s)"),
        ("median_ns", "Median latency (random queries; ns)"),
        ("max_ns", "Max latency (random queries; ns)"),
        ("binary_size_mib", "Binary size (MiB)"),
        ("unique_surface_fraction", "Unique surface fraction (sum)"),
        ("unique_entry_fraction", "Unique entry fraction"),
        ("coverage_ratio", "Coverage fraction (sum)"),
    ]

    res_check_cols = sorted(col for col in df.columns if col.startswith("res_checks_r"))
    for col in res_check_cols:
        heatmap_specs.append(
            (col, f"Shortcut checks at resolution {col.split('r')[-1]}")
        )

    sns.set_theme(style="white")
    output_dir.mkdir(parents=True, exist_ok=True)
    for column, title in heatmap_specs:
        if column not in df.columns:
            continue
        pivot = df.pivot(index="min_res", columns="max_res", values=column)
        pivot = pivot.reindex(index=sorted(df["min_res"].unique()))
        pivot = pivot.reindex(columns=sorted(df["max_res"].unique()))

        mask = np.zeros_like(pivot, dtype=bool)
        for i, min_res in enumerate(pivot.index):
            for j, max_res in enumerate(pivot.columns):
                if max_res < min_res:
                    mask[i, j] = True

        plt.figure(figsize=(8, 6))
        sns.heatmap(
            pivot,
            mask=mask,
            cmap="viridis",
            annot=False,
            cbar_kws={"label": title},
        )
        plt.title(title)
        plt.xlabel("max_res")
        plt.ylabel("min_res")
        plt.tight_layout()
        path = output_dir / f"heatmap_{column}.png"
        plt.savefig(path, dpi=200)
        plt.close()
        print(f"  - Saved {path}")


def save_size_throughput_plots(df: pd.DataFrame, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    plot_df = df.copy()
    raw_sizes = plot_df["binary_size_mib"].fillna(0.0)
    positive = raw_sizes[raw_sizes > 0]
    min_positive = positive.min() if not positive.empty else 1.0
    plot_df["plot_size"] = np.where(raw_sizes > 0, raw_sizes, min_positive)

    def _scatter(x: str, y: str, filename: str, xlabel: str, ylabel: str) -> None:
        plt.figure(figsize=(8, 6))
        sns.scatterplot(
            data=plot_df,
            x=x,
            y=y,
            hue="min_res",
            style="max_res",
            size="plot_size",
            sizes=(40, 400),
            palette="viridis",
            legend="brief",
        )
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.title(f"{ylabel} vs {xlabel}")
        plt.tight_layout()
        path = output_dir / filename
        plt.savefig(path, dpi=200)
        plt.close()
        print(f"  - Saved {path}")

    _scatter(
        x="binary_size_mib",
        y="mean_throughput_kpts",
        filename="scatter_size_vs_throughput.png",
        xlabel="Binary size (MiB)",
        ylabel="Mean throughput (k queries/s)",
    )
    _scatter(
        x="mean_throughput_kpts",
        y="binary_size_mib",
        filename="scatter_throughput_vs_size.png",
        xlabel="Mean throughput (k queries/s)",
        ylabel="Binary size (MiB)",
    )


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

    plots_dir = csv_path.parent
    print("\nGenerating static heatmaps...")
    save_heatmaps(df, plots_dir)
    print("Generating static throughput/size plots...")
    save_size_throughput_plots(df, plots_dir)

    show_scatter_matrix(df, metrics)
    show_resolution_scatter(df, "mean_throughput_kpts")
    show_resolution_scatter(df, "median_ns")
    show_size_throughput_scatter(
        df,
        x="binary_size_mib",
        y="mean_throughput_kpts",
        title="Binary size vs mean throughput",
    )
    show_size_throughput_scatter(
        df,
        x="mean_throughput_kpts",
        y="binary_size_mib",
        title="Mean throughput vs binary size",
    )
    show_parallel_coordinates(df, metrics)


if __name__ == "__main__":
    main()
