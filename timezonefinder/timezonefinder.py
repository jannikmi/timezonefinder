"""
Core TimezoneFinder implementation.

This module provides the TimezoneFinder and TimezoneFinderL classes for offline
timezone lookups from geographic coordinates. The module uses H3-based spatial
shortcuts and optimized polygon-based algorithms for fast, accurate results.

Core classes:
    - AbstractTimezoneFinder: Base class with shared functionality
    - TimezoneFinder: Full accuracy with all polygon boundaries checked
    - TimezoneFinderL: Lightweight heuristic using shortcuts only
"""

import json
import warnings
from abc import ABC, abstractmethod
from collections.abc import Iterable
from pathlib import Path
from typing import Final, Self

import numpy as np
from h3.api import numpy_int as h3

from timezonefinder.np_binary_helpers import (
    get_zone_ids_path,
    get_zone_positions_path,
    read_per_polygon_vector,
)
from timezonefinder.polygon_array import HoleArray, PolygonArray
from timezonefinder import utils, utils_clang
from timezonefinder.configs import (
    DEFAULT_DATA_DIR,
    MAX_LAT_VAL,
    MAX_LNG_VAL,
    NO_ZONE_ID,
    SHORTCUT_H3_RES,
    DATA_VERSION_FILENAME,
    CoordArrayLike,
    CoordLists,
    CoordPairs,
    IdArrayLike,
    IntegerLike,
)

from timezonefinder.shortcut_index import (
    ABSENT,
    ShortcutIndex,
    get_shortcut_file_path,
    read_shortcuts_binary,
)
from timezonefinder.zone_names import read_zone_names


#: What ``on_invalid`` accepts on the batch lookups. ``"raise"`` is the default because
#: it is what the scalar methods do, and a batch call is not the place to quietly change
#: the contract; ``"skip"`` exists because raising on element 999,999 and discarding the
#: 999,998 answers already computed is hostile.
ON_INVALID_POLICIES: Final[tuple[str, ...]] = ("raise", "skip")

#: Batch size from which converting zone ids to names through a numpy gather beats a
#: Python loop. Measured, not guessed - min ns per id over uniformly random fixture
#: points, with 10 % of the ids being the sentinel, on one machine:
#:
#: ======  ========  ======
#: N       loop      gather
#: ======  ========  ======
#: 10      33.4      316.6
#: 64      30.6      56.0
#: **128** **31.2**  **31.9**
#: 256     33.7      19.4
#: 10,000  38.8      7.6
#: ======  ========  ======
#:
#: numpy's per-call overhead is what dominates a short batch, so below the crossover the
#: gather is up to 16x *worse* per id and above it up to 5x better. The threshold does not
#: have to be exact on another machine: near it the two are within a few percent of each
#: other by definition, which is what makes a single constant safe here.
NAMES_GATHER_MIN_BATCH: Final[int] = 128

#: dtype of a batch answer. Signed, because :data:`~timezonefinder.configs.NO_ZONE_ID` is
#: negative; 32-bit rather than 16-bit because the ambiguous fallback reads ids out of
#: ``zone_ids``, whose stored dtype is unsigned 16-bit - ``int16`` could not hold its
#: upper half, and a dtype that truncates silently is worse than four bytes per answer.
ZONE_ID_RESULT_DTYPE: Final[np.dtype] = np.dtype(np.int32)


def _negative_id_error(kind: str, value: object) -> ValueError:
    """Build the error a negative id gets, for any of the public id-taking methods.

    A negative index is valid Python and counts from the end, so an unguarded lookup
    answers ``-1`` - the conventional "not found" sentinel of an index lookup - with the
    last entry of the dataset rather than an error.
    """
    return ValueError(
        f"{value} is not a valid {kind} id: ids are non-negative. "
        "A negative index would silently select an entry counting from the end."
    )


def _coordinate_arrays(
    lngs: CoordArrayLike, lats: CoordArrayLike
) -> tuple[np.ndarray, np.ndarray]:
    """The two input axes as 1-D float64 arrays.

    ``np.asarray`` is what makes the zero-copy path real: a C-contiguous float64 array
    is passed straight through, and anything else is converted once for the whole batch
    rather than per point.

    :raises TypeError: if either axis holds something that is not convertible to float.
    :raises ValueError: if either axis is not one-dimensional, or the two differ in length.
    """
    arrays = []
    for name, values in (("lngs", lngs), ("lats", lats)):
        try:
            array = np.asarray(values, dtype=np.float64)
        except (TypeError, ValueError) as e:
            raise TypeError(
                f"{name} must hold numbers convertible to float: {e}"
            ) from e
        if array.ndim != 1:
            raise ValueError(
                f"{name} must be one-dimensional, got shape {array.shape}. "
                "Coordinates are passed one axis per argument, never as an (N, 2) array "
                "whose column order would have to be guessed."
            )
        arrays.append(array)
    lng_array, lat_array = arrays
    if lng_array.shape != lat_array.shape:
        raise ValueError(
            "lngs and lats must hold the same number of coordinates, got "
            f"{lng_array.shape[0]} and {lat_array.shape[0]}"
        )
    return lng_array, lat_array


def _out_of_bounds(lngs: np.ndarray, lats: np.ndarray) -> np.ndarray:
    """Which coordinates no lookup can answer, as a boolean mask.

    A bound comparison rejects NaN and infinity as a side effect - both compare ``False``
    against everything - so this is the whole of what ``utils.validate_coordinates`` does
    per point, in two vectorised passes instead of 2N calls.
    """
    return ~((np.abs(lngs) <= MAX_LNG_VAL) & (np.abs(lats) <= MAX_LAT_VAL))


