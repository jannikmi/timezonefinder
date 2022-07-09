# for TimezoneFinderL:
BASIC_TEST_LOCATIONS = [
    # lat, lng, description, expected
    (35.295953, -89.662186, "Arlington, TN", "America/Chicago"),
    (35.1322601, -90.0902499, "Memphis, TN", "America/Chicago"),
    (61.17, -150.02, "Anchorage, AK", "America/Anchorage"),
    (40.2, -119.3, "California/Nevada border", "America/Los_Angeles"),
    (42.652647, -73.756371, "Albany, NY", "America/New_York"),
    (55.743749, 37.6207923, "Moscow", "Europe/Moscow"),
    (34.104255, -118.4055591, "Los Angeles", "America/Los_Angeles"),
    (55.743749, 37.6207923, "Moscow", "Europe/Moscow"),
    (39.194991, -106.8294024, "Aspen, Colorado", "America/Denver"),
    (50.438114, 30.5179595, "Kiev", "Europe/Kiev"),
    (12.936873, 77.6909136, "Jogupalya", "Asia/Kolkata"),
    (38.889144, -77.0398235, "Washington DC", "America/New_York"),
    (19, -135, "pacific ocean", "Etc/GMT+9"),
    (30, -33, "atlantic ocean", "Etc/GMT+2"),
    (-24, 79, "indian ocean", "Etc/GMT-5"),
]

# for TimezoneFinder:
# certain algorithm should give the same results for all normal test cases
TEST_LOCATIONS = BASIC_TEST_LOCATIONS + [
    (59.932490, 30.3164291, "St Petersburg", "Europe/Moscow"),
    (50.300624, 127.559166, "Blagoveshchensk", "Asia/Yakutsk"),
    (42.439370, -71.0700416, "Boston", "America/New_York"),
    (41.84937, -87.6611995, "Chicago", "America/Chicago"),
    (28.626873, -81.7584514, "Orlando", "America/New_York"),
    (47.610615, -122.3324847, "Seattle", "America/Los_Angeles"),
    (51.499990, -0.1353549, "London", "Europe/London"),
    (51.256241, -0.8186531, "Church Crookham", "Europe/London"),
    (51.292215, -0.8002638, "Fleet", "Europe/London"),
    (48.868743, 2.3237586, "Paris", "Europe/Paris"),
    (22.158114, 113.5504603, "Macau", "Asia/Macau"),
    (56.833123, 60.6097054, "Russia", "Asia/Yekaterinburg"),
    (60.887496, 26.6375756, "Salo", "Europe/Helsinki"),
    (52.799992, -1.8524408, "Staffordshire", "Europe/London"),
    (5.016666, 115.0666667, "Muara", "Asia/Brunei"),
    (-41.466666, -72.95, "Puerto Montt seaport", "America/Santiago"),
    (34.566666, 33.0333333, "Akrotiri seaport", "Asia/Nicosia"),
    (37.466666, 126.6166667, "Inchon seaport", "Asia/Seoul"),
    (42.8, 132.8833333, "Nakhodka seaport", "Asia/Vladivostok"),
    (50.26, -5.051, "Truro", "Europe/London"),
    (37.790792, -122.389980, "San Francisco", "America/Los_Angeles"),
    (37.81, -122.35, "San Francisco Bay", "America/Los_Angeles"),
    (68.3597987, -133.745786, "America", "America/Inuvik"),
    # lng 180 == -180
    # 180.0: right on the timezone boundary polygon edge, the return value is uncertain (None in this case)
    # being tested in test_helpers.py
    (65.2, 179.9999, "lng 180", "Asia/Anadyr"),
    (65.2, -179.9999, "lng -180", "Asia/Anadyr"),
    # test cases for hole handling:
    (41.0702284, 45.0036352, "Aserbaid. Enklave", "Asia/Yerevan"),
    (39.8417402, 70.6020068, "Tajikistani Enklave", "Asia/Dushanbe"),
    (47.7024174, 8.6848462, "Busingen Ger", "Europe/Busingen"),
    (46.2085101, 6.1246227, "Genf", "Europe/Zurich"),
    (-29.391356857138753, 28.50989829115889, "Lesotho", "Africa/Maseru"),
    (39.93143377877638, 71.08546583764965, "Uzbek enclave1", "Asia/Tashkent"),
    (39.969915, 71.134060, "Uzbek enclave2", "Asia/Tashkent"),
    (39.862402, 70.568449, "Tajik enclave", "Asia/Dushanbe"),
    (35.7396116, -110.15029571, "Arizona Desert 1", "America/Denver"),
    (36.4091869, -110.7520236, "Arizona Desert 2", "America/Phoenix"),
    (36.10230848, -111.1882385, "Arizona Desert 3", "America/Phoenix"),
    # ocean:
    (37.81, -123.5, "Far off San Fran.", "Etc/GMT+8"),
    (50.26, -9.0, "Far off Cornwall", "Etc/GMT+1"),
    (50.5, 1, "English Channel1", "Etc/GMT"),
    (56.218, 19.4787, "baltic sea", "Etc/GMT-1"),
]

BOUNDARY_TEST_CASES = [
    # directly at the poles and the 180deg longitude border the zone result is ambiguous
    # the result should still be well defined
    # zone_name="" is interpreted as "don't care"
    (-180.0, 90.0, ""),
    (-180.0, 0.0, ""),
    (-180.0, -90.0, ""),
    (180.0, 90.0, ""),
    (180.0, 0.0, ""),
    (180.0, -90.0, ""),
    (179.999, 0.0, "Etc/GMT-12"),
    (-179.999, 0.0, "Etc/GMT+12"),
]
