from math import radians, cos, sin, asin, sqrt, floor, degrees, ceil, atan2
from struct import unpack
from numpy import fromfile, empty, array
from os.path import join, dirname

# from numba import jit

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


# @jit('b1(i8,i8,i8[:,:])', nopython=True, cache=True)
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
                everything has to be divided by 1000 because otherwise there would be overflow with int8
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


# @jit(nopython=True, cache=True)
def cartesian2rad(x, y, z):
    return atan2(y, x), asin(z)


# @jit(nopython=True, cache=True)
def cartesian2coords(x, y, z):
    return degrees(atan2(y, x)), degrees(asin(z))


# @jit(nopython=True, cache=True)
def x_rotate(rad, point):
    # Attention: this rotation uses radians!
    # x stays the same
    sin_rad = sin(rad)
    cos_rad = cos(rad)
    return point[0], point[1] * cos_rad + point[2] * sin_rad, point[2] * cos_rad - point[1] * sin_rad


# @jit(nopython=True, cache=True)
def y_rotate(degree, point):
    # y stays the same
    degree = radians(-degree)
    sin_rad = sin(degree)
    cos_rad = cos(degree)
    return point[0] * cos_rad - point[2] * sin_rad, point[1], point[0] * sin_rad + point[2] * cos_rad


# @jit(nopython=True, cache=True)
def coords2cartesian(lng, lat):
    lng = radians(lng)
    lat = radians(lat)
    return cos(lng) * cos(lat), sin(lng) * cos(lat), sin(lat)


# @jit(nopython=True, cache=True)
def distance_to_point_on_equator(lng_rad, lat_rad, lng_rad_p1):
    """
    uses the simplified haversine formula for this special case
    :param lng_rad: the longitude of the point in radians
    :param lat_rad: the latitude of the point
    :param lng_rad_p1: the latitude of the point1 on the equator (lat=0)
    :return: distance between the point and p1 (lng_rad_p1,0) in radians
    """
    return 2 * asin(sqrt((sin(lat_rad) / 2) ** 2 + cos(lat_rad) * sin((lng_rad - lng_rad_p1) / 2) ** 2))


# @jit(nopython=True, cache=True)
def haversine(lng_p1, lat_p1, lng_p2, lat_p2):
    """
    :param lng_p1: the longitude of point 1 in radians
    :param lat_p1: the latitude of point 1 in radians
    :param lng_p2: the longitude of point 1 in radians
    :param lat_p2: the latitude of point 1 in radians
    :return: distance between p1 and p2 in radians
    """
    return 2 * asin(sqrt(sin((lat_p1 - lat_p2) / 2) ** 2 + cos(lat_p2) * cos(lat_p1) * sin((lng_p1 - lng_p2) / 2) ** 2))


# @jit(nopython=True, cache=True)
def compute_min_distance(lng, lat, p0_lng, p0_lat, pm1_lng, pm1_lat, p1_lng, p1_lat):
    """
    :param lng: lng of px in degree
    :param lat: lat of px in degree
    :param p0_lng: lng of p0 in degree
    :param p0_lat: lat of p0 in degree
    :param pm1_lng: lng of pm1 in degree
    :param pm1_lat: lat of pm1 in degree
    :param p1_lng: lng of p1 in degree
    :param p1_lat: lat of p1 in degree
    :return: shortest distance between pX and the polygon section (pm1---p0---p1) in radians
    """
    # rotate coordinate system (= all the points) so that p0 would have lat=lng=0 (=origin)
    # z rotation is simply substracting the lng
    # convert the points to the cartesian coorinate system
    px_cartesian = coords2cartesian(lng - p0_lng, lat)
    p1_cartesian = coords2cartesian(p1_lng - p0_lng, p1_lat)
    pm1_cartesian = coords2cartesian(pm1_lng - p0_lng, pm1_lat)

    px_cartesian = y_rotate(p0_lat, px_cartesian)
    p1_cartesian = y_rotate(p0_lat, p1_cartesian)
    pm1_cartesian = y_rotate(p0_lat, pm1_cartesian)

    # for both p1 and pm1 separately do:

    # rotate coordinate system so that this point also has lat=0 (p0 does not change!)
    rotation_rad = atan2(p1_cartesian[2], p1_cartesian[1])
    p1_cartesian = x_rotate(rotation_rad, p1_cartesian)
    lng_p1_rad = atan2(p1_cartesian[1], p1_cartesian[0])
    px_retrans_rad = cartesian2rad(*x_rotate(rotation_rad, px_cartesian))

    # if lng of px is between 0 (<-point1) and lng of point 2:
    # the distance between point x and the 'equator' is the shortest
    # if the point is not between p0 and p1 the distance to the closest of the two points should be used
    # so clamp/clip the lng of px to the interval of [0; lng p1] and compute the distance with it
    temp_distance = distance_to_point_on_equator(px_retrans_rad[0], px_retrans_rad[1],
                                                 max(min(px_retrans_rad[0], lng_p1_rad), 0))

    # ATTENTION: vars are being reused. p1 is actually pm1 here!
    rotation_rad = atan2(pm1_cartesian[2], pm1_cartesian[1])
    p1_cartesian = x_rotate(rotation_rad, pm1_cartesian)
    lng_p1_rad = atan2(p1_cartesian[1], p1_cartesian[0])
    px_retrans_rad = cartesian2rad(*x_rotate(rotation_rad, px_cartesian))

    return min(temp_distance,
               distance_to_point_on_equator(px_retrans_rad[0], px_retrans_rad[1],
                                            max(min(px_retrans_rad[0], lng_p1_rad), 0)))


