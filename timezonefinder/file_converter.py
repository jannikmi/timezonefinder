import linecache
import math
import re
from datetime import datetime
from struct import *

# number of shortcuts per longitude
NR_SHORTCUTS_PER_LNG = 1
# shortcuts per latitude
NR_SHORTCUTS_PER_LAT = 2

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


# HELPERS:

def check_zone_names():
    '''
    scans for zone name in the original .csv which are not listed yet
    :return:
    '''
    omitted_zones = []
    for (zone_name, list_of_points) in _read_polygons_from_original_csv():

        if zone_name not in time_zones:
            if zone_name not in omitted_zones:
                omitted_zones.append(zone_name)

    print(omitted_zones)
    return


def coordinate_to_longlong(double):
    return int(double * 10 ** 15)


def longlong_to_coordinate(longlong):
    return float(longlong / 10 ** 15)


def inside_polygon(x, y, x_coords, y_coords):
    def is_left_of(x, y, x1, x2, y1, y2):
        return (x2 - x1) * (y - y1) - (x - x1) * (y2 - y1)

    n = len(y_coords) - 1

    wn = 0
    for i in range(n):
        iplus = i + 1
        if y_coords[i] <= y:
            # print('Y1<=y')
            if y_coords[iplus] > y:
                # print('Y2>y')
                if is_left_of(x, y, x_coords[i], x_coords[iplus], y_coords[i], y_coords[iplus]) > 0:
                    wn += 1
                    # print('wn is:')
                    # print(wn)

        else:
            # print('Y1>y')
            if y_coords[iplus] <= y:
                # print('Y2<=y')
                if is_left_of(x, y, x_coords[i], x_coords[iplus], y_coords[i], y_coords[iplus]) < 0:
                    wn -= 1
                    # print('wn is:')
                    # print(wn)

    return wn is not 0


def _read_polygons_from_original_csv(path='tz_world.csv'):
    with open(path, 'r') as f:
        for row in f:
            row = row.split(',')
            yield (row[0], [[float(coordinate) for coordinate in point.split(' ')] for point in row[1:]])


def convert_csv(path='tz_world.csv'):
    '''
    create a new .csv with rearranged data
    converts the zone names into their ids (int instead of string, for later storing it in a .bin)
    additionally splits up the rows into:  id,xmax,xmin,ymax,ymin,y1 y2...,x1 x2 ...\n
    #those boundaries help do quickly decide wether to check the polygon at all (saves a lot of time)
    :param path:
    :return:
    '''
    output_file = open('tz_world_converted.csv', 'w')
    print('converting the old .csv now...')
    for (zone_name, list_of_points) in _read_polygons_from_original_csv(path):
        xmax = -180
        xmin = 180
        ymax = -90
        ymin = 90
        string_of_x_coords = ''
        string_of_y_coords = ''
        # in the original .csv the earch polygon starts and ends with the same coordinate (=redundancy)
        # this is not needed, because the algorithms can do the job without this because value will be in the RAM anyway
        # 50+k floats and reading effort saved!
        for i in range(len(list_of_points) - 1):

            x = list_of_points[i][0]
            y = list_of_points[i][1]

            match = re.match(r'[-]?\d+\.?\d?', str(y))
            if match is None:
                raise ValueError('newline in y coord at value: ' + str(i - 1), y)

            match = re.match(r'[-]?\d+\.?\d?', str(x))
            if match is None:
                raise ValueError('newline in x coord at value: ' + str(i - 1), x)

            if x > xmax:
                xmax = x
            if x < xmin:
                xmin = x
            if y > ymax:
                ymax = y
            if y < ymin:
                ymin = y
            string_of_x_coords += str(x) + ' '
            string_of_y_coords += str(y) + ' '

        output_file.write(str(time_zones[zone_name]) + ',' + str(xmax) + ',' + str(xmin) + ',' + str(ymax) + ',' + str(
            ymin) + ',' + string_of_x_coords.strip() + ',' + string_of_y_coords.strip() + '\n')


