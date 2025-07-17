# examples/aware_datetime.py

from timezonefinder import TimezoneFinder
from pytz import timezone, utc
from pytz.exceptions import UnknownTimeZoneError
from datetime import datetime


def main(timezone_name, naive_datetime):
    if timezone_name is None:
        print("No timezone found for the given coordinates.")
        return

    try:
        tz = timezone(timezone_name)
    except UnknownTimeZoneError:
        print("Unknown timezone:", timezone_name)
        return

    aware_datetime = naive_datetime.replace(tzinfo=tz)
    aware_datetime_in_utc = aware_datetime.astimezone(utc)
    naive_datetime_as_utc = tz.localize(naive_datetime)

    print("Timezone:", timezone_name)
    print("Naive datetime:", naive_datetime)
    print("Aware datetime:", aware_datetime)
    print("Aware datetime (UTC):", aware_datetime_in_utc)
    print("Naive as UTC converted to TZ:", naive_datetime_as_utc)


if __name__ == "__main__":
    tf = TimezoneFinder()

    # Example: Berlin coordinates
    timezone_name = tf.timezone_at(lng=13.41, lat=52.52)

    # naive datetime (no timezone info)
    naive_datetime = datetime.now().replace(tzinfo=None)
    main(timezone_name, naive_datetime)
