"""Unit tests for the RST-report benchmark-name humanization and stats formatting."""

import re

import pytest

from scripts.benchmark_utils import BenchmarkReporter, add_system_status_section
from scripts.configs import (
    INITIALIZATION_REPORT_FILE,
    MEMORY_REPORT_FILE,
    PERFORMANCE_REPORT_FILE,
    POLYGON_REPORT_FILE,
)
from scripts.reporting import DATA_VERSION_LABEL, FIXTURE_VERSION_LABEL
from scripts.render_benchmark_reports import (
    PROVENANCE_FIELDS,
    acceleration_path_label,
    add_benchmark_table,
    add_comparison_bullet,
    add_fastest_slowest_bullet,
    add_headline_section,
    format_duration,
    format_ratio,
    format_rate,
    get_batch_size,
    get_fixture_provenance,
    humanize_benchmark_name,
    is_ci_tracked_configuration,
    percent_faster,
    render_initialization,
    render_memory,
    render_polygon,
    render_timezone_finding,
    speedup_ratio,
    split_benchmark_label,
)
from tests.auxiliaries import benchmark_fixture_provenance
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


# minimal shape of scripts.benchmark_utils.get_system_status(), enough for
# add_system_status_section() to render the parts this module asserts on
_FAKE_SYSTEM_INFO = {
    "python_version": "3.13.0",
    "python_implementation": "CPython",
    "platform_system": "Linux",
    "platform_machine": "x86_64",
    "platform_processor": "Unknown",
    "numpy_version": "2.0.0",
    "using_clang_pip": True,
    "using_numba": False,
}


def _texts(reporter: BenchmarkReporter) -> list[str]:
    # content items are heterogeneous tuples (sections carry a level, tables
    # carry headers and rows), so index rather than unpack
    return [item[1] for item in reporter.content if item[0] == "text"]


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
    # 1.0s vs 0.5s: the faster one took half the time -> twice as fast ->
    # 100% faster, 2x. percent_faster is anchored to the same "x times"
    # scale as speedup_ratio (ratio=2 <=> 100%), not the percent *time
    # reduction* ((slower-faster)/slower), which would give 50% here and,
    # worse, asymptotes toward 100% for arbitrarily large speedups - e.g. it
    # would report a 192x speedup as just "99% faster"
    assert percent_faster(slower_seconds=1.0, faster_seconds=0.5) == pytest.approx(
        100.0
    )
    assert speedup_ratio(slower_seconds=1.0, faster_seconds=0.5) == pytest.approx(2.0)


def test_percent_faster_stays_consistent_with_speedup_ratio_for_large_speedups():
    # regression test for the bug this formula fixes: a large speedup must
    # not read as a percentage that looks smaller than 100%
    ratio = speedup_ratio(slower_seconds=53.8e-3, faster_seconds=280e-6)
    pct = percent_faster(slower_seconds=53.8e-3, faster_seconds=280e-6)
    assert ratio == pytest.approx(192.14, rel=1e-3)
    assert pct == pytest.approx((ratio - 1) * 100)
    assert pct > 100  # a >100x speedup must read as well over 100% faster


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
    # fast=0.001s took half the time of slow=0.002s -> twice as fast -> 100% faster, 2x
    assert "100% faster" in text
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


def test_get_batch_size_reads_the_value_the_json_recorded():
    # regression test: rendering must use the batch size the *measured run*
    # recorded, not whatever benchmarks.conftest.BATCH_SIZE happens to be in
    # the checkout doing the rendering - that's what makes it safe to render
    # an older stored JSON after BATCH_SIZE has since changed
    assert get_batch_size({"batch_size": 500}) == 500
    assert get_batch_size({"batch_size": 1_000}) == 1_000


def test_get_batch_size_missing_raises_a_clear_error():
    with pytest.raises(ValueError, match="batch_size"):
        get_batch_size({"using_numba": True})


