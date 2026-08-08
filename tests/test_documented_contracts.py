"""tests pinning the contracts the public docstrings promise

A docstring is the only place some of these promises live: nothing else in the package
states which exception ``zone_id_of`` raises for a bad id, or that ``read_zone_names``
raises rather than returning an empty list. That is precisely how three of them came to
say the opposite of what the code does. Each test below corresponds to one ``:raises:``
or ``:return:`` line, so a future change to the behaviour fails here instead of quietly
turning the docstring into fiction again.

Distinct from ``test_error_diagnostics.py``, which pins what the messages *say*; this
pins which exception type comes out at all.
"""

from pathlib import Path

import pytest

from timezonefinder import TimezoneFinder
from timezonefinder.coord_accessors import FileCoordAccessor, MemoryCoordAccessor
from timezonefinder.zone_names import get_zone_names_path, read_zone_names


@pytest.mark.unit
def test_zone_id_of_reports_an_out_of_range_id_as_value_error(tf: TimezoneFinder):
    """``AbstractTimezoneFinder.zone_id_of`` documents ValueError, not IndexError."""
    with pytest.raises(ValueError):
        tf.zone_id_of(tf.nr_of_polygons)


@pytest.mark.unit
@pytest.mark.parametrize(
    "bad_id",
    [
        # the two ids reach the handler by different routes, and the docstring promises
        # ValueError for both: numpy rejects a non-integer index with IndexError, while a
        # multi-element selection indexes fine and only fails in the int() conversion
        pytest.param("not-an-id", id="non-integer-index"),
        pytest.param([0, 1], id="multi-element-selection"),
    ],
)
def test_zone_id_of_converts_every_unusable_id_to_value_error(
    tf: TimezoneFinder, bad_id
):
    """ValueError is the only type callers have to handle, as documented."""
    with pytest.raises(ValueError):
        tf.zone_id_of(bad_id)  # type: ignore[arg-type]


@pytest.mark.unit
def test_zone_name_from_id_reports_an_out_of_range_id_as_value_error(
    tf: TimezoneFinder,
):
    """``zone_name_from_id`` converts the list lookup's IndexError to ValueError."""
    with pytest.raises(ValueError):
        tf.zone_name_from_id(tf.nr_of_zones)


@pytest.mark.unit
def test_zone_name_from_id_lets_a_non_integer_raise_type_error(tf: TimezoneFinder):
    """Only IndexError is converted; a non-integer id still surfaces as TypeError."""
    with pytest.raises(TypeError):
        tf.zone_name_from_id("Europe/Berlin")  # type: ignore[arg-type]


@pytest.mark.unit
def test_read_zone_names_raises_for_a_missing_file(tmp_path: Path):
    """It does not return an empty list for a directory without the names file."""
    assert not get_zone_names_path(tmp_path).exists()
    with pytest.raises(FileNotFoundError):
        read_zone_names(tmp_path)


@pytest.mark.unit
@pytest.mark.parametrize(
    "in_memory, expected_accessor",
    [(True, MemoryCoordAccessor), (False, FileCoordAccessor)],
)
def test_in_memory_selects_the_coordinate_access_mode(in_memory, expected_accessor):
    """``in_memory`` is honoured for polygon coordinates - it is not an inert argument.

    The base class docstring claimed for several releases that it was ignored and kept
    only for API compatibility, while ``docs/1_usage.rst`` documented it as working.
    """
    with TimezoneFinder(in_memory=in_memory) as finder:
        assert isinstance(finder.boundaries.coordinates, expected_accessor)
        assert isinstance(finder.holes.coordinates, expected_accessor)
