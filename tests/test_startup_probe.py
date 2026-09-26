"""What a cold process costs before its first answer, and how it is aggregated.

The numbers themselves are published rather than asserted - they are hardware and
environment, and ``docs/benchmark_results_acceleration_paths.rst`` is where they
belong. What is worth a test is the part that would silently mislabel them: the
probe must report the path its *own* process bound, and the aggregation must refuse
a sample taken in a different environment than the run it is filed under, because
that would put one environment's import cost in the other's column.
"""

import json

import pytest

from scripts import measure_acceleration_paths
from scripts.measure_acceleration_paths import STARTUP_METRICS, measure_startup
from scripts.assert_acceleration_path import interpreted_path_name


def _sample(**overrides) -> dict:
    sample = {
        "import_rss": 4 * 1024**2,
        "init_rss": 30 * 1024**2,
        "first_query_rss": 1024**2,
        "ready_rss": 50 * 1024**2,
        "import_seconds": 0.03,
        "init_seconds": 0.4,
        "first_query_seconds": 0.0001,
        "numba_installed": False,
        "using_numba": False,
        "using_clang_pip": True,
    }
    sample.update(overrides)
    return sample


def _fake_probe(monkeypatch, samples):
    """Hand ``measure_startup`` a scripted sequence of probe processes."""
    remaining = list(samples)

    class Completed:
        def __init__(self, stdout):
            self.stdout = stdout

    def fake_run(_command, **_kwargs):
        return Completed(json.dumps(remaining.pop(0)))

    monkeypatch.setattr(measure_acceleration_paths.subprocess, "run", fake_run)


def test_startup_reports_the_median_process(monkeypatch):
    # the compiling process is the outlier the median exists to drop
    _fake_probe(
        monkeypatch,
        [
            _sample(init_seconds=2.0, ready_rss=200 * 1024**2),
            _sample(init_seconds=0.4, ready_rss=50 * 1024**2),
            _sample(init_seconds=0.5, ready_rss=52 * 1024**2),
        ],
    )

    startup = measure_startup("python")

    assert startup["init_seconds"] == 0.5
    assert startup["ready_rss"] == 52 * 1024**2
    assert startup["repetitions"] == measure_acceleration_paths.STARTUP_REPETITIONS


def test_startup_refuses_a_probe_from_another_environment(monkeypatch):
    # what identifies the environment is the numba *installed* in it: since the C
    # extension outranks numba, a numba environment binds clang and reports
    # `using_numba` false, so the binding cannot tell the two runs apart
    _fake_probe(monkeypatch, [_sample(numba_installed=True)] * 3)

    with pytest.raises(RuntimeError, match="numba"):
        measure_startup("python")


def test_startup_reports_an_unavailable_measurement_as_such(monkeypatch):
    # RSS is unobtainable on Windows; a missing byte count must not read as zero
    _fake_probe(monkeypatch, [_sample(ready_rss=None)] * 3)

    startup = measure_startup("python")

    assert startup["ready_rss"] is None
    assert startup["init_seconds"] is not None


def test_the_probe_measures_this_environment():
    """The one end-to-end run: a real subprocess, on whatever path is installed."""
    startup = measure_startup(interpreted_path_name())

    assert all(startup[metric] is not None for metric in STARTUP_METRICS)
    # the process holds the package and its data by the time it has answered
    assert startup["ready_rss"] > startup["init_rss"] > 0
    # the probe reports the environment it ran in; the binding is a different question
    # and is false here whenever the C extension loaded
    assert startup["numba_installed"] is (interpreted_path_name() == "numba")
    assert startup["using_numba"] is not startup["using_clang_pip"]
