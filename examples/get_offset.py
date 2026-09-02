"""
A location's UTC offset, which ``utc_offset_at()`` answers directly.

The offset is a property of a zone *and a date* - it changes with daylight saving time -
so it is read off an aware datetime rather than off the zone. ``utc_offset_at`` does
that, taking the moment to read it at and defaulting to now.

Do not derive the offset from the returned zone *name*. The packaged data covers the
oceans, so every coordinate at sea resolves to an ``Etc/GMT±X`` zone, and that family
uses an **inverted** sign convention: ``Etc/GMT+2`` is UTC-2. Parsing the name produces
the wrong sign without failing anywhere, which is the whole reason this helper exists -
the last section below shows it.

On Windows, ``pip install tzdata`` first: the platform ships no timezone database, and
this package returns IANA names rather than carrying one.
"""

from datetime import datetime, timedelta

from timezonefinder import TimezoneFinder, utc_offset_at

BERGAMO = {"lng": 9.67, "lat": 45.69}
# mid-Atlantic, two hours west of Greenwich
OPEN_SEA = {"lng": -30.0, "lat": 0.0}


def offset_in_minutes(
    *, lng: float, lat: float, when: datetime | None = None
) -> float | None:
    """A location's UTC offset in minutes, or None where no zone covers the point."""
    offset = utc_offset_at(lng=lng, lat=lat, when=when)
    return None if offset is None else offset.total_seconds() / 60


def main():
    tf = TimezoneFinder()

    print("Right now:")
    print(f"  Bergamo: {tf.utc_offset_at(**BERGAMO)}")
    print(f"  {offset_in_minutes(**BERGAMO)} minutes, as a number")

    print("\nThe same place on two dates - the offset moves with daylight saving:")
    for label, when in (
        ("winter", datetime(2026, 1, 15)),
        ("summer", datetime(2026, 7, 15)),
    ):
        print(f"  {label}: {tf.utc_offset_at(**BERGAMO, when=when)}")

    print("\nAt sea, where reading the name would give the wrong sign:")
    name = tf.timezone_at(**OPEN_SEA)
    offset = tf.utc_offset_at(**OPEN_SEA, when=datetime(2026, 1, 15))
    hours = offset.total_seconds() / 3600
    print(f"  the zone is named {name!r}, and its actual offset is UTC{hours:+g}")
    assert offset == timedelta(hours=-2), "Etc/GMT+2 denotes UTC-2, not UTC+2"

    print("\nThe global function is the same lookup on a shared instance:")
    print(f"  {utc_offset_at(**BERGAMO, when=datetime(2026, 1, 15))}")


if __name__ == "__main__":
    main()
