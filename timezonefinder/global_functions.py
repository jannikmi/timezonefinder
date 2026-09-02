"""
Global singleton functions for TimezoneFinder.

This module provides module-level timezone lookup functions that use a lazily-initialized
singleton instance of TimezoneFinder. These functions are simpler to use than creating your own
TimezoneFinder instance.

Thread Safety:
    The global functions provide a thread-safe singleton instance for concurrent reads.
    Multiple threads can safely call these functions simultaneously without explicit
    synchronization. The singleton is initialized exactly once using double-checked locking,
    even under high concurrency.

    However, for performance-critical parallel workloads, consider creating separate
    TimezoneFinder instances for each thread to avoid singleton overhead:

        import threading
        from timezonefinder import TimezoneFinder

        def lookup_in_thread(lng, lat):
            # Each thread creates its own instance (faster for parallel work)
            tf = TimezoneFinder(in_memory=True)
            return tf.timezone_at(lng=lng, lat=lat)

    For custom configurations (different data locations, etc.), create separate TimezoneFinder
    instances as needed.

Example:
    >>> from timezonefinder import timezone_at
    >>> tz = timezone_at(lng=13.4, lat=52.5)
    >>> print(tz)
    'Europe/Berlin'
"""

import threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np

from timezonefinder.timezonefinder import TimezoneFinder
from timezonefinder.configs import CoordArrayLike, CoordPairs, CoordLists, OnInvalid

__all__ = [
    "timezone_at",
    "timezone_ids_at",
    "timezone_names_at",
    "timezone_at_land",
    "timezone_ids_at_land",
    "timezone_names_at_land",
    "unique_timezone_at",
    "certain_timezone_at",
    "get_geometry",
    "zoneinfo_at",
    "utc_offset_at",
    "localize",
]

# Global singleton instance and lock for thread-safe initialization
TF_INSTANCE: TimezoneFinder | None = None
_TF_INSTANCE_LOCK = threading.Lock()


def _get_tf_instance() -> TimezoneFinder:
    """Get or create the global TimezoneFinder instance (thread-safe).

    Implements lazy initialization with thread-safe double-checked locking.
    This ensures the singleton is created exactly once, even with concurrent access.

    The first thread to call this function will acquire the lock and initialize
    the instance. Subsequent calls (even from other threads) will return the
    already-initialized instance without needing to acquire the lock.

    :return: The shared TimezoneFinder singleton instance
    """
    global TF_INSTANCE

    # First check (no lock): avoid lock contention on every call
    if TF_INSTANCE is not None:
        return TF_INSTANCE

    # Second check (with lock): ensure only one thread initializes
    with _TF_INSTANCE_LOCK:
        # Check again inside the lock: another thread may have initialized
        # the instance while we were waiting for the lock
        if TF_INSTANCE is None:
            TF_INSTANCE = TimezoneFinder()

    return TF_INSTANCE


def timezone_at(*, lng: float, lat: float) -> str | None:
    """
    Look up the timezone for a geographic coordinate using the global singleton.

    :param lng: Longitude of the point in degrees (-180.0 to 180.0)
    :param lat: Latitude of the point in degrees (-90.0 to 90.0)
    :return: The timezone name of a matching polygon, or None if no match found

    Thread Safety:
        This function is thread-safe for concurrent calls. The underlying global
        TimezoneFinder instance uses a thread-safe singleton pattern. However, for
        performance-critical parallel workloads, create separate TimezoneFinder
        instances per thread to avoid singleton overhead.

    Example:
        >>> timezone_at(lng=13.4, lat=52.5)
        'Europe/Berlin'
    """
    return _get_tf_instance().timezone_at(lng=lng, lat=lat)


def timezone_ids_at(
    *,
    lngs: CoordArrayLike,
    lats: CoordArrayLike,
    on_invalid: OnInvalid = "raise",
) -> np.ndarray:
    """
    Look up many coordinates at once using the global singleton, answering with ids.

    Equivalent to :meth:`TimezoneFinder.timezone_ids_at`, which documents the arguments,
    the ``on_invalid`` policies and every error raised.

    :return: one ``int16`` timezone id per input coordinate, or ``NO_ZONE_ID`` (``-1``)
        where the scalar lookup would answer ``None``

    Example:
        >>> ids = timezone_ids_at(lngs=[13.358, 2.3522], lats=[52.5061, 48.8566])
        >>> ids.dtype
        dtype('int16')
    """
    return _get_tf_instance().timezone_ids_at(
        lngs=lngs, lats=lats, on_invalid=on_invalid
    )


