import unittest
from timezonefinder import TimezoneFinder
from tzwhere import tzwhere
import random
from datetime import datetime
from realistic_points import realistic_points

time_zones = {
    "Europe/Andorra": 1,
    "Asia/Dubai": 2,
    "Asia/Kabul": 3,
    "America/Antigua": 4,
    "America/Anguilla": 5,
    "Europe/Tirane": 6,
    "Asia/Yerevan": 7,
    "Africa/Luanda": 8,
    "Antarctica/McMurdo": 9,
    "Antarctica/Rothera": 10,
    "Antarctica/Palmer": 11,
    "Antarctica/Mawson": 12,
    "Antarctica/Davis": 13,
    "Antarctica/Casey": 14,
    "Antarctica/Vostok": 15,
    "Antarctica/DumontDUrville": 16,
    "Antarctica/Syowa": 17,
    "Antarctica/Troll": 18,
    "America/Argentina/Buenos_Aires": 19,
    "America/Argentina/Cordoba": 20,
    "America/Argentina/Salta": 21,
    "America/Argentina/Jujuy": 22,
    "America/Argentina/Tucuman": 23,
    "America/Argentina/Catamarca": 24,
    "America/Argentina/La_Rioja": 25,
    "America/Argentina/San_Juan": 26,
    "America/Argentina/Mendoza": 27,
    "America/Argentina/San_Luis": 28,
    "America/Argentina/Rio_Gallegos": 29,
    "America/Argentina/Ushuaia": 30,
    "Pacific/Pago_Pago": 31,
    "Europe/Vienna": 32,
    "Australia/Lord_Howe": 33,
    "Antarctica/Macquarie": 34,
    "Australia/Hobart": 35,
    "Australia/Currie": 36,
    "Australia/Melbourne": 37,
    "Australia/Broken_Hill": 39,
    "Australia/Brisbane": 40,
    "Australia/Lindeman": 41,
    "Australia/Adelaide": 42,
    "Australia/Darwin": 43,
    "Australia/Perth": 44,
    "Australia/Eucla": 45,
    "America/Aruba": 46,
    "Europe/Mariehamn": 47,
    "Asia/Baku": 48,
    "Europe/Sarajevo": 49,
    "America/Barbados": 50,
    "Asia/Dhaka": 51,
    "Europe/Brussels": 52,
    "Africa/Ouagadougou": 53,
    "Europe/Sofia": 54,
    "Asia/Bahrain": 55,
    "Africa/Bujumbura": 56,
    "Africa/Porto-Novo": 57,
    "America/St_Barthelemy": 58,
    "Atlantic/Bermuda": 59,
    "Asia/Brunei": 60,
    "America/La_Paz": 61,
    "America/Kralendijk": 62,
    "America/Noronha": 63,
    "America/Belem": 64,
    "America/Fortaleza": 65,
    "America/Recife": 66,
    "America/Araguaina": 67,
    "America/Maceio": 68,
    "America/Bahia": 69,
    "America/Sao_Paulo": 70,
    "America/Campo_Grande": 71,
    "America/Cuiaba": 72,
    "America/Santarem": 73,
    "America/Porto_Velho": 74,
    "America/Boa_Vista": 75,
    "America/Manaus": 76,
    "America/Eirunepe": 77,
    "America/Rio_Branco": 78,
    "America/Nassau": 79,
    "Asia/Thimphu": 80,
    "Africa/Gaborone": 81,
    "Europe/Minsk": 82,
    "America/Belize": 83,
    "America/St_Johns": 84,
    "America/Halifax": 85,
    "America/Glace_Bay": 86,
    "America/Moncton": 87,
    "America/Goose_Bay": 88,
    "America/Blanc-Sablon": 89,
    "America/Toronto": 90,
    "America/Nipigon": 91,
    "America/Thunder_Bay": 92,
    "America/Iqaluit": 93,
    "America/Pangnirtung": 94,
    "America/Resolute": 95,
    "America/Atikokan": 96,
    "America/Rankin_Inlet": 97,
    "America/Winnipeg": 98,
    "America/Rainy_River": 99,
    "America/Regina": 100,
    "America/Swift_Current": 101,
    "America/Edmonton": 102,
    "America/Cambridge_Bay": 103,
    "America/Yellowknife": 104,
    "America/Inuvik": 105,
    "America/Creston": 106,
    "America/Dawson_Creek": 107,
    "America/Fort_Nelson": 108,
    "America/Vancouver": 109,
    "America/Whitehorse": 110,
    "America/Dawson": 111,
    "Indian/Cocos": 112,
    "Africa/Kinshasa": 113,
    "Africa/Lubumbashi": 114,
    "Africa/Bangui": 115,
    "Africa/Brazzaville": 116,
    "Europe/Zurich": 117,
    "Africa/Abidjan": 118,
    "Pacific/Rarotonga": 119,
    "America/Santiago": 120,
    "Pacific/Easter": 121,
    "Africa/Douala": 122,
    "Asia/Shanghai": 123,
    "Asia/Urumqi": 124,
    "America/Bogota": 125,
    "America/Costa_Rica": 126,
    "America/Havana": 127,
    "Atlantic/Cape_Verde": 128,
    "America/Curacao": 129,
    "Indian/Christmas": 130,
    "Asia/Nicosia": 131,
    "Europe/Prague": 132,
    "Europe/Berlin": 133,
    "Europe/Busingen": 134,
    "Africa/Djibouti": 135,
    "Europe/Copenhagen": 136,
    "America/Dominica": 137,
    "America/Santo_Domingo": 138,
    "Africa/Algiers": 139,
    "America/Guayaquil": 140,
    "Pacific/Galapagos": 141,
    "Europe/Tallinn": 142,
    "Africa/Cairo": 143,
    "Africa/El_Aaiun": 144,
    "Africa/Asmara": 145,
    "Europe/Madrid": 146,
    "Africa/Ceuta": 147,
    "Atlantic/Canary": 148,
    "Africa/Addis_Ababa": 149,
    "Europe/Helsinki": 150,
    "Pacific/Fiji": 151,
    "Atlantic/Stanley": 152,
    "Pacific/Chuuk": 153,
    "Pacific/Pohnpei": 154,
    "Pacific/Kosrae": 155,
    "Atlantic/Faroe": 156,
    "Europe/Paris": 157,
    "Africa/Libreville": 158,
    "Europe/London": 159,
    "America/Grenada": 160,
    "Asia/Tbilisi": 161,
    "America/Cayenne": 162,
    "Europe/Guernsey": 163,
    "Africa/Accra": 164,
    "Europe/Gibraltar": 165,
    "America/Godthab": 166,
    "America/Danmarkshavn": 167,
    "America/Scoresbysund": 168,
    "America/Thule": 169,
    "Africa/Banjul": 170,
    "Africa/Conakry": 171,
    "America/Guadeloupe": 172,
    "Africa/Malabo": 173,
    "Europe/Athens": 174,
    "Atlantic/South_Georgia": 175,
    "America/Guatemala": 176,
    "Pacific/Guam": 177,
    "Africa/Bissau": 178,
    "America/Guyana": 179,
    "Asia/Hong_Kong": 180,
    "America/Tegucigalpa": 181,
    "Europe/Zagreb": 182,
    "America/Port-au-Prince": 183,
    "Europe/Budapest": 184,
    "Asia/Jakarta": 185,
    "Asia/Pontianak": 186,
    "Asia/Makassar": 187,
    "Asia/Jayapura": 188,
    "Europe/Dublin": 189,
    "Asia/Jerusalem": 190,
    "Europe/Isle_of_Man": 191,
    "Asia/Kolkata": 192,
    "Indian/Chagos": 193,
    "Asia/Baghdad": 194,
    "Asia/Tehran": 195,
    "Atlantic/Reykjavik": 196,
    "Europe/Rome": 197,
    "Europe/Jersey": 198,
    "America/Jamaica": 199,
    "Asia/Amman": 200,
    "Asia/Tokyo": 201,
    "Africa/Nairobi": 202,
    "Asia/Bishkek": 203,
    "Asia/Phnom_Penh": 204,
    "Pacific/Tarawa": 205,
    "Pacific/Enderbury": 206,
    "Pacific/Kiritimati": 207,
    "Indian/Comoro": 208,
    "America/St_Kitts": 209,
    "Asia/Pyongyang": 210,
    "Asia/Seoul": 211,
    "Asia/Kuwait": 212,
    "America/Cayman": 213,
    "Asia/Almaty": 214,
    "Asia/Qyzylorda": 215,
    "Asia/Aqtobe": 216,
    "Asia/Aqtau": 217,
    "Asia/Oral": 218,
    "Asia/Vientiane": 219,
    "Asia/Beirut": 220,
    "America/St_Lucia": 221,
    "Europe/Vaduz": 222,
    "Asia/Colombo": 223,
    "Africa/Monrovia": 224,
    "Africa/Maseru": 225,
    "Europe/Vilnius": 226,
    "Europe/Luxembourg": 227,
    "Europe/Riga": 228,
    "Africa/Tripoli": 229,
    "Africa/Casablanca": 230,
    "Europe/Monaco": 231,
    "Europe/Chisinau": 232,
    "Europe/Podgorica": 233,
    "America/Marigot": 234,
    "Indian/Antananarivo": 235,
    "Pacific/Majuro": 236,
    "Pacific/Kwajalein": 237,
    "Europe/Skopje": 238,
    "Africa/Bamako": 239,
    "Asia/Rangoon": 240,
    "Asia/Ulaanbaatar": 241,
    "Asia/Hovd": 242,
    "Asia/Choibalsan": 243,
    "Asia/Macau": 244,
    "Pacific/Saipan": 245,
    "America/Martinique": 246,
    "Africa/Nouakchott": 247,
    "America/Montserrat": 248,
    "Europe/Malta": 249,
    "Indian/Mauritius": 250,
    "Indian/Maldives": 251,
    "Africa/Blantyre": 252,
    "America/Mexico_City": 253,
    "America/Cancun": 254,
    "America/Merida": 255,
    "America/Monterrey": 256,
    "America/Matamoros": 257,
    "America/Mazatlan": 258,
    "America/Chihuahua": 259,
    "America/Ojinaga": 260,
    "America/Hermosillo": 261,
    "America/Tijuana": 262,
    "America/Santa_Isabel": 263,
    "America/Bahia_Banderas": 264,
    "Asia/Kuala_Lumpur": 265,
    "Asia/Kuching": 266,
    "Africa/Maputo": 267,
    "Africa/Windhoek": 268,
    "Pacific/Noumea": 269,
    "Africa/Niamey": 270,
    "Pacific/Norfolk": 271,
    "Africa/Lagos": 272,
    "America/Managua": 273,
    "Europe/Amsterdam": 274,
    "Europe/Oslo": 275,
    "Asia/Kathmandu": 276,
    "Pacific/Nauru": 277,
    "Pacific/Niue": 278,
    "Pacific/Auckland": 279,
    "Pacific/Chatham": 280,
    "Asia/Muscat": 281,
    "America/Panama": 282,
    "America/Lima": 283,
    "Pacific/Tahiti": 284,
    "Pacific/Marquesas": 285,
    "Pacific/Gambier": 286,
    "Pacific/Port_Moresby": 287,
    "Pacific/Bougainville": 288,
    "Asia/Manila": 289,
    "Asia/Karachi": 290,
    "Europe/Warsaw": 291,
    "America/Miquelon": 292,
    "Pacific/Pitcairn": 293,
    "America/Puerto_Rico": 294,
    "Asia/Gaza": 295,
    "Asia/Hebron": 296,
    "Europe/Lisbon": 297,
    "Atlantic/Madeira": 298,
    "Atlantic/Azores": 299,
    "Pacific/Palau": 300,
    "America/Asuncion": 301,
    "Asia/Qatar": 302,
    "Indian/Reunion": 303,
    "Europe/Bucharest": 304,
    "Europe/Belgrade": 305,
    "Europe/Kaliningrad": 306,
    "Europe/Moscow": 307,
    "Europe/Simferopol": 308,
    "Europe/Volgograd": 309,
    "Europe/Samara": 310,
    "Asia/Yekaterinburg": 311,
    "Asia/Omsk": 312,
    "Asia/Novosibirsk": 313,
    "Asia/Novokuznetsk": 314,
    "Asia/Krasnoyarsk": 315,
    "Asia/Irkutsk": 316,
    "Asia/Chita": 317,
    "Asia/Yakutsk": 318,
    "Asia/Khandyga": 319,
    "Asia/Vladivostok": 320,
    "Asia/Sakhalin": 321,
    "Asia/Ust-Nera": 322,
    "Asia/Magadan": 323,
    "Asia/Srednekolymsk": 324,
    "Asia/Kamchatka": 325,
    "Asia/Anadyr": 326,
    "Africa/Kigali": 327,
    "Asia/Riyadh": 328,
    "Pacific/Guadalcanal": 329,
    "Indian/Mahe": 330,
    "Africa/Khartoum": 331,
    "Europe/Stockholm": 332,
    "Asia/Singapore": 333,
    "Atlantic/St_Helena": 334,
    "Europe/Ljubljana": 335,
    "Arctic/Longyearbyen": 336,
    "Europe/Bratislava": 337,
    "Africa/Freetown": 338,
    "Europe/San_Marino": 339,
    "Africa/Dakar": 340,
    "Africa/Mogadishu": 341,
    "America/Paramaribo": 342,
    "Africa/Juba": 343,
    "Africa/Sao_Tome": 344,
    "America/El_Salvador": 345,
    "America/Lower_Princes": 346,
    "Asia/Damascus": 347,
    "Africa/Mbabane": 348,
    "America/Grand_Turk": 349,
    "Africa/Ndjamena": 350,
    "Indian/Kerguelen": 351,
    "Africa/Lome": 352,
    "Asia/Bangkok": 353,
    "Asia/Dushanbe": 354,
    "Pacific/Fakaofo": 355,
    "Asia/Dili": 356,
    "Asia/Ashgabat": 357,
    "Africa/Tunis": 358,
    "Pacific/Tongatapu": 359,
    "Europe/Istanbul": 360,
    "America/Port_of_Spain": 361,
    "Pacific/Funafuti": 362,
    "Asia/Taipei": 363,
    "Africa/Dar_es_Salaam": 364,
    "Europe/Kiev": 365,
    "Europe/Uzhgorod": 366,
    "Europe/Zaporozhye": 367,
    "Africa/Kampala": 368,
    "Pacific/Johnston": 369,
    "Pacific/Midway": 370,
    "Pacific/Wake": 371,
    "America/New_York": 372,
    "America/Detroit": 373,
    "America/Kentucky/Louisville": 374,
    "America/Kentucky/Monticello": 375,
    "America/Indiana/Indianapolis": 376,
    "America/Indiana/Vincennes": 377,
    "America/Indiana/Winamac": 378,
    "America/Indiana/Marengo": 379,
    "America/Indiana/Petersburg": 380,
    "America/Indiana/Vevay": 381,
    "America/Chicago": 382,
    "America/Indiana/Tell_City": 383,
    "America/Indiana/Knox": 384,
    "America/Menominee": 385,
    "America/North_Dakota/Center": 386,
    "America/North_Dakota/New_Salem": 387,
    "America/North_Dakota/Beulah": 388,
    "America/Denver": 389,
    "America/Boise": 390,
    "America/Phoenix": 391,
    "America/Los_Angeles": 392,
    "America/Metlakatla": 393,
    "America/Anchorage": 394,
    "America/Juneau": 395,
    "America/Sitka": 396,
    "America/Yakutat": 397,
    "America/Nome": 398,
    "America/Adak": 399,
    "Pacific/Honolulu": 400,
    "America/Montevideo": 401,
    "Asia/Samarkand": 402,
    "Asia/Tashkent": 403,
    "Europe/Vatican": 404,
    "America/St_Vincent": 405,
    "America/Caracas": 406,
    "America/Tortola": 407,
    "America/St_Thomas": 408,
    "Asia/Ho_Chi_Minh": 409,
    "Pacific/Efate": 410,
    "Pacific/Wallis": 411,
    "Pacific/Apia": 412,
    "Asia/Aden": 413,
    "Indian/Mayotte": 414,
    "Africa/Johannesburg": 415,
    "Africa/Lusaka": 416,
    "Africa/Harare": 417,
    'Asia/Kashgar': 418,
    'America/Montreal': 419,
    'Asia/Harbin': 420,
    'America/Coral_Harbour': 421,
    'uninhabited': 422,
    'Australia/Sydney': 423,
    'Asia/Chongqing': 424
}


