"""Guard the memory footprint against a regression that changes its order of magnitude.

`CLAUDE.md` requires this package to stay usable in containers with
constrained memory, and specifically that `in_memory=False` remains a viable
low-memory option. The trend chart tracks how the footprint *drifts*; these
ceilings catch the change that would make it meaningless in the first place -
something starting to read the whole 60+ MB of coordinate data into Python
objects on a path that used to memory-map it.

They are deliberately loose. A ceiling tight enough to notice a few hundred
kilobytes would fail on every dataset update, and everyone would learn to
raise it without looking. The narrow question here is whether a mode still has
the footprint of its own category.

Only `tracemalloc` heap figures are asserted on. RSS additionally counts
memory-mapped pages, whose residency depends on the platform's page cache
behaviour and on machine-wide memory pressure, so an RSS assertion would fail
for reasons that have nothing to do with this code.
"""

import pytest

from scripts.measure_memory import CONFIGS, measure_configs, metric_name

MIB = 1024**2

# Roughly 2x the measured figures, which leaves room for a dataset that grows
# substantially before anyone has to think about these numbers again. If a data
# update pushes a value past its ceiling, confirm the growth is proportional to
# the new dataset and then raise the constant - that is a legitimate increase,
# not the failure this is looking for.
HEAP_CEILINGS_MIB = {
    # holds the shortcut index only, no polygon data at all
    "TimezoneFinderL": 16,
    # memory maps the coordinates: the heap holds the index and bounding boxes,
    # and must stay in the same category as TimezoneFinderL rather than
    # approaching the in-memory mode below
    "TimezoneFinder[file_based]": 20,
    # reads every coordinate file into memory by design, so this tracks the
    # size of the boundary data itself
    "TimezoneFinder[in_memory]": 160,
}

# The ratio that actually encodes the design constraint: whatever the dataset
# grows to, the memory-mapped mode must stay a fraction of the in-memory one.
# Anything approaching 1.0 means the mapping stopped being a mapping.
MAX_FILE_BASED_SHARE_OF_IN_MEMORY = 0.25


@pytest.fixture(scope="module")
def measured_heap() -> dict[str, float]:
    """Steady-state heap per configuration, in bytes.

    One repetition: `tracemalloc` figures for a fixed construction are
    deterministic to within a couple of hundred bytes (`make memory-noise`
    reports a 0.0% coefficient of variation), so repeating would only cost
    time.
    """
    samples = measure_configs(CONFIGS, repetitions=1)
    return {
        config.id: samples[metric_name(config.id, "steady_heap")][0]
        for config in CONFIGS
    }


@pytest.mark.unit
@pytest.mark.parametrize("config_id, ceiling_mib", sorted(HEAP_CEILINGS_MIB.items()))
def test_heap_stays_under_ceiling(
    measured_heap: dict[str, float], config_id: str, ceiling_mib: int
) -> None:
    measured_mib = measured_heap[config_id] / MIB
    assert measured_mib < ceiling_mib, (
        f"{config_id} allocates {measured_mib:.1f} MiB, over its {ceiling_mib} MiB "
        "ceiling. Either something now reads data into memory that used to be "
        "memory mapped, or the dataset grew - see the note on raising these in "
        "this module's docstring."
    )


@pytest.mark.unit
def test_every_ceiling_covers_a_real_config() -> None:
    """A ceiling for a configuration that no longer exists asserts nothing."""
    assert set(HEAP_CEILINGS_MIB) == {config.id for config in CONFIGS}


@pytest.mark.unit
def test_memory_mapped_mode_stays_far_below_in_memory(
    measured_heap: dict[str, float],
) -> None:
    """The default mode must keep its low-memory character as data grows.

    Expressed as a ratio rather than an absolute size so it keeps holding
    across dataset updates - it is the property `in_memory=False` exists to
    provide, and the one an accidental eager read would destroy.
    """
    share = (
        measured_heap["TimezoneFinder[file_based]"]
        / measured_heap["TimezoneFinder[in_memory]"]
    )
    assert share < MAX_FILE_BASED_SHARE_OF_IN_MEMORY, (
        f"the file-based mode now allocates {share:.0%} of what the in-memory "
        "mode does. The two modes are supposed to differ by an order of "
        "magnitude - the coordinate data is no longer being memory mapped."
    )