class AbstractTimezoneFinder(ABC):
    """
    Abstract base class for TimezoneFinder instances.

    Provides shared functionality for timezone lookups including:
    - Timezone name/ID mapping
    - H3 spatial indexing for shortcut lookups
    - Boundary polygon management
    - Coordinate validation

    This class should not be instantiated directly. Use TimezoneFinder
    (full accuracy) or TimezoneFinderL (lightweight heuristic) instead.

    Thread Safety:
        For parallel computation with multiple threads, each thread must create
        its own independent instance. Do not share a single instance across threads.

    Attributes:
        timezone_names: List of all available timezone names
        zone_ids: NumPy array mapping boundary polygons to timezone IDs
        shortcuts: H3-indexed lookup of the timezones that can cover a point
        data_location: Path to the timezone data directory
    """

    # prevent dynamic attribute assignment (-> safe memory). Every name here must be
    # assigned by this class or a subclass; an unassigned one is just a hole in that
    # guarantee, so `test_declared_slots_are_assigned` pins the list against instances.
    __slots__ = [
        "data_location",
        "shortcuts",
        "timezone_names",
        "zone_ids",
        "holes_dir",
        "boundaries_dir",
        "boundaries",
        "holes",
        "_zone_names_lookup",
    ]

    zone_ids: np.ndarray
    #: which timezones can possibly cover a point. This class asks it what a cell resolves
    #: to and never how that is stored - see ``timezonefinder/shortcut_index.py``.
    shortcuts: ShortcutIndex

    def __init__(
        self,
        bin_file_location: str | Path | None = None,
        in_memory: bool = False,
    ):
        """
        Initialize the AbstractTimezoneFinder.

        Loads the zone names, the per-polygon zone ids and the shortcut index. These are
        always held in memory; only the polygon coordinate data a subclass may load is
        subject to ``in_memory``.

        :param bin_file_location: Path to the directory containing binary timezone data.
                                 If None, uses the bundled package data directory.
        :param in_memory: Whether to read the polygon coordinate data into memory instead of
                         accessing it through a memory-mapped file. Selects the access mode of
                         ``TimezoneFinder``'s boundary and hole data; ``TimezoneFinderL`` loads
                         no polygon data at all, so it is without effect there.
        :raises FileNotFoundError: If timezone data files cannot be found at the specified location
        :raises ValueError: If timezone data files are corrupted or in an invalid format
        """
        if bin_file_location is None:
            bin_file_location = DEFAULT_DATA_DIR
        self.data_location: Path = Path(bin_file_location)

        self.timezone_names = read_zone_names(self.data_location)

        self.zone_ids = read_per_polygon_vector(get_zone_ids_path(self.data_location))

        self.shortcuts = read_shortcuts_binary(
            get_shortcut_file_path(self.data_location)
        )

        # built on first use rather than here, so that a finder which never converts a
        # large batch of ids allocates nothing for it - construction heap and resident
        # set are what `docs/benchmark_results_memory.rst` measures, and a lightweight
        # finder's whole footprint is small enough that ~450 object pointers would show.
        self._zone_names_lookup: np.ndarray | None = None

    def _iter_boundary_ids_of_zone(self, zone_id: int) -> Iterable[int]:
        """
        Yield the boundary polygon IDs for a given zone ID.

        :param zone_id: ID of the zone
        :yield: boundary polygon IDs
        """
        # load only on demand. used when shortcuts contain zone IDs (hybrid optimization)
        zone_positions_path = get_zone_positions_path(self.data_location)
        zone_positions = np.load(zone_positions_path, mmap_mode="r")
        first_boundary_id_zone = zone_positions[zone_id]
        # read the id of the first boundary polygon of the consequent zone
        # NOTE: this has also been added for the last zone
        first_boundary_id_next = zone_positions[zone_id + 1]
        yield from range(first_boundary_id_zone, first_boundary_id_next)

    @property
    def data_version(self) -> str:
        """The timezone-boundary-builder release this finder answers from.

        Reads the stamp ``scripts/file_converter.py`` wrote into the data
        directory at build time (``data_version.txt``), so an installed
        ``timezonefinder`` can state which dataset it is answering from without
        reverse-engineering it from the package version - which also changes
        for unrelated code fixes and, under the automated data-update
        pipeline, changes together with the data in a way callers cannot
        distinguish.

        For the packaged data this is the release ``update_data.sh`` downloaded.
        A data directory compiled from your own GeoJSON reads ``"unknown"``
        unless ``scripts/file_converter.py --data-version`` named the release it
        came from, since nothing about the input states it.

        :raises FileNotFoundError: if the data directory carries no stamp, which
            a directory compiled before this file existed does not.
        """
        version_path = self.data_location / DATA_VERSION_FILENAME
        try:
            return version_path.read_text(encoding="utf-8").strip()
        except FileNotFoundError as exc:
            # every other file of a pre-stamp data directory still loads, so the
            # bare OS error arrives with no hint that regenerating is the fix
            raise FileNotFoundError(
                f"no dataset version stamp at {version_path}. This data directory "
                "was compiled before the stamp existed - recompile it with "
                "`scripts/file_converter.py --data-version <timezone-boundary-builder "
                "release>` to state which boundary data it holds."
            ) from exc

    @property
    def nr_of_zones(self) -> int:
        """
        Get the number of timezones.

        :rtype: int
        """
        return len(self.timezone_names)

    @staticmethod
    def using_numba() -> bool:
        """
        Check if Numba is being used.

        :rtype: bool
        :return: True if Numba is being used to JIT compile helper functions
        """
        return utils.using_numba

    @staticmethod
    def using_clang_pip() -> bool:
        """
        :return: True if the compiled C implementation of the point in polygon algorithm is being used
        """
        return utils.inside_polygon == utils_clang.pt_in_poly_clang

    # Validation happens at the public edge only. Every internal caller below obtains its
    # id from the shortcut index or from ``zone_ids``, neither of which can hold a negative
    # value, and the unchecked accessors run once per successful query - so the guard the
    # public methods need is not paid on the lookup path.

    def _zone_id_of(self, boundary_id: IntegerLike) -> int:
        """Look up a boundary polygon's zone id without checking its sign."""
        try:
            return int(self.zone_ids[boundary_id])
        except (TypeError, IndexError) as e:
            raise ValueError(
                f"Cannot get zone ID for boundary {boundary_id}: "
                f"ensure timezone data is properly loaded from {self.data_location}"
            ) from e

    def _zone_ids_of(self, boundary_ids: np.ndarray) -> np.ndarray:
        """Look up several boundary polygons' zone ids without checking their signs."""
        return self.zone_ids[boundary_ids]

    def _zone_name_of(self, zone_id: int) -> str:
        """Look up a zone name without checking the id's sign."""
        try:
            return self.timezone_names[zone_id]
        except IndexError as e:
            raise ValueError(
                f"Zone ID {zone_id} is out of range. "
                f"Valid range: 0-{len(self.timezone_names) - 1}. "
                f"Loaded dataset has {self.nr_of_zones} timezones."
            ) from e

    def zone_id_of(self, boundary_id: IntegerLike) -> int:
        """
        Get the timezone ID for a specific boundary polygon.

        :param boundary_id: The numeric identifier of the boundary polygon
        :return: The timezone ID (index into timezone_names)
        :raises ValueError: If ``boundary_id`` does not select exactly one zone id - negative,
            out of range, not usable as an index, or selecting several. The underlying
            ``IndexError`` and ``TypeError`` are both re-raised as ``ValueError``, so that is
            the only type callers have to handle.
        """
        try:
            if boundary_id < 0:
                raise _negative_id_error("boundary polygon", boundary_id)
            return self._zone_id_of(boundary_id)
        except (TypeError, IndexError) as e:
            raise ValueError(
                f"Cannot get zone ID for boundary {boundary_id}: "
                f"ensure timezone data is properly loaded from {self.data_location}"
            ) from e

    def zone_ids_of(self, boundary_ids: np.ndarray) -> np.ndarray:
        """
        Get the zone IDs of multiple boundary polygons.

        :param boundary_ids: An array of boundary polygon IDs.
        :return: array of corresponding timezone IDs.
        :raises ValueError: If any id is negative. Out-of-range ids raise ``IndexError``
            from NumPy, as they do for any array indexing.
        """
        negative = np.asarray(boundary_ids) < 0
        if negative.any():
            raise _negative_id_error(
                "boundary polygon", np.asarray(boundary_ids)[negative][0]
            )
        return self._zone_ids_of(boundary_ids)

    def zone_name_from_id(self, zone_id: int) -> str:
        """
        Get the timezone name corresponding to a zone ID.

        :param zone_id: The numeric ID of the timezone (0-based index)
        :return: The IANA timezone name (e.g., 'Europe/Berlin')
        :raises ValueError: If ``zone_id`` is negative or out of range for the loaded
            dataset. The underlying ``IndexError`` is re-raised as ``ValueError``.
        :raises TypeError: If ``zone_id`` is not an integer.

        Example:
            >>> tf = TimezoneFinder()
            >>> tf.zone_name_from_id(0)
            'Africa/Abidjan'
        """
        if zone_id < 0:
            raise _negative_id_error("zone", zone_id)
        return self._zone_name_of(zone_id)

    def _zone_names_lookup_array(self) -> np.ndarray:
        """The names as an object array with ``None`` appended, built once per instance.

        The trailing ``None`` is what makes the gather need no masking:
        :data:`~timezonefinder.configs.NO_ZONE_ID` is ``-1``, so it indexes the last
        element by Python's own negative-index rule. That is the same "counts from the
        end" behaviour the public id-taking methods reject - deliberate here, because
        here the end *is* the sentinel, and every other negative is rejected before the
        gather runs.

        Instances are per-thread by contract, and even a race would build an identical
        array twice and assign the same content, so no lock is warranted.
        """
        lookup = self._zone_names_lookup
        if lookup is None:
            lookup = np.asarray([*self.timezone_names, None], dtype=object)
            self._zone_names_lookup = lookup
        return lookup

    def _zone_names_of(self, zone_ids: np.ndarray) -> list[str | None]:
        """Names for zone ids already known to be valid.

        Two regimes, because neither wins everywhere - see
        :data:`NAMES_GATHER_MIN_BATCH` for the measurement that sets the boundary.
        """
        if zone_ids.shape[0] < NAMES_GATHER_MIN_BATCH:
            timezone_names = self.timezone_names
            return [
                None if zone_id < 0 else timezone_names[zone_id]
                for zone_id in zone_ids.tolist()
            ]
        return self._zone_names_lookup_array()[zone_ids].tolist()

    def zone_names_from_ids(self, zone_ids: IdArrayLike) -> list[str | None]:
        """Convert many zone ids to timezone names in one call.

        The batch counterpart of :meth:`zone_name_from_id`, and what
        :meth:`timezone_ids_at` is meant to be paired with: keep the ids while they are
        being joined, filtered or grouped, and name them once at the end. Above a
        threshold the conversion is a numpy gather rather than a Python loop, which is
        several times faster per id on a large batch.

        :param zone_ids: the ids to name, as any 1-D array-like of integers.
        :return: one name per id, with ``None`` wherever the id is
            :data:`~timezonefinder.configs.NO_ZONE_ID` (``-1``) - so an answer from
            :meth:`timezone_ids_at` round-trips to exactly what
            :meth:`timezone_names_at` would have returned.
        :raises TypeError: if ``zone_ids`` does not hold integers.
        :raises ValueError: if ``zone_ids`` is not one-dimensional, or holds an id that
            is neither a valid zone id nor the sentinel. A negative other than ``-1`` is
            rejected rather than counted from the end of the dataset, as for
            :meth:`zone_name_from_id`.

        Example:
            >>> tf = TimezoneFinder()
            >>> ids = tf.timezone_ids_at(lngs=[13.358, 2.3522], lats=[52.5061, 48.8566])
            >>> tf.zone_names_from_ids(ids)
            ['Europe/Berlin', 'Europe/Paris']
        """
        ids = np.asarray(zone_ids)
        if ids.size == 0:
            # an empty list arrives as float64, which is not an error to convert
            return []
        if not np.issubdtype(ids.dtype, np.integer):
            raise TypeError(
                f"zone ids must be integers, got dtype {ids.dtype}. "
                f"An id is an index into the {self.nr_of_zones} loaded timezone names."
            )
        if ids.ndim != 1:
            raise ValueError(f"zone_ids must be one-dimensional, got shape {ids.shape}")
        # one pass for both bounds: below the sentinel, or past the last zone. The upper
        # half is not redundant with numpy's own IndexError - the lookup array carries one
        # extra slot for the sentinel, so ``nr_of_zones`` itself would quietly read it.
        invalid = (ids < NO_ZONE_ID) | (ids >= self.nr_of_zones)
        if invalid.any():
            offender = int(ids[invalid][0])
            raise ValueError(
                f"{offender} is not a valid zone id. Valid range: "
                f"0-{self.nr_of_zones - 1}, or {NO_ZONE_ID} for 'no zone'. "
                f"Loaded dataset has {self.nr_of_zones} timezones."
            )
        return self._zone_names_of(ids)

    def zone_name_from_boundary_id(self, boundary_id: IntegerLike) -> str:
        """
        Get the zone name from a boundary polygon ID.

        :param boundary_id: The ID of the boundary polygon.
        :return: The name of the zone.
        :raises ValueError: If ``boundary_id`` is negative or does not select exactly one
            zone id, as for :meth:`zone_id_of`.
        """
        # the id is validated by ``zone_id_of``; what it returns comes from ``zone_ids``
        # and is never negative, so the second lookup needs no second guard
        zone_id = self.zone_id_of(boundary_id)
        return self._zone_name_of(zone_id)

    def _iter_boundaries_in_shortcut(self, *, lng: float, lat: float) -> Iterable[int]:
        """
        Iterate over boundary polygon IDs in the shortcut corresponding to the given coordinates.

        :param lng: The longitude of the point in degrees (-180.0 to 180.0).
        :param lat: The latitude of the point in degrees (90.0 to -90.0).
        :yield: Boundary polygon IDs.
        """
        hex_id = h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES)

        entry = self.shortcuts.entry_of(hex_id)
        if entry == ABSENT:
            return
        if entry >= 0:
            # a cell a single zone covers: every boundary polygon of that zone is a
            # candidate. Most are quickly ruled out by the bounding box check.
            yield from self._iter_boundary_ids_of_zone(entry)
        else:
            yield from self.shortcuts.candidates_of(entry)

    @abstractmethod
    def timezone_at(self, *, lng: float, lat: float) -> str | None:
        """looks up in which timezone the given coordinate is included in

        :param lng: longitude of the point in degree (-180.0 to 180.0)
        :param lat: latitude in degree (90.0 to -90.0)
        :return: the timezone name of a matching polygon or None
        """
        ...

    @abstractmethod
    def _zone_id_in_ambiguous_cell(self, entry: int, lng: float, lat: float) -> int:
        """The zone id of a point whose H3 cell several timezones cover.

        Reached only for ``entry < ABSENT``: a cell a single zone covers and a cell no
        zone covers are both answered by the shortcut table itself. Both
        :meth:`timezone_at` and :meth:`timezone_ids_at` funnel through here, so the
        subclass's candidate handling exists exactly once.

        :param entry: the shortcut table's value for the cell, below ``ABSENT``
        :param lng: longitude of the point, already validated
        :param lat: latitude of the point, already validated
        :return: the id of the matching timezone
        """
        ...

    def timezone_ids_at(
        self,
        *,
        lngs: CoordArrayLike,
        lats: CoordArrayLike,
        on_invalid: str = "raise",
    ) -> np.ndarray:
        """Look up many coordinates at once, answering with timezone **ids**.

        The batch counterpart of :meth:`timezone_at`, and the primary one: a caller doing
        millions of lookups should not pay for millions of string lookups it maps straight
        back to something else. :meth:`timezone_names_at` is the convenience on top.

        What a batch amortises is the per-call overhead, not the geometry. Validation, the
        integer scaling and the shortcut lookup run once over the whole batch as numpy
        operations; ambiguous points still fall through to the point-in-polygon loop one
        at a time, and ``h3``'s cell lookup has no vectorised form, so it stays a loop
        too. Expect the win to be largest on points whose cell a single zone covers.

        :param lngs: longitudes in degrees, as any 1-D array-like. A C-contiguous
            ``float64`` numpy array is used without copying.
        :param lats: latitudes in degrees, the same length as ``lngs``.
        :param on_invalid: what to do with a coordinate outside the valid range (which
            includes ``NaN`` and infinity). ``"raise"`` (the default) matches the scalar
            methods; ``"skip"`` answers those points with
            :data:`~timezonefinder.configs.NO_ZONE_ID` and the rest normally.
        :return: one ``int32`` per input coordinate - a timezone id, or
            :data:`~timezonefinder.configs.NO_ZONE_ID` (``-1``) where the scalar method
            would answer ``None``: no zone covers the point, or it was skipped.
        :raises TypeError: if either axis holds values that are not numbers.
        :raises ValueError: if the two axes differ in length, either is not
            one-dimensional, ``on_invalid`` is not a known policy, or - under
            ``on_invalid="raise"`` - a coordinate is out of range.

        .. note:: coordinates are passed one axis per argument on purpose. A single
            ``(N, 2)`` array would have to be read positionally, and a swapped pair is
            still a valid coordinate for most of the populated world - so the mistake
            would return a real but wrong timezone instead of raising.

        Example:
            >>> tf = TimezoneFinder()
            >>> ids = tf.timezone_ids_at(lngs=[13.358, 2.3522], lats=[52.5061, 48.8566])
            >>> [tf.zone_name_from_id(int(i)) for i in ids]
            ['Europe/Berlin', 'Europe/Paris']
        """
        if on_invalid not in ON_INVALID_POLICIES:
            raise ValueError(
                f"unknown on_invalid policy {on_invalid!r}. "
                f"Choose one of: {', '.join(map(repr, ON_INVALID_POLICIES))}"
            )
        lng_array, lat_array = _coordinate_arrays(lngs, lats)
        out_of_bounds = _out_of_bounds(lng_array, lat_array)
        if not out_of_bounds.any():
            return self._zone_ids_of_valid(lng_array, lat_array)

        if on_invalid == "raise":
            first = int(np.argmax(out_of_bounds))
            raise ValueError(
                f"invalid coordinate at index {first}: "
                f"lng={lng_array[first]}, lat={lat_array[first]}. Longitude must be in "
                f"range [-{MAX_LNG_VAL}, {MAX_LNG_VAL}] and latitude in range "
                f'[-{MAX_LAT_VAL}, {MAX_LAT_VAL}], both finite. Pass on_invalid="skip" '
                f"to answer the remaining coordinates and get {NO_ZONE_ID} for this one."
            )

        keep = ~out_of_bounds
        zone_ids = np.full(lng_array.shape[0], NO_ZONE_ID, dtype=ZONE_ID_RESULT_DTYPE)
        zone_ids[keep] = self._zone_ids_of_valid(lng_array[keep], lat_array[keep])
        return zone_ids

    def timezone_names_at(
        self,
        *,
        lngs: CoordArrayLike,
        lats: CoordArrayLike,
        on_invalid: str = "raise",
    ) -> list[str | None]:
        """Look up many coordinates at once, answering with timezone **names**.

        The convenience on top of :meth:`timezone_ids_at`, which documents the arguments,
        the ``on_invalid`` policies and every error raised. Each answer is what
        :meth:`timezone_at` would return for that point, ``None`` included.

        Prefer the id form whenever the names are not the end product: this method adds
        one list index and one Python object per coordinate, which is most of what a
        batch lookup was meant to avoid.

        :return: one timezone name per input coordinate, or ``None`` where no zone covers
            the point or the coordinate was skipped.

        Example:
            >>> tf = TimezoneFinder()
            >>> tf.timezone_names_at(lngs=[13.358, 2.3522], lats=[52.5061, 48.8566])
            ['Europe/Berlin', 'Europe/Paris']
        """
        zone_ids = self.timezone_ids_at(lngs=lngs, lats=lats, on_invalid=on_invalid)
        # the unchecked converter: every id here came from the shortcut index or from
        # ``zone_ids``, so re-validating what this call itself just produced would pay a
        # pass over the batch to learn nothing - the same split as the id-taking methods
        return self._zone_names_of(zone_ids)

    def _zone_ids_of_valid(self, lngs: np.ndarray, lats: np.ndarray) -> np.ndarray:
        """Zone ids for coordinates already known to be in range.

        The prologue every point shares runs once over the whole batch: the slot
        arithmetic and the table read are one numpy operation each rather than N. What
        cannot join them is ``h3.latlng_to_cell`` - h3-py exposes no vectorised form, so
        N points cost N scalar C calls, and that is nearly the whole cost of a batched
        lookup once the cells resolve to a single zone.
        """
        nr_points = lngs.shape[0]
        if nr_points == 0:
            return np.empty(0, dtype=ZONE_ID_RESULT_DTYPE)

        # bound once outside the loop: N attribute lookups are a measurable share of a
        # stage that is otherwise a single C call per point
        latlng_to_cell = h3.latlng_to_cell
        resolution = SHORTCUT_H3_RES
        hex_ids = np.fromiter(
            (
                latlng_to_cell(lat, lng, resolution)
                for lat, lng in zip(lats.tolist(), lngs.tolist())
            ),
            dtype=np.uint64,
            count=nr_points,
        )
        entries = self.shortcuts.entries_of(hex_ids)

        # a non-negative entry is the answer itself. ABSENT and the candidate-list
        # encodings are both "no answer yet"; the latter are then resolved per point,
        # which is the only part of a batch that is not vectorised.
        zone_ids = np.where(entries >= 0, entries, NO_ZONE_ID).astype(
            ZONE_ID_RESULT_DTYPE
        )
        for i in np.flatnonzero(entries < ABSENT):
            zone_ids[i] = self._zone_id_in_ambiguous_cell(
                int(entries[i]), float(lngs[i]), float(lats[i])
            )
        return zone_ids

    def timezone_at_land(self, *, lng: float, lat: float) -> str | None:
        """computes in which land timezone a point is included in

        Especially for large polygons it is expensive to check if a point is really included.
        To speed things up there are "shortcuts" being used (stored in a binary file),
        which have been precomputed and store which timezone polygons have to be checked.

        :param lng: longitude of the point in degree (-180.0 to 180.0)
        :param lat: latitude in degree (90.0 to -90.0)
        :return: the timezone name of a matching polygon or
            ``None`` when an ocean timezone ("Etc/GMT+-XX") has been matched.
        """
        tz_name = self.timezone_at(lng=lng, lat=lat)
        if tz_name is not None and utils.is_ocean_timezone(tz_name):
            return None
        return tz_name

    def unique_timezone_at(self, *, lng: float, lat: float) -> str | None:
        """returns the name of a unique zone within the corresponding shortcut

        :param lng: longitude of the point in degree (-180.0 to 180.0)
        :param lat: latitude in degree (90.0 to -90.0)
        :return: the timezone name of the unique zone or ``None`` if there are no or multiple zones in this shortcut
        """
        lng, lat = utils.validate_coordinates(lng, lat)
        hex_id = h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES)

        # a zone id in the table *is* the precomputed uniqueness; anything else in it
        # means either no coverage or several zones, and neither is a unique answer
        zone_id = self.shortcuts.entry_of(hex_id)
        if zone_id < 0:
            return None
        return self._zone_name_of(zone_id)

    def cleanup(self) -> None:
        """Clean up resources. Override in subclasses as needed."""
        # At termination utils may have been tidied up. If we're terminating we don't need to
        # worry about closing file handles so just avoid an exception.
        close_resource = getattr(utils, "close_resource", None)
        if close_resource is None:
            return

        # PolygonArray exposes underlying accessors that manage their own buffers;
        # this is a best-effort close for any objects with a close() method.
        close_resource(getattr(self, "boundaries", None))
        close_resource(getattr(self, "holes", None))
        # hole_registry is an in-memory dict only; nothing to close

    def __enter__(self) -> Self:
        """Enter the runtime context for the TimezoneFinder."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the runtime context and clean up resources."""
        self.cleanup()
        return False