class TimezoneEqualityTest(unittest.TestCase):
    # Test Points for equality-test of the algorithms:
    equality_test_data = {

        # invalid cause this is no zone so also no ID (-52.9883809, 29.6183884): '',

        (-44.7402611, 70.2989263): 'America/Godthab',

        (-4.8663325, 40.0663485): 'Europe/Madrid',

        (-60.968888, -3.442172): 'America/Manaus',

        (14.1315716, 2.99999): 'Africa/Douala',

        (14.1315716, 0.2350623): 'Africa/Brazzaville',

        (-71.9996885, -52.7868679): 'America/Santiago',

        (-152.4617352, 62.3415036): 'America/Anchorage',

        (37.0720767, 55.74929): 'Europe/Moscow',

        (103.7069307, 1.3150701): 'Asia/Singapore',

        (12.9125913, 50.8291834): 'Europe/Berlin',

        (-106.1706459, 23.7891123): 'America/Mazatlan',

        (33, -84): 'uninhabited',

    }

    def setUp(self):
        # prepare tests
        self.timezone_finder = TimezoneFinder()
        self.tz_where = tzwhere()

        self.n = 1000

    def tearDown(self):
        pass

    def test_correctness(self):
        # Test correctness
        for k, v in self.equality_test_data.items():
            lng = k[0]
            lat = k[1]
            print('should be:', v)

            my_result = self.timezone_finder.timezone_at(lng, lat)
            his_result = self.tz_where.tzNameAt(latitude=lat, longitude=lng)
            print('results: ', my_result, his_result, '\n')
            assert my_result == v

            assert his_result == v

    def test_equality(self):
        # Test the equality if the two algorithms

        # test_points = []
        # for i in range(n):
        # test_points.append(random_point())

        mistakes = 0
        print('testing realistic points')
        print('MISMATCHES:')

        for p in realistic_points:

            his_result = self.tz_where.tzNameAt(latitude=p[1], longitude=p[0])

            my_result = self.timezone_finder.timezone_at(*p)

            if my_result != his_result:
                mistakes += 1
                # mistake_point_nrs.append(i)
                print(p)
                print(my_result)
                print('should be equal to')
                print(his_result)

        n = 1000
        print('testing', n, 'random points')
        print('MISMATCHES:')

        i = 0
        while i < n:
            p = random_point()

            his_result = self.tz_where.tzNameAt(latitude=p[1], longitude=p[0])

            if his_result is not None:
                i += 1
                my_result = self.timezone_finder.timezone_at(*p)

                if my_result != his_result:
                    mistakes += 1
                    # mistake_point_nrs.append(i)
                    print(p)
                    print(my_result)
                    print('should be equal to')
                    print(his_result)

                    # assert my_result == his_result

        print('\nin', n + self.n, 'tries', mistakes, 'mismatches were made')
        print('fail percentage is:', mistakes * 100 / (n + self.n))

    def test_startup_time(self):

        def test_speed_his_algor(points):
            start_time = datetime.now()

            tz_where = tzwhere()

            end_time = datetime.now()

            tz_where.tzNameAt(latitude=13.3, longitude=53.2)

            return end_time - start_time

        def test_speed_my_algor(points):
            start_time = datetime.now()

            timezonefinder = TimezoneFinder()

            end_time = datetime.now()

            timezonefinder.timezone_at(13.3, 53.2)

            return end_time - start_time

        my_time = test_speed_my_algor(realistic_points)
        his_time = test_speed_his_algor(realistic_points)

        print('Startup times:')
        print('tzwhere:', his_time)
        print('timezonefinder:', my_time)
        print(round(his_time / my_time, 2), 'times faster')

    def test_speed(self):

        def test_speed_his_algor(points):
            start_time = datetime.now()

            # old algorithm (tzwhere)
            for point in points:
                self.tz_where.tzNameAt(latitude=point[1], longitude=point[0])

            end_time = datetime.now()

            return end_time - start_time

            # test my first algorithm (boundaries, csv)


            # test second algorithm ( double, .bin)

        def test_speed_my_algor(points):
            # test final algorithm ( long long, .bin)

            start_time = datetime.now()

            for point in points:
                self.timezone_finder.timezone_at(point[0], point[1])

            end_time = datetime.now()

            return end_time - start_time

        runs = 1

        my_time = test_speed_my_algor(realistic_points)
        his_time = test_speed_his_algor(realistic_points)
        for i in range(runs - 1):
            my_time += test_speed_my_algor(realistic_points)
            his_time += test_speed_his_algor(realistic_points)

        my_time /= runs
        his_time /= runs

        print('')
        print('\n\nTIMES for', self.n, 'realistic queries:')
        print('tzwhere:', his_time)
        print('timezonefinder:', my_time)

        print(round(his_time / my_time, 2), 'times faster')

    def test_speed_random(self):

        def test_speed_his_algor(points):
            start_time = datetime.now()

            # old algorithm (tzwhere)
            for point in points:
                self.tz_where.tzNameAt(latitude=point[1], longitude=point[0])

            end_time = datetime.now()

            return end_time - start_time

            # test my first algorithm (boundaries, csv)


            # test second algorithm ( double, .bin)

        def test_speed_my_algor(points):
            # test final algorithm ( long long, .bin)

            start_time = datetime.now()

            for point in points:
                self.timezone_finder.timezone_at(point[0], point[1])

            end_time = datetime.now()

            return end_time - start_time

        runs = 1

        n = 10000
        points = []

        for i in range(n):
            points.append(random_point())

        my_time = test_speed_my_algor(points)
        his_time = test_speed_his_algor(points)
        for i in range(runs - 1):
            my_time += test_speed_my_algor(points)
            his_time += test_speed_his_algor(points)

        my_time /= runs
        his_time /= runs

        print('')
        print('\n\nTIMES for ', n, 'random queries:')
        print('tzwhere:', his_time)
        print('timezonefinder:', my_time)

        print(round(his_time / my_time, 2), 'times faster')

        # TODO test start up time
        # Test, store and document the speed of all the Algorithms

    '''
    def test_equality_until_mistake(self):
        # Test the equality if the two algorithms

        mistake_after = 0
        print('Testing until missmatch:')
        print('valid points checked:')
        i = 0

        while 1:
            point = random_point()
            his_result = self.tz_where.tzNameAt(latitude=point[1], longitude=point[0])

            if his_result is not None:
                i += 1
                if i % 1000 == 0:
                    print(i)

                my_result = self.timezone_finder.timezone_at(point[0], point[1])

                if my_result != his_result:
                    mistake_after = i
                    # mistake_point_nrs.append(i)
                    print(point)
                    print(my_result)
                    print('should be equal to')
                    print(his_result)
                    break

                    # assert my_result == his_result

        print('mistake made when testing the ', mistake_after, 'th non empty random point')
    '''


def random_point():
    # tzwhere does not work for points with more latitude!
    return random.uniform(-180, 180), random.uniform(-84, 84)
