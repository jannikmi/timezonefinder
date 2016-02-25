from cmath import phase
from math import radians, cos, sin, asin, sqrt, floor, degrees, ceil
from struct import unpack
from numpy import fromfile, empty, array
from numba import jit

# maps the timezone ids to their name
time_zone_names = {
    1: "Europe/Andorra",
    2: "Asia/Dubai",
    3: "Asia/Kabul",
    4: "America/Antigua",
    5: "America/Anguilla",
    6: "Europe/Tirane",
    7: "Asia/Yerevan",
    8: "Africa/Luanda",
    9: "Antarctica/McMurdo",
    10: "Antarctica/Rothera",
    11: "Antarctica/Palmer",
    12: "Antarctica/Mawson",
    13: "Antarctica/Davis",
    14: "Antarctica/Casey",
    15: "Antarctica/Vostok",
    16: "Antarctica/DumontDUrville",
    17: "Antarctica/Syowa",
    18: "Antarctica/Troll",
    19: "America/Argentina/Buenos_Aires",
    20: "America/Argentina/Cordoba",
    21: "America/Argentina/Salta",
    22: "America/Argentina/Jujuy",
    23: "America/Argentina/Tucuman",
    24: "America/Argentina/Catamarca",
    25: "America/Argentina/La_Rioja",
    26: "America/Argentina/San_Juan",
    27: "America/Argentina/Mendoza",
    28: "America/Argentina/San_Luis",
    29: "America/Argentina/Rio_Gallegos",
    30: "America/Argentina/Ushuaia",
    31: "Pacific/Pago_Pago",
    32: "Europe/Vienna",
    33: "Australia/Lord_Howe",
    34: "Antarctica/Macquarie",
    35: "Australia/Hobart",
    36: "Australia/Currie",
    37: "Australia/Melbourne",
    39: "Australia/Broken_Hill",
    40: "Australia/Brisbane",
    41: "Australia/Lindeman",
    42: "Australia/Adelaide",
    43: "Australia/Darwin",
    44: "Australia/Perth",
    45: "Australia/Eucla",
    46: "America/Aruba",
    47: "Europe/Mariehamn",
    48: "Asia/Baku",
    49: "Europe/Sarajevo",
    50: "America/Barbados",
    51: "Asia/Dhaka",
    52: "Europe/Brussels",
    53: "Africa/Ouagadougou",
    54: "Europe/Sofia",
    55: "Asia/Bahrain",
    56: "Africa/Bujumbura",
    57: "Africa/Porto-Novo",
    58: "America/St_Barthelemy",
    59: "Atlantic/Bermuda",
    60: "Asia/Brunei",
    61: "America/La_Paz",
    62: "America/Kralendijk",
    63: "America/Noronha",
    64: "America/Belem",
    65: "America/Fortaleza",
    66: "America/Recife",
    67: "America/Araguaina",
    68: "America/Maceio",
    69: "America/Bahia",
    70: "America/Sao_Paulo",
    71: "America/Campo_Grande",
    72: "America/Cuiaba",
    73: "America/Santarem",
    74: "America/Porto_Velho",
    75: "America/Boa_Vista",
    76: "America/Manaus",
    77: "America/Eirunepe",
    78: "America/Rio_Branco",
    79: "America/Nassau",
    80: "Asia/Thimphu",
    81: "Africa/Gaborone",
    82: "Europe/Minsk",
    83: "America/Belize",
    84: "America/St_Johns",
    85: "America/Halifax",
    86: "America/Glace_Bay",
    87: "America/Moncton",
    88: "America/Goose_Bay",
    89: "America/Blanc-Sablon",
    90: "America/Toronto",
    91: "America/Nipigon",
    92: "America/Thunder_Bay",
    93: "America/Iqaluit",
    94: "America/Pangnirtung",
    95: "America/Resolute",
    96: "America/Atikokan",
    97: "America/Rankin_Inlet",
    98: "America/Winnipeg",
    99: "America/Rainy_River",
    100: "America/Regina",
    101: "America/Swift_Current",
    102: "America/Edmonton",
    103: "America/Cambridge_Bay",
    104: "America/Yellowknife",
    105: "America/Inuvik",
    106: "America/Creston",
    107: "America/Dawson_Creek",
    108: "America/Fort_Nelson",
    109: "America/Vancouver",
    110: "America/Whitehorse",
    111: "America/Dawson",
    112: "Indian/Cocos",
    113: "Africa/Kinshasa",
    114: "Africa/Lubumbashi",
    115: "Africa/Bangui",
    116: "Africa/Brazzaville",
    117: "Europe/Zurich",
    118: "Africa/Abidjan",
    119: "Pacific/Rarotonga",
    120: "America/Santiago",
    121: "Pacific/Easter",
    122: "Africa/Douala",
    123: "Asia/Shanghai",
    124: "Asia/Urumqi",
    125: "America/Bogota",
    126: "America/Costa_Rica",
    127: "America/Havana",
    128: "Atlantic/Cape_Verde",
    129: "America/Curacao",
    130: "Indian/Christmas",
    131: "Asia/Nicosia",
    132: "Europe/Prague",
    133: "Europe/Berlin",
    134: "Europe/Busingen",
    135: "Africa/Djibouti",
    136: "Europe/Copenhagen",
    137: "America/Dominica",
    138: "America/Santo_Domingo",
    139: "Africa/Algiers",
    140: "America/Guayaquil",
    141: "Pacific/Galapagos",
    142: "Europe/Tallinn",
    143: "Africa/Cairo",
    144: "Africa/El_Aaiun",
    145: "Africa/Asmara",
    146: "Europe/Madrid",
    147: "Africa/Ceuta",
    148: "Atlantic/Canary",
    149: "Africa/Addis_Ababa",
    150: "Europe/Helsinki",
    151: "Pacific/Fiji",
    152: "Atlantic/Stanley",
    153: "Pacific/Chuuk",
    154: "Pacific/Pohnpei",
    155: "Pacific/Kosrae",
    156: "Atlantic/Faroe",
    157: "Europe/Paris",
    158: "Africa/Libreville",
    159: "Europe/London",
    160: "America/Grenada",
    161: "Asia/Tbilisi",
    162: "America/Cayenne",
    163: "Europe/Guernsey",
    164: "Africa/Accra",
    165: "Europe/Gibraltar",
    166: "America/Godthab",
    167: "America/Danmarkshavn",
    168: "America/Scoresbysund",
    169: "America/Thule",
    170: "Africa/Banjul",
    171: "Africa/Conakry",
    172: "America/Guadeloupe",
    173: "Africa/Malabo",
    174: "Europe/Athens",
    175: "Atlantic/South_Georgia",
    176: "America/Guatemala",
    177: "Pacific/Guam",
    178: "Africa/Bissau",
    179: "America/Guyana",
    180: "Asia/Hong_Kong",
    181: "America/Tegucigalpa",
    182: "Europe/Zagreb",
    183: "America/Port-au-Prince",
    184: "Europe/Budapest",
    185: "Asia/Jakarta",
    186: "Asia/Pontianak",
    187: "Asia/Makassar",
    188: "Asia/Jayapura",
    189: "Europe/Dublin",
    190: "Asia/Jerusalem",
    191: "Europe/Isle_of_Man",
    192: "Asia/Kolkata",
    193: "Indian/Chagos",
    194: "Asia/Baghdad",
    195: "Asia/Tehran",
    196: "Atlantic/Reykjavik",
    197: "Europe/Rome",
    198: "Europe/Jersey",
    199: "America/Jamaica",
    200: "Asia/Amman",
    201: "Asia/Tokyo",
    202: "Africa/Nairobi",
    203: "Asia/Bishkek",
    204: "Asia/Phnom_Penh",
    205: "Pacific/Tarawa",
    206: "Pacific/Enderbury",
    207: "Pacific/Kiritimati",
    208: "Indian/Comoro",
    209: "America/St_Kitts",
    210: "Asia/Pyongyang",
    211: "Asia/Seoul",
    212: "Asia/Kuwait",
    213: "America/Cayman",
    214: "Asia/Almaty",
    215: "Asia/Qyzylorda",
    216: "Asia/Aqtobe",
    217: "Asia/Aqtau",
    218: "Asia/Oral",
    219: "Asia/Vientiane",
    220: "Asia/Beirut",
    221: "America/St_Lucia",
    222: "Europe/Vaduz",
    223: "Asia/Colombo",
    224: "Africa/Monrovia",
    225: "Africa/Maseru",
    226: "Europe/Vilnius",
    227: "Europe/Luxembourg",
    228: "Europe/Riga",
    229: "Africa/Tripoli",
    230: "Africa/Casablanca",
    231: "Europe/Monaco",
    232: "Europe/Chisinau",
    233: "Europe/Podgorica",
    234: "America/Marigot",
    235: "Indian/Antananarivo",
    236: "Pacific/Majuro",
    237: "Pacific/Kwajalein",
    238: "Europe/Skopje",
    239: "Africa/Bamako",
    240: "Asia/Rangoon",
    241: "Asia/Ulaanbaatar",
    242: "Asia/Hovd",
    243: "Asia/Choibalsan",
    244: "Asia/Macau",
    245: "Pacific/Saipan",
    246: "America/Martinique",
    247: "Africa/Nouakchott",
    248: "America/Montserrat",
    249: "Europe/Malta",
    250: "Indian/Mauritius",
    251: "Indian/Maldives",
    252: "Africa/Blantyre",
    253: "America/Mexico_City",
    254: "America/Cancun",
    255: "America/Merida",
    256: "America/Monterrey",
    257: "America/Matamoros",
    258: "America/Mazatlan",
    259: "America/Chihuahua",
    260: "America/Ojinaga",
    261: "America/Hermosillo",
    262: "America/Tijuana",
    263: "America/Santa_Isabel",
    264: "America/Bahia_Banderas",
    265: "Asia/Kuala_Lumpur",
    266: "Asia/Kuching",
    267: "Africa/Maputo",
    268: "Africa/Windhoek",
    269: "Pacific/Noumea",
    270: "Africa/Niamey",
    271: "Pacific/Norfolk",
    272: "Africa/Lagos",
    273: "America/Managua",
    274: "Europe/Amsterdam",
    275: "Europe/Oslo",
    276: "Asia/Kathmandu",
    277: "Pacific/Nauru",
    278: "Pacific/Niue",
    279: "Pacific/Auckland",
    280: "Pacific/Chatham",
    281: "Asia/Muscat",
    282: "America/Panama",
    283: "America/Lima",
    284: "Pacific/Tahiti",
    285: "Pacific/Marquesas",
    286: "Pacific/Gambier",
    287: "Pacific/Port_Moresby",
    288: "Pacific/Bougainville",
    289: "Asia/Manila",
    290: "Asia/Karachi",
    291: "Europe/Warsaw",
    292: "America/Miquelon",
    293: "Pacific/Pitcairn",
    294: "America/Puerto_Rico",
    295: "Asia/Gaza",
    296: "Asia/Hebron",
    297: "Europe/Lisbon",
    298: "Atlantic/Madeira",
    299: "Atlantic/Azores",
    300: "Pacific/Palau",
    301: "America/Asuncion",
    302: "Asia/Qatar",
    303: "Indian/Reunion",
    304: "Europe/Bucharest",
    305: "Europe/Belgrade",
    306: "Europe/Kaliningrad",
    307: "Europe/Moscow",
    308: "Europe/Simferopol",
    309: "Europe/Volgograd",
    310: "Europe/Samara",
    311: "Asia/Yekaterinburg",
    312: "Asia/Omsk",
    313: "Asia/Novosibirsk",
    314: "Asia/Novokuznetsk",
    315: "Asia/Krasnoyarsk",
    316: "Asia/Irkutsk",
    317: "Asia/Chita",
    318: "Asia/Yakutsk",
    319: "Asia/Khandyga",
    320: "Asia/Vladivostok",
    321: "Asia/Sakhalin",
    322: "Asia/Ust-Nera",
    323: "Asia/Magadan",
    324: "Asia/Srednekolymsk",
    325: "Asia/Kamchatka",
    326: "Asia/Anadyr",
    327: "Africa/Kigali",
    328: "Asia/Riyadh",
    329: "Pacific/Guadalcanal",
    330: "Indian/Mahe",
    331: "Africa/Khartoum",
    332: "Europe/Stockholm",
    333: "Asia/Singapore",
    334: "Atlantic/St_Helena",
    335: "Europe/Ljubljana",
    336: "Arctic/Longyearbyen",
    337: "Europe/Bratislava",
    338: "Africa/Freetown",
    339: "Europe/San_Marino",
    340: "Africa/Dakar",
    341: "Africa/Mogadishu",
    342: "America/Paramaribo",
    343: "Africa/Juba",
    344: "Africa/Sao_Tome",
    345: "America/El_Salvador",
    346: "America/Lower_Princes",
    347: "Asia/Damascus",
    348: "Africa/Mbabane",
    349: "America/Grand_Turk",
    350: "Africa/Ndjamena",
    351: "Indian/Kerguelen",
    352: "Africa/Lome",
    353: "Asia/Bangkok",
    354: "Asia/Dushanbe",
    355: "Pacific/Fakaofo",
    356: "Asia/Dili",
    357: "Asia/Ashgabat",
    358: "Africa/Tunis",
    359: "Pacific/Tongatapu",
    360: "Europe/Istanbul",
    361: "America/Port_of_Spain",
    362: "Pacific/Funafuti",
    363: "Asia/Taipei",
    364: "Africa/Dar_es_Salaam",
    365: "Europe/Kiev",
    366: "Europe/Uzhgorod",
    367: "Europe/Zaporozhye",
    368: "Africa/Kampala",
    369: "Pacific/Johnston",
    370: "Pacific/Midway",
    371: "Pacific/Wake",
    372: "America/New_York",
    373: "America/Detroit",
    374: "America/Kentucky/Louisville",
    375: "America/Kentucky/Monticello",
    376: "America/Indiana/Indianapolis",
    377: "America/Indiana/Vincennes",
    378: "America/Indiana/Winamac",
    379: "America/Indiana/Marengo",
    380: "America/Indiana/Petersburg",
    381: "America/Indiana/Vevay",
    382: "America/Chicago",
    383: "America/Indiana/Tell_City",
    384: "America/Indiana/Knox",
    385: "America/Menominee",
    386: "America/North_Dakota/Center",
    387: "America/North_Dakota/New_Salem",
    388: "America/North_Dakota/Beulah",
    389: "America/Denver",
    390: "America/Boise",
    391: "America/Phoenix",
    392: "America/Los_Angeles",
    393: "America/Metlakatla",
    394: "America/Anchorage",
    395: "America/Juneau",
    396: "America/Sitka",
    397: "America/Yakutat",
    398: "America/Nome",
    399: "America/Adak",
    400: "Pacific/Honolulu",
    401: "America/Montevideo",
    402: "Asia/Samarkand",
    403: "Asia/Tashkent",
    404: "Europe/Vatican",
    405: "America/St_Vincent",
    406: "America/Caracas",
    407: "America/Tortola",
    408: "America/St_Thomas",
    409: "Asia/Ho_Chi_Minh",
    410: "Pacific/Efate",
    411: "Pacific/Wallis",
    412: "Pacific/Apia",
    413: "Asia/Aden",
    414: "Indian/Mayotte",
    415: "Africa/Johannesburg",
    416: "Africa/Lusaka",
    417: "Africa/Harare",
    418: 'Asia/Kashgar',
    419: 'America/Montreal',
    420: 'Asia/Harbin',
    421: 'America/Coral_Harbour',
    422: 'uninhabited',
    423: 'Australia/Sydney',
    424: 'Asia/Chongqing',
}


