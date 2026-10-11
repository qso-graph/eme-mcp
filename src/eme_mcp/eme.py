"""What the moon's position means for an EME contact.

Path loss, degradation and the windows an operator plans around. Everything
here is arithmetic over `moon.py`'s output: no network, no table to go stale.

**What is not here yet: sky noise.** The full degradation figure an EME
operator uses combines the distance term below with the galactic noise
temperature behind the moon, which comes from the Haslam 408 MHz all-sky map.
That map is not yet carried and pinned (qso-graph-devel#52), so `degradation`
reports its distance and declination terms and says so, rather than quietly
reporting a number that looks complete and is not.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# The moon's mean distance, and the extremes it actually reaches. Perigee and
# apogee vary month to month; these are the usual bounds, used only to express
# a degradation relative to the best case.
MEAN_DISTANCE_KM = 385_000.56
PERIGEE_KM = 356_500.0
APOGEE_KM = 406_700.0

# Radius and radar cross-section. The moon reflects about 6.5% of what reaches
# it (its radar albedo at VHF/UHF), over a disc of its own radius — the figure
# EME link budgets have used for decades.
MOON_RADIUS_KM = 1737.4
RADAR_ALBEDO = 0.065

# The bands EME is worked on, and what this server answers for by default.
BANDS_MHZ = {"2m": 144.1, "70cm": 432.1, "23cm": 1296.1}


def free_space_path_loss_db(distance_km: float, frequency_mhz: float) -> float:
    """One-way free-space path loss, in dB.

    The standard form: 20 log10(d_km) + 20 log10(f_MHz) + 32.44778, which is
    the constant for kilometres and megahertz.
    """
    if distance_km <= 0 or frequency_mhz <= 0:
        raise ValueError("distance and frequency must be positive")
    return (20.0 * math.log10(distance_km)
            + 20.0 * math.log10(frequency_mhz) + 32.44778)


@dataclass(frozen=True)
class PathLoss:
    """What the path costs, both ways."""
    frequency_mhz: float
    distance_km: float
    one_way_db: float
    round_trip_db: float
    echo_db: float


def path_loss(distance_km: float, frequency_mhz: float) -> PathLoss:
    """Loss to the moon and back.

    Two figures, because they answer different questions and are often
    confused:

    - `round_trip_db` is twice the free-space loss. It is what the path costs
      if the moon were a perfect isotropic repeater, and it is **not** the
      number to budget a station with.
    - `echo_db` is the real one: the radar equation, which accounts for the
      moon being a reflector of finite size and poor efficiency. For 432 MHz at
      mean distance it lands near 262 dB, the figure EME operators know.
    """
    one_way = free_space_path_loss_db(distance_km, frequency_mhz)
    wavelength_m = 299.792458 / frequency_mhz

    # Radar equation: L = (4*pi)^3 * d^4 / (lambda^2 * sigma).
    sigma_m2 = RADAR_ALBEDO * math.pi * (MOON_RADIUS_KM * 1000.0) ** 2
    distance_m = distance_km * 1000.0
    ratio = ((4.0 * math.pi) ** 3 * distance_m ** 4
             / (wavelength_m ** 2 * sigma_m2))
    return PathLoss(
        frequency_mhz=frequency_mhz,
        distance_km=distance_km,
        one_way_db=one_way,
        round_trip_db=2.0 * one_way,
        echo_db=10.0 * math.log10(ratio),
    )


@dataclass(frozen=True)
class Degradation:
    """How much worse than the best case this moment is."""
    distance_km: float
    distance_db: float
    declination_deg: float
    complete: bool
    note: str


def degradation(distance_km: float, declination_deg: float) -> Degradation:
    """Degradation from distance, with the declination that shapes the window.

    The distance term is exact and is the larger part of what operators plan
    around: loss goes as the fourth power of range, so apogee costs about 2.1 dB
    over perigee. It is expressed against perigee, so 0 dB is the best the moon
    gets and every other moment is worse.

    Declination is reported rather than folded in: it does not change the loss,
    it changes how long and how high the moon is available, which is the other
    half of planning a schedule.
    """
    best = 40.0 * math.log10(PERIGEE_KM)
    here = 40.0 * math.log10(distance_km)
    return Degradation(
        distance_km=distance_km,
        distance_db=here - best,
        declination_deg=declination_deg,
        complete=False,
        note=(
            "Distance term only. Sky noise — the galactic background behind the "
            "moon, from the Haslam 408 MHz map — is not yet included, so this is "
            "not the full degradation figure an EME planner reports."
        ),
    )
