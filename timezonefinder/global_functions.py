"""
Global singleton functions for TimezoneFinder.

This module provides module-level timezone lookup functions that use a lazily-initialized
singleton instance of TimezoneFinder. These functions are simpler to use than creating your own
TimezoneFinder instance, but come with a thread-safety limitation.

Thread Safety Warning:
    These global functions use a shared singleton instance and are NOT thread-safe.
    For multi-threaded environments, create separate TimezoneFinder instances for each thread.

Example:
    >>> from timezonefinder import timezone_at
    >>> tz = timezone_at(lng=13.4, lat=52.5)
    >>> print(tz)
    'Europe/Berlin'
"""

from timezonefinder.timezonefinder import TimezoneFinder
from timezonefinder.configs import CoordPairs, CoordLists

__all__ = [
    "timezone_at",
    "timezone_at_land",
    "unique_timezone_at",
    "certain_timezone_at",
    "get_geometry",
]

# Use a global variable to store the singleton instance
TF_INSTANCE: TimezoneFinder


def _get_tf_instance() -> TimezoneFinder:
    """Get or create the global TimezoneFinder instance.

    Implements lazy initialization to delay memory allocation until the first actual use.
    This is important because the package might be used with a user-defined instance,
    and we want to avoid wasting memory with duplicate initialization.

    :return: The shared TimezoneFinder singleton instance
    """
    global TF_INSTANCE
    try:
        return TF_INSTANCE
    except NameError:
        # If TF_INSTANCE is not defined, create it
        TF_INSTANCE = TimezoneFinder()
    return TF_INSTANCE


def timezone_at(*, lng: float, lat: float) -> str | None:
    """
    Look up the timezone for a geographic coordinate using the global singleton.

    :param lng: Longitude of the point in degrees (-180.0 to 180.0)
    :param lat: Latitude of the point in degrees (-90.0 to 90.0)
    :return: The timezone name of a matching polygon, or None if no match found

    Thread Safety:
        This function is not thread-safe. See module docstring for alternatives.

    Example:
        >>> timezone_at(lng=13.4, lat=52.5)
        'Europe/Berlin'
    """
    return _get_tf_instance().timezone_at(lng=lng, lat=lat)


def timezone_at_land(*, lng: float, lat: float) -> str | None:
    """
    Look up the land timezone for a geographic coordinate using the global singleton.

    Returns None for ocean coordinates (which have fixed-offset timezones like Etc/GMT±XX).

    :param lng: Longitude of the point in degrees (-180.0 to 180.0)
    :param lat: Latitude of the point in degrees (-90.0 to 90.0)
    :return: The timezone name for land locations, or None for ocean areas

    Thread Safety:
        This function is not thread-safe. See module docstring for alternatives.
    """
    return _get_tf_instance().timezone_at_land(lng=lng, lat=lat)


def unique_timezone_at(*, lng: float, lat: float) -> str | None:
    """
    Get the timezone for a coordinate if the shortcut zone is unambiguous.

    Returns None if the H3 shortcut cell contains multiple timezones or no zones.

    :param lng: Longitude of the point in degrees (-180.0 to 180.0)
    :param lat: Latitude of the point in degrees (-90.0 to 90.0)
    :return: The timezone name if the shortcut contains exactly one zone, None otherwise

    Thread Safety:
        This function is not thread-safe. See module docstring for alternatives.

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
        This function is not thread-safe. See module docstring for alternatives.

    Note:
        For the standard global dataset, this is equivalent to timezone_at() since
        all earth locations are covered by polygons (including ocean zones).
        This is primarily useful with custom timezone data.
    """
    return _get_tf_instance().certain_timezone_at(lng=lng, lat=lat)


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

    :param tz_name: one of the names in ``timezone_names.json`` or ``self.timezone_names``
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
