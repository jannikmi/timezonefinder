"""Tests for the batch lookups ``timezone_ids_at`` / ``timezone_names_at``.

The seam that matters is **agreement with the scalar path**. A batch answer is not a new
computation: it is the same lookup with its prologue hoisted out of the loop, so any
divergence from ``timezone_at`` is a defect by definition and no other assertion can
substitute for comparing the two over real coordinates.

The rest pins what only the batch API has: the shapes it rejects, the ``on_invalid``
policies, and the sentinel that stands where the scalar method answers ``None``.
"""

import numpy as np
import pytest
from h3.api import numpy_int as h3

from tests.auxiliaries import (
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
    ON_LAND_POINTS_FIXTURE,
    RANDOM_POINTS_FIXTURE,
    UNIQUE_SHORTCUT_POINTS_FIXTURE,
    load_benchmark_points,
)
from tests.locations import TEST_LOCATIONS
from timezonefinder import (
    NO_ZONE_ID,
    TimezoneFinder,
    TimezoneFinderL,
    timezone_ids_at,
    timezone_names_at,
)
from timezonefinder.configs import SHORTCUT_H3_RES, ZONE_ID_RESULT_DTYPE
from timezonefinder.shortcut_index import ABSENT, ShortcutIndex, slot_of
from timezonefinder.zone_names import NAMES_GATHER_MIN_BATCH

# enough points to reach every branch without turning a unit test into a sweep; the
# exhaustive comparison over all four fixtures is the ``slow`` test at the bottom
SAMPLE_SIZE = 300

FIXTURES = [
    RANDOM_POINTS_FIXTURE,
    ON_LAND_POINTS_FIXTURE,
    UNIQUE_SHORTCUT_POINTS_FIXTURE,
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
]


# ``TimezoneFinder`` is built in memory so the batch runs against loaded coordinates;
# ``TimezoneFinderL`` loads no polygon data and takes no ``in_memory`` at all
FINDERS = [
    pytest.param(lambda: TimezoneFinder(in_memory=True), id="TimezoneFinder"),
    pytest.param(TimezoneFinderL, id="TimezoneFinderL"),
]


@pytest.fixture(scope="module", params=FINDERS)
def finder(request):
    """Both finders: the batch path is inherited, the ambiguous fallback is not."""
    with request.param() as instance:
        yield instance


def _axes(points):
    return [lng for lng, _ in points], [lat for _, lat in points]


@pytest.mark.unit
@pytest.mark.parametrize("fixture_name", FIXTURES)
def test_batch_names_agree_with_the_scalar_lookup(finder, fixture_name):
    points = load_benchmark_points(fixture_name)[:SAMPLE_SIZE]
    lngs, lats = _axes(points)

    expected = [finder.timezone_at(lng=lng, lat=lat) for lng, lat in points]
    assert finder.timezone_names_at(lngs=lngs, lats=lats) == expected


@pytest.mark.unit
def test_batch_ids_and_names_describe_the_same_answers(finder):
    points = load_benchmark_points(RANDOM_POINTS_FIXTURE)[:SAMPLE_SIZE]
    lngs, lats = _axes(points)

    zone_ids = finder.timezone_ids_at(lngs=lngs, lats=lats)
    names = finder.timezone_names_at(lngs=lngs, lats=lats)

    assert [
        None if zone_id < 0 else finder.zone_name_from_id(int(zone_id))
        for zone_id in zone_ids
    ] == names


@pytest.mark.unit
def test_the_documented_test_locations_come_back_unchanged(finder):
    lats = [lat for lat, _, _, _ in TEST_LOCATIONS]
    lngs = [lng for _, lng, _, _ in TEST_LOCATIONS]
    expected = [
        finder.timezone_at(lng=lng, lat=lat)
        for lng, lat in zip(lngs, lats, strict=True)
    ]
    assert finder.timezone_names_at(lngs=lngs, lats=lats) == expected


@pytest.mark.unit
def test_the_answer_dtype_is_the_declared_one(finder):
    zone_ids = finder.timezone_ids_at(lngs=[13.358], lats=[52.5061])
    assert zone_ids.dtype == ZONE_ID_RESULT_DTYPE