def _ids():
    with open('tz_world_converted.csv', 'r') as f:
        for row in f:
            row = row.split(',')
            # (id,xmax,xmin,ymax,ymin, [x1 x2 ...], [y1 y2...])
            # x = horizontal = longitude, y = vertical = latitude
            yield int(row[0])


def _boundaries():
    with open('tz_world_converted.csv', 'r') as f:
        for row in f:
            row = row.split(',')
            # (id,xmax,xmin,ymax,ymin, [x1 x2 ...], [y1 y2...])
            # x = horizontal = longitude, y = vertical = latitude
            yield (float(row[1]), float(row[2]), float(row[3]), float(row[4]),)


def _coordinates():
    with open('tz_world_converted.csv', 'r') as f:
        for row in f:
            row = row.split(',')
            # (id,xmax,xmin,ymax,ymin, [x1 x2 ...], [y1 y2...])
            # x = horizontal = longitude, y = vertical = latitude
            yield ([float(x) for x in row[5].split(' ')], [float(x) for x in row[6].strip().split(' ')])


def longs_in(line=0):
    row = linecache.getline('tz_world_converted.csv', lineno=line)
    row = row.split(',')
    return (
        [int(float(x) * 10 ** 15) for x in row[5].split(' ')],
        [int(float(x) * 10 ** 15) for x in row[6].strip().split(' ')])


def _length_of_rows():
    with open('tz_world_converted.csv', 'r') as f:
        for row in f:
            yield len(row.split(',')[5].split(' '))


