"""Unit tests for the RST-report benchmark-name humanization and stats formatting."""

import pytest

from scripts.benchmark_utils import BenchmarkReporter
from scripts.render_benchmark_reports import (
    add_benchmark_table,
    add_comparison_bullet,
    add_fastest_slowest_bullet,
    format_duration,
    format_ratio,
    format_rate,
    humanize_benchmark_name,
    percent_faster,
    speedup_ratio,
    split_benchmark_label,
)
from tests.test_benchmark_names import EXPECTED_BENCHMARK_NAMES

pytestmark = pytest.mark.unit


def _fake_bench(name: str, mean: float = 1.0, rounds: int = 1) -> dict:
    return {
        "name": name,
        "stats": {
            "mean": mean,
            "median": mean,
            "stddev": 0.0,
            "min": mean,
            "max": mean,
            "rounds": rounds,
        },
    }


def _texts(reporter: BenchmarkReporter) -> list[str]:
    return [text for kind, text in reporter.content if kind == "text"]


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


@pytest.mark.parametrize(
    "seconds, expected",
    [
        (0.0, "0ms"),
        # human-friendly rounding: ~3 significant figures, fewer decimals as
        # the value grows, rather than a fixed number of decimals always
        (1.5, "1.50s"),
        (0.414, "414ms"),  # >=100 in-unit -> 0 decimals, not "414.000ms"
        (0.0537, "53.7ms"),  # >=10 in-unit -> 1 decimal
        (0.0015, "1.50ms"),  # <10 in-unit -> 2 decimals
        (9.4e-3, "9.40ms"),
        (2.8e-4, "280µs"),  # >=100 in-unit -> 0 decimals
        (2.5e-6, "2.50µs"),
        (1e-9, "1.00ns"),
    ],
)
def test_format_duration(seconds: float, expected: str):
    assert format_duration(seconds) == expected


@pytest.mark.parametrize(
    "rate, expected",
    [
        (999, "999/s"),  # below 1k: no suffix
        (106.4, "106/s"),
        (41_800, "41.8k/s"),  # k suffix, >=10 in-unit -> 1 decimal
        (947_438, "947k/s"),  # k suffix, >=100 in-unit -> 0 decimals
        (1_234_567, "1.23M/s"),  # M suffix, <10 in-unit -> 2 decimals
    ],
)
def test_format_rate(rate: float, expected: str):
    # abbreviated k/M suffixes read faster than a long digit run like
    # "1,234,567/s" - that's the point of "human friendly" here
    assert format_rate(rate) == expected


@pytest.mark.parametrize(
    "ratio, expected",
    [
        (1.3944, "1.39x"),  # <10 -> 2 decimals
        (12.083, "12.1x"),  # >=10 -> 1 decimal
        (192.297, "192x"),  # >=100 -> 0 decimals, not "192.30x"
    ],
)
def test_format_ratio(ratio: float, expected: str):
    assert format_ratio(ratio) == expected


def test_percent_faster_and_speedup_ratio():
    # 1.0s vs 0.5s: the faster one took half the time -> 50% faster, 2x
    assert percent_faster(slower_seconds=1.0, faster_seconds=0.5) == pytest.approx(50.0)
    assert speedup_ratio(slower_seconds=1.0, faster_seconds=0.5) == pytest.approx(2.0)


def test_add_benchmark_table_extra_columns_are_appended():
    benches = [_fake_bench("test_pt_in_poly_clang[small]", mean=0.001, rounds=42)]
    reporter = BenchmarkReporter(title="t", output_path="/dev/null")
    add_benchmark_table(
        reporter,
        benches,
        section_level=3,
        extra_columns=(("Throughput", lambda b: format_rate(1 / b["stats"]["mean"])),),
    )

    (_, headers, rows) = next(item for item in reporter.content if item[0] == "table")
    assert headers[-1] == "Throughput"
    assert rows[0][-1] == "1.00k/s"
    assert rows[0][-2] == "42"  # Rounds column untouched by the extra column


def test_add_comparison_bullet_picks_the_actually_faster_bench():
    # bench_a is passed first but is the *slower* one - the bullet must not
    # assume argument order, it must compare the JSON's mean values
    slow = _fake_bench("test_pt_in_poly_clang[small]", mean=0.002)
    fast = _fake_bench("test_pt_in_poly_python[small]", mean=0.001)
    reporter = BenchmarkReporter(title="t", output_path="/dev/null")

    add_comparison_bullet(reporter, "Small polygons", slow, fast)

    (text,) = _texts(reporter)
    assert "point-in-polygon (Python, Numba if available)" in text
    # fast=0.001s took half the time of slow=0.002s -> 50% faster, 2x
    assert "50% faster" in text
    assert "2.00x" in text
    # the slower one must still be named as the one being compared against
    assert "point-in-polygon (C/clang)" in text


def test_add_comparison_bullet_custom_label_fn_avoids_redundancy():
    in_memory = _fake_bench("test_timezone_at[random-in_memory]", mean=0.002)
    file_based = _fake_bench("test_timezone_at[random-file_based]", mean=0.003)
    reporter = BenchmarkReporter(title="t", output_path="/dev/null")

    add_comparison_bullet(
        reporter,
        "Random points",
        in_memory,
        file_based,
        label_fn=lambda b: "in-memory" if "in_memory" in b["name"] else "file-based",
    )

    (text,) = _texts(reporter)
    # the shared function name must not appear in the bullet body - the
    # whole point of a custom label_fn is not repeating it
    assert "TimezoneFinder.timezone_at()" not in text
    assert "**in-memory**" in text
    assert "**file-based**" in text


def test_add_comparison_bullet_negligible_difference_does_not_declare_a_winner():
    # a razor-thin, noise-level gap must not be reported as "0% faster" -
    # that reads as a false, uninformative signal
    a = _fake_bench("test_timezone_at[unique_shortcut-in_memory]", mean=0.001055)
    b = _fake_bench("test_timezone_at[unique_shortcut-file_based]", mean=0.001056)
    reporter = BenchmarkReporter(title="t", output_path="/dev/null")

    add_comparison_bullet(reporter, "Unique-shortcut points", a, b)

    (text,) = _texts(reporter)
    assert "about the same" in text
    assert "% faster" not in text


def test_add_fastest_slowest_bullet_reports_both_ends():
    benches = [
        _fake_bench("test_pt_in_poly_clang[small]", mean=0.001),
        _fake_bench("test_pt_in_poly_clang[large]", mean=0.05),
    ]
    reporter = BenchmarkReporter(title="t", output_path="/dev/null")

    add_fastest_slowest_bullet(reporter, benches, context="Overall")

    (text,) = _texts(reporter)
    assert "Overall" in text
    assert "small polygons" in text
    assert "large polygons" in text
    assert "98% faster" in text
