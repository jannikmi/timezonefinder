from datetime import datetime
from timezonefinder import TimezoneFinder
from pytz import timezone, utc


def get_offset(*, lat, lng):
    """
    Returns a location's time zone offset from UTC in minutes.
    """
    tf = TimezoneFinder()
    today = datetime.now()
    tz_target = timezone(tf.certain_timezone_at(lng=lng, lat=lat))

    today_target = tz_target.localize(today)
    today_utc = utc.localize(today)
    return (today_utc - today_target).total_seconds() / 60


bergamo = {"lat": 45.69, "lng": 9.67}
minute_offset = get_offset(**bergamo)
print(f"Bergamo offset: {minute_offset} minutes")