class TimezoneFinderL(AbstractTimezoneFinder):
    """A lightweight version of TimezoneFinder for quick timezone suggestions.

    Instead of using timezone polygon data like ``TimezoneFinder``,
    this class only uses a precomputed 'shortcut' to suggest a probable result:
    the most common zone in a rectangle of a half degree of latitude and one degree of longitude.

    Thread Safety:
        Each thread that performs timezone lookups must create its own independent
        TimezoneFinderL instance. Do not share a single instance across threads.
    """

    def __init__(
        self,
        bin_file_location: str | Path | None = None,
        in_memory: bool = False,
    ):
        super().__init__(bin_file_location, in_memory)

    def timezone_at(self, *, lng: float, lat: float) -> str | None:
        """instantly returns the name of the most common zone within the corresponding shortcut

        Note: 'most common' in this context means that the boundary polygons with the most coordinates in sum
            occurring in the corresponding shortcut belong to this zone.

        :param lng: longitude of the point in degree (-180.0 to 180.0)
        :param lat: latitude in degree (90.0 to -90.0)
        :return: the timezone name of the most common zone or None if there are no timezone polygons in this shortcut
        """
        lng, lat = utils.validate_coordinates(lng, lat)
        # Inline fast-path to minimize helper overhead
        hex_id = h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES)

        entry = self.shortcuts.entry_of(hex_id)
        if entry >= 0:
            # unique zone case: the index holds the answer
            return self._zone_name_of(entry)
        if entry == ABSENT:
            return None
        return self._zone_name_of(self._zone_id_in_ambiguous_cell(entry, lng, lat))

    def _zone_id_in_ambiguous_cell(self, entry: int, lng: float, lat: float) -> int:
        """The most common zone of the cell - this class tests no geometry.

        The coordinates are therefore unused: which zone is *most* common in a cell is a
        property of the cell, and answering without a point-in-polygon test is the whole
        of what makes this class lightweight.
        """
        # several zones - the last candidate belongs to the most common one
        poly_of_biggest_zone = self.shortcuts.candidates_of(entry)[-1]
        # a numpy integer scalar from array indexing, which mypy reads as ndarray. Safe:
        # element access yields a scalar compatible with IntegerLike
        return self._zone_id_of(poly_of_biggest_zone)  # type: ignore[arg-type]