@pytest.mark.unit
def test_the_answer_dtype_holds_every_id_and_the_sentinel(finder):
    """The width is chosen by fit, so what has to hold is that it fits: signed for the
    sentinel, and wide enough for the largest id this dataset can produce.
    ``scripts.data_integrity.validate_shortcut_index`` refuses a data directory that
    outgrows it, at build time and over the committed data, so this is the runtime half
    of the same statement rather than a second guard on the query path."""
    info = np.iinfo(ZONE_ID_RESULT_DTYPE)
    assert info.min <= NO_ZONE_ID
    assert finder.nr_of_zones - 1 <= info.max


@pytest.mark.unit
def test_an_empty_batch_answers_empty(finder):
    assert finder.timezone_ids_at(lngs=[], lats=[]).shape == (0,)
    assert finder.timezone_names_at(lngs=[], lats=[]) == []


@pytest.mark.unit
@pytest.mark.parametrize(
    "container", [list, tuple, np.array], ids=["list", "tuple", "ndarray"]
)
def test_any_array_like_is_accepted(finder, container):
    """An API only numpy users can call would make everyone else write the loop first."""
    lngs = container([13.358, 2.3522])
    lats = container([52.5061, 48.8566])
    assert finder.timezone_names_at(lngs=lngs, lats=lats) == [
        finder.timezone_at(lng=13.358, lat=52.5061),
        finder.timezone_at(lng=2.3522, lat=48.8566),
    ]


class _ArrayLike:
    """The whole of what makes a pandas Series work here, and nothing else.

    ``np.asarray`` honours ``__array__``, which is how a Series, a pyarrow-backed
    column or an ``xarray.DataArray`` all arrive as coordinates without this package
    knowing any of them exist.
    """

    def __init__(self, values):
        self._values = np.asarray(values, dtype=np.float64)

    def __array__(self, dtype=None, copy=None):
        if dtype is None:
            return self._values
        return self._values.astype(dtype, copy=False)


@pytest.mark.unit
def test_anything_exposing_array_is_accepted(finder):
    """The contract behind the documented "any 1-D array-like", pinned without the
    library that motivated it.

    ``test_a_pandas_series_is_accepted`` below is the real thing, and it skips wherever
    pandas is not installed - which is every CI test environment, since pandas is in the
    ``proto`` group. So this is the one that has to hold the promise: narrowing the input
    handling to ``np.ndarray``, or acting on an annotation that admits only sequences,
    breaks here rather than in an environment nobody runs.
    """
    lngs = _ArrayLike([13.358, 2.3522])
    lats = _ArrayLike([52.5061, 48.8566])
    assert finder.timezone_names_at(lngs=lngs, lats=lats) == [
        finder.timezone_at(lng=13.358, lat=52.5061),
        finder.timezone_at(lng=2.3522, lat=48.8566),
    ]


@pytest.mark.unit
def test_the_caller_s_arrays_are_left_alone(finder):
    """The zero-copy path passes the caller's buffer straight through, so nothing may
    write into it - a lookup that scaled coordinates in place would corrupt the input."""
    lngs = np.array([13.358, 2.3522], dtype=np.float64)
    lats = np.array([52.5061, 48.8566], dtype=np.float64)
    finder.timezone_ids_at(lngs=lngs, lats=lats)
    assert lngs.tolist() == [13.358, 2.3522]
    assert lats.tolist() == [52.5061, 48.8566]


@pytest.mark.unit
def test_a_pandas_series_is_accepted(finder):
    """The array-like the batch API was asked for by name.

    Skips wherever pandas is absent, which is every CI test environment - pandas is in
    the ``proto`` group, not ``test``. ``test_anything_exposing_array_is_accepted`` is
    the version that always runs; this one is here because "accepts a pandas Series" is
    a promise the docs make in those words, and a stub cannot catch a pandas-side
    change to how a Series converts.
    """
    pd = pytest.importorskip("pandas")
    frame = pd.DataFrame(
        {"lng": [13.358, 2.3522], "lat": [52.5061, 48.8566]}, index=[7, 3]
    )
    expected = [
        finder.timezone_at(lng=13.358, lat=52.5061),
        finder.timezone_at(lng=2.3522, lat=48.8566),
    ]

    # a non-default index on purpose: the answer is positional, in the Series' own
    # order, so assigning it straight back to a column is what a caller should do
    assert finder.timezone_names_at(lngs=frame["lng"], lats=frame["lat"]) == expected
    frame["tz"] = finder.timezone_names_at(lngs=frame["lng"], lats=frame["lat"])
    assert frame["tz"].tolist() == expected

    # an integer column converts, and so does pandas' nullable extension dtype
    integer = pd.Series([13, 2])
    assert len(finder.timezone_names_at(lngs=integer, lats=pd.Series([52, 48]))) == 2
    nullable = pd.Series([13.358, 2.3522], dtype="Float64")
    assert (
        finder.timezone_names_at(lngs=nullable, lats=pd.Series([52.5061, 48.8566]))
        == expected
    )