# @profile
@jit('b1(i8,i8,i8[:,:])', nopython=True, cache=True)
def inside_polygon(x, y, coords):
    wn = 0
    i = 0
    y1 = coords[1][0]
    for y2 in coords[1]:
        if y1 < y:
            if y2 >= y:
                x1 = coords[0][i - 1]
                x2 = coords[0][i]
                """tests if a point is Left|On|Right of an infinite line from p1 to p2
                //    Return: >0 for xy left of the line from! p1 to! p2
                //            =0 for xy on the line
                            <0 for xy  right of the line
                """
                if ((x2 - x1) / 1000) * ((y - y1) / 1000) - ((x - x1) / 1000) * ((y2 - y1) / 1000) > 0:
                    wn += 1

        else:
            if y2 < y:
                x1 = coords[0][i - 1]
                x2 = coords[0][i]
                if ((x2 - x1) / 1000) * ((y - y1) / 1000) - ((x - x1) / 1000) * ((y2 - y1) / 1000) < 0:
                    wn -= 1

        y1 = y2
        i += 1

    y1 = coords[1][-1]
    y2 = coords[1][0]
    if y1 < y:
        if y2 >= y:
            x1 = coords[0][-1]
            x2 = coords[0][0]
            if ((x2 - x1) / 1000) * ((y - y1) / 1000) - ((x - x1) / 1000) * ((y2 - y1) / 1000) > 0:
                wn += 1
    else:
        if y2 < y:
            x1 = coords[0][-1]
            x2 = coords[0][0]
            if ((x2 - x1) / 1000) * ((y - y1) / 1000) - ((x - x1) / 1000) * ((y2 - y1) / 1000) < 0:
                wn -= 1
    return wn != 0


