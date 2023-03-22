from unittest import TestCase, main

from timezonefinder.timezonefinder import TimezoneFinder

tf = TimezoneFinder()


class TestCompatibility(TestCase):
    def test_with_pytz(self):
        try:
            from pytz import timezone
        except Exception:
            return
        for tz in tf.timezone_names:
            timezone(tz)


if __name__ == "__main___":
    main()
