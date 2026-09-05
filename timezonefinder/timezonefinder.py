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
from datetime import datetime, timedelta
from pathlib import Path
from typing import Self
from zoneinfo import ZoneInfo

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
    OnInvalid,
    ZONE_ID_RESULT_DTYPE,
)

from timezonefinder.shortcut_index import (
    ABSENT,
    ShortcutIndex,
    get_shortcut_file_path,
    read_shortcuts_binary,
)
from timezonefinder.zone_names import ZoneNames, read_zone_names


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
        zone_names: the dataset's names, and every way a zone id becomes one
        timezone_names: List of all available timezone names (a view onto ``zone_names``)
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
        "zone_names",
        "zone_ids",
        "_zone_positions",
        "holes_dir",
        "boundaries_dir",
        "boundaries",
        "holes",
    ]

    zone_ids: np.ndarray
    #: where each zone's boundary polygons start, read on first use - see
    #: ``_iter_boundary_ids_of_zone``, which is the only thing that reads it.
    _zone_positions: np.ndarray | None
    #: which timezones can possibly cover a point. This class asks it what a cell resolves
    #: to and never how that is stored - see ``timezonefinder/shortcut_index.py``.
    shortcuts: ShortcutIndex
    #: the dataset's names, and every way a zone id becomes one. This class produces ids
    #: and asks it to name them - see ``timezonefinder/zone_names.py``.
    zone_names: ZoneNames

    def __init__(
        self,
        bin_file_location: str | Path | None = None,
    ):
        """
        Initialize the AbstractTimezoneFinder.

        Loads the zone names, the per-polygon zone ids and the shortcut index, all of
        which are always held in memory. Selecting how the polygon coordinate data is
        accessed belongs to the subclass that loads it: ``TimezoneFinder`` takes
        ``in_memory`` for that, and this class has nothing to apply it to.

        :param bin_file_location: Path to the directory containing binary timezone data.
                                 If None, uses the bundled package data directory.
        :raises FileNotFoundError: If timezone data files cannot be found at the specified location
        :raises ValueError: If timezone data files are corrupted or in an invalid format
        """
        if bin_file_location is None:
            bin_file_location = DEFAULT_DATA_DIR
        self.data_location: Path = Path(bin_file_location)

        self.zone_names = ZoneNames(read_zone_names(self.data_location))

        self.zone_ids = read_per_polygon_vector(get_zone_ids_path(self.data_location))

        self.shortcuts = read_shortcuts_binary(
            get_shortcut_file_path(self.data_location)
        )

        # not read here: only ``certain_timezone_at`` and ``get_geometry`` address a
        # zone's boundary range, and the ``timezone_at`` majority never calls either.
        # See ``_iter_boundary_ids_of_zone`` for why the first caller reads it once.
        self._zone_positions = None

    def _iter_boundary_ids_of_zone(self, zone_id: int) -> Iterable[int]:
        """
        Yield the boundary polygon IDs for a given zone ID.

        :param zone_id: ID of the zone
        :yield: boundary polygon IDs
        """
        # Read on first use and then kept, rather than per call: the file is 890
        # immutable bytes and a per-call ``np.load`` paid a file open, a header parse
        # and a mapping for every one of them. Reading it in ``__init__`` instead would
        # charge every construction - itself a tracked benchmark, and multiplied by the
        # thread count under the documented one-instance-per-thread pattern - for an
        # array the majority of instances never touch. Two threads racing this both read
        # the same immutable array, so the race costs a duplicated read and nothing else.
        zone_positions = self._zone_positions
        if zone_positions is None:
            zone_positions = read_per_polygon_vector(
                get_zone_positions_path(self.data_location)
            )
            self._zone_positions = zone_positions
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
    def timezone_names(self) -> list[str]:
        """
        All timezone names of the loaded dataset, in zone id order.

        A read-only view onto :attr:`zone_names`, which owns the list and everything
        that turns an id back into one.

        :rtype: list[str]
        """
        return self.zone_names.names

    @property
    def nr_of_zones(self) -> int:
        """
        Get the number of timezones.

        :rtype: int
        """
        return len(self.zone_names)

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
        # The packed kernel, because that is the one a lookup reaches
        # (``PolygonArray.pip``). ``utils.inside_polygon`` is bound by the same rule but
        # serves callers holding a bare ring, so reading it here would answer about an
        # implementation this method's caller never runs.
        #
        # This reports the *import-time* binding, which is what every normally
        # constructed finder runs. A collection built while the module attribute was
        # deliberately rebound - what ``tests/test_acceleration_paths.py`` and
        # ``scripts/measure_acceleration_paths.py`` do - keeps the kernel it captured,
        # and this method does not see that. Deliberate: it stays a ``staticmethod``
        # because it is public API called on the class, and nothing that rebinds the
        # path asks it which path is bound - each of them names the path it bound.
        return utils.inside_polygon_packed == utils_clang.pt_in_poly_clang_packed

    # Validation happens at the public edge only. Every internal caller below obtains its
    # id from the shortcut index or from ``zone_ids``, neither of which can hold a negative
    # value, and the unchecked accessors run once per successful query - so the guard the
    # public methods need is not paid on the lookup path. Names are reached through
    # ``self.zone_names`` directly rather than through a private wrapper here: a
    # forwarding method would be a second call on the one accessor every successful
    # query makes.

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
        return self.zone_names.name_of(zone_id)

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
        return self.zone_names.names_from_ids(zone_ids)

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
        return self.zone_names.name_of(zone_id)

    def _iter_boundaries_in_shortcut(self, *, lng: float, lat: float) -> Iterable[int]:
        """
        Iterate over boundary polygon IDs in the shortcut corresponding to the given coordinates.

        Every candidate the shortcut index offers for a point, in the order they are
        stored - what ``certain_timezone_at`` tests, and what a test asking "which
        zones could this point have matched" walks. ``timezone_at`` deliberately does
        not call it: a cell resolving to a single zone is answered by name there,
        without addressing that zone's boundary polygons at all.

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
    def _resolve_ambiguous_cells(
        self,
        entries: np.ndarray,
        positions: np.ndarray,
        lngs: np.ndarray,
        lats: np.ndarray,
        out: np.ndarray,
    ) -> None:
        """Write the zone id of every point whose cell several zones cover into ``out``.

        Separate from :meth:`_zone_id_in_ambiguous_cell` because a batch can share what a
        single query cannot: **points in a batch cluster.** A delivery round, a city, a
        border region all land in a handful of cells, and everything a cell costs to
        prepare is identical for every point in it. Each implementation therefore does
        that preparation once per distinct shortcut entry, in whichever way suits how
        much of its answer the entry decides:

        * :class:`TimezoneFinder` still has to test the point against the geometry, so
          only the preparation is shared - memoised in a dict rather than reached by
          sorting the batch, because a dict lookup is a few tens of nanoseconds against
          the preparation it skips and, unlike an ``argsort``, costs essentially nothing
          when a batch happens to share nothing, which a uniformly random one largely
          does.
        * :class:`TimezoneFinderL` answers from the entry alone, so the whole resolution
          is one gather over the distinct entries and the per-point work is a scatter.

        Whatever the shape, read the batch's arrays once per stage and not once per
        point: a numpy scalar extraction inside the loop costs more than the loop body
        it feeds.

        :param entries: the shortcut table value of every point in the batch
        :param positions: indices into ``entries`` of the points to resolve
        :param lngs: longitudes of the whole batch, already validated
        :param lats: latitudes of the whole batch, already validated
        :param out: the answer array, written in place at ``positions``
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
        on_invalid: OnInvalid = "raise",
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
        :return: one ``int16`` per input coordinate - a timezone id, or
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
        if on_invalid not in utils.ON_INVALID_POLICIES:
            raise ValueError(
                f"unknown on_invalid policy {on_invalid!r}. "
                f"Choose one of: {', '.join(map(repr, utils.ON_INVALID_POLICIES))}"
            )
        lng_array, lat_array = utils.coordinate_arrays(lngs, lats)
        out_of_bounds = utils.out_of_bounds(lng_array, lat_array)
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
        on_invalid: OnInvalid = "raise",
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
        return self.zone_names.names_of(zone_ids)

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
        ambiguous = np.flatnonzero(entries < ABSENT)
        if ambiguous.size:
            self._resolve_ambiguous_cells(entries, ambiguous, lngs, lats, zone_ids)
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

    def timezone_ids_at_land(
        self,
        *,
        lngs: CoordArrayLike,
        lats: CoordArrayLike,
        on_invalid: OnInvalid = "raise",
    ) -> np.ndarray:
        """Look up many coordinates at once, answering with **land** timezone ids.

        The batch counterpart of :meth:`timezone_at_land`, and - as with
        :meth:`timezone_ids_at`, whose arguments and errors this shares - the primary
        one, with :meth:`timezone_names_at_land` the convenience on top.

        The ocean check costs nothing per point here. Ocean-ness is a fixed property of
        a *zone id* for a given dataset, so the whole answer array is masked in one
        indexing operation rather than testing each answer's name - which makes this
        cheaper per point than calling :meth:`timezone_at_land` in a loop, not merely
        equal to it.

        :param lngs: longitudes in degrees, as any 1-D array-like.
        :param lats: latitudes in degrees, the same length as ``lngs``.
        :param on_invalid: what to do with a coordinate outside the valid range - see
            :meth:`timezone_ids_at`, which documents the policies.
        :return: one ``int16`` per input coordinate - a land timezone id, or
            :data:`~timezonefinder.configs.NO_ZONE_ID` (``-1``) where
            :meth:`timezone_at_land` would answer ``None``: an ocean zone matched, no
            zone covers the point, or it was skipped. The three are deliberately one
            sentinel, exactly as in :meth:`timezone_ids_at`.
        :raises TypeError: if either axis holds values that are not numbers.
        :raises ValueError: if the two axes differ in length, either is not
            one-dimensional, ``on_invalid`` is not a known policy, or - under
            ``on_invalid="raise"`` - a coordinate is out of range.

        .. note:: coordinates are passed one axis per argument, for the reason
            :meth:`timezone_ids_at` gives: a single ``(N, 2)`` array would be read
            positionally, and a swapped pair is still a valid coordinate for most of the
            populated world - so the mistake would return a real but wrong answer
            instead of raising. Such an array is rejected as not one-dimensional.

        Example:
            >>> tf = TimezoneFinder()
            >>> ids = tf.timezone_ids_at_land(lngs=[13.358, -30.0], lats=[52.5061, 0.0])
            >>> ids[1] == NO_ZONE_ID  # mid-Atlantic: an ocean zone, so no land answer
            True
        """
        zone_ids = self.timezone_ids_at(lngs=lngs, lats=lats, on_invalid=on_invalid)
        # a fresh array from the call above, so masking it in place copies nothing
        zone_ids[self.zone_names.ocean_flags()[zone_ids]] = NO_ZONE_ID
        return zone_ids

    def timezone_names_at_land(
        self,
        *,
        lngs: CoordArrayLike,
        lats: CoordArrayLike,
        on_invalid: OnInvalid = "raise",
    ) -> list[str | None]:
        """Look up many coordinates at once, answering with **land** timezone names.

        The convenience on top of :meth:`timezone_ids_at_land`, which documents the
        arguments and every error raised. Each answer is what :meth:`timezone_at_land`
        would return for that point, ``None`` included.

        Prefer the id form whenever the names are not the end product, for the reason
        :meth:`timezone_names_at` gives.

        :return: one timezone name per input coordinate, or ``None`` where an ocean zone
            matched, no zone covers the point, or the coordinate was skipped.

        Example:
            >>> tf = TimezoneFinder()
            >>> tf.timezone_names_at_land(lngs=[13.358, -30.0], lats=[52.5061, 0.0])
            ['Europe/Berlin', None]
        """
        zone_ids = self.timezone_ids_at_land(
            lngs=lngs, lats=lats, on_invalid=on_invalid
        )
        return self.zone_names.names_of(zone_ids)

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
        return self.zone_names.name_of(zone_id)

    # --- turning the answer into something usable -------------------------------
    #
    # The three steps every caller takes next, and the reason they are here rather
    # than in each caller: the ``Etc/GMT`` zones the packaged data returns for every
    # coordinate at sea carry an **inverted** sign convention - ``Etc/GMT+5`` is
    # UTC-5. Deriving an offset by reading the name produces the wrong sign without
    # failing, and the library is the party that knows this. All three resolve the
    # name through the standard library's ``zoneinfo``, which applies the convention
    # correctly and caches its ``ZoneInfo`` objects, so repeated calls do not re-read
    # the timezone database.

    def zoneinfo_at(self, *, lng: float, lat: float) -> ZoneInfo | None:
        """The timezone covering a point, as a ``zoneinfo.ZoneInfo``.

        :param lng: longitude of the point in degree (-180.0 to 180.0)
        :param lat: latitude in degree (90.0 to -90.0)
        :return: the zone :meth:`timezone_at` names, or ``None`` where that answers
            ``None``
        :raises ValueError: if the coordinates are out of bounds
        :raises zoneinfo.ZoneInfoNotFoundError: if the platform has no timezone
            database holding that name. Windows ships none, so ``pip install tzdata``
            is required there - this package returns IANA names and does not carry
            the database itself.

        Example:
            >>> tf = TimezoneFinder()
            >>> tf.zoneinfo_at(lng=13.358, lat=52.5061)
            zoneinfo.ZoneInfo(key='Europe/Berlin')
        """
        tz_name = self.timezone_at(lng=lng, lat=lat)
        if tz_name is None:
            return None
        return ZoneInfo(tz_name)

    def utc_offset_at(
        self, *, lng: float, lat: float, when: datetime | None = None
    ) -> timedelta | None:
        """The UTC offset in force at a point, at a given moment.

        The offset is a property of a zone *and a date*, since it changes with daylight
        saving time - so it is read off an aware datetime rather than off the zone.

        :param lng: longitude of the point in degree (-180.0 to 180.0)
        :param lat: latitude in degree (90.0 to -90.0)
        :param when: the moment to read the offset at, defaulting to now. A naive
            datetime is read as local wall-clock time in the zone found; an aware one
            is read as the instant it denotes.
        :return: the offset as a ``timedelta``, or ``None`` where :meth:`timezone_at`
            answers ``None``
        :raises ValueError: if the coordinates are out of bounds
        :raises zoneinfo.ZoneInfoNotFoundError: on a platform without a timezone
            database - see :meth:`zoneinfo_at`, which names the Windows case

        Example:
            >>> tf = TimezoneFinder()
            >>> tf.utc_offset_at(lng=13.358, lat=52.5061, when=datetime(2026, 1, 1))
            datetime.timedelta(seconds=3600)
        """
        zone = self.zoneinfo_at(lng=lng, lat=lat)
        if zone is None:
            return None
        if when is None:
            return datetime.now(tz=zone).utcoffset()
        if when.tzinfo is None:
            return when.replace(tzinfo=zone).utcoffset()
        return when.astimezone(zone).utcoffset()

    def localize(self, dt: datetime, *, lng: float, lat: float) -> datetime | None:
        """Attach the timezone covering a point to a naive datetime.

        The datetime is read as local wall-clock time there: the instant it denotes is
        decided by the zone, which is what makes this different from
        ``dt.astimezone(...)`` on an already-aware value.

        :param dt: a naive datetime, i.e. local time at the point
        :param lng: longitude of the point in degree (-180.0 to 180.0)
        :param lat: latitude in degree (90.0 to -90.0)
        :return: the same wall-clock time made aware, or ``None`` where
            :meth:`timezone_at` answers ``None``
        :raises ValueError: if the coordinates are out of bounds, or if ``dt`` already
            carries a timezone - converting one is ``dt.astimezone()``'s job, and
            silently re-labelling it would move the instant it denotes
        :raises zoneinfo.ZoneInfoNotFoundError: on a platform without a timezone
            database - see :meth:`zoneinfo_at`, which names the Windows case

        Example:
            >>> tf = TimezoneFinder()
            >>> tf.localize(datetime(2026, 1, 1, 12), lng=13.358, lat=52.5061)
            datetime.datetime(2026, 1, 1, 12, 0, tzinfo=zoneinfo.ZoneInfo(key='Europe/Berlin'))
        """
        if dt.tzinfo is not None:
            raise ValueError(
                f"{dt!r} already carries a timezone. localize() interprets a naive "
                "datetime as local time at the given point; to convert an aware one, "
                "call dt.astimezone(tf.zoneinfo_at(lng=..., lat=...))."
            )
        zone = self.zoneinfo_at(lng=lng, lat=lat)
        if zone is None:
            return None
        return dt.replace(tzinfo=zone)

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
            return self.zone_names.name_of(entry)
        if entry == ABSENT:
            return None
        return self.zone_names.name_of(self._zone_id_in_ambiguous_cell(entry, lng, lat))

    def _resolve_ambiguous_cells(
        self,
        entries: np.ndarray,
        positions: np.ndarray,
        lngs: np.ndarray,
        lats: np.ndarray,
        out: np.ndarray,
    ) -> None:
        """One lookup per *distinct* cell answers every point in it.

        Exact rather than an approximation: which zone is most common in a cell does not
        depend on the point, so this class's whole ambiguous answer is a property of the
        entry - which is why the resolution goes through :meth:`_most_common_zone_of`
        and never through the coordinate-taking :meth:`_zone_id_in_ambiguous_cell`.
        Nothing here has to invent a point for a signature that would not use it.

        ``np.unique`` rather than a dict: the answer being a pure function of the entry
        makes the whole batch one gather over the distinct entries, so the per-point
        work is a scatter numpy does rather than a lookup Python does.
        """
        distinct, inverse = np.unique(entries[positions], return_inverse=True)
        answers = np.fromiter(
            (self._most_common_zone_of(entry) for entry in distinct.tolist()),
            dtype=out.dtype,
            count=distinct.shape[0],
        )
        out[positions] = answers[inverse]

    def _most_common_zone_of(self, entry: int) -> int:
        """The zone covering most of a cell several zones cover - no geometry tested.

        A property of the cell alone, which is the whole of what makes this class
        lightweight, and what lets a batch answer every point in a cell from one lookup.
        """
        # several zones - the last candidate belongs to the most common one
        poly_of_biggest_zone = self.shortcuts.candidates_of(entry)[-1]
        # a numpy integer scalar from array indexing, which mypy reads as ndarray. Safe:
        # element access yields a scalar compatible with IntegerLike
        return self._zone_id_of(poly_of_biggest_zone)  # type: ignore[arg-type]

    def _zone_id_in_ambiguous_cell(self, entry: int, lng: float, lat: float) -> int:
        """The most common zone of the cell - the point is not consulted.

        The coordinates the contract passes are unused here, which is why the batch path
        calls :meth:`_most_common_zone_of` directly instead of handing this a point it
        would have to invent.
        """
        return self._most_common_zone_of(entry)


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
        super().__init__(bin_file_location)
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

    def _hole_ids_of(self, boundary_id: IntegerLike) -> range:
        """
        The hole IDs of a boundary polygon, as an empty ``range`` when it has none.

        A ``dict.get`` and a ``range``, not a lookup that raises and a generator: 1,225
        of the 1,322 packaged boundary polygons own no hole at all, so the majority path
        used to build a generator object, enter it, raise a ``KeyError``, catch it and
        return - to establish that there was nothing to check. That is ~190 ns of every
        hole probe, on a step ``inside_of_polygon`` performs for every candidate polygon
        surviving the bounding-box test.

        A ``range`` rather than a generator because both callers only iterate it, and
        because the empty case is then the same object shape as the non-empty one.

        :param boundary_id: id of the boundary polygon
        :return: the hole ids, in storage order
        """
        entry = self.hole_registry.get(int(boundary_id))
        if entry is None:
            return range(0)
        amount_of_holes, first_hole_id = entry
        return range(first_hole_id, first_hole_id + amount_of_holes)

    def _holes_of_poly(self, boundary_id: IntegerLike) -> Iterable[np.ndarray]:
        """
        Get the hole coordinates of a boundary polygon from the FlatBuffers collection.

        :param boundary_id: id of the boundary polygon
        :yield: Generator of hole coordinates
        """
        for hole_id in self._hole_ids_of(boundary_id):
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
        #
        # The emptiness test is not redundant with the loop inside ``in_any_polygon``:
        # 1,225 of the 1,322 packaged boundary polygons own no hole, so on the majority
        # path this is one truth test against a whole bound-method call that iterates
        # nothing and answers False.
        hole_ids = self._hole_ids_of(boundary_id)
        if hole_ids and self.holes.in_any_polygon(hole_ids, x, y):
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
            return self.zone_names.name_of(entry)
        if entry == ABSENT:
            # NOTE: hypothetical case, with ocean data every cell holds at least one boundary polygon
            return None

        # several zones - the candidates have to be tested. One call, shared with the
        # batch path, so the loop below exists once.
        return self.zone_names.name_of(self._zone_id_in_ambiguous_cell(entry, lng, lat))

    def _prepare_ambiguous_cell(self, entry: int) -> tuple[np.ndarray, np.ndarray, int]:
        """Everything a cell's candidate list costs before any point is tested.

        A property of the *cell*, not of the query point, which is what lets a batch pay
        it once per distinct cell. Measured at 898 ns against 10,228 ns for resolving a
        whole ambiguous point on the C-extension backend in mapped mode - so this is the
        8.8 % ceiling on what sharing it can win, and the geometry below is the rest.

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

        return possible_boundaries, zone_ids, last_zone_change_idx

    def _zone_id_among(
        self,
        possible_boundaries: np.ndarray,
        zone_ids: np.ndarray,
        last_zone_change_idx: int,
        lng: float,
        lat: float,
    ) -> int:
        """Work a prepared cell's candidate polygons until one contains the point.

        The last remaining zone is returned without a test - see :meth:`timezone_at`,
        whose note explains when that is and is not correct.
        """
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

    def _resolve_ambiguous_cells(
        self,
        entries: np.ndarray,
        positions: np.ndarray,
        lngs: np.ndarray,
        lats: np.ndarray,
        out: np.ndarray,
    ) -> None:
        """Prepare each distinct cell once, then test every point that landed in it.

        The three arrays are read once for the whole batch rather than one element at a
        time inside the loop: ``int(entries[i])`` and the two ``float(…[i])`` are numpy
        scalar extractions, measured at 242 ns per point against 103 ns for the same
        values taken through ``tolist()`` up front. That is the loop's own overhead, so
        it is paid on every ambiguous point whether or not the cell was already prepared.
        """
        prepared: dict[int, tuple[np.ndarray, np.ndarray, int]] = {}
        for i, entry, lng, lat in zip(
            positions.tolist(),
            entries[positions].tolist(),
            lngs[positions].tolist(),
            lats[positions].tolist(),
        ):
            cell = prepared.get(entry)
            if cell is None:
                cell = self._prepare_ambiguous_cell(entry)
                prepared[entry] = cell
            possible_boundaries, zone_ids, last_zone_change_idx = cell
            out[i] = self._zone_id_among(
                possible_boundaries,
                zone_ids,
                last_zone_change_idx,
                lng,
                lat,
            )

    def _zone_id_in_ambiguous_cell(self, entry: int, lng: float, lat: float) -> int:
        """Prepare this one cell and work it - the single-point path.

        The three preparation expressions are written out here rather than delegated to
        :meth:`_prepare_ambiguous_cell`, which is the only duplication in this class and
        is deliberate: this runs on every ambiguous ``timezone_at``, and the extra call
        measured **+0.8 %** of such a query on the C-extension backend - against a batch
        gain that does not need it. Nothing can drift silently, because
        ``test_batch_and_scalar_agree_over_every_committed_point`` compares the two paths
        over every point in every committed fixture; a change to one and not the other
        fails there.
        """
        possible_boundaries = self.shortcuts.candidates_of(entry)
        return self._zone_id_among(
            possible_boundaries,
            self._zone_ids_of(possible_boundaries),
            self.shortcuts.stop_index_of(entry),
            lng,
            lat,
        )

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

        # ATTENTION: the polygons are stored converted to 32-bit ints,
        # convert the query coordinates in the same fashion in order to make the data formats match
        # x = longitude  y = latitude  both converted to 8byte int
        x = utils.coord2int(lng)
        y = utils.coord2int(lat)

        # check if the query point is found to be truly included in one of the possible boundary polygons
        for boundary_id in self._iter_boundaries_in_shortcut(lng=lng, lat=lat):
            if self.inside_of_polygon(boundary_id, x, y):
                zone_id = self._zone_id_of(boundary_id)
                return self.zone_names.name_of(zone_id)

        # none of the boundary polygon candidates truly matched
        return None
