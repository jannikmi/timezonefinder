"""
Localizing a dataset's UTC timestamps: one batch lookup, then the stdlib ``zoneinfo``.

Observations from sensors, trackers or field stations are often recorded as a UTC
timestamp plus the coordinate they were taken at. Questions about daily cycles need the
local time instead, and that depends on the zone *and the date*: the same UTC instant
lands on a different local hour in summer and in winter wherever daylight saving time
applies, so convert through the zone rather than a fixed offset.

``on_invalid="skip"`` answers ``None`` for a coordinate that cannot be looked up instead
of failing the whole batch, so a bad row stays visible rather than taking the rest down.

Report ``TimezoneFinder.data_version`` with the results and pin the
``timezonefinder-data`` version: a later boundary release can move a zone, and the
pinned version is what lets someone else repeat the lookup exactly.

On Windows, ``pip install tzdata`` first: the platform ships no timezone database.
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from timezonefinder import TimezoneFinder

# (station, lng, lat, UTC timestamp) - the last row has an out-of-range longitude
OBSERVATIONS = [
    ("Berlin", 13.358, 52.5061, datetime(2026, 1, 15, 12, tzinfo=timezone.utc)),
    ("Berlin", 13.358, 52.5061, datetime(2026, 7, 15, 12, tzinfo=timezone.utc)),
    ("New York", -74.0060, 40.7128, datetime(2026, 7, 15, 12, tzinfo=timezone.utc)),
    ("Sydney", 151.2093, -33.8688, datetime(2026, 7, 15, 12, tzinfo=timezone.utc)),
    ("broken GPS fix", 999.0, 0.0, datetime(2026, 7, 15, 12, tzinfo=timezone.utc)),
]


def localize(
    utc_times: list[datetime], zone_names: list[str | None]
) -> list[datetime | None]:
    """Each UTC timestamp as local time in its zone, or None where no zone was found."""
    return [
        None if name is None else t.astimezone(ZoneInfo(name))
        for t, name in zip(utc_times, zone_names, strict=True)
    ]


def main():
    stations, lngs, lats, utc_times = map(list, zip(*OBSERVATIONS, strict=True))

    # Initialisation dominates a single lookup, so one instance serves the whole dataset.
    with TimezoneFinder() as tf:
        zone_names = tf.timezone_names_at(lngs=lngs, lats=lats, on_invalid="skip")
        data_version = tf.data_version

    local_times = localize(utc_times, zone_names)

    print(f"Boundary data release: {data_version} (report it with the results)\n")
    for station, utc, name, local in zip(
        stations, utc_times, zone_names, local_times, strict=True
    ):
        if local is None:
            print(f"{station:15} {utc:%Y-%m-%d %H:%M} UTC -> no zone, row kept as None")
            continue
        print(
            f"{station:15} {utc:%Y-%m-%d %H:%M} UTC -> "
            f"{local:%Y-%m-%d %H:%M} {local.tzname():5} ({name})"
        )

    print("\n✓ Localized every valid row with one lookup call")


if __name__ == "__main__":
    main()