# @jit('f8(i8)', nopython=True, cache=True)
def long2coord(longlong):
    return float(longlong / 10 ** 15)


# @jit('i8(f8)', nopython=True, cache=True)
def coord2long(double):
    return int(double * 10 ** 15)


# @jit(nopython=True, cache=True)
def distance_to_polygon(lng, lat, nr_points, points, trans_points):
    # transform all points (long long) to coords
    for i in range(nr_points):
        trans_points[0][i] = long2coord(points[0][i])
        trans_points[1][i] = long2coord(points[1][i])

    # check points -2, -1, 0 first
    pm1_lng = trans_points[0][0]
    pm1_lat = trans_points[1][0]

    p1_lng = trans_points[0][-2]
    p1_lat = trans_points[1][-2]
    min_distance = compute_min_distance(lng, lat, trans_points[0][-1], trans_points[1][-1], pm1_lng, pm1_lat, p1_lng,
                                        p1_lat)

    index_p0 = 1
    index_p1 = 2
    for i in range(int(ceil((nr_points / 2) - 1))):
        p1_lng = trans_points[0][index_p1]
        p1_lat = trans_points[1][index_p1]

        distance = compute_min_distance(lng, lat, trans_points[0][index_p0], trans_points[1][index_p0], pm1_lng,
                                        pm1_lat, p1_lng, p1_lat)
        if distance < min_distance:
            min_distance = distance

        index_p0 += 2
        index_p1 += 2
        pm1_lng = p1_lng
        pm1_lat = p1_lat

    return min_distance


class TimezoneFinder:
    """
    This class lets you quickly find the timezone of a point on earth.
    It keeps the binary file with the timezonefinder open in reading mode to enable fast consequent access.
    In the file currently used there are two shortcuts stored per degree of latitude and one per degree of longitude
    (tests evaluated this to be the fastest setup when being used with numba)
    """

    def __init__(self):

        # open the file in binary reading mode
        self.binary_file = open(join(dirname(__file__),'timezone_data.bin'), 'rb')
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
    def closest_timezone_at(self, lng, lat, delta_degree=1):
        """
        This function searches for the closest polygon in the surrounding shortcuts.
        Make sure that the point does not lie within a polygon (for that case the algorithm is simply wrong!)
        Note that the algorithm won't find the closest polygon when it's on the 'other end of earth'
        (it can't search beyond the 180 deg lng border yet)
        this checks all the polygons within [delta_degree] degree lng and lat
        Keep in mind that x degrees lat are not the same distance apart than x degree lng!
        :param lng: longitude of the point in degree
        :param lat: latitude in degree
        :param delta_degree: the 'search radius' in degree
        :return: the timezone name of the closest found polygon or None
        """

        # the maximum possible distance is pi = 3.14...
        min_distance = 4
        # transform point X into cartesian coordinates
        current_closest_id = None
        central_x_shortcut = int(floor((lng + 180)))
        central_y_shortcut = int(floor((90 - lat) * 2))

        polygon_nrs = []

        # there are 2 shortcuts per 1 degree lat, so to cover 1 degree two shortcuts (rows) have to be checked
        # the highest shortcut is 0
        top = max(central_y_shortcut - 2 * delta_degree, 0)
        # the lowest shortcut is 360 (= 2 shortcuts per 1 degree lat)
        bottom = min(central_y_shortcut + 2 * delta_degree, 360)

        # the most left shortcut is 0
        left = max(central_x_shortcut - delta_degree, 0)
        # the most right shortcut is 360 (= 1 shortcuts per 1 degree lng)
        right = min(central_x_shortcut + delta_degree, 360)

        # TODO make algorithm work when closest polygon is on the 'other end of earth'
        # select all the polygons from the surrounding shortcuts
        for x in range(left, right + 1, 1):
            for y in range(top, bottom + 1, 1):
                for p in self.polygons_of_shortcut(x, y):
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
                empty_array = empty([2, nr_points], dtype='f8')
                distance = distance_to_polygon(lng, lat, nr_points, coords, empty_array)

                already_checked[pointer] = True
                if distance < min_distance:
                    min_distance = distance
                    current_closest_id = ids[pointer]
                    # whole list has to be searched again!
                    polygons_checked = 1
            pointer = (pointer + 1) % polygons_in_list

        # the the whole list has been searched
        return time_zone_names[current_closest_id]

    def timezone_at(self, lng=0.0, lat=0.0):
        """
        this function looks up in which polygons the point could be included
        to speed things up there are shortcuts being used (stored in the binary file)
        especially for large polygons it is expensive to check if a point is really included,
        so certain simplifications are made and even when you get a hit the point might actually
        not be inside the polygon (for example when there is only one timezone nearby)
        if you want to make sure a point is really inside a timezone use 'certain_timezone_at'
        make sure its called with valid values only!
        :param lng: longitude of the point in degree (-180 to 180)
        :param lat: latitude in degree (90 to -90)
        :return: the timezone name of the matching polygon or None
        """
        # if lng > 180.0 or lng < -180.0 or lat > 90.0 or lat < 90.0:
        # raise ValueError

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

        # otherwise check if the point is included for all the possible polygons
        for i in range(nr_possible_polygons):
            polygon_nr = possible_polygons[i]

            # get the boundaries of the polygon = (lng_max, lng_min, lat_max, lat_min)
            self.binary_file.seek((self.bound_start_address + 32 * polygon_nr), )
            boundaries = fromfile(self.binary_file, dtype='>i8', count=4)
            # only run the algorithm if it the point is withing the boundaries
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