def test_get_fixture_provenance_reads_what_the_json_recorded():
    # same reasoning as the batch size above: the report must state the
    # fixture set and boundary data of the *measured run*, not those of
    # whichever checkout renders it
    system_info = {"fixture_version": 2, "data_version": "2026c", "batch_size": 1}

    assert get_fixture_provenance(system_info) == {
        "fixture_version": 2,
        "data_version": "2026c",
    }


@pytest.mark.parametrize("missing_field", PROVENANCE_FIELDS)
def test_get_fixture_provenance_missing_raises_a_clear_error(missing_field):
    system_info = {"fixture_version": 2, "data_version": "2026c"}
    del system_info[missing_field]

    with pytest.raises(ValueError, match=missing_field):
        get_fixture_provenance(system_info)


def test_rendered_system_status_stamps_the_input_provenance():
    # the point of the stamp: regenerating the fixtures or updating the
    # boundary data must leave the committed docs/benchmark_results_*.rst
    # visibly describing the older workload, instead of silently claiming to
    # describe the new one
    reporter = BenchmarkReporter(title="t", output_path="/dev/null")

    add_system_status_section(
        reporter,
        _FAKE_SYSTEM_INFO,
        provenance={"fixture_version": 2, "data_version": "2026c"},
    )

    texts = _texts(reporter)
    assert "**Fixture Version**: 2" in texts
    assert "**Timezone Data Version**: 2026c" in texts


@pytest.mark.parametrize(
    "using_numba, using_clang_pip, expected",
    [
        # utils.py prefers Numba when both are importable, so "both true" is
        # the Numba path and not an ambiguous state
        (True, True, "Numba JIT"),
        (True, False, "Numba JIT"),
        (False, True, "C extension (clang)"),
        (False, False, "pure Python"),
    ],
)
def test_acceleration_path_label_collapses_the_two_flags_to_the_live_path(
    using_numba, using_clang_pip, expected
):
    system_info = {"using_numba": using_numba, "using_clang_pip": using_clang_pip}

    assert acceleration_path_label(system_info) == expected


@pytest.mark.parametrize(
    "using_numba, using_clang_pip, expected",
    [
        (False, True, True),  # what a plain `pip install timezonefinder` gives you
        (True, True, False),  # a numba install would make this a different path
        (True, False, False),
        (False, False, False),
    ],
)
def test_is_ci_tracked_configuration(using_numba, using_clang_pip, expected):
    system_info = {"using_numba": using_numba, "using_clang_pip": using_clang_pip}

    assert is_ci_tracked_configuration(system_info) is expected


def test_headline_section_warns_when_the_run_is_not_the_ci_tracked_one():
    # the committed reports are rendered from a developer machine, so this is
    # the branch that ships: a reader must not compare these tables against the
    # trend chart, which measures a different implementation
    reporter = BenchmarkReporter(title="t", output_path="/dev/null")

    add_headline_section(reporter, _FAKE_SYSTEM_INFO | {"using_numba": True}, [])

    (banner,) = _texts(reporter)
    assert "Numba JIT" in banner
    assert "not comparable to the trend chart" in banner
    assert ":doc:`benchmarking_methodology`" in banner


def test_headline_section_says_so_when_the_run_is_the_ci_tracked_one():
    reporter = BenchmarkReporter(title="t", output_path="/dev/null")

    # _FAKE_SYSTEM_INFO is clang-without-numba, i.e. the tracked configuration
    add_headline_section(reporter, _FAKE_SYSTEM_INFO, [])

    (banner,) = _texts(reporter)
    assert "C extension (clang)" in banner
    assert "This is the configuration continuous integration tracks" in banner
    assert "not comparable" not in banner


def test_headline_section_describes_the_measured_environment():
    reporter = BenchmarkReporter(title="t", output_path="/dev/null")

    add_headline_section(reporter, _FAKE_SYSTEM_INFO, ["**~1.00ms** per thing"])

    headline, banner = _texts(reporter)
    assert headline == "**~1.00ms** per thing"
    # the environment named is the one recorded in the JSON, not the one
    # rendering the report
    assert "Linux x86_64" in banner
    assert "Python 3.13.0" in banner


