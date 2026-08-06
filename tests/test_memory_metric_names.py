"""Pin the exact set of metric names `scripts/measure_memory.py` can emit.

Memory metric names are the join key for the memory trend chart
(.github/workflows/benchmark.yml), exactly as benchmark node ids are for the
timing one - see tests/test_benchmark_names.py, which exists for the same
reason. `benchmark-action/github-action-benchmark` stores each point under its
name, so renaming a metric (or adding a configuration) silently starts a brand
new history instead of continuing the old one: no error, no warning, just a
chart that begins again from today.

Unlike the benchmark suite, these names are not produced by pytest collection,
so there is no `--collect-only` to compare against. They are built from
`CONFIGS` and the metric tuples instead, which is what this pins.
"""

import pytest

from scripts.measure_memory import (
    CONFIG_METRICS,
    CONFIGS,
    HEAP_METRICS,
    IMPORT_METRIC_NAME,
    expected_metric_names,
)
from scripts.export_memory_chart_json import is_charted

EXPECTED_METRIC_NAMES = {
    "memory::import::rss",
    "memory::TimezoneFinder[in_memory]::init_heap",
    "memory::TimezoneFinder[in_memory]::init_rss",
    "memory::TimezoneFinder[in_memory]::steady_heap",
    "memory::TimezoneFinder[in_memory]::steady_rss",
    "memory::TimezoneFinder[file_based]::init_heap",
    "memory::TimezoneFinder[file_based]::init_rss",
    "memory::TimezoneFinder[file_based]::steady_heap",
    "memory::TimezoneFinder[file_based]::steady_rss",
    "memory::TimezoneFinderL::init_heap",
    "memory::TimezoneFinderL::init_rss",
    "memory::TimezoneFinderL::steady_heap",
    "memory::TimezoneFinderL::steady_rss",
}

# the subset actually plotted: heap only, because RSS counts memory-mapped
# pages whose residency is decided by machine-wide pressure rather than by this
# code (see scripts/export_memory_chart_json.py)
EXPECTED_CHARTED_METRIC_NAMES = {
    "memory::TimezoneFinder[in_memory]::init_heap",
    "memory::TimezoneFinder[in_memory]::steady_heap",
    "memory::TimezoneFinder[file_based]::init_heap",
    "memory::TimezoneFinder[file_based]::steady_heap",
    "memory::TimezoneFinderL::init_heap",
    "memory::TimezoneFinderL::steady_heap",
}


@pytest.mark.unit
def test_expected_metric_names():
    collected = expected_metric_names()
    assert collected == EXPECTED_METRIC_NAMES, (
        "scripts/measure_memory.py emits a different set of metric names than "
        "expected - if this is an intentional rename/addition/removal, update "
        "EXPECTED_METRIC_NAMES in this test (and be aware the rename orphans "
        "the old metric's chart history). "
        f"missing: {EXPECTED_METRIC_NAMES - collected}, "
        f"unexpected: {collected - EXPECTED_METRIC_NAMES}"
    )


@pytest.mark.unit
def test_expected_charted_metric_names():
    collected = {name for name in expected_metric_names() if is_charted(name)}
    assert collected == EXPECTED_CHARTED_METRIC_NAMES, (
        "the set of metrics pushed to the trend chart changed - if intentional, "
        "update EXPECTED_CHARTED_METRIC_NAMES in this test. "
        f"missing: {EXPECTED_CHARTED_METRIC_NAMES - collected}, "
        f"unexpected: {collected - EXPECTED_CHARTED_METRIC_NAMES}"
    )


@pytest.mark.unit
def test_every_config_reports_every_metric():
    """No configuration may quietly skip a metric.

    The chart compares configurations against each other, so a mode that
    reports three of the four numbers would leave a gap that reads as a
    measurement rather than as an omission.
    """
    names = expected_metric_names() - {IMPORT_METRIC_NAME}
    assert len(names) == len(CONFIGS) * len(CONFIG_METRICS)


@pytest.mark.unit
def test_heap_metrics_are_a_subset_of_all_metrics():
    """The charted metrics must exist among those actually measured.

    `scripts/export_memory_chart_json.py` selects charted metrics by suffix; a
    heap metric renamed in one place and not the other would silently produce
    an empty chart payload.
    """
    assert set(HEAP_METRICS) <= set(CONFIG_METRICS)
