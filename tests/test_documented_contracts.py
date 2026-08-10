"""tests pinning the contracts the documentation promises

Documentation is the only place some of these promises live: nothing else in the package
states which exception ``zone_id_of`` raises for a bad id, or that ``read_zone_names``
raises rather than returning an empty list. That is precisely how three of them came to
say the opposite of what the code does. Each test below corresponds to one ``:raises:``
or ``:return:`` line, or to one claim the hand-written pages make, so a future change to
the behaviour or to the packaged data fails here instead of quietly turning the
documentation into fiction again.

Distinct from ``test_error_diagnostics.py``, which pins what the messages *say*; this
pins which exception type comes out at all.
"""

from pathlib import Path

import pytest

from timezonefinder import TimezoneFinder, TimezoneFinderL
from timezonefinder.coord_accessors import FileCoordAccessor, MemoryCoordAccessor
from timezonefinder.zone_names import get_zone_names_path, read_zone_names

# the coordinate every snippet in ``README.rst`` and ``docs/1_usage.rst`` queries, and
# the zone those snippets annotate as its result
USAGE_DOCS_EXAMPLE_COORDS = {"lng": 13.358, "lat": 52.5061}
USAGE_DOCS_EXAMPLE_ZONE = "Europe/Berlin"


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


@pytest.fixture(scope="module")
def tfl() -> TimezoneFinderL:
    """``TimezoneFinderL``, which the last two usage snippets are written against."""
    return TimezoneFinderL(in_memory=True)


@pytest.mark.unit
@pytest.mark.parametrize(
    "finder_fixture, method_name",
    [
        # one case per lookup the usage pages annotate with a result, because the four
        # reach the answer differently: only ``unique_timezone_at`` can start returning
        # None without any of the others changing, if the example's H3 cell stops being
        # covered by a single zone
        ("tf", "timezone_at"),
        ("tf", "timezone_at_land"),
        ("tf", "certain_timezone_at"),
        ("tf", "unique_timezone_at"),
        ("tfl", "timezone_at"),
        ("tfl", "unique_timezone_at"),
    ],
)
def test_usage_docs_example_returns_the_annotated_zone(
    request: pytest.FixtureRequest, finder_fixture: str, method_name: str
):
    """The running example of ``README.rst`` and ``docs/1_usage.rst`` resolves as annotated.

    Every snippet on those pages queries this one coordinate and states the answer in a
    trailing comment. Nothing tied those comments to the packaged data, and for several
    releases all of them read ``'Europe/Paris'`` - what the reduced ``timezones-now``
    dataset returns, where Berlin is merged into Paris, rather than what the full dataset
    the package ships by default returns. A data update that moves this coordinate's zone
    now fails here, where the fix is to re-annotate the snippets.

    The pages show each lookup as a global function as well as a method; the global
    functions delegate to an instance of these same classes, so the data claim is the same
    one.
    """
    finder = request.getfixturevalue(finder_fixture)
    lookup = getattr(finder, method_name)
    assert lookup(**USAGE_DOCS_EXAMPLE_COORDS) == USAGE_DOCS_EXAMPLE_ZONE