@pytest.mark.unit
@pytest.mark.parametrize("missing", [None, "NA"], ids=["none", "pd_na"])
def test_a_pandas_missing_value_is_a_coordinate_the_policy_governs(finder, missing):
    """pandas normalises both ``None`` and ``pd.NA`` to ``NaN`` inside the Series, so a
    missing value never reaches this package as the object a bare Python list would
    hand it. It arrives as an out-of-range coordinate and ``on_invalid`` governs it -
    which is the right answer for pandas, whose missing value *is* NaN, and the reason
    ``None`` in a plain list is treated as the caller's mistake instead."""
    pd = pytest.importorskip("pandas")
    value = None if missing is None else pd.NA
    lngs = pd.Series([13.358, value], dtype="Float64")
    lats = pd.Series([52.5061, 0.0], dtype="Float64")

    zone_ids = finder.timezone_ids_at(lngs=lngs, lats=lats, on_invalid="skip")
    assert zone_ids[1] == NO_ZONE_ID
    with pytest.raises(ValueError, match="invalid coordinate at index 1"):
        finder.timezone_ids_at(lngs=lngs, lats=lats)


@pytest.mark.unit
def test_axes_of_different_length_are_rejected(finder):
    with pytest.raises(ValueError, match="same number of coordinates"):
        finder.timezone_ids_at(lngs=[1.0, 2.0], lats=[1.0])


@pytest.mark.unit
def test_a_pair_array_is_rejected_rather_than_read_positionally(finder):
    """An (N, 2) array would have to be read by column position, and a swapped pair is
    still a valid coordinate for most of the populated world - so the mistake would
    return a real but wrong timezone. Refuse the shape instead of guessing."""
    pairs = np.array([[13.358, 52.5061], [2.3522, 48.8566]])
    with pytest.raises(ValueError, match="one-dimensional"):
        finder.timezone_ids_at(lngs=pairs, lats=pairs)


@pytest.mark.unit
def test_non_numeric_input_raises_type_error(finder):
    with pytest.raises(TypeError):
        finder.timezone_ids_at(lngs=["thirteen"], lats=[52.5061])


@pytest.mark.unit
@pytest.mark.parametrize("on_invalid", ["raise", "skip"])
def test_a_missing_coordinate_is_rejected_rather_than_read_as_nan(finder, on_invalid):
    """``None`` is the one unconvertible value numpy turns into a number: an explicit
    float cast makes it NaN. Read that far it becomes an out-of-range coordinate, so
    under ``skip`` a null in the caller's data would come back as ``NO_ZONE_ID`` -
    indistinguishable from a point no timezone covers, and answered rather than
    reported. The scalar methods raise ``TypeError`` for it, and so must a batch."""
    with pytest.raises(TypeError, match="holds None"):
        finder.timezone_ids_at(
            lngs=[13.358, None], lats=[52.5061, 48.8566], on_invalid=on_invalid
        )


@pytest.mark.unit
def test_a_genuine_nan_is_still_a_coordinate_the_policy_governs(finder):
    """The rejection above must not swallow a NaN the caller passed on purpose - a
    float column with missing values is the ordinary case ``on_invalid`` exists for."""
    zone_ids = finder.timezone_ids_at(
        lngs=[13.358, float("nan")], lats=[52.5061, 0.0], on_invalid="skip"
    )
    assert zone_ids[1] == NO_ZONE_ID