def timezone_names_at(
    *,
    lngs: CoordArrayLike,
    lats: CoordArrayLike,
    on_invalid: OnInvalid = "raise",
) -> list[str | None]:
    """
    Look up many coordinates at once using the global singleton, answering with names.

    Equivalent to :meth:`TimezoneFinder.timezone_names_at`. Prefer
    :func:`timezone_ids_at` whenever the names are not the end product.

    :return: one timezone name per input coordinate, or ``None`` where no zone covers the
        point or the coordinate was skipped

    Example:
        >>> timezone_names_at(lngs=[13.358, 2.3522], lats=[52.5061, 48.8566])
        ['Europe/Berlin', 'Europe/Paris']
    """
    return _get_tf_instance().timezone_names_at(
        lngs=lngs, lats=lats, on_invalid=on_invalid
    )


def timezone_at_land(*, lng: float, lat: float) -> str | None:
    """
    Look up the land timezone for a geographic coordinate using the global singleton.

    Returns None for ocean coordinates (which have fixed-offset timezones like Etc/GMT±XX).

    :param lng: Longitude of the point in degrees (-180.0 to 180.0)
    :param lat: Latitude of the point in degrees (-90.0 to 90.0)
    :return: The timezone name for land locations, or None for ocean areas

    Thread Safety:
        This function is thread-safe for concurrent calls. The underlying global
        TimezoneFinder instance uses a thread-safe singleton pattern. However, for
        performance-critical parallel workloads, create separate TimezoneFinder
        instances per thread to avoid singleton overhead.
    """
    return _get_tf_instance().timezone_at_land(lng=lng, lat=lat)


def timezone_ids_at_land(
    *,
    lngs: CoordArrayLike,
    lats: CoordArrayLike,
    on_invalid: OnInvalid = "raise",
) -> np.ndarray:
    """
    Look up many coordinates at once using the global singleton, answering with land ids.

    Equivalent to :meth:`TimezoneFinder.timezone_ids_at_land`, which documents the
    arguments, the ``on_invalid`` policies and every error raised.

    :return: one ``int16`` timezone id per input coordinate, or ``NO_ZONE_ID`` (``-1``)
        where :func:`timezone_at_land` would answer ``None``

    Example:
        >>> ids = timezone_ids_at_land(lngs=[13.358, -30.0], lats=[52.5061, 0.0])
        >>> ids[1]  # mid-Atlantic: an ocean zone, so no land answer
        np.int16(-1)
    """
    return _get_tf_instance().timezone_ids_at_land(
        lngs=lngs, lats=lats, on_invalid=on_invalid
    )


def timezone_names_at_land(
    *,
    lngs: CoordArrayLike,
    lats: CoordArrayLike,
    on_invalid: OnInvalid = "raise",
) -> list[str | None]:
    """
    Look up many coordinates at once using the global singleton, answering with land names.

    Equivalent to :meth:`TimezoneFinder.timezone_names_at_land`. Prefer
    :func:`timezone_ids_at_land` whenever the names are not the end product.

    :return: one timezone name per input coordinate, or ``None`` where an ocean zone
        matched, no zone covers the point, or the coordinate was skipped

    Example:
        >>> timezone_names_at_land(lngs=[13.358, -30.0], lats=[52.5061, 0.0])
        ['Europe/Berlin', None]
    """
    return _get_tf_instance().timezone_names_at_land(
        lngs=lngs, lats=lats, on_invalid=on_invalid
    )


def unique_timezone_at(*, lng: float, lat: float) -> str | None:
    """
    Get the timezone for a coordinate if the shortcut zone is unambiguous.

    Returns None if the H3 shortcut cell contains multiple timezones or no zones.

    :param lng: Longitude of the point in degrees (-180.0 to 180.0)
    :param lat: Latitude of the point in degrees (-90.0 to 90.0)
    :return: The timezone name if the shortcut contains exactly one zone, None otherwise

    Thread Safety:
        This function is thread-safe for concurrent calls. The underlying global
        TimezoneFinder instance uses a thread-safe singleton pattern. However, for
        performance-critical parallel workloads, create separate TimezoneFinder
        instances per thread to avoid singleton overhead.

    Note:
        This is faster than timezone_at() but may return None even for valid coordinates
        if the H3 cell spans multiple timezones.
    """
    return _get_tf_instance().unique_timezone_at(lng=lng, lat=lat)