def compile_into_binary(path='tz_binary.bin'):
    nr_of_floats = 0
    nr_of_lines = 0
    zone_ids = []
    shortcuts = {}

    def x_shortcut(lng):
        # if lng < -180 or lng >= 180:
        # print(lng)
        # raise ValueError('longitude out of bounds')
        return math.floor((lng + 180) * NR_SHORTCUTS_PER_LNG)

    def y_shortcut(lat):
        # if lat < -90 or lat >= 90:
        # print(lat)
        # raise ValueError('this latitude is out of bounds')
        return math.floor((90 - lat) * NR_SHORTCUTS_PER_LAT)

    def big_zone(xmax, xmin, ymax, ymin):
        # returns True if a zone with those boundaries could have more than 4 shortcuts
        return xmax - xmin > 2 / NR_SHORTCUTS_PER_LNG and ymax - ymin > 2 / NR_SHORTCUTS_PER_LAT

    def included_shortcut_row_nrs(max_lat, min_lat):
        return list(range(y_shortcut(max_lat), y_shortcut(min_lat) + 1))

    def included_shortcut_column_nrs(max_lng, min_lng):
        return list(range(x_shortcut(min_lng), x_shortcut(max_lng) + 1))

    def longitudes_to_check(max_lng, min_lng):
        output_list = []
        step = 1 / NR_SHORTCUTS_PER_LNG
        current = math.ceil(min_lng * NR_SHORTCUTS_PER_LNG) / NR_SHORTCUTS_PER_LNG
        end = math.floor(max_lng * NR_SHORTCUTS_PER_LNG) / NR_SHORTCUTS_PER_LNG
        while current < end:
            output_list.append(current)
            current += step

        output_list.append(end)
        return output_list

    def latitudes_to_check(max_lat, min_lat):
        output_list = []
        step = 1 / NR_SHORTCUTS_PER_LAT
        current = math.ceil(min_lat * NR_SHORTCUTS_PER_LAT) / NR_SHORTCUTS_PER_LAT
        end = math.floor(max_lat * NR_SHORTCUTS_PER_LAT) / NR_SHORTCUTS_PER_LAT
        while current < end:
            output_list.append(current)
            current += step

        output_list.append(end)
        return output_list

    def compute_x_intersection(y, x1, x2, y1, y2):
        """returns the x intersection from a horizontal line in y with the line from x1,y1 to x1,y2
        """
        delta_y = y2 - y1
        if delta_y == 0:
            return x1
        return ((y - y1) * (x2 - x1) / delta_y) + x1

    def compute_y_intersection(x, x1, x2, y1, y2):
        """returns the y intersection from a vertical line in x with the line from x1,y1 to x1,y2
        """
        delta_x = x2 - x1
        if delta_x == 0:
            return x1
        return ((x - x1) * (y2 - y1) / delta_x) + y1

    def x_intersections(y, x_coords, y_coords):

        # print(x_coords)
        # print(y)
        # print(y_coords)

        intersects = []
        for i in range(len(y_coords) - 1):
            iplus1 = i + 1
            if y_coords[i] <= y:
                # print('Y1<=y')
                if y_coords[iplus1] > y:
                    # this was a crossing. compute the intersect
                    # print('Y2>y')
                    intersects.append(
                        compute_x_intersection(y, x_coords[i], x_coords[iplus1], y_coords[i], y_coords[iplus1]))
            else:
                # print('Y1>y')
                if y_coords[iplus1] <= y:
                    # this was a crossing. compute the intersect
                    # print('Y2<=y')
                    intersects.append(compute_x_intersection(y, x_coords[i], x_coords[iplus1], y_coords[i],
                                                             y_coords[iplus1]))
        return intersects

    def y_intersections(x, x_coords, y_coords):

        intersects = []
        for i in range(len(y_coords) - 1):
            iplus1 = i + 1
            if x_coords[i] <= x:
                if x_coords[iplus1] > x:
                    # this was a crossing. compute the intersect
                    intersects.append(
                        compute_y_intersection(x, x_coords[i], x_coords[iplus1], y_coords[i], y_coords[iplus1]))
            else:
                if x_coords[iplus1] <= x:
                    # this was a crossing. compute the intersect
                    intersects.append(compute_y_intersection(x, x_coords[i], x_coords[iplus1], y_coords[i],
                                                             y_coords[iplus1]))
        return intersects

    def compute_exact_shortcuts(xmax, xmin, ymax, ymin, line):
        shortcuts_for_line = set()

        # x_longs = binary_reader.x_coords_of(line)
        longs = longs_in(line + 1)
        x_longs = longs[0]
        y_longs = longs[1]

        # y_longs = binary_reader.y_coords_of(line)
        y_longs.append(y_longs[0])
        x_longs.append(x_longs[0])

        step = 1 / NR_SHORTCUTS_PER_LAT
        # print('checking the latitudes')
        for lat in latitudes_to_check(ymax, ymin):
            # print(lat)
            # print(coordinate_to_longlong(lat))
            # print(y_longs)
            # print(x_intersections(coordinate_to_longlong(lat), x_longs, y_longs))
            # raise ValueError
            intersects = [longlong_to_coordinate(x) for x in
                          x_intersections(coordinate_to_longlong(lat), x_longs, y_longs)]
            intersects.sort()
            # print(intersects)

            nr_of_intersects = len(intersects)
            if nr_of_intersects % 2 != 0:
                raise ValueError('an uneven number of intersections has been accounted')

            for i in range(0, nr_of_intersects, 2):
                possible_longitudes = []
                # collect all the zones between two intersections [in,out,in,out,...]
                iplus = i + 1
                intersection_in = intersects[i]
                intersection_out = intersects[iplus]
                if intersection_in == intersection_out:
                    # the polygon has a point exactly on the border of a shortcut zone here!
                    # only select the top shortcut if it is actually inside the polygon (point a little up is inside)
                    if inside_polygon(coordinate_to_longlong(intersection_in), coordinate_to_longlong(lat) + 1, x_longs,
                                      y_longs):
                        shortcuts_for_line.add((x_shortcut(intersection_in), y_shortcut(lat) - 1))
                    # the bottom shortcut is always selected
                    shortcuts_for_line.add((x_shortcut(intersection_in), y_shortcut(lat)))

                else:
                    # add all the shortcuts for the whole found area of intersection
                    possible_y_shortcut = y_shortcut(lat)

                    # both shortcuts should only be selected when the polygon doesnt stays on the border
                    middle = intersection_in + (intersection_out - intersection_in) / 2
                    if inside_polygon(coordinate_to_longlong(middle), coordinate_to_longlong(lat) + 1, x_longs,
                                      y_longs):
                        while intersection_in < intersection_out:
                            possible_longitudes.append(intersection_in)
                            intersection_in += step

                        possible_longitudes.append(intersection_out)

                        # the shortcut above and below of the intersection should be selected!
                        possible_y_shortcut_min1 = possible_y_shortcut - 1
                        for possible_x_coord in possible_longitudes:
                            shortcuts_for_line.add((x_shortcut(possible_x_coord), possible_y_shortcut))
                            shortcuts_for_line.add((x_shortcut(possible_x_coord), possible_y_shortcut_min1))
                    else:
                        # polygon does not cross the border!
                        while intersection_in < intersection_out:
                            possible_longitudes.append(intersection_in)
                            intersection_in += step

                        possible_longitudes.append(intersection_out)

                        # only the shortcut above of the intersection should be selected!
                        for possible_x_coord in possible_longitudes:
                            shortcuts_for_line.add((x_shortcut(possible_x_coord), possible_y_shortcut))

        # print('now all the longitudes to check')
        # same procedure horizontally
        step = 1 / NR_SHORTCUTS_PER_LAT
        for lng in longitudes_to_check(xmax, xmin):
            # print(lng)
            # print(coordinate_to_longlong(lng))
            # print(x_longs)
            # print(x_intersections(coordinate_to_longlong(lng), x_longs, y_longs))
            intersects = [longlong_to_coordinate(y) for y in
                          y_intersections(coordinate_to_longlong(lng), x_longs, y_longs)]
            intersects.sort()
            # print(intersects)

            nr_of_intersects = len(intersects)
            if nr_of_intersects % 2 != 0:
                raise ValueError('an uneven number of intersections has been accounted')

            possible_latitudes = []
            for i in range(0, nr_of_intersects, 2):
                # collect all the zones between two intersections [in,out,in,out,...]
                iplus = i + 1
                intersection_in = intersects[i]
                intersection_out = intersects[iplus]
                if intersection_in == intersection_out:
                    # the polygon has a point exactly on the border of a shortcut here!
                    # only select the left shortcut if it is actually inside the polygon (point a little left is inside)
                    if inside_polygon(coordinate_to_longlong(lng) - 1, coordinate_to_longlong(intersection_in), x_longs,
                                      y_longs):
                        shortcuts_for_line.add((x_shortcut(lng) - 1, y_shortcut(intersection_in)))
                    # the right shortcut is always selected
                    shortcuts_for_line.add((x_shortcut(lng), y_shortcut(intersection_in)))

                else:
                    # add all the shortcuts for the whole found area of intersection
                    possible_x_shortcut = x_shortcut(lng)

                    # both shortcuts should only be selected when the polygon doesnt stays on the border
                    middle = intersection_in + (intersection_out - intersection_in) / 2
                    if inside_polygon(coordinate_to_longlong(lng) - 1, coordinate_to_longlong(middle), x_longs,
                                      y_longs):
                        while intersection_in < intersection_out:
                            possible_latitudes.append(intersection_in)
                            intersection_in += step

                        possible_latitudes.append(intersection_out)

                        # both shortcuts right and left of the intersection should be selected!
                        possible_x_shortcut_min1 = possible_x_shortcut - 1
                        for possible_latitude in possible_latitudes:
                            shortcuts_for_line.add((possible_x_shortcut, y_shortcut(possible_latitude)))
                            shortcuts_for_line.add((possible_x_shortcut_min1, y_shortcut(possible_latitude)))

                    else:
                        while intersection_in < intersection_out:
                            possible_latitudes.append(intersection_in)
                            intersection_in += step
                        # only the shortcut right of the intersection should be selected!
                        possible_latitudes.append(intersection_out)

                        for possible_latitude in possible_latitudes:
                            shortcuts_for_line.add((possible_x_shortcut, y_shortcut(possible_latitude)))

        return shortcuts_for_line

    def construct_shortcuts():
        print('building shortucts...')
        line = 0
        for xmax, xmin, ymax, ymin in _boundaries():
            # xmax, xmin, ymax, ymin = boundaries_of(line=line)
            if line % 1000 == 0:
                print('line ' + str(line))
                # print([xmax, xmin, ymax, ymin])

            column_nrs = included_shortcut_column_nrs(xmax, xmin)
            row_nrs = included_shortcut_row_nrs(ymax, ymin)

            if big_zone(xmax, xmin, ymax, ymin):
                '''
                print('line ' + str(line))
                print('This is a big zone! computing exact shortcuts')
                print('Nr of entries before')
                print(len(column_nrs) * len(row_nrs))
                
                print('columns and rows before optimisation:')
                
                print(column_nrs)
                print(row_nrs)
                '''

                # This is a big zone! compute exact shortcuts with the whole polygon points
                shortcuts_for_line = compute_exact_shortcuts(xmax, xmin, ymax, ymin, line)
                # n += len(shortcuts_for_line)

                '''
                accurracy = 1000000000000
                while len(shortcuts_for_line) < 3 and accurracy > 10000000000:
                    shortcuts_for_line = compute_exact_shortcuts(line=i,accurracy)
                    accurracy = int(accurracy/10)
                '''
                min_x_shortcut = column_nrs[0]
                max_x_shortcut = column_nrs[-1]
                min_y_shortcut = row_nrs[0]
                max_y_shortcut = row_nrs[-1]
                shortcuts_to_remove = []
                for x, y in shortcuts_for_line:
                    if x < min_x_shortcut:
                        shortcuts_to_remove.append((x, y))
                    if x > max_x_shortcut:
                        shortcuts_to_remove.append((x, y))
                    if y < min_y_shortcut:
                        shortcuts_to_remove.append((x, y))
                    if y > max_y_shortcut:
                        shortcuts_to_remove.append((x, y))

                for s in shortcuts_to_remove:
                    shortcuts_for_line.remove(s)

                '''
                print('and after:')
                print(len(shortcuts_for_line))
                
                column_nrs_after = set()
                row_nrs_after = set()
                for x, y in shortcuts_for_line:
                    column_nrs_after.add(x)
                    row_nrs_after.add(y)
                print(column_nrs_after)
                print(row_nrs_after)
                print(shortcuts_for_line)
                '''
                if len(shortcuts_for_line) > len(column_nrs) * len(row_nrs):
                    raise ValueError(
                        'there are more shortcuts than before now. there is something wrong with the algorithm!')
                if len(shortcuts_for_line) < 3:
                    raise ValueError('algorithm not accurate enough. less than 3 zones detected')

            else:

                shortcuts_for_line = []
                for column_nr in column_nrs:
                    for row_nr in row_nrs:
                        shortcuts_for_line.append((column_nr, row_nr))

                        # print(shortcuts_for_line)
            for shortcut in shortcuts_for_line:
                shortcuts[shortcut] = shortcuts.get(shortcut, []) + [line]

            line += 1
            # print('collected entries:')
            # print(n)

    print('reading the converted .csv file')
    for ID in _ids():
        nr_of_lines += 1
        zone_ids.append(ID)

    for length in _length_of_rows():
        nr_of_floats += 2 * length

    start_time = datetime.now()
    construct_shortcuts()
    end_time = datetime.now()

    print(end_time - start_time)

    polygon_address = (40 * nr_of_lines + 6)
    shortcut_start_address = polygon_address + 8 * nr_of_floats
    nr_of_floats += nr_of_lines * 4
    print('The number of polygons is:', nr_of_lines)
    print('The number of floats in all the polygons is:', nr_of_floats)
    print('now writing file "', path, '"')
    output_file = open(path, 'wb')
    # write nr_of_lines
    output_file.write(pack('!H', nr_of_lines))
    # write start address of shortcut_data:
    output_file.write(pack('!I', shortcut_start_address))
    # write zone_ids
    for zone_id in zone_ids:
        output_file.write(pack('!H', zone_id))
    # write number of values
    for length in _length_of_rows():
        output_file.write(pack('!H', length))

    # write polygon_addresses
    for length in _length_of_rows():
        output_file.write(pack('!I', polygon_address))
        polygon_address += 16 * length

    if shortcut_start_address != polygon_address:
        # both should be the same!
        raise ValueError('shortcut_start_address and polygon_address should now be the same!')

    # write boundary_data
    for xmax, xmin, ymax, ymin in _boundaries():
        output_file.write(pack('!qqqq',
                               coordinate_to_longlong(xmax), coordinate_to_longlong(xmin), coordinate_to_longlong(ymax),
                               coordinate_to_longlong(ymin)))

    # write polygon_data
    for x_coords, y_coords in _coordinates():
        for x in x_coords:
            output_file.write(pack('!q', coordinate_to_longlong(x)))
        for y in y_coords:
            output_file.write(pack('!q', coordinate_to_longlong(y)))

    print('position after writing all polygon data:', output_file.tell())
    # write number of entries in shortcut field (x,y)
    nr_of_entries_in_shortcut = []
    shortcut_entries = []
    total_entries_in_shortcuts = 0

    # count how many shortcut addresses will be written:
    for x in range(360 * NR_SHORTCUTS_PER_LNG):
        for y in range(180 * NR_SHORTCUTS_PER_LAT):
            try:
                this_lines_shortcuts = shortcuts[(x, y)]
                shortcut_entries.append(this_lines_shortcuts)
                total_entries_in_shortcuts += 1
                nr_of_entries_in_shortcut.append(len(this_lines_shortcuts))
                # print((x,y,this_lines_shortcuts))
            except KeyError:
                nr_of_entries_in_shortcut.append(0)

    print('The number of filled shortcut zones are:', total_entries_in_shortcuts)

    if len(nr_of_entries_in_shortcut) != 64800 * NR_SHORTCUTS_PER_LNG * NR_SHORTCUTS_PER_LAT:
        print(len(nr_of_entries_in_shortcut))
        raise ValueError('this number of shortcut zones is wrong')

    # write all nr of entries
    for nr in nr_of_entries_in_shortcut:
        if nr > 300:
            raise ValueError(nr)
        output_file.write(pack('!H', nr))

    # write  Address of first Polygon_nr  in shortcut field (x,y)
    # Attention: 0 is written when no entries are in this shortcut
    shortcut_address = output_file.tell() + 259200 * NR_SHORTCUTS_PER_LNG * NR_SHORTCUTS_PER_LAT
    for nr in nr_of_entries_in_shortcut:
        if nr == 0:
            output_file.write(pack('!I', 0))
        else:
            output_file.write(pack('!I', shortcut_address))
            # each polygon takes up 2 bytes of space
            shortcut_address += 2 * nr

    # write Line_Nrs for every shortcut
    for entries in shortcut_entries:
        for entry in entries:
            if entry > nr_of_lines:
                raise ValueError(entry)
            output_file.write(pack('!H', entry))

    print('Success!')
    return


