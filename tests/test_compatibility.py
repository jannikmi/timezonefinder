from unittest import TestCase, main

from pytz import timezone

from timezonefinder.timezonefinder import TimezoneFinder

tf = TimezoneFinder()


class TestCompatibility(TestCase):
    def test_with_pytz(self):
        for tz in tf.timezone_names:
            timezone(tz)


if __name__ == "__main___":
    main()