@jit(nopython=True, cache=True)
def cartesian_to_radlng(x, y):
    return phase(complex(x, y))


@jit(nopython=True, cache=True)
def cartesian2rad(x, y, z):
    return phase(complex(x, y)), asin(z)


@jit(nopython=True, cache=True)
def cartesian2coords(x, y, z):
    return degrees(phase(complex(x, y))), degrees(asin(z))


@jit(nopython=True, cache=True)
def x_rotation(rad, point):
    # x stays the same
    sin_deg = sin(rad)
    cos_deg = cos(rad)
    return point[0], point[1] * cos_deg + point[2] * sin_deg, -point[1] * sin_deg + point[2] * cos_deg


@jit(nopython=True, cache=True)
def y_rotation(degree, point):
    # y stays the same
    degree = radians(-degree)
    sin_deg = sin(degree)
    cos_deg = cos(degree)
    return point[0] * cos_deg + -point[2] * sin_deg, point[1], point[0] * sin_deg + point[2] * cos_deg


@jit(nopython=True, cache=True)
def z_rotation(degree, point):
    # z stays the same
    degree = radians(degree)
    sin_deg = sin(degree)
    cos_deg = cos(degree)
    return point[0] * cos_deg + point[1] * sin_deg, -point[0] * sin_deg + point[1] * cos_deg, point[2]