"""
Data format in the .bin:
IMPORTANT: all coordinates multiplied by 10**15 (to store them as longs/ints not floats, because floats arithmetic
are slower)

no of rows (= no of polygons = no of boundaries)
approx. 28k -> use 2byte unsigned short (has range until 65k)
'!H' = n


I Address of Shortcut area (end of polygons+1) @ 2

'!H'  n times [H unsigned short: zone number=ID in this line, @ 6 + 2* lineNr]

'!H'  n times [H unsigned short: nr of values (coordinate PAIRS! x,y in long long) in this line, @ 6 + 4* lineNr]

'!I'n times [ I unsigned int: absolute address of the byte where the polygon-data of that line starts,
@ 6 + 4 * n +  4*lineNr]



n times 4 long longs: xmax, xmin, ymax, ymin  @ 6 + 8n
'!qqqq'



(for all lines: x coords, y coords:)   @ Address see above
'!q'


56700 times H   number of entries in shortcut field (x,y)  @ Pointer see above


X times I   Address of first Polygon_nr  in shortcut field (x,y)  @ 56700 + Pointer see above


X times H  Polygon_Nr     @Pointer see one above

"""

if __name__ == '__main__':
    convert_csv()

    # Don't change this setup or timezonefinder wont work!
    # different setups of shortcuts are not supported, because then addresses in the .bin
    # would need to be calculated depending on how many shortcuts are being used.

    # set the number of shortcuts created per longitude
    NR_SHORTCUTS_PER_LNG = 1
    # shortcuts per latitude
    NR_SHORTCUTS_PER_LAT = 2
    compile_into_binary(path='timezone_data.bin')