@pytest.mark.unit
@pytest.mark.parametrize(
    "lng, lat",
    [
        (181.0, 0.0),
        (0.0, 91.0),
        (float("nan"), 0.0),
        (0.0, float("inf")),
    ],
    ids=["lng_too_large", "lat_too_large", "nan", "inf"],
)
def test_out_of_bounds_coordinates_raise_by_default(finder, lng, lat):
    """The default matches the scalar methods; NaN and infinity are out of bounds too."""
    with pytest.raises(ValueError, match="invalid coordinate at index 1"):
        finder.timezone_ids_at(lngs=[13.358, lng], lats=[52.5061, lat])


@pytest.mark.unit
def test_the_raised_error_names_the_escape_hatch(finder):
    """Discovering ``on_invalid`` should not require reading the source."""
    with pytest.raises(ValueError, match="on_invalid"):
        finder.timezone_ids_at(lngs=[999.0], lats=[0.0])


@pytest.mark.unit
def test_skip_answers_every_valid_coordinate(finder):
    lngs = [13.358, 999.0, 2.3522, float("nan")]
    lats = [52.5061, 0.0, 48.8566, 0.0]

    zone_ids = finder.timezone_ids_at(lngs=lngs, lats=lats, on_invalid="skip")
    names = finder.timezone_names_at(lngs=lngs, lats=lats, on_invalid="skip")

    assert zone_ids[1] == NO_ZONE_ID
    assert zone_ids[3] == NO_ZONE_ID
    assert names[1] is None
    assert names[3] is None
    assert names[0] == finder.timezone_at(lng=13.358, lat=52.5061)
    assert names[2] == finder.timezone_at(lng=2.3522, lat=48.8566)


@pytest.mark.unit
def test_skipping_does_not_shift_the_remaining_answers(finder):
    """One answer per input coordinate, in input order - the property a caller zipping
    the result back against its own rows depends on."""
    points = load_benchmark_points(RANDOM_POINTS_FIXTURE)[:SAMPLE_SIZE]
    lngs, lats = _axes(points)
    # every third coordinate replaced by an unanswerable one
    spoilt_lngs = [999.0 if i % 3 == 0 else lng for i, lng in enumerate(lngs)]

    names = finder.timezone_names_at(lngs=spoilt_lngs, lats=lats, on_invalid="skip")

    assert len(names) == len(points)
    for i, (lng, lat) in enumerate(points):
        if i % 3 == 0:
            assert names[i] is None
        else:
            assert names[i] == finder.timezone_at(lng=lng, lat=lat)


@pytest.mark.unit
def test_an_unknown_policy_is_rejected(finder):
    with pytest.raises(ValueError, match="unknown on_invalid policy"):
        finder.timezone_ids_at(lngs=[13.358], lats=[52.5061], on_invalid="ignore")


@pytest.mark.unit
def test_a_cell_no_zone_covers_answers_the_same_as_the_scalar_lookup():
    """The packaged data covers every cell (ocean zones), so this is the branch custom
    data reaches and the packaged data cannot. One slot is blanked to reach it, and the
    point of the test is that both paths agree on what an uncovered cell means."""
    lng, lat = 13.358, 52.5061
    with TimezoneFinder(in_memory=True) as tf:
        slot = slot_of(h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES))
        assert tf.shortcuts.table[slot] != ABSENT, "the cell is covered to begin with"
        # Loaded index state is immutable. Replace it with purpose-built test state
        # instead of mutating the dataset the finder loaded.
        table = tf.shortcuts.table.copy()
        table[slot] = ABSENT
        tf.shortcuts = ShortcutIndex(
            table,
            tf.shortcuts.starts,
            tf.shortcuts.ends,
            tf.shortcuts.last_change,
            tf.shortcuts.payload,
        )

        assert tf.timezone_at(lng=lng, lat=lat) is None
        assert tf.timezone_ids_at(lngs=[lng], lats=[lat])[0] == NO_ZONE_ID
        assert tf.timezone_names_at(lngs=[lng], lats=[lat]) == [None]


@pytest.mark.unit
def test_the_global_functions_answer_like_an_instance():
    lngs = [13.358, 2.3522, 1.0]
    lats = [52.5061, 48.8566, 50.5]
    with TimezoneFinder() as tf:
        assert timezone_names_at(lngs=lngs, lats=lats) == tf.timezone_names_at(
            lngs=lngs, lats=lats
        )
        assert np.array_equal(
            timezone_ids_at(lngs=lngs, lats=lats),
            tf.timezone_ids_at(lngs=lngs, lats=lats),
        )


