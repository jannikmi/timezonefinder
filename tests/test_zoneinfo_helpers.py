"""The ``zoneinfo`` / UTC-offset helpers, and the sign convention they exist to own.

Every assertion about an ocean coordinate here is the point of the feature rather than a
corner case: the packaged data covers the seas, so a coordinate at sea returns
``Etc/GMT±X``, whose sign is *inverted* relative to the offset it denotes. A caller
deriving the offset from the name gets it backwards without anything failing; these
helpers go through ``zoneinfo``, which reads the convention correctly.
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from timezonefinder import (
    TimezoneFinder,
    TimezoneFinderL,
    localize,
    utc_offset_at,
    zoneinfo_at,
)

BERLIN: dict[str, float] = {"lng": 13.358, "lat": 52.5061}
#: mid-Atlantic, two hours west of Greenwich - ``Etc/GMT+2``, i.e. UTC**-**2
OCEAN = {"lng": -30.0, "lat": 0.0}

WINTER = datetime(2026, 1, 15, 12)
SUMMER = datetime(2026, 7, 15, 12)


@pytest.mark.unit
def test_zoneinfo_at_returns_the_zone_timezone_at_names(tf: TimezoneFinder):
    assert str(tf.zoneinfo_at(**BERLIN)) == tf.timezone_at(**BERLIN)


@pytest.mark.unit
def test_all_three_answer_none_where_timezone_at_does(
    tf: TimezoneFinder, monkeypatch: pytest.MonkeyPatch
):
    """The packaged data covers the whole globe, so the ``None`` branch is unreachable.

    It is still part of every one of these signatures, and reachable with custom data
    that has areas of no coverage - so the lookup is stubbed rather than left untested.
    """
    monkeypatch.setattr(type(tf), "timezone_at", lambda self, *, lng, lat: None)
    assert tf.zoneinfo_at(**BERLIN) is None
    assert tf.utc_offset_at(**BERLIN, when=WINTER) is None
    assert tf.localize(WINTER, **BERLIN) is None


@pytest.mark.unit
@pytest.mark.parametrize(
    "when, expected",
    [(WINTER, timedelta(hours=1)), (SUMMER, timedelta(hours=2))],
    ids=["winter", "summer"],
)
def test_utc_offset_at_follows_daylight_saving(
    tf: TimezoneFinder, when: datetime, expected: timedelta
):
    """The offset is a property of the zone *and the date*, which is why ``when`` exists."""
    assert tf.utc_offset_at(**BERLIN, when=when) == expected


@pytest.mark.unit
def test_utc_offset_at_defaults_to_now(tf: TimezoneFinder):
    """Omitting ``when`` reads the offset in force at this moment."""
    offset = tf.utc_offset_at(lng=BERLIN["lng"], lat=BERLIN["lat"])
    assert offset in (timedelta(hours=1), timedelta(hours=2))


@pytest.mark.unit
def test_the_ocean_sign_convention_is_inverted_and_handled(tf: TimezoneFinder):
    """``Etc/GMT+2`` denotes UTC-2. Reading the sign off the name gives the opposite."""
    assert tf.timezone_at(**OCEAN) == "Etc/GMT+2"
    assert tf.utc_offset_at(**OCEAN, when=WINTER) == timedelta(hours=-2)


@pytest.mark.unit
def test_an_aware_when_is_read_as_the_instant_it_denotes(tf: TimezoneFinder):
    """The same moment, expressed in UTC, gets the same answer as the naive local one."""
    naive = tf.utc_offset_at(**BERLIN, when=WINTER)
    aware = tf.utc_offset_at(
        **BERLIN, when=(WINTER - timedelta(hours=1)).replace(tzinfo=timezone.utc)
    )
    assert naive == aware


@pytest.mark.unit
def test_localize_keeps_the_wall_clock_and_adds_the_zone(tf: TimezoneFinder):
    localized = tf.localize(WINTER, **BERLIN)
    assert localized is not None
    assert localized.replace(tzinfo=None) == WINTER
    assert localized.utcoffset() == timedelta(hours=1)


@pytest.mark.unit
def test_localize_refuses_an_already_aware_datetime(tf: TimezoneFinder):
    """Re-labelling an aware datetime would move the instant it denotes, silently."""
    with pytest.raises(ValueError, match="already carries a timezone"):
        tf.localize(WINTER.replace(tzinfo=timezone.utc), **BERLIN)


@pytest.mark.unit
def test_the_helpers_are_on_the_lightweight_finder_too():
    """They live on the shared base, so ``TimezoneFinderL`` gets them unchanged."""
    tfl = TimezoneFinderL()
    assert str(tfl.zoneinfo_at(**BERLIN)) == tfl.timezone_at(**BERLIN)
    assert tfl.utc_offset_at(**BERLIN, when=WINTER) == timedelta(hours=1)
    assert tfl.localize(WINTER, **BERLIN) == WINTER.replace(
        tzinfo=ZoneInfo("Europe/Berlin")
    )


@pytest.mark.unit
def test_the_global_functions_answer_the_same(tf: TimezoneFinder):
    """The module-level mirrors delegate to the singleton and must not drift."""
    assert str(zoneinfo_at(**BERLIN)) == str(tf.zoneinfo_at(**BERLIN))
    assert utc_offset_at(**BERLIN, when=WINTER) == tf.utc_offset_at(
        **BERLIN, when=WINTER
    )
    assert localize(WINTER, **BERLIN) == tf.localize(WINTER, **BERLIN)
