"""Our arithmetic against NASA's.

This is the test the whole server rests on. The moon's position is computed
locally (`moon.py`) so the server needs no network — and the risk that creates
is that our numbers are checked only against themselves. The fixtures below
are recorded responses from **JPL Horizons**, NASA's own ephemeris service, so
every run compares what we compute against what NASA says.

Recording a new fixture:

    https://ssd.jpl.nasa.gov/api/horizons.api?format=json&COMMAND='301'
      &OBJ_DATA='NO'&MAKE_EPHEM='YES'&EPHEM_TYPE='OBSERVER'
      &CENTER='coord@399'&SITE_COORD='<lon>,<lat>,<alt_km>'
      &START_TIME='...'&STOP_TIME='...'&STEP_SIZE='1 h'&QUANTITIES='4,20'

Horizons' elevation is airless by default, which is why it compares directly
with ours: we compute geometric elevation and apply no refraction. That was
checked rather than assumed — at 1.77 degrees elevation, where refraction would
lift an object by about a third of a degree, the two agree to 0.003.
"""

from __future__ import annotations

import pytest

from eme_mcp import moon

AU_KM = 149_597_870.7

# JPL Horizons, recorded 2026-10-11. Site: longitude -116.2, latitude 43.6,
# altitude 0.8 km — a Boise grid, chosen because the moon sets through the
# window, so the rows span high elevation to below the horizon.
SITE = (43.6, -116.2, 0.8)
HORIZONS = [
    # (UTC, apparent azimuth deg, elevation deg, range AU)
    ("2026-10-12 00:00", 231.744193, 10.763100, 0.00261736729706),
    ("2026-10-12 01:00", 242.386840, 1.767730, 0.00262507909472),
    ("2026-10-12 02:00", 252.137895, -8.058710, 0.00263345394224),
]

# What we hold ourselves to. Meeus states about 10 arcseconds in longitude for
# the abridged series; these are the margins actually achieved against the
# fixtures, with room to spare. A 432 MHz array is degrees wide, so even the
# loosest of these is far finer than anything that could mispoint a dish.
AZIMUTH_TOLERANCE_DEG = 0.05
ELEVATION_TOLERANCE_DEG = 0.05
RANGE_TOLERANCE_KM = 50.0


def _jd(stamp: str) -> float:
    date, clock = stamp.split()
    year, month, day = (int(part) for part in date.split("-"))
    hour, minute = (int(part) for part in clock.split(":"))
    return moon.julian_day(year, month, day + (hour + minute / 60.0) / 24.0)


@pytest.mark.parametrize("stamp,azimuth,elevation,range_au", HORIZONS)
def test_matches_nasa(stamp: str, azimuth: float, elevation: float, range_au: float) -> None:
    """EME-001: our moon agrees with NASA's, to far better than a beamwidth."""
    latitude, longitude, height = SITE
    look = moon.look_angle(_jd(stamp), latitude, longitude, height)

    assert abs(look.azimuth - azimuth) < AZIMUTH_TOLERANCE_DEG, (
        f"{stamp}: azimuth {look.azimuth:.4f} against NASA's {azimuth:.4f}")
    assert abs(look.elevation - elevation) < ELEVATION_TOLERANCE_DEG, (
        f"{stamp}: elevation {look.elevation:.4f} against NASA's {elevation:.4f}")
    assert abs(look.distance_km - range_au * AU_KM) < RANGE_TOLERANCE_KM, (
        f"{stamp}: range {look.distance_km:.1f} km against NASA's {range_au * AU_KM:.1f}")


def test_the_oracle_would_catch_a_wrong_moon() -> None:
    """EME-002: the control — the comparison above is not vacuous.

    A tolerance wide enough to absorb a real error is a test that passes on
    anything. One degree of hour angle is four minutes of time, which is a
    small slip in a sidereal-time calculation and a large one in where a dish
    points. It must fail.
    """
    latitude, longitude, height = SITE
    stamp, azimuth, _elevation, _range = HORIZONS[0]
    # Four minutes later: the sky has turned one degree.
    slipped = moon.look_angle(_jd(stamp) + 4.0 / (24.0 * 60.0), latitude, longitude, height)
    assert abs(slipped.azimuth - azimuth) > AZIMUTH_TOLERANCE_DEG, (
        "a four-minute error must exceed the azimuth tolerance, or the "
        "tolerance is too wide to mean anything")


def test_topocentric_is_not_geocentric() -> None:
    """EME-003: the observer's offset from the Earth's centre is applied.

    The moon is close enough that where you stand moves it by up to about a
    degree — more than a 23cm dish's beamwidth. Computing the geocentric
    position and calling it topocentric is a mistake that looks right in a
    table and misses the moon on the air, so it is asserted directly.
    """
    latitude, longitude, height = SITE
    jd = _jd(HORIZONS[0][0])
    geocentric = moon.position(jd)
    topocentric = moon.look_angle(jd, latitude, longitude, height)
    difference = abs(topocentric.distance_km - geocentric.distance_km)
    assert difference > 1000.0, (
        f"topocentric and geocentric range differ by only {difference:.1f} km; "
        "the observer's position does not appear to be applied")
