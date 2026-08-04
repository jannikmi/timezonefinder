"""Unit tests for the RST-report benchmark-name humanization."""

import pytest

from scripts.benchmark_utils import BenchmarkReporter
from scripts.render_benchmark_reports import (
    add_benchmark_table,
    humanize_benchmark_name,
    split_benchmark_label,
)
from tests.test_benchmark_names import EXPECTED_BENCHMARK_NAMES

pytestmark = pytest.mark.unit


def _fake_bench(name: str, mean: float = 1.0) -> dict:
    return {
        "name": name,
        "stats": {
            "mean": mean,
            "median": mean,
            "stddev": 0.0,
            "min": mean,
            "max": mean,
            "rounds": 1,
        },
    }


@pytest.mark.parametrize(
    "raw_name, expected_label",
    [
        (
            "test_timezone_at[ambiguous_shortcut-in_memory]",
            "TimezoneFinder.timezone_at() - ambiguous-shortcut points, in-memory",
        ),
        (
            "test_timezone_at[on_land-file_based]",
            "TimezoneFinder.timezone_at() - on-land points, file-based",
        ),
        (
            "test_timezone_at_land[in_memory]",
            "TimezoneFinder.timezone_at_land() - in-memory",
        ),
        (
            "test_timezone_at_timezonefinderl",
            "TimezoneFinderL.timezone_at() (ambiguous-shortcut points)",
        ),
        (
            "test_pt_in_poly_clang[large]",
            "point-in-polygon (C/clang) - large polygons",
        ),
        (
            "test_initialization[TimezoneFinder-in_memory]",
            "Initialization - TimezoneFinder, in-memory",
        ),
    ],
)
def test_humanize_benchmark_name(raw_name: str, expected_label: str):
    assert humanize_benchmark_name(raw_name) == expected_label


def test_humanize_benchmark_name_unmapped_fragment_falls_back():
    # an unmapped function/param still renders (underscores -> spaces)
    # instead of erroring, so a new benchmark doesn't break report rendering
    assert humanize_benchmark_name("test_something_new[weird_param]") == (
        "test_something_new - weird param"
    )


def test_humanize_benchmark_name_covers_every_expected_benchmark():
    for fullname in EXPECTED_BENCHMARK_NAMES:
        raw_name = fullname.split("::", 1)[1]
        label = humanize_benchmark_name(raw_name)
        assert label
        assert "[" not in label and "]" not in label


@pytest.mark.parametrize(
    "raw_name, expected_func, expected_params",
    [
        (
            "test_timezone_at[ambiguous_shortcut-in_memory]",
            "TimezoneFinder.timezone_at()",
            "ambiguous-shortcut points, in-memory",
        ),
        (
            "test_timezone_at_timezonefinderl",
            "TimezoneFinderL.timezone_at() (ambiguous-shortcut points)",
            "",
        ),
        (
            "test_pt_in_poly_clang[small]",
            "point-in-polygon (C/clang)",
            "small polygons",
        ),
    ],
)
def test_split_benchmark_label(raw_name: str, expected_func: str, expected_params: str):
    assert split_benchmark_label(raw_name) == (expected_func, expected_params)


def test_add_benchmark_table_hoists_shared_function_label_out_of_rows():
    # regression test: a table must not repeat the same FUNCTION_LABELS
    # prefix in every row - it belongs in a section heading instead
    benches = [
        _fake_bench("test_pt_in_poly_clang[small]"),
        _fake_bench("test_pt_in_poly_clang[medium]"),
        _fake_bench("test_pt_in_poly_clang[large]"),
    ]
    reporter = BenchmarkReporter(title="t", output_path="/dev/null")
    add_benchmark_table(reporter, benches, section_level=3)

    sections = [item for item in reporter.content if item[0] == "section"]
    tables = [item for item in reporter.content if item[0] == "table"]
    assert [title for _, title, _ in sections] == ["point-in-polygon (C/clang)"]

    (_, _, rows) = tables[0]
    assert len(rows) == 3
    for row in rows:
        # the function label lives in the section heading now, not the row
        assert "point-in-polygon" not in row[0]
    assert {row[0] for row in rows} == {
        "small polygons",
        "medium polygons",
        "large polygons",
    }


def test_add_benchmark_table_groups_multiple_functions_separately():
    benches = [
        _fake_bench("test_timezone_at[on_land-in_memory]"),
        _fake_bench("test_timezone_at_land[in_memory]"),
    ]
    reporter = BenchmarkReporter(title="t", output_path="/dev/null")
    add_benchmark_table(reporter, benches, section_level=3)

    sections = [title for kind, title, _ in reporter.content if kind == "section"]
    assert sections == [
        "TimezoneFinder.timezone_at()",
        "TimezoneFinder.timezone_at_land()",
    ]

    tables = [item for item in reporter.content if item[0] == "table"]
    assert len(tables) == 2
    assert all(len(rows) == 1 for _, _, rows in tables)