class TimezoneFinder(AbstractTimezoneFinder):
    """Class for quickly finding the timezone of a point on earth offline.

    Because of indexing ("shortcuts"), not all timezone polygons have to be tested during a query.

    Opens the required timezone polygon data in binary files to enable fast access.
    For a detailed documentation of data management please refer to the code documentation of
    `file_converter.py <https://github.com/jannikmi/timezonefinder/blob/master/scripts/file_converter.py>`__

    Thread Safety:
        Each thread that performs timezone lookups must create its own independent
        TimezoneFinder instance. Do not share a single instance across threads, as this can
        lead to race conditions and incorrect results. Example:

            import threading
            from timezonefinder import TimezoneFinder

            def lookup_in_thread(lng, lat):
                # Each thread creates its own instance
                tf = TimezoneFinder(in_memory=True)
                return tf.timezone_at(lng=lng, lat=lat)

    Parameters:
        :param bin_file_location: path to the binary data files to use, None if native package data should be used
        :param in_memory: Whether to completely read and keep the coordinate data in memory as numpy arrays.
    """

    # __slots__ declared in parents are available in child classes. However, child subclasses will get a __dict__
    # and __weakref__ unless they also define __slots__ (which should only contain names of any additional slots).
    __slots__ = [
        "hole_registry",
    ]

    def __init__(
        self,
        bin_file_location: str | Path | None = None,
        in_memory: bool = False,
    ):
        super().__init__(bin_file_location, in_memory)
        self.holes_dir = utils.get_holes_dir(self.data_location)
        self.boundaries_dir = utils.get_boundaries_dir(self.data_location)
        self.boundaries = PolygonArray(
            data_location=self.boundaries_dir, in_memory=in_memory
        )
        self.holes = HoleArray(
            data_location=self.holes_dir,
            boundaries=self.boundaries,
            in_memory=in_memory,
        )

        # stores for which polygons (how many) holes exits and the id of the first of those holes
        # since there are very few entries it is feasible to keep them in the memory
        self.hole_registry = self._load_hole_registry()

    def __del__(self) -> None:
        """Clean up resources when the object is destroyed."""
        try:
            self.cleanup()
        except (AttributeError, FileNotFoundError, OSError, ValueError):
            # Expected cleanup errors when resource is not fully initialized
            # or already cleaned up. It's safe to ignore these.
            pass
        except Exception as e:
            # Unexpected errors during cleanup should not be silenced
            warnings.warn(
                f"Error during TimezoneFinder cleanup: {e}",
                ResourceWarning,
                stacklevel=2,
            )

    def _load_hole_registry(self) -> dict[int, tuple[int, int]]:
        """
        Load and convert the hole registry from JSON file, converting keys to int.
        """
        path = utils.get_hole_registry_path(self.data_location)
        with open(path, encoding="utf-8") as json_file:
            hole_registry_tmp = json.loads(json_file.read())
        # convert the json string keys to int
        return {int(k): v for k, v in hole_registry_tmp.items()}

    @property
    def nr_of_polygons(self) -> int:
        return len(self.boundaries)

    @property
    def nr_of_holes(self) -> int:
        return len(self.holes)

    def coords_of(self, boundary_id: IntegerLike = 0) -> np.ndarray:
        """
        Get the coordinates of a boundary polygon from the FlatBuffers collection.

        :param boundary_id: The index of the polygon.
        :return: Array of coordinates.
        """
        return self.boundaries.coords_of(boundary_id)

    def _iter_hole_ids_of(self, boundary_id: IntegerLike) -> Iterable[int]:
        """
        Yield the hole IDs for a given boundary polygon id.

        :param boundary_id: id of the boundary polygon
        :yield: Hole IDs
        """
        try:
            amount_of_holes, first_hole_id = self.hole_registry[int(boundary_id)]
        except KeyError:
            return
        for i in range(amount_of_holes):
            yield first_hole_id + i

    def _holes_of_poly(self, boundary_id: IntegerLike) -> Iterable[np.ndarray]:
        """
        Get the hole coordinates of a boundary polygon from the FlatBuffers collection.

        :param boundary_id: id of the boundary polygon
        :yield: Generator of hole coordinates
        """
        for hole_id in self._iter_hole_ids_of(boundary_id):
            yield self.holes.coords_of(hole_id)

    def get_polygon(
        self, boundary_id: IntegerLike, coords_as_pairs: bool = False
    ) -> list[CoordPairs | CoordLists]:
        """
        Get the polygon coordinates of a given boundary polygon including its holes.

        :param boundary_id:  ID of the boundary polygon
        :param coords_as_pairs: If True, returns coordinates as pairs (lng, lat).
            If False, returns coordinates as separate lists of longitudes and latitudes.
        :return: List of polygon coordinates
        """
        list_of_converted_polygons = []
        if coords_as_pairs:
            conversion_method = utils.convert2coord_pairs
        else:
            conversion_method = utils.convert2coords
        list_of_converted_polygons.append(
            conversion_method(self.coords_of(boundary_id=boundary_id))
        )

        for hole in self._holes_of_poly(boundary_id):
            list_of_converted_polygons.append(conversion_method(hole))

        return list_of_converted_polygons

    def get_geometry(
        self,
        tz_name: str | None = "",
        tz_id: int | None = 0,
        use_id: bool = False,
        coords_as_pairs: bool = False,
    ) -> list[list[CoordPairs | CoordLists]]:
        """retrieves the geometry of a timezone: multiple boundary polygons with holes

        :param tz_name: one of the names in ``timezone_names.txt`` or ``self.timezone_names``
        :param tz_id: the id of the timezone (=index in ``self.timezone_names``)
        :param use_id: if ``True`` uses ``tz_id`` instead of ``tz_name``
        :param coords_as_pairs: determines the structure of the polygon representation
        :return: a data structure representing the multipolygon of this timezone
            output format: ``[ [polygon1, hole1, hole2...], [polygon2, ...], ...]``
            and each polygon and hole is itself formatted like: ``([longitudes], [latitudes])``
            or ``[(lng1,lat1), (lng2,lat2),...]`` if ``coords_as_pairs=True``.
        """

        if use_id:
            if not isinstance(tz_id, int):
                raise TypeError("the zone id must be given as int.")
            if tz_id < 0 or tz_id >= self.nr_of_zones:
                raise ValueError(
                    f"the given zone id {tz_id} is invalid (value range: 0 - {self.nr_of_zones - 1}."
                )
        else:
            if tz_name is None:
                raise ValueError("no timezone name given.")
            try:
                tz_id = self.timezone_names.index(tz_name)
            except ValueError:
                # deliberately unchained: the underlying "x is not in list" from
                # ``list.index`` adds nothing over the message built here
                raise ValueError(f"The timezone '{tz_name}' does not exist.") from None
        if tz_id is None:
            raise ValueError("no timezone id given.")

        return [
            self.get_polygon(boundary_id, coords_as_pairs)
            for boundary_id in self._iter_boundary_ids_of_zone(tz_id)
        ]

    def inside_of_polygon(self, boundary_id: IntegerLike, x: int, y: int) -> bool:
        """
        Check if a point is inside a boundary polygon.

        :param boundary_id: boundary polygon ID
        :param x: X-coordinate of the point
        :param y: Y-coordinate of the point
        :return: True if the point lies inside the boundary polygon, False if outside or in a hole.
        """
        # avoid running the expensive PIP algorithm at any cost
        # -> check bboxes first
        if self.boundaries.outside_bbox(boundary_id, x, y):
            return False

        # NOTE: holes are much smaller (fewer points) -> less expensive to check
        # -> check holes before the boundary
        hole_id_iter = self._iter_hole_ids_of(boundary_id)
        if self.holes.in_any_polygon(hole_id_iter, x, y):
            # the point is within one of the holes
            # it is excluded fromn this boundary polygon
            return False

        return self.boundaries.pip(boundary_id, x, y)

    def timezone_at(self, *, lng: float, lat: float) -> str | None:
        """
        Find the timezone for a given point using hybrid shortcuts, considering both land and ocean timezones.

        Uses precomputed hybrid shortcuts to reduce the number of polygons checked. Returns the timezone name
        of the matched polygon, which may be an ocean timezone ("Etc/GMT+-XX") if applicable.

        Since ocean timezones span the whole globe, some timezone will always be matched!
        `None` can only be returned when using custom timezone data without such ocean timezones.

        .. note:: for speed the last remaining zone is returned *without* a point in polygon test:
            once no other zone can be matched, its polygons cannot change the outcome. With the
            packaged data this is always correct, since the ocean zones cover the globe and every
            point therefore lies within one of the candidate polygons. With custom data that leaves
            areas uncovered it is not: a point inside none of the candidates is still attributed to
            that last zone. Use :meth:`certain_timezone_at` there, which tests every candidate.

        :param lng: longitude of the point in degrees (-180.0 to 180.0)
        :param lat: latitude of the point in degrees (90.0 to -90.0)
        :return: the timezone name of the matched polygon, or None if no match is found.
        """
        # NOTE: performance critical code. avoid helper function call overhead as much as possible
        lng, lat = utils.validate_coordinates(lng, lat)
        hex_id = h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES)

        # one lookup answers most queries: a zone id is the answer itself
        entry = self.shortcuts.entry_of(hex_id)
        if entry >= 0:
            return self._zone_name_of(entry)
        if entry == ABSENT:
            # NOTE: hypothetical case, with ocean data every cell holds at least one boundary polygon
            return None

        # several zones - the candidates have to be tested. One call, shared with the
        # batch path, so the loop below exists once.
        return self._zone_name_of(self._zone_id_in_ambiguous_cell(entry, lng, lat))

    def _zone_id_in_ambiguous_cell(self, entry: int, lng: float, lat: float) -> int:
        """Work the cell's candidate polygons until one contains the point.

        The last remaining zone is returned without a test - see :meth:`timezone_at`,
        whose note explains when that is and is not correct.

        NOTE: neither the empty nor the single-candidate case can occur here; both are
        unambiguous and are stored in the shortcut table itself.
        """
        possible_boundaries = self.shortcuts.candidates_of(entry)

        # create a list of all the timezone ids of all possible boundary polygons
        zone_ids = self._zone_ids_of(possible_boundaries)

        # where the loop may stop, precomputed at build time - a property of the candidate
        # list, so it is stored once per distinct list rather than recomputed per query.
        # NOTE: the case last_zone_change_idx == 0 is covered by the unique zone shortcut
        last_zone_change_idx = self.shortcuts.stop_index_of(entry)

        # ATTENTION: the polygons are stored converted to 32-bit ints,
        # convert the query coordinates in the same fashion in order to make the data formats match
        # x = longitude  y = latitude  both converted to 8byte int
        x = utils.coord2int(lng)
        y = utils.coord2int(lat)

        # check until the point is included in one of the possible boundary polygons
        for i, boundary_id in enumerate(possible_boundaries):
            if i >= last_zone_change_idx:
                # avoid expensive PIP checks when no other zone can be matched anymore
                break

            if self.inside_of_polygon(boundary_id, x, y):
                return int(zone_ids[i])

        # since it is the last possible option,
        # the polygons of the last possible zone don't actually have to be checked
        # -> instantly return the last zone
        return int(zone_ids[-1])

    def certain_timezone_at(self, *, lng: float, lat: float) -> str | None:
        """checks in which timezone polygon the point is certainly included in using hybrid shortcuts

        .. note:: this is only meaningful when you have compiled your own timezone data
            where there are areas without timezone polygon coverage.
            Otherwise, some timezone will always be matched and the functionality is equal to using `.timezone_at()`
            -> useless to actually test all polygons.

        .. note:: using this function is less performant than `.timezone_at()`

        :param lng: longitude of the point in degree
        :param lat: latitude of the point in degree
        :return: the timezone name of the polygon the point is included in or `None`
        """
        lng, lat = utils.validate_coordinates(lng, lat)
        hex_id = h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES)

        entry = self.shortcuts.entry_of(hex_id)
        if entry == ABSENT:
            return None

        # ATTENTION: the polygons are stored converted to 32-bit ints,
        # convert the query coordinates in the same fashion in order to make the data formats match
        # x = longitude  y = latitude  both converted to 8byte int
        x = utils.coord2int(lng)
        y = utils.coord2int(lat)

        # check if the query point is found to be truly included in one of the possible boundary polygons
        boundary_ids: Iterable[int]
        if entry >= 0:
            # a zone id: every boundary polygon of that zone is a candidate.
            # Most are quickly ruled out by the bounding box check.
            boundary_ids = self._iter_boundary_ids_of_zone(entry)
        else:
            boundary_ids = self.shortcuts.candidates_of(entry)

        for boundary_id in boundary_ids:
            if self.inside_of_polygon(boundary_id, x, y):
                zone_id = self._zone_id_of(boundary_id)
                return self._zone_name_of(zone_id)

        # none of the boundary polygon candidates truly matched
        return None
