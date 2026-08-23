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
from typing import Self

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
    SHORTCUT_H3_RES,
    DATA_VERSION_FILENAME,
    CoordLists,
    CoordPairs,
    IntegerLike,
)

from timezonefinder.shortcut_index import (
    ABSENT,
    SLOT_DIGITS_SHIFT,
    SLOT_MASK,
    get_shortcut_file_path,
    read_shortcuts_binary,
    slot_of,
)
from timezonefinder.zone_names import read_zone_names


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
        shortcut_table: H3 slot -> zone id, absent marker, or candidate list index
        data_location: Path to the timezone data directory
    """

    # prevent dynamic attribute assignment (-> safe memory). Every name here must be
    # assigned by this class or a subclass; an unassigned one is just a hole in that
    # guarantee, so `test_declared_slots_are_assigned` pins the list against instances.
    __slots__ = [
        "data_location",
        "shortcut_table",
        "shortcut_starts",
        "shortcut_ends",
        "shortcut_last_change",
        "shortcut_polygons",
        "timezone_names",
        "zone_ids",
        "holes_dir",
        "boundaries_dir",
        "boundaries",
        "holes",
    ]

    zone_ids: np.ndarray
    #: the shortcut index, unpacked into one attribute per array. Held flat rather than
    #: behind the ``ShortcutIndex`` tuple it is read as: every query indexes the table,
    #: and an attribute hop on that path is not worth the tidier grouping.
    shortcut_table: np.ndarray
    shortcut_starts: np.ndarray
    shortcut_ends: np.ndarray
    shortcut_last_change: np.ndarray
    shortcut_polygons: np.ndarray

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

        shortcuts = read_shortcuts_binary(get_shortcut_file_path(self.data_location))
        self.shortcut_table = shortcuts.table
        self.shortcut_starts = shortcuts.starts
        self.shortcut_ends = shortcuts.ends
        self.shortcut_last_change = shortcuts.last_change
        self.shortcut_polygons = shortcuts.payload

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

    def zone_id_of(self, boundary_id: IntegerLike) -> int:
        """
        Get the timezone ID for a specific boundary polygon.

        :param boundary_id: The numeric identifier of the boundary polygon
        :return: The timezone ID (index into timezone_names)
        :raises ValueError: If ``boundary_id`` does not select exactly one zone id - out of
            range, not usable as an index, or selecting several. The underlying ``IndexError``
            and ``TypeError`` are both re-raised as ``ValueError``, so that is the only type
            callers have to handle.
        """
        try:
            return int(self.zone_ids[boundary_id])
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
        """
        return self.zone_ids[boundary_ids]

    def zone_name_from_id(self, zone_id: int) -> str:
        """
        Get the timezone name corresponding to a zone ID.

        :param zone_id: The numeric ID of the timezone (0-based index)
        :return: The IANA timezone name (e.g., 'Europe/Berlin')
        :raises ValueError: If ``zone_id`` is out of range for the loaded dataset. The
            underlying ``IndexError`` is re-raised as ``ValueError``.
        :raises TypeError: If ``zone_id`` is not an integer.

        Example:
            >>> tf = TimezoneFinder()
            >>> tf.zone_name_from_id(0)
            'Africa/Abidjan'
        """
        try:
            return self.timezone_names[zone_id]
        except IndexError as e:
            raise ValueError(
                f"Zone ID {zone_id} is out of range. "
                f"Valid range: 0-{len(self.timezone_names) - 1}. "
                f"Loaded dataset has {self.nr_of_zones} timezones."
            ) from e

    def zone_name_from_boundary_id(self, boundary_id: IntegerLike) -> str:
        """
        Get the zone name from a boundary polygon ID.

        :param boundary_id: The ID of the boundary polygon.
        :return: The name of the zone.
        """
        zone_id = self.zone_id_of(boundary_id)
        return self.zone_name_from_id(zone_id)

    def _candidates_of(self, entry: int) -> np.ndarray:
        """The candidate boundary polygon ids a shortcut table value below ``ABSENT`` names.

        ``timezone_at`` inlines this: it needs the entry index for ``shortcut_last_change``
        anyway, and it is the one caller on the critical path.
        """
        i = -(entry + 2)
        return self.shortcut_polygons[self.shortcut_starts[i] : self.shortcut_ends[i]]

    def _iter_boundaries_in_shortcut(self, *, lng: float, lat: float) -> Iterable[int]:
        """
        Iterate over boundary polygon IDs in the shortcut corresponding to the given coordinates.

        :param lng: The longitude of the point in degrees (-180.0 to 180.0).
        :param lat: The latitude of the point in degrees (90.0 to -90.0).
        :yield: Boundary polygon IDs.
        """
        hex_id = h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES)

        entry = int(self.shortcut_table[slot_of(hex_id)])
        if entry == ABSENT:
            return
        if entry >= 0:
            # a cell a single zone covers: every boundary polygon of that zone is a
            # candidate. Most are quickly ruled out by the bounding box check.
            yield from self._iter_boundary_ids_of_zone(entry)
        else:
            yield from self._candidates_of(entry)

    @abstractmethod
    def timezone_at(self, *, lng: float, lat: float) -> str | None:
        """looks up in which timezone the given coordinate is included in

        :param lng: longitude of the point in degree (-180.0 to 180.0)
        :param lat: latitude in degree (90.0 to -90.0)
        :return: the timezone name of a matching polygon or None
        """
        ...

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
        zone_id = int(self.shortcut_table[slot_of(hex_id)])
        if zone_id < 0:
            return None
        return self.zone_name_from_id(zone_id)

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

        entry = int(self.shortcut_table[(hex_id >> SLOT_DIGITS_SHIFT) & SLOT_MASK])
        if entry >= 0:
            # unique zone case: the table holds the answer
            return self.zone_name_from_id(entry)
        if entry == ABSENT:
            return None
        # several zones - the last candidate belongs to the most common one
        poly_of_biggest_zone = self._candidates_of(entry)[-1]
        # a numpy integer scalar from array indexing, which mypy reads as ndarray. Safe:
        # element access yields a scalar compatible with IntegerLike
        most_common_id = self.zone_id_of(poly_of_biggest_zone)  # type: ignore[arg-type]
        return self.zone_name_from_id(most_common_id)


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

        # one table read answers most queries: a zone id is the answer itself
        entry = int(self.shortcut_table[(hex_id >> SLOT_DIGITS_SHIFT) & SLOT_MASK])
        if entry >= 0:
            return self.zone_name_from_id(entry)
        if entry == ABSENT:
            # NOTE: hypothetical case, with ocean data every cell holds at least one boundary polygon
            return None

        # several zones - the candidates have to be tested. NOTE: neither the empty nor
        # the single-candidate case can occur here; both are unambiguous and are stored
        # in the table itself.
        # named apart from the loop counter below on purpose: both index something, and a
        # stop index read for the wrong entry is a wrong timezone that nothing announces -
        # the stored values would still be correct, so no build-time check could see it
        entry_idx = -(entry + 2)
        possible_boundaries = self.shortcut_polygons[
            self.shortcut_starts[entry_idx] : self.shortcut_ends[entry_idx]
        ]

        # create a list of all the timezone ids of all possible boundary polygons
        zone_ids = self.zone_ids_of(possible_boundaries)

        # where the loop may stop, precomputed at build time - a property of the candidate
        # list, so it is stored once per distinct list rather than recomputed per query.
        # NOTE: the case last_zone_change_idx == 0 is covered by the unique zone shortcut
        last_zone_change_idx = self.shortcut_last_change[entry_idx]

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
                zone_id = zone_ids[i]
                return self.zone_name_from_id(int(zone_id))

        # since it is the last possible option,
        # the polygons of the last possible zone don't actually have to be checked
        # -> instantly return the last zone
        zone_id = zone_ids[-1]
        return self.zone_name_from_id(int(zone_id))

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

        entry = int(self.shortcut_table[slot_of(hex_id)])
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
            boundary_ids = self._candidates_of(entry)

        for boundary_id in boundary_ids:
            if self.inside_of_polygon(boundary_id, x, y):
                zone_id = self.zone_id_of(boundary_id)
                return self.zone_name_from_id(zone_id)

        # none of the boundary polygon candidates truly matched
        return None