@pytest.mark.slow
@pytest.mark.parametrize("fixture_name", FIXTURES)
def test_batch_and_scalar_agree_over_every_committed_point(finder, fixture_name):
    """The full sweep the sampled test above is a cheap stand-in for."""
    points = load_benchmark_points(fixture_name)
    lngs, lats = _axes(points)
    expected = [finder.timezone_at(lng=lng, lat=lat) for lng, lat in points]
    assert finder.timezone_names_at(lngs=lngs, lats=lats) == expected


# --- zone_names_from_ids ------------------------------------------------------
#
# Two implementations behind one method - a Python loop below
# ``NAMES_GATHER_MIN_BATCH`` and a numpy gather above it - so every behavioural test
# here has to be reachable in both regimes, and the first test below is the one that
# says they agree at all.


@pytest.mark.unit
@pytest.mark.parametrize(
    "size",
    [1, NAMES_GATHER_MIN_BATCH - 1, NAMES_GATHER_MIN_BATCH, NAMES_GATHER_MIN_BATCH + 1],
    ids=["one", "below_threshold", "at_threshold", "above_threshold"],
)
def test_both_conversion_regimes_answer_identically(finder, size):
    """The loop and the gather are one method's two halves; a difference between them
    would show only at batch sizes nobody happens to test."""
    zone_ids = np.arange(size, dtype=ZONE_ID_RESULT_DTYPE) % finder.nr_of_zones
    expected = [finder.zone_name_from_id(int(zone_id)) for zone_id in zone_ids]
    assert finder.zone_names_from_ids(zone_ids) == expected


@pytest.mark.unit
def test_every_zone_id_names_the_same_zone_as_the_scalar_method(finder):
    zone_ids = np.arange(finder.nr_of_zones, dtype=ZONE_ID_RESULT_DTYPE)
    assert finder.zone_names_from_ids(zone_ids) == list(finder.timezone_names)


@pytest.mark.unit
@pytest.mark.parametrize("fixture_name", FIXTURES)
def test_ids_round_trip_to_the_names_the_batch_lookup_would_have_given(
    finder, fixture_name
):
    """The pairing the id form exists for: keep ids while joining or grouping, name them
    at the end, and land on exactly what ``timezone_names_at`` returns."""
    points = load_benchmark_points(fixture_name)[:SAMPLE_SIZE]
    lngs, lats = _axes(points)

    zone_ids = finder.timezone_ids_at(lngs=lngs, lats=lats)
    assert finder.zone_names_from_ids(zone_ids) == finder.timezone_names_at(
        lngs=lngs, lats=lats
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "size", [1, NAMES_GATHER_MIN_BATCH + 1], ids=["loop", "gather"]
)
def test_the_sentinel_names_nothing(finder, size):
    zone_ids = np.full(size, NO_ZONE_ID, dtype=ZONE_ID_RESULT_DTYPE)
    assert finder.zone_names_from_ids(zone_ids) == [None] * size


@pytest.mark.unit
def test_a_negative_that_is_not_the_sentinel_is_rejected(finder):
    """``-1`` is the sentinel and names nothing; ``-2`` is a bug, and counting it from
    the end of the dataset would answer it with a real timezone name."""
    with pytest.raises(ValueError, match="not a valid zone id"):
        finder.zone_names_from_ids([0, -2])


@pytest.mark.unit
def test_the_id_one_past_the_last_zone_is_rejected(finder):
    """The lookup array carries one extra slot for the sentinel, so this id would read
    it and answer ``None`` instead of raising - the one out-of-range value numpy's own
    bounds check cannot catch here."""
    with pytest.raises(ValueError, match="not a valid zone id"):
        finder.zone_names_from_ids([finder.nr_of_zones])


@pytest.mark.unit
def test_non_integer_ids_are_rejected(finder):
    with pytest.raises(TypeError, match="must be integers"):
        finder.zone_names_from_ids([1.5])


@pytest.mark.unit
def test_a_two_dimensional_id_array_is_rejected(finder):
    with pytest.raises(ValueError, match="one-dimensional"):
        finder.zone_names_from_ids(np.zeros((2, 2), dtype=np.int32))


