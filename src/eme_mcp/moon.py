"""The moon's position, computed locally (Meeus, Astronomical Algorithms, ch. 47).

Standard library only, and no network: see README.

The abridged ELP-2000/82 series Meeus tabulates: 60 periodic terms for
longitude and distance, 60 for latitude. Meeus states the accuracy as about
10 arcseconds in longitude and 4 in latitude, which is far finer than an EME
dish's beamwidth — a 432 MHz array is degrees wide.

Nothing here reaches the network. JPL Horizons is the oracle these numbers are
checked against in tests, not a service called at run time.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

D2R = math.pi / 180.0
R2D = 180.0 / math.pi


def julian_day(year: int, month: int, day: float) -> float:
    """Julian Day for a Gregorian calendar date (Meeus ch. 7)."""
    if month <= 2:
        year -= 1
        month += 12
    a = year // 100
    b = 2 - a + a // 4
    return (math.floor(365.25 * (year + 4716))
            + math.floor(30.6001 * (month + 1)) + day + b - 1524.5)


# Meeus Table 47.A — multiples of D, M, M', F, then the coefficients of the
# sine (longitude, 1e-6 deg) and cosine (distance, 1e-3 km) terms.
_TERMS_LR = [
    (0, 0, 1, 0, 6288774, -20905355), (2, 0, -1, 0, 1274027, -3699111),
    (2, 0, 0, 0, 658314, -2955968), (0, 0, 2, 0, 213618, -569925),
    (0, 1, 0, 0, -185116, 48888), (0, 0, 0, 2, -114332, -3149),
    (2, 0, -2, 0, 58793, 246158), (2, -1, -1, 0, 57066, -152138),
    (2, 0, 1, 0, 53322, -170733), (2, -1, 0, 0, 45758, -204586),
    (0, 1, -1, 0, -40923, -129620), (1, 0, 0, 0, -34720, 108743),
    (0, 1, 1, 0, -30383, 104755), (2, 0, 0, -2, 15327, 10321),
    (0, 0, 1, 2, -12528, 0), (0, 0, 1, -2, 10980, 79661),
    (4, 0, -1, 0, 10675, -34782), (0, 0, 3, 0, 10034, -23210),
    (4, 0, -2, 0, 8548, -21636), (2, 1, -1, 0, -7888, 24208),
    (2, 1, 0, 0, -6766, 30824), (1, 0, -1, 0, -5163, -8379),
    (1, 1, 0, 0, 4987, -16675), (2, -1, 1, 0, 4036, -12831),
    (2, 0, 2, 0, 3994, -10445), (4, 0, 0, 0, 3861, -11650),
    (2, 0, -3, 0, 3665, 14403), (0, 1, -2, 0, -2689, -7003),
    (2, 0, -1, 2, -2602, 0), (2, -1, -2, 0, 2390, 10056),
    (1, 0, 1, 0, -2348, 6322), (2, -2, 0, 0, 2236, -9884),
    (0, 1, 2, 0, -2120, 5751), (0, 2, 0, 0, -2069, 0),
    (2, -2, -1, 0, 2048, -4950), (2, 0, 1, -2, -1773, 4130),
    (2, 0, 0, 2, -1595, 0), (4, -1, -1, 0, 1215, -3958),
    (0, 0, 2, 2, -1110, 0), (3, 0, -1, 0, -892, 3258),
    (2, 1, 1, 0, -810, 2616), (4, -1, -2, 0, 759, -1897),
    (0, 2, -1, 0, -713, -2117), (2, 2, -1, 0, -700, 2354),
    (2, 1, -2, 0, 691, 0), (2, -1, 0, -2, 596, 0),
    (4, 0, 1, 0, 549, -1423), (0, 0, 4, 0, 537, -1117),
    (4, -1, 0, 0, 520, -1571), (1, 0, -2, 0, -487, -1739),
    (2, 1, 0, -2, -399, 0), (0, 0, 2, -2, -381, -4421),
    (1, 1, 1, 0, 351, 0), (3, 0, -2, 0, -340, 0),
    (4, 0, -3, 0, 330, 0), (2, -1, 2, 0, 327, 0),
    (0, 2, 1, 0, -323, 1165), (1, 1, -1, 0, 299, 0),
    (2, 0, 3, 0, 294, 0), (2, 0, -1, -2, 0, 8752),
]

# Meeus Table 47.B — the latitude series, coefficient of the sine term
# (1e-6 deg).
_TERMS_B = [
    (0, 0, 0, 1, 5128122), (0, 0, 1, 1, 280602), (0, 0, 1, -1, 277693),
    (2, 0, 0, -1, 173237), (2, 0, -1, 1, 55413), (2, 0, -1, -1, 46271),
    (2, 0, 0, 1, 32573), (0, 0, 2, 1, 17198), (2, 0, 1, -1, 9266),
    (0, 0, 2, -1, 8822), (2, -1, 0, -1, 8216), (2, 0, -2, -1, 4324),
    (2, 0, 1, 1, 4200), (2, 1, 0, -1, -3359), (2, -1, -1, 1, 2463),
    (2, -1, 0, 1, 2211), (2, -1, -1, -1, 2065), (0, 1, -1, -1, -1870),
    (4, 0, -1, -1, 1828), (0, 1, 0, 1, -1794), (0, 0, 0, 3, -1749),
    (0, 1, -1, 1, -1565), (1, 0, 0, 1, -1491), (0, 1, 1, 1, -1475),
    (0, 1, 1, -1, -1410), (0, 1, 0, -1, -1344), (1, 0, 0, -1, -1335),
    (0, 0, 3, 1, 1107), (4, 0, 0, -1, 1021), (4, 0, -1, 1, 833),
    (0, 0, 1, -3, 777), (4, 0, -2, 1, 671), (2, 0, 0, -3, 607),
    (2, 0, 2, -1, 596), (2, -1, 1, -1, 491), (2, 0, -2, 1, -451),
    (0, 0, 3, -1, 439), (2, 0, 2, 1, 422), (2, 0, -3, -1, 421),
    (2, 1, -1, 1, -366), (2, 1, 0, 1, -351), (4, 0, 0, 1, 331),
    (2, -1, 1, 1, 315), (2, -2, 0, -1, 302), (0, 0, 1, 3, -283),
    (2, 1, 1, -1, -229), (1, 1, 0, -1, 223), (1, 1, 0, 1, 223),
    (0, 1, -2, -1, -220), (2, 1, -1, -1, -220), (1, 0, 1, 1, -185),
    (2, -1, -2, -1, 181), (0, 1, 2, 1, -177), (4, 0, -2, -1, 176),
    (4, -1, -1, -1, 166), (1, 0, 1, -1, -164), (4, 0, 1, -1, 132),
    (1, 0, -1, -1, -119), (4, -1, 0, -1, 115), (2, -2, 0, 1, 107),
]


@dataclass(frozen=True)
class Position:
    """Where the moon is, geocentric."""
    right_ascension: float   # degrees
    declination: float       # degrees
    distance_km: float


def position(jd: float) -> Position:
    """Geocentric apparent RA, declination and distance for a Julian Day."""
    t = (jd - 2451545.0) / 36525.0

    # Mean elements (Meeus 47.1-47.6), degrees.
    lp = 218.3164477 + 481267.88123421 * t - 0.0015786 * t * t \
        + t ** 3 / 538841.0 - t ** 4 / 65194000.0           # moon's mean longitude
    d = 297.8501921 + 445267.1114034 * t - 0.0018819 * t * t \
        + t ** 3 / 545868.0 - t ** 4 / 113065000.0          # mean elongation
    m = 357.5291092 + 35999.0502909 * t - 0.0001536 * t * t \
        + t ** 3 / 24490000.0                               # sun's mean anomaly
    mp = 134.9633964 + 477198.8675055 * t + 0.0087414 * t * t \
        + t ** 3 / 69699.0 - t ** 4 / 14712000.0            # moon's mean anomaly
    f = 93.2720950 + 483202.0175233 * t - 0.0036539 * t * t \
        - t ** 3 / 3526000.0 + t ** 4 / 863310000.0         # argument of latitude

    a1 = 119.75 + 131.849 * t
    a2 = 53.09 + 479264.290 * t
    a3 = 313.45 + 481266.484 * t
    # Eccentricity of Earth's orbit: terms in M are scaled by it (Meeus 47.6).
    e = 1.0 - 0.002516 * t - 0.0000074 * t * t

    sum_l = sum_r = sum_b = 0.0
    for cd, cm, cmp_, cf, cl, cr in _TERMS_LR:
        arg = (cd * d + cm * m + cmp_ * mp + cf * f) * D2R
        scale = e ** abs(cm)
        sum_l += cl * scale * math.sin(arg)
        sum_r += cr * scale * math.cos(arg)
    for cd, cm, cmp_, cf, cb in _TERMS_B:
        arg = (cd * d + cm * m + cmp_ * mp + cf * f) * D2R
        sum_b += cb * (e ** abs(cm)) * math.sin(arg)

    # Additive terms for Venus, Jupiter and Earth's flattening (Meeus p.342).
    sum_l += 3958 * math.sin(a1 * D2R) + 1962 * math.sin((lp - f) * D2R) \
        + 318 * math.sin(a2 * D2R)
    sum_b += (-2235 * math.sin(lp * D2R) + 382 * math.sin(a3 * D2R)
              + 175 * math.sin((a1 - f) * D2R) + 175 * math.sin((a1 + f) * D2R)
              + 127 * math.sin((lp - mp) * D2R) - 115 * math.sin((lp + mp) * D2R))

    longitude = lp + sum_l / 1_000_000.0
    latitude = sum_b / 1_000_000.0
    distance = 385000.56 + sum_r / 1000.0

    # Nutation in longitude, so the result is apparent rather than mean.
    omega = 125.04452 - 1934.136261 * t
    l_sun = 280.4665 + 36000.7698 * t
    l_moon = 218.3165 + 481267.8813 * t
    d_psi = (-17.20 * math.sin(omega * D2R) - 1.32 * math.sin(2 * l_sun * D2R)
             - 0.23 * math.sin(2 * l_moon * D2R) + 0.21 * math.sin(2 * omega * D2R)) / 3600.0
    d_eps = (9.20 * math.cos(omega * D2R) + 0.57 * math.cos(2 * l_sun * D2R)
             + 0.10 * math.cos(2 * l_moon * D2R) - 0.09 * math.cos(2 * omega * D2R)) / 3600.0
    longitude += d_psi

    # Obliquity of the ecliptic (Meeus 22.2), plus nutation.
    eps0 = (23.0 + 26.0 / 60.0 + 21.448 / 3600.0
            - (46.8150 * t + 0.00059 * t * t - 0.001813 * t ** 3) / 3600.0)
    eps = eps0 + d_eps

    lam, bet = longitude * D2R, latitude * D2R
    e_rad = eps * D2R
    ra = math.atan2(math.sin(lam) * math.cos(e_rad) - math.tan(bet) * math.sin(e_rad),
                    math.cos(lam))
    dec = math.asin(math.sin(bet) * math.cos(e_rad)
                    + math.cos(bet) * math.sin(e_rad) * math.sin(lam))
    return Position((ra * R2D) % 360.0, dec * R2D, distance)


def greenwich_sidereal(jd: float) -> float:
    """Apparent Greenwich sidereal time in degrees (Meeus 12.4)."""
    t = (jd - 2451545.0) / 36525.0
    theta = (280.46061837 + 360.98564736629 * (jd - 2451545.0)
             + 0.000387933 * t * t - t ** 3 / 38710000.0)
    return theta % 360.0


@dataclass(frozen=True)
class LookAngle:
    """Where to point, from one place on the Earth."""
    azimuth: float      # degrees, from north through east
    elevation: float    # degrees, geometric (no refraction)
    distance_km: float  # topocentric


def look_angle(jd: float, latitude: float, longitude: float,
               height_km: float = 0.0) -> LookAngle:
    """Topocentric azimuth, elevation and range for an observer.

    Topocentric, not geocentric: the moon is close enough that an observer's
    offset from the Earth's centre moves it by up to about a degree, which is
    the difference between pointing at it and missing it.
    """
    p = position(jd)
    lst = (greenwich_sidereal(jd) + longitude) % 360.0
    hour_angle = (lst - p.right_ascension) % 360.0

    # Observer's geocentric position, allowing for the Earth's flattening
    # (Meeus ch. 11).
    lat = latitude * D2R
    flattening = 1.0 / 298.257223563
    b_over_a = 1.0 - flattening
    u = math.atan(b_over_a * math.tan(lat))
    rho_sin = b_over_a * math.sin(u) + (height_km / 6378.14) * math.sin(lat)
    rho_cos = math.cos(u) + (height_km / 6378.14) * math.cos(lat)

    # Geocentric -> topocentric (Meeus ch. 40), by vector difference.
    ra, dec = p.right_ascension * D2R, p.declination * D2R
    x = p.distance_km * math.cos(dec) * math.cos(ra)
    y = p.distance_km * math.cos(dec) * math.sin(ra)
    z = p.distance_km * math.sin(dec)
    theta = greenwich_sidereal(jd) * D2R + longitude * D2R
    ox = 6378.14 * rho_cos * math.cos(theta)
    oy = 6378.14 * rho_cos * math.sin(theta)
    oz = 6378.14 * rho_sin
    dx, dy, dz = x - ox, y - oy, z - oz
    topo_distance = math.sqrt(dx * dx + dy * dy + dz * dz)
    topo_ra = math.atan2(dy, dx)
    topo_dec = math.asin(dz / topo_distance)

    hour_angle = (greenwich_sidereal(jd) + longitude - topo_ra * R2D) % 360.0
    h = hour_angle * D2R
    azimuth = math.atan2(math.sin(h),
                         math.cos(h) * math.sin(lat) - math.tan(topo_dec) * math.cos(lat))
    elevation = math.asin(math.sin(lat) * math.sin(topo_dec)
                          + math.cos(lat) * math.cos(topo_dec) * math.cos(h))
    return LookAngle((azimuth * R2D + 180.0) % 360.0, elevation * R2D, topo_distance)