# one benchmark per renderer, enough to exercise the full render path: the
# renderers tolerate a missing benchmark (headline blocks are conditional), so
# a minimal JSON still reaches the point where provenance is - or isn't -
# stamped
_RENDERERS = {
    "timezonefinding": (
        render_timezone_finding,
        "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
    ),
    "polygon": (
        render_polygon,
        "benchmarks/test_inside_polygon.py::test_pt_in_poly_clang[small]",
    ),
    "initialization": (
        render_initialization,
        "benchmarks/test_initialization.py::test_initialization[TimezoneFinder-file_based]",
    ),
    "memory": (render_memory, "memory::TimezoneFinder[file_based]::steady_heap"),
}


def _fake_benchmark_json(fullname: str) -> dict:
    return {
        "machine_info": {
            "timezonefinder": {
                **_FAKE_SYSTEM_INFO,
                "batch_size": 100,
                "fixture_version": 2,
                "data_version": "2026c",
            }
        },
        "benchmarks": [
            {**_fake_bench(fullname.split("::", 1)[1]), "fullname": fullname}
        ],
    }


@pytest.mark.parametrize("render, fullname", _RENDERERS.values(), ids=list(_RENDERERS))
def test_every_renderer_stamps_the_provenance_into_the_written_report(
    tmp_path, render, fullname
):
    # asserting on the file each renderer writes, not on
    # add_system_status_section() in isolation: a renderer that simply forgets
    # to pass `provenance=` still produces a complete, plausible-looking report,
    # and that omission is what leaves a page silently describing a workload
    # that no longer exists
    output_path = tmp_path / "report.rst"

    render(_fake_benchmark_json(fullname), output_path)

    text = output_path.read_text(encoding="utf-8")
    assert f"{FIXTURE_VERSION_LABEL}: 2" in text
    assert f"{DATA_VERSION_LABEL}: 2026c" in text


@pytest.mark.parametrize(
    "report_path",
    [
        PERFORMANCE_REPORT_FILE,
        POLYGON_REPORT_FILE,
        INITIALIZATION_REPORT_FILE,
        MEMORY_REPORT_FILE,
    ],
    ids=lambda path: path.name,
)
def test_committed_report_describes_the_current_benchmark_inputs(report_path):
    # the staleness alarm itself: regenerating the fixtures or updating the
    # boundary data without re-running `make reports` leaves these pages
    # describing the previous workload, and every number on them stays
    # plausible, so nothing else catches it
    provenance = benchmark_fixture_provenance()
    text = report_path.read_text(encoding="utf-8")

    for label, field in (
        (FIXTURE_VERSION_LABEL, "fixture_version"),
        (DATA_VERSION_LABEL, "data_version"),
    ):
        assert f"{label}: {provenance[field]}" in text, (
            f"{report_path.name} does not state {label}: {provenance[field]}. It was "
            "rendered from benchmark measurements taken against different inputs - "
            "re-measure and re-render with `make reports`."
        )


def test_headline_markup_never_nests_bold_and_literals():
    # RST inline markup does not nest: a ``literal`` inside **bold** renders
    # its backticks verbatim in the HTML instead of becoming a code span. This
    # shipped once and only showed up in the built docs, which emit no warning.
    reporter = BenchmarkReporter(title="t", output_path="/dev/null")

    add_headline_section(
        reporter,
        _FAKE_SYSTEM_INFO,
        ["**~389ms** to construct a ``TimezoneFinder`` in the default mode"],
    )

    for text in _texts(reporter):
        for bold_span in re.findall(r"\*\*(.+?)\*\*", text):
            assert "``" not in bold_span, f"nested literal in bold: {bold_span!r}"


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
    # 0.001s vs 0.05s -> 50x -> 4900% faster (not the old, misleadingly-small
    # 98% that (slower-faster)/slower would give for a 50x speedup)
    assert "4900% faster" in text
