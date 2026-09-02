"""
Turning a coordinate into an aware datetime, with ``localize()`` and ``zoneinfo_at()``.

``localize`` reads a naive datetime as local wall-clock time at the coordinate and
returns it aware. ``zoneinfo_at`` returns the zone itself, for the cases that want a
``ZoneInfo`` rather than a datetime. Both answer ``None`` wherever ``timezone_at()``
does.

On Windows, ``pip install tzdata`` first: the platform ships no timezone database, and
this package returns IANA names rather than carrying one.

The last section is for callers still on ``pytz`` (the optional ``timezonefinder[pytz]``
extra), and shows the trap that motivates the helpers above: with ``pytz``,
``replace(tzinfo=...)`` silently attaches a historical offset rather than the current
one, so a naive datetime has to go through ``tz.localize()`` instead. With ``zoneinfo``
- the standard library, and what new code should use - ``replace`` is correct, which is
what ``localize()`` above does.
"""

from datetime import datetime, timezone as utc_timezone

from timezonefinder import TimezoneFinder, localize, zoneinfo_at

BERLIN = {"lng": 13.41, "lat": 52.52}
NAIVE = datetime(2026, 1, 1, 12, 0)


def with_zoneinfo():
    tf = TimezoneFinder()

    aware = tf.localize(NAIVE, **BERLIN)
    print("localize() - the naive time read as local time there:")
    print(f"  {NAIVE} -> {aware}")
    print(f"  the same instant in UTC: {aware.astimezone(utc_timezone.utc)}")

    zone = tf.zoneinfo_at(**BERLIN)
    print("\nzoneinfo_at() - the zone itself, for building your own datetimes:")
    print(f"  {zone!r}")
    print(f"  now there: {datetime.now(tz=zone)}")

    print("\nBoth are available as global functions on a shared instance:")
    print(f"  {localize(NAIVE, **BERLIN)}")
    print(f"  {zoneinfo_at(**BERLIN)!r}")

    print("\nAn already-aware datetime is refused rather than silently re-labelled:")
    try:
        tf.localize(aware, **BERLIN)
    except ValueError as e:
        print(f"  ValueError: {e}")


def with_pytz():
    """The same thing for callers on the optional ``pytz`` extra."""
    try:
        from pytz import timezone
    except ImportError:
        print("\npytz is not installed - skipping the pytz section")
        return

    tf = TimezoneFinder()
    tz_name = tf.timezone_at(**BERLIN)
    tz = timezone(tz_name)

    print("\npytz needs tz.localize(); replace(tzinfo=...) is the classic bug:")
    print(f"  tz.localize(naive):        {tz.localize(NAIVE)}")
    print(f"  naive.replace(tzinfo=tz):  {NAIVE.replace(tzinfo=tz)}  <- wrong offset")
    print("  zoneinfo has no such split, which is why localize() above just replaces")


def main():
    with_zoneinfo()
    with_pytz()


if __name__ == "__main__":
    main()