@jit(nopython=True, cache=True)
def coords2cartesian(lng, lat):
    lng = radians(lng)
    lat = radians(lat)
    return cos(lng) * cos(lat), sin(lng) * cos(lat), sin(lat)


@jit(nopython=True, cache=True)
def distance_to_origin(lng_rad, lat_rad):
    """
    :param lng_rad: the longitude of the point in radians
    :param lat_rad: the latitude
    :return: distance between the point and the origin (0,0) in radians
    """
    return 2 * asin(sqrt(sin(lat_rad / 2) ** 2 + cos(lat_rad) * sin(lng_rad / 2) ** 2))


@jit(nopython=True, cache=True)
def distance_to_point_on_equator(lng_rad, lat_rad, lng_rad_p1):
    """
    :param lng_rad: the longitude of the point in radians
    :param lat_rad: the latitude of the point
    :param lng_rad_p1: the latitude of the point
    :return: distance between the point and p1 (lng_rad,0) in radians
    """
    return 2 * asin(sqrt((sin(lat_rad) / 2) ** 2 + cos(lat_rad) * sin((lng_rad - lng_rad_p1) / 2) ** 2))


@jit(nopython=True, cache=True)
def haversine_rad(lng_p1, lat_p1, lng_p2, lat_p2):
    """
    :param lng_p1: the longitude of point 1 in radians
    :param lat_p1: the latitude of point 1 in radians
    :param lng_p2: the longitude of point 1 in radians
    :param lat_p2: the latitude of point 1 in radians
    :return: distance between p1 and p2 in radians
    """
    return 2 * asin(sqrt(sin((lat_p1 - lat_p2) / 2) ** 2 + cos(lat_p2) * cos(lat_p1) * sin((lng_p1 - lng_p2) / 2) ** 2))


