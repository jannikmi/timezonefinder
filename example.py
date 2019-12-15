from timezonefinder import TimezoneFinder

TimezoneFinder.using_numba()  # this is a static method returning True or False

tf = TimezoneFinder()
# tf = TimezoneFinder(in_memory=True) # to use the faster "in-memory" mode
# tf = TimezoneFinder(bin_file_location='path/to/files') # to use data files from another location

longitude, latitude = 13.358, 52.5061
tf.timezone_at(lng=longitude, lat=latitude)  # returns 'Europe/Berlin'
tf.certain_timezone_at(lng=longitude, lat=latitude)  # returns 'Europe/Berlin'

longitude = 12.773955
latitude = 55.578595
tf.closest_timezone_at(lng=longitude, lat=latitude)  # returns 'Europe/Copenhagen'

longitude = 42.1052479
latitude = -16.622686
tf.closest_timezone_at(lng=longitude, lat=latitude, delta_degree=2, exact_computation=True, return_distances=True,
                       force_evaluation=True)

tf.get_geometry(tz_name='Africa/Addis_Ababa', coords_as_pairs=True)
tf.get_geometry(tz_id=400, use_id=True)


# To maximize the chances of getting a result in a Django view it might look like:
def find_timezone(request, lat, lng):
    lat = float(lat)
    lng = float(lng)

    try:
        timezone_name = tf.timezone_at(lng=lng, lat=lat)
        if timezone_name is None:
            timezone_name = tf.closest_timezone_at(lng=lng, lat=lat)
            # maybe even increase the search radius when it is still None

    except ValueError:
        # the coordinates were out of bounds
        # {handle error}
        pass

    # ... do something with timezone_name ...


# To get an aware datetime object from the timezone name:
# first install pytz
# first install pytz
from pytz import timezone, utc
from pytz.exceptions import UnknownTimeZoneError


def make_aware(naive_datetime, timezone_name):
    # naive means: tzinfo is None
    try:
        tz = timezone(timezone_name)
        aware_datetime = naive_datetime.replace(tzinfo=tz)
        aware_datetime_in_utc = aware_datetime.astimezone(utc)

        naive_datetime_as_utc_converted_to_tz = tz.localize(naive_datetime)

    except UnknownTimeZoneError:
        # ... handle the error ..
        pass


# Getting a location's time zone offset from UTC in minutes:
# adapted solution from https://github.com/communikein and `phineas-pta <https://github.com/phineas-pta>`__
from datetime import datetime
from pytz import timezone, utc

def get_offset(*, lat, lng):
    """
    returns a location's time zone offset from UTC in minutes.
    """

    today = datetime.now()
    tz_target = timezone(tf.certain_timezone_at(lng=lng, lat=lat))
    # ATTENTION: tz_target could be None! handle error case
    today_target = tz_target.localize(today)
    today_utc = utc.localize(today)
    return (today_utc - today_target).total_seconds() / 60


bergamo = {'lat': 45.69, 'lng': 9.67}
minute_offset = get_offset(**bergamo)
