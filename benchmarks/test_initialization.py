"""pytest-benchmark suite for TimezoneFinder / TimezoneFinderL construction.

This measures *cold* construction, so state must be fresh every round.
`benchmark.pedantic(..., warmup_rounds=0)` is used instead of the plain
`benchmark()` fixture: the plain fixture always runs an internal
calibration/warmup phase before the timed rounds, which would touch the
on-disk/memory-mapped data (and warm the OS file cache) ahead of the "cold"
measurement this benchmark is meant to capture. Each round still constructs
a brand new instance, so no state is shared between rounds either way.
"""

import pytest

from timezonefinder import TimezoneFinder, TimezoneFinderL

# `TimezoneFinderL` appears once, not twice: it holds no `PolygonArray`, takes no
# `in_memory` argument and has one construction. The two ids it used to have measured
# the same thing and presented the duplicate as coverage - the same reasoning
# `scripts/measure_memory.py` already applies to its own configs.
CONFIGS = [
    pytest.param(TimezoneFinder, {"in_memory": True}, id="TimezoneFinder-in_memory"),
    pytest.param(TimezoneFinder, {"in_memory": False}, id="TimezoneFinder-file_based"),
    pytest.param(TimezoneFinderL, {}, id="TimezoneFinderL"),
]

# rounds, not iterations: each round must construct exactly one fresh instance
ROUNDS = 30


@pytest.mark.benchmark
@pytest.mark.parametrize("finder_cls, kwargs", CONFIGS)
def test_initialization(benchmark, finder_cls, kwargs):
    def init():
        finder_cls(**kwargs)

    benchmark.pedantic(init, rounds=ROUNDS, warmup_rounds=0, iterations=1)