@jit(nopython=True, cache=True)
def compute_min_distance(px_cartesian, p0, pm1_cartesian, p1_cartesian):
    """
    :param px_cartesian: given in (x,y,z)
    :param p0: point from the polygon between p1 and pm1 given in (lng,lat) degree
    :param pm1_cartesian: point after p0 given in (x,y,z)
    :param p1_cartesian: point before p0 given in (x,y,z)
    :return: shortest distance between pX and the polygon section (pm1---p0---p1) in radians
    """
    # rotate coordinate system (= all the points) so that point 0 would have lat=lng=0 (=origin)
    px_cartesian = z_rotation(p0[0], px_cartesian)
    p1_cartesian = z_rotation(p0[0], p1_cartesian)
    pm1_cartesian = z_rotation(p0[0], pm1_cartesian)

    px_cartesian = y_rotation(p0[1], px_cartesian)
    p1_cartesian = y_rotation(p0[1], p1_cartesian)
    pm1_cartesian = y_rotation(p0[1], pm1_cartesian)

    # for both p1 and pm1 separately do:

    # rotate coordinate system so that this point also has lat=0 (point 0 does not change)
    rotation_rad = phase(complex(p1_cartesian[1], p1_cartesian[2]))
    p1_cartesian = x_rotation(rotation_rad, p1_cartesian)
    lng_p1_rad = cartesian_to_radlng(p1_cartesian[0], p1_cartesian[1])
    px_cartesian_temp = x_rotation(rotation_rad, px_cartesian)
    p_x_retrans_rad = cartesian2rad(*px_cartesian_temp)

    # if the point is not between p0 and p1 return the distance to the closest of the two points
    if p_x_retrans_rad[0] <= 0:
        # store the distance between p0=(0,0) and px
        temp_distance = distance_to_origin(p_x_retrans_rad[0], p_x_retrans_rad[1])
    elif p_x_retrans_rad[0] >= lng_p1_rad:
        # return the distance between p1=(longitude,0) and px
        temp_distance = distance_to_point_on_equator(p_x_retrans_rad[0], p_x_retrans_rad[1], lng_p1_rad)

    else:
        # lng of point X is between 0 (<-point1) and lng of point 2:
        # the distance between point x and the 'equator' is the shortest
        temp_distance = abs(p_x_retrans_rad[1])

    # ATTENTION: vars are being reused. p1 is actually pm1 here!
    rotation_rad = phase(complex(pm1_cartesian[1], pm1_cartesian[2]))
    p1_cartesian = x_rotation(rotation_rad, pm1_cartesian)
    lng_p1_rad = cartesian_to_radlng(p1_cartesian[0], p1_cartesian[1])
    px_cartesian_temp = x_rotation(rotation_rad, px_cartesian)
    p_x_retrans_rad = cartesian2rad(*px_cartesian_temp)

    if p_x_retrans_rad[0] <= 0:
        return min(temp_distance, distance_to_origin(p_x_retrans_rad[0], p_x_retrans_rad[1]))
    elif p_x_retrans_rad[0] >= lng_p1_rad:
        return min(temp_distance, distance_to_point_on_equator(p_x_retrans_rad[0], p_x_retrans_rad[1], lng_p1_rad))
    return min(temp_distance, abs(p_x_retrans_rad[1]))


