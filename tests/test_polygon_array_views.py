"""The buffer views a candidate polygon is read through.

``PolygonArray`` holds its bounding-box columns, its vertex counts and - on
``HoleArray`` - its reference vector twice: as the numpy arrays that describe the
loaded dataset, and as ``memoryview``s over the same bytes. The views exist because
indexing one yields a Python ``int`` where indexing the array yields a numpy scalar,
which is what the point-in-polygon path pays for once per candidate polygon.

Two copies of one column can disagree, which is the whole risk the views introduce, so
what these tests pin is that they cannot: same length, same values, and a Python ``int``
out of every read. The answers themselves are covered by the lookup tests.
"""

import numpy as np
import pytest

from timezonefinder import TimezoneFinder
from timezonefinder.polygon_array import HoleArray, PolygonArray


@pytest.fixture(scope="module")
def finder() -> TimezoneFinder:
    return TimezoneFinder()


def _columns(array: PolygonArray) -> list[tuple[str, np.ndarray, memoryview]]:
    columns = [
        ("xmin", array.xmin, array._xmin_ints),
        ("xmax", array.xmax, array._xmax_ints),
        ("ymin", array.ymin, array._ymin_ints),
        ("ymax", array.ymax, array._ymax_ints),
        ("nr_vertices", array.nr_vertices, array._nr_vertices_ints),
    ]
    if isinstance(array, HoleArray):
        columns.append(("poly_ref", array.poly_ref, array._poly_ref_ints))
    return columns


@pytest.mark.unit
@pytest.mark.parametrize("collection", ["boundaries", "holes"])
def test_every_view_reads_what_its_array_holds(
    finder: TimezoneFinder, collection: str
) -> None:
    """A view and its array are one column, so no index may disagree."""
    array = getattr(finder, collection)
    for name, values, view in _columns(array):
        assert len(view) == len(values), name
        assert view.tolist() == values.tolist(), name


@pytest.mark.unit
@pytest.mark.parametrize("collection", ["boundaries", "holes"])
def test_a_view_reads_back_a_python_int(
    finder: TimezoneFinder, collection: str
) -> None:
    """The point of the views: a read is an ``int``, not a numpy scalar.

    A numpy scalar answers every comparison the lookup makes and would pass the test
    above, so this is what would actually fail if a view were replaced by its array.
    """
    array = getattr(finder, collection)
    for name, _, view in _columns(array):
        assert type(view[0]) is int, name


@pytest.mark.unit
@pytest.mark.parametrize("collection", ["boundaries", "holes"])
def test_a_numpy_index_reads_the_same_entry(
    finder: TimezoneFinder, collection: str
) -> None:
    """Candidate ids arrive as numpy integers, so no caller converts one first."""
    array = getattr(finder, collection)
    for name, _, view in _columns(array):
        # each column has its own length: a hole collection stores one bbox per hole id
        # but only the inline rings' vertex counts, which is what ``_resolve`` is for
        idx = len(view) - 1
        assert view[np.uint16(idx)] == view[idx], name


@pytest.mark.unit
def test_the_views_are_read_only(finder: TimezoneFinder) -> None:
    """Loaded vectors are immutable, and a view onto one must not be a way around that."""
    view = finder.boundaries._xmin_ints
    assert view.readonly
    with pytest.raises(TypeError):
        view[0] = 0