def certain_timezone_at(*, lng: float, lat: float) -> str | None:
    """
    Get the timezone for a coordinate with certainty (tests all polygons).

    This function checks if a point is contained in ANY timezone polygon. It is slower
    than timezone_at() but useful when you have custom timezone data with areas of no coverage.

    :param lng: Longitude of the point in degrees (-180.0 to 180.0)
    :param lat: Latitude of the point in degrees (-90.0 to 90.0)
    :return: The timezone name if definitely matched, None if not in any polygon

    Thread Safety:
        This function is thread-safe for concurrent calls. The underlying global
        TimezoneFinder instance uses a thread-safe singleton pattern. However, for
        performance-critical parallel workloads, create separate TimezoneFinder
        instances per thread to avoid singleton overhead.

    Note:
        For the standard global dataset, this is equivalent to timezone_at() since
        all earth locations are covered by polygons (including ocean zones).
        This is primarily useful with custom timezone data.
    """
    return _get_tf_instance().certain_timezone_at(lng=lng, lat=lat)


def zoneinfo_at(*, lng: float, lat: float) -> ZoneInfo | None:
    """
    Look up the timezone for a coordinate as a ``zoneinfo.ZoneInfo``, using the global singleton.

    Equivalent to :meth:`TimezoneFinder.zoneinfo_at`, which documents the arguments and
    every error raised - including the ``tzdata`` a Windows machine needs installed
    before any IANA name resolves.

    :return: the zone covering the point, or None where :func:`timezone_at` answers None

    Example:
        >>> zoneinfo_at(lng=13.358, lat=52.5061)
        zoneinfo.ZoneInfo(key='Europe/Berlin')
    """
    return _get_tf_instance().zoneinfo_at(lng=lng, lat=lat)


def utc_offset_at(
    *, lng: float, lat: float, when: datetime | None = None
) -> timedelta | None:
    """
    Get the UTC offset in force at a coordinate, using the global singleton.

    Equivalent to :meth:`TimezoneFinder.utc_offset_at`, which documents the arguments,
    how a naive and an aware ``when`` differ, and every error raised - including the
    ``tzdata`` a Windows machine needs installed.

    :return: the offset as a ``timedelta``, or None where :func:`timezone_at` answers None

    Example:
        >>> from datetime import datetime
        >>> utc_offset_at(lng=13.358, lat=52.5061, when=datetime(2026, 1, 1))
        datetime.timedelta(seconds=3600)
    """
    return _get_tf_instance().utc_offset_at(lng=lng, lat=lat, when=when)


def localize(dt: datetime, *, lng: float, lat: float) -> datetime | None:
    """
    Attach the timezone covering a coordinate to a naive datetime, using the global singleton.

    Equivalent to :meth:`TimezoneFinder.localize`, which documents the arguments and
    every error raised - including the ``tzdata`` a Windows machine needs installed.

    :return: the same wall-clock time made aware, or None where :func:`timezone_at`
        answers None

    Example:
        >>> from datetime import datetime
        >>> localize(datetime(2026, 1, 1, 12), lng=13.358, lat=52.5061)
        datetime.datetime(2026, 1, 1, 12, 0, tzinfo=zoneinfo.ZoneInfo(key='Europe/Berlin'))
    """
    return _get_tf_instance().localize(dt, lng=lng, lat=lat)


def get_geometry(
    tz_name: str | None = "",
    tz_id: int | None = 0,
    use_id: bool = False,
    coords_as_pairs: bool = False,
) -> list[list[CoordPairs | CoordLists]]:
    """
    Retrieves the geometry of a timezone polygon.
    Uses the global TimezoneFinder instance.

    Note: This function is not thread-safe. For multi-threaded environments,
    create separate TimezoneFinder instances.

    :param tz_name: one of the names in ``timezone_names.txt`` or ``self.timezone_names``
    :param tz_id: the id of the timezone (=index in ``self.timezone_names``)
    :param use_id: if ``True`` uses ``tz_id`` instead of ``tz_name``
    :param coords_as_pairs: determines the structure of the polygon representation
    :return: a data structure representing the multipolygon of this timezone
        output format: ``[ [polygon1, hole1, hole2...], [polygon2, ...], ...]``
        and each polygon and hole is itself formatted like: ``([longitudes], [latitudes])``
        or ``[(lng1,lat1), (lng2,lat2),...]`` if ``coords_as_pairs=True``.
    """
    return _get_tf_instance().get_geometry(
        tz_name=tz_name, tz_id=tz_id, use_id=use_id, coords_as_pairs=coords_as_pairs
    )