@jit('f8(i8)', nopython=True, cache=True)
def long2coord(longlong):
    return float(longlong / 10 ** 15)


@jit('i8(f8)', nopython=True, cache=True)
def coord2long(double):
    return int(double * 10 ** 15)


@jit(nopython=True, cache=True)
def surrounding_shortcuts(central_x_shortcut=0, central_y_shortcut=0):
    # return the surrounding shortcuts
    shortcuts = []
    top = central_y_shortcut - 1

    bottom = central_y_shortcut + 1
    right = central_x_shortcut + 1
    left = central_x_shortcut - 1
    for x in range(left, right + 1, 1):
        shortcuts.append((x, top))
        shortcuts.append((x, bottom))

    for y in range(central_y_shortcut, bottom, 1):
        shortcuts.append((left, y))
        shortcuts.append((right, y))

    return shortcuts


# @jit('f8(float64[:], int64, i8[:, :])', nopython=True, cache=True)
@jit(nopython=True, cache=True)
def distance_to_polygon(lng, lat, px_cartesian, nr_points, points, trans_points):
    # max possible is pi = 3.14...
    min_distance = 4

    # transform all points (long long) to coords
    for i in range(nr_points):
        trans_points[0][i] = long2coord(points[0][i])
        trans_points[1][i] = long2coord(points[1][i])

    # only check the points which actually face the point (all the others cannot be closer anyway).
    # therefore find the most extreme points
    min_phase = 3.2
    max_phase = -3.2
    extreme_p1 = 0
    extreme_p2 = 0
    for i in range(nr_points):
        ph = phase(complex(trans_points[0][i] - lng, trans_points[1][i] - lat))
        if ph > max_phase:
            max_phase = ph
            extreme_p1 = i
        if ph < min_phase:
            min_phase = ph
            extreme_p2 = i

    if extreme_p1 > extreme_p2:
        min_point = extreme_p2
        max_point = extreme_p1
    else:
        min_point = extreme_p1
        max_point = extreme_p2

    # find out in which direction to go
    # since polygons don't overlap simply test the two closest points of one extreme point
    adr1 = (max_point - 1) % nr_points
    adr2 = (max_point + 1) % nr_points
    if haversine_rad(lng, lat, trans_points[0][adr1], trans_points[1][adr1]) \
            < haversine_rad(lng, lat, trans_points[0][adr2], trans_points[1][adr2]):
        # the point before the maximum point was closer than the one after it.
        # direction is  [... | min_point| ... |<-- -1 --|max_point | ..]
        backward = True
        step = -2

    else:
        # direction is  [ -- +1 -->| ...| min_point| ...  |max_point | --> ..]
        backward = False
        step = 2

    pm1_cartesian = coords2cartesian(trans_points[0][max_point], trans_points[1][max_point])
    if backward:
        index_p1 = (max_point - 2) % nr_points
        index_p0 = (max_point - 1) % nr_points
        steps_to_make = int(ceil((max_point - min_point) / 2))

    else:
        index_p1 = (max_point + 2) % nr_points
        index_p0 = (max_point + 1) % nr_points
        steps_to_make = int(ceil((abs(nr_points - max_point + min_point)) / 2))

    for i in range(steps_to_make):
        p0 = trans_points[0][index_p0], trans_points[1][index_p0]
        p1_cartesian = coords2cartesian(trans_points[0][index_p1], trans_points[1][index_p1])

        distance = compute_min_distance(px_cartesian, p0, pm1_cartesian, p1_cartesian)
        if distance < min_distance:
            min_distance = distance

        index_p0 = (index_p0 + step) % nr_points
        index_p1 = (index_p1 + step) % nr_points
        pm1_cartesian = p1_cartesian

    return min_distance