@pytest.mark.unit
def test_an_empty_id_array_of_the_wrong_shape_is_rejected_too(finder):
    """The shape is a property of the caller's pipeline, not of this batch: accepting
    it while it happens to be empty defers the error to the first run with data in it."""
    with pytest.raises(ValueError, match="one-dimensional"):
        finder.zone_names_from_ids(np.zeros((0, 2), dtype=np.int32))


@pytest.mark.unit
def test_no_ids_name_nothing(finder):
    assert finder.zone_names_from_ids([]) == []


@pytest.mark.unit
@pytest.mark.parametrize(
    "container", [list, tuple, np.array], ids=["list", "tuple", "ndarray"]
)
def test_ids_are_accepted_from_any_array_like(finder, container):
    assert finder.zone_names_from_ids(container([0, 1])) == [
        finder.zone_name_from_id(0),
        finder.zone_name_from_id(1),
    ]


@pytest.mark.unit
def test_the_names_lookup_array_is_not_built_until_a_gather_needs_it():
    """Construction cost is what ``docs/benchmark_results_memory.rst`` measures, and a
    lightweight finder's whole footprint is small enough that ~450 object pointers would
    show in it. Building the array eagerly would move a committed measurement with
    nothing to signal it, so the laziness is pinned rather than left to a comment."""
    with TimezoneFinderL() as tf:
        assert tf.zone_names._gather_lookup is None

        tf.zone_names_from_ids(np.zeros(NAMES_GATHER_MIN_BATCH - 1, dtype=np.int32))
        assert tf.zone_names._gather_lookup is None, "the loop regime allocates nothing"

        tf.zone_names_from_ids(np.zeros(NAMES_GATHER_MIN_BATCH, dtype=np.int32))
        assert tf.zone_names._gather_lookup is not None


# --- shared per-cell work -----------------------------------------------------
#
# A batch prepares each distinct shortcut entry once and reuses it for every point that
# landed in it, which is what makes a clustered batch cheap. The fixtures are spread over
# the globe and barely exercise that, so these build the clustered case explicitly.


def _clustered_points(lng, lat, count, spread=0.2, seed=0):
    rng = np.random.default_rng(seed)
    return (
        (lng + rng.normal(0, spread, count)).tolist(),
        (lat + rng.normal(0, spread, count)).tolist(),
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "lng, lat",
    [(7.5886, 47.5596), (6.1432, 46.2044), (13.358, 52.5061)],
    ids=["basel_tri_border", "geneva_border", "berlin_interior"],
)
def test_a_clustered_batch_answers_like_the_scalar_lookup(finder, lng, lat):
    """Where the sharing is: points around a border city land in a handful of cells, so
    almost every point reads a prepared cell rather than preparing one."""
    lngs, lats = _clustered_points(lng, lat, 500)

    expected = [
        finder.timezone_at(lng=a, lat=b) for a, b in zip(lngs, lats, strict=True)
    ]
    assert finder.timezone_names_at(lngs=lngs, lats=lats) == expected


@pytest.mark.unit
def test_the_cluster_really_does_share_cells(finder):
    """Guards the test above from going vacuous. If a data update moved the boundaries
    so that these points no longer share entries, the test would still pass while
    exercising none of the sharing it exists for."""
    lngs, lats = _clustered_points(7.5886, 47.5596, 500)
    cells = np.fromiter(
        (
            h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES)
            for lng, lat in zip(lngs, lats, strict=True)
        ),
        dtype=np.uint64,
        count=len(lngs),
    )
    entries = finder.shortcuts.entries_of(cells)
    ambiguous = entries[entries < ABSENT]

    assert ambiguous.size > 100, "the cluster reaches no ambiguous cell at all"
    assert len(np.unique(ambiguous)) < ambiguous.size / 10, (
        "the cluster spreads over too many distinct entries to exercise the sharing"
    )


@pytest.mark.unit
def test_repeating_one_coordinate_gives_one_answer(finder):
    """The degenerate cluster: every point in one cell, so one preparation serves all."""
    points = load_benchmark_points(AMBIGUOUS_SHORTCUT_POINTS_FIXTURE)[:1]
    lng, lat = points[0]
    expected = finder.timezone_at(lng=lng, lat=lat)

    names = finder.timezone_names_at(lngs=[lng] * 200, lats=[lat] * 200)
    assert names == [expected] * 200
