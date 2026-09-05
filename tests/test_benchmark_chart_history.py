"""Cover the one-off restatement of the stored trend history.

`scripts/migrate_benchmark_chart_history.py` rewrites the points already on
`gh-pages` so the switch from the action's `pytest` extractor (batches per
second, under a raw node id) to `scripts/export_timing_chart_json.py`
(lookups/sec, under the docs' labels) continues each metric's history instead
of orphaning it.

It runs once, by hand, against a branch CI owns - which is exactly why its
behaviour is pinned here instead of being checked by reading the diff: a
mistake in it is a silently wrong 100+ point chart that nothing recomputes.
"""

import json

import pytest

from scripts.migrate_benchmark_chart_history import (
    DEFAULT_SUITE,
    dump_data_js,
    load_data_js,
    migrate,
)

MEMORY_SUITE = "memory footprint (heap, min)"

# one stored point, in the shape the action's pytest extractor wrote
STORED_BENCH = {
    "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
    "value": 200.0,
    "unit": "iter/sec",
    "range": "stddev: 0.0001",
    "extra": "mean: 5.0 msec\nrounds: 153 on AMD EPYC 9V74 80-Core Processor @ 3.1 GHz",
}


def _data(*benches: dict) -> dict:
    return {
        "lastUpdate": 1,
        "repoUrl": "https://github.com/jannikmi/timezonefinder",
        "entries": {
            DEFAULT_SUITE: [{"commit": {"id": "abc"}, "benches": list(benches)}],
            MEMORY_SUITE: [
                {
                    "commit": {"id": "abc"},
                    "benches": [
                        {
                            "name": "memory::TimezoneFinderL::init_heap",
                            "value": 1.0,
                            "unit": "MiB",
                        }
                    ],
                }
            ],
        },
    }


def _migrated(*benches: dict) -> dict:
    data, _ = migrate(_data(*benches), DEFAULT_SUITE, 2500, "min")
    return data["entries"][DEFAULT_SUITE][0]["benches"][0]


@pytest.mark.unit
def test_a_stored_point_is_restated_as_lookups_per_second():
    # 200 batches/sec over batches of 2,500 points is 500,000 lookups/sec -
    # the same measurement, in the unit the chart now plots
    bench = _migrated(STORED_BENCH)

    assert bench["unit"] == "lookups/sec"
    assert bench["value"] == pytest.approx(500_000)


@pytest.mark.unit
def test_a_stored_point_is_renamed_to_its_chart_label():
    # the same label scripts/export_timing_chart_json.py will store the next
    # point under - which is the whole point: the two have to join
    assert (
        _migrated(STORED_BENCH)["name"]
        == "TimezoneFinder.timezone_at() - random points, in-memory"
    )


@pytest.mark.unit
def test_the_tooltip_keeps_the_machine_and_gains_the_estimator():
    bench = _migrated(STORED_BENCH)

    assert (
        bench["extra"]
        == "min of 153 round(s) on AMD EPYC 9V74 80-Core Processor @ 3.1 GHz"
    )
    # the spread was stored in seconds; the chart now plots a throughput
    assert bench["range"] == f"± {500_000 * 0.0001 / 0.005:.0f}"


@pytest.mark.unit
def test_a_point_without_a_parsable_annotation_still_migrates():
    # an early point, or one the extractor wrote differently: the value and
    # the name are what the chart joins on, so losing a tooltip is preferable
    # to losing the point
    bench = _migrated({**STORED_BENCH, "range": "", "extra": ""})

    assert bench["value"] == pytest.approx(500_000)
    assert "range" not in bench and "extra" not in bench


@pytest.mark.unit
def test_migrating_twice_changes_nothing():
    once, first_count = migrate(_data(STORED_BENCH), DEFAULT_SUITE, 2500, "min")
    twice, second_count = migrate(
        json.loads(json.dumps(once)), DEFAULT_SUITE, 2500, "min"
    )

    assert first_count == 1
    assert second_count == 0
    assert twice == once


@pytest.mark.unit
def test_the_other_suite_is_left_alone():
    # both charts live in one file, keyed by suite name; the memory one is
    # already exported in its own shape and must not be touched
    data, _ = migrate(_data(STORED_BENCH), DEFAULT_SUITE, 2500, "min")

    assert data["entries"][MEMORY_SUITE] == _data()["entries"][MEMORY_SUITE]


@pytest.mark.unit
def test_a_missing_suite_is_an_error_rather_than_a_clean_no_op():
    with pytest.raises(KeyError, match="no suite named"):
        migrate(_data(STORED_BENCH), "typo", 2500, "min")


@pytest.mark.unit
def test_the_file_round_trips_through_the_action_s_own_shape():
    data = _data(STORED_BENCH)

    assert load_data_js(dump_data_js(data)) == data