class TimezoneFinder:
    """
    This class lets you quickly find the timezone of a point on earth.
    It keeps the binary file with the data open in reading mode to enable fast consequent access.
    In the file currently used there are two shortcuts stored per degree of latitude and one per degree of longitude
    (tests evaluated this to be the fastest setup)
    """

    def __init__(self):

        path = 'timezone_data.bin'
        # open the file in binary reading mode
        self.binary_file = open(path, 'rb')
        # read the first 2byte int (= number of polygons stored in the .bin)
        self.nr_of_entries = unpack('!H', self.binary_file.read(2))[0]

        # set addresses
        # the address where the shortcut section starts (after all the polygons) this is 34 433 054
        self.shortcuts_start = unpack('!I', self.binary_file.read(4))[0]

        self.nr_val_start_address = 2 * self.nr_of_entries + 6
        self.adr_start_address = 4 * self.nr_of_entries + 6
        self.bound_start_address = 8 * self.nr_of_entries + 6
        self.poly_start_address = 40 * self.nr_of_entries + 6
        self.first_shortcut_address = self.shortcuts_start + 259200

    def __del__(self):
        self.binary_file.close()

    def id_of(self, line=0):
        # ids start at address 6. per line one unsigned 2byte int is used
        self.binary_file.seek((6 + 2 * line))
        return unpack('!H', self.binary_file.read(2))[0]

    def ids_of(self, iterable):

        id_array = empty(shape=len(iterable), dtype='>i1')

        i = 0
        for line_nr in iterable:
            self.binary_file.seek((6 + 2 * line_nr))
            id_array[i] = unpack('!H', self.binary_file.read(2))[0]
            i += 1

        return id_array

    # @profile
    def shortcuts_of(self, lng=0.0, lat=0.0):
        # convert coords into shortcut
        x = int(floor((lng + 180)))
        y = int(floor((90 - lat) * 2))

        # get the address of the first entry in this shortcut
        # offset: 180 * number of shortcuts per lat degree * 2bytes = entries per column of x shortcuts
        # shortcuts are stored: (0,0) (0,1) (0,2)... (1,0)...
        self.binary_file.seek(self.shortcuts_start + 720 * x + 2 * y)

        nr_of_polygons = unpack('!H', self.binary_file.read(2))[0]

        self.binary_file.seek(self.first_shortcut_address + 1440 * x + 4 * y)
        self.binary_file.seek(unpack('!I', self.binary_file.read(4))[0])
        return fromfile(self.binary_file, dtype='>u2', count=nr_of_polygons)

    def polygons_of_shortcut(self, x=0, y=0):
        # get the address of the first entry in this shortcut
        # offset: 180 * number of shortcuts per lat degree * 2bytes = entries per column of x shortcuts
        # shortcuts are stored: (0,0) (0,1) (0,2)... (1,0)...
        self.binary_file.seek(self.shortcuts_start + 720 * x + 2 * y)

        nr_of_polygons = unpack('!H', self.binary_file.read(2))[0]

        self.binary_file.seek(self.first_shortcut_address + 1440 * x + 4 * y)
        self.binary_file.seek(unpack('!I', self.binary_file.read(4))[0])
        return fromfile(self.binary_file, dtype='>u2', count=nr_of_polygons)

    def coords_of(self, line=0):
        self.binary_file.seek((self.nr_val_start_address + 2 * line))
        nr_of_values = unpack('!H', self.binary_file.read(2))[0]

        self.binary_file.seek((self.adr_start_address + 4 * line))
        self.binary_file.seek(unpack('!I', self.binary_file.read(4))[0])

        return array([fromfile(self.binary_file, dtype='>i8', count=nr_of_values),
                      fromfile(self.binary_file, dtype='>i8', count=nr_of_values)])

    # @profile
    def closest_timezone_at(self, lng, lat):
        """
        This function searches for the closest polygon just in the actual and the surrounding shortcuts.
        Make sure that the point does not lie within a polygon (for that case the algorithm is simply wrong!)
        This is feature still experimental.
        :param lng: longitude of the point in degree
        :param lat: latitude in degree
        :return: the timezone name of the closest found polygon or None
        """

        # the maximum possible distance is pi = 3.14...
        min_distance = 4
        # transform point X into cartesian coordinates
        px_cartesian = coords2cartesian(lng, lat)
        current_closest_id = None
        central_x_shortcut = int(floor((lng + 180)))
        central_y_shortcut = int(floor((90 - lat) * 2))

        polygon_nrs = list(self.polygons_of_shortcut(central_x_shortcut, central_y_shortcut))

        # also select the polygons from the surrounding shortcuts
        for sh in surrounding_shortcuts(central_x_shortcut, central_y_shortcut):
            # TODO make algorithm work when closest polygon is on the 'other end of earth'
            if sh[0] <= 360 and sh[1] <= 360:
                for p in self.polygons_of_shortcut(*sh):
                    if p not in polygon_nrs:
                        polygon_nrs.append(p)

        polygons_in_list = len(polygon_nrs)

        if polygons_in_list == 0:
            return None

        # initialize the list of ids
        ids = [self.id_of(x) for x in polygon_nrs]

        # if all the polygons in this shortcut belong to the same zone return it
        first_entry = ids[0]
        if ids.count(first_entry) == polygons_in_list:
            return time_zone_names[first_entry]

        # stores which polygons have been checked yet
        already_checked = [False for i in range(polygons_in_list)]

        pointer = 0
        polygons_checked = 0

        while polygons_checked < polygons_in_list:

            # only check a polygon when its id is not the closest a the moment!
            if already_checked[pointer] or ids[pointer] == current_closest_id:
                # go to the next polygon
                polygons_checked += 1

            else:
                # this polygon has to be checked
                coords = self.coords_of(polygon_nrs[pointer])
                nr_points = len(coords[0])
                empty_array = empty([nr_points, 2], dtype='f8')
                distance = distance_to_polygon(lng, lat, px_cartesian, nr_points, coords, empty_array)

                already_checked[pointer] = True
                if distance < min_distance:
                    min_distance = distance
                    current_closest_id = ids[pointer]
                    # whole list has to be searched again!
                    polygons_checked = 1
            pointer = (pointer + 1) % polygons_in_list

        # the the whole list has been searched
        return time_zone_names[current_closest_id]

    # @profile
    def timezone_at(self, lng=0.0, lat=0.0):
        """
        this function looks up in which polygons the point could be included
        to speed things up there are shortcuts being used (stored in the binary file)
        especially for large polygons it is expensive to check if a point is really included,
        so certain simplifications are made and even when you get a hit the point might actually
        not be inside the polygon (for example when there is only one timezone nearby)
        if you want to make sure a point is really inside a timezone use 'certain_timezone_at'
        :param lng: longitude of the point in degree (-180 to 180)
        :param lat: latitude in degree (90 to -90)
        :return: the timezone name of the matching polygon or None
        """

        possible_polygons = self.shortcuts_of(lng, lat)

        # x = longitude  y = latitude  both converted to 8byte int
        x = coord2long(lng)
        y = coord2long(lat)

        nr_possible_polygons = len(possible_polygons)

        if nr_possible_polygons == 0:
            return None

        if nr_possible_polygons == 1:
            return time_zone_names[self.id_of(possible_polygons[0])]

        # initialize the list of ids
        ids = [self.id_of(p) for p in possible_polygons]

        # if all the polygons belong to the same zone return it
        first_entry = ids[0]
        if ids.count(first_entry) == nr_possible_polygons:
            return time_zone_names[first_entry]

        for i in range(nr_possible_polygons):
            polygon_nr = possible_polygons[i]

            # get boundaries
            self.binary_file.seek((self.bound_start_address + 32 * polygon_nr), )
            boundaries = fromfile(self.binary_file, dtype='>i8', count=4)
            if not (x > boundaries[0] or x < boundaries[1] or y > boundaries[2] or y < boundaries[3]):
                if inside_polygon(x, y, self.coords_of(line=polygon_nr)):
                    return time_zone_names[ids[i]]
        return None

    def certain_timezone_at(self, lng=0.0, lat=0.0):
        """
        this function looks up in which polygon the point certainly is included
        this is much slower than 'timezone_at'!
        :param lng: longitude of the point in degree
        :param lat: latitude in degree
        :return: the timezone name of the polygon the point is included in or None
        """

        possible_polygons = self.shortcuts_of(lng, lat)

        # x = longitude  y = latitude  both converted to 8byte int
        x = coord2long(lng)
        y = coord2long(lat)

        for polygon_nr in possible_polygons:
            # get boundaries
            self.binary_file.seek((self.bound_start_address + 32 * polygon_nr), )
            boundaries = fromfile(self.binary_file, dtype='>i8', count=4)
            if not (x > boundaries[0] or x < boundaries[1] or y > boundaries[2] or y < boundaries[3]):
                if inside_polygon(x, y, self.coords_of(line=polygon_nr)):
                    return time_zone_names[self.id_of(polygon_nr)]
        return None
