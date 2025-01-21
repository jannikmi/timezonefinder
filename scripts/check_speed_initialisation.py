import timeit

import pytest

from timezonefinder import TimezoneFinder, TimezoneFinderL

N = int(1e1)


@pytest.mark.parametrize("in_memory_mode", [True, False])
@pytest.mark.parametrize(
    "class_under_test",
    [
        TimezoneFinder,
        TimezoneFinderL,
    ],
)
def test_initialisation_speed(class_under_test, in_memory_mode: bool):
    print()
    print(
        f"testing initialiation: {class_under_test.__name__}(in_memory={in_memory_mode})"
    )

    def initialise_instance():
        class_under_test(in_memory=in_memory_mode)

    t = timeit.timeit(
        "initialise_instance()",
        globals={"initialise_instance": initialise_instance},
        number=N,
    )
    t_avg = t / N
    print(f"avg. startup time: {t_avg:.2f} ({N} runs)\n")
