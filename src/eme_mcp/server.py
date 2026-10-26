"""eme-mcp: EME (Earth-Moon-Earth) prediction for amateur radio.

Read-only, and **no network at run time**. The moon's position is computed
here from Meeus's series (`moon.py`); JPL Horizons is the oracle those numbers
are tested against, not a service this calls. That is what lets a QG Desktop
card answer instantly and keep answering when the network is down.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from typing import Any, NoReturn

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from . import __version__, eme, grid, moon

P = "eme"

mcp = FastMCP(
    "eme-mcp",
    version=__version__,
    instructions=(
        "EME (moonbounce) planning: when the moon is up from your grid, when it is up from "
        "both ends of a schedule at once, what the path costs on 2m/70cm/23cm, and which "
        "days are least degraded. Everything is computed locally from the moon's ephemeris; "
        "nothing is fetched. Start with eme_moon_window for a grid square such as DN13."
    ),
)

# A ceiling on every range a caller can ask for, so one request cannot make the
# server compute for ever. Generous for planning, finite by construction.
MAX_HOURS = 24.0 * 14
MAX_DAYS = 365
MIN_STEP_MINUTES = 1.0


def _err(message: str) -> NoReturn:
    """Reject bad input the way the protocol specifies.

    This returned ``{"error": message}`` as a *successful* result, so a client could not
    tell a rejection from an answer. The specification says of ``CallToolResult.isError``
    that otherwise "the LLM would not be able to see that an error occurred and
    self-correct".

    Nine call sites reached it, and the messages are the useful part: a bad locator, a
    frequency outside 30 MHz to 25 GHz, a band this server does not name, a time it
    cannot parse. Each tells the caller what to send instead, so each survives the
    conversion unchanged.
    """
    raise ToolError(message)


def _version_info_payload() -> dict[str, Any]:
    return {"service_name": "eme-mcp", "service_version": __version__,
            "spec_version": "Meeus ch. 47 (ELP-2000/82 abridged)"}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _parse_when(when: str | None) -> datetime | None:
    """A UTC instant, or None for now. Returns None on anything unreadable."""
    if not when:
        return datetime.now(timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(when).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo:
        return parsed.astimezone(timezone.utc)
    return parsed.replace(tzinfo=timezone.utc)


def _jd(moment: datetime) -> float:
    return moon.julian_day(moment.year, moment.month,
                           moment.day + (moment.hour + moment.minute / 60.0
                                         + moment.second / 3600.0) / 24.0)


# MCP 2026-07-28 tool annotations. The defaults are pessimistic — a tool that declares
# nothing is advertised as destructive, non-idempotent and open-world, and the
# specification tells a client it may keep a human in the loop for that.
#
# All five tools share one block, and the reason is not the owner-list servers' reason.
# There it is reference data carried in the wheel; here nothing is carried at all. This
# server *computes* — the moon's position from Meeus chapter 47, free-space path loss,
# degradation, a calendar of windows — so there is nothing to fetch and nothing to read.
# tests/test_mcp_conformance.py asserts that premise rather than the values.
_COMPUTED_ON_THIS_MACHINE = {
    "readOnlyHint": True,
    "destructiveHint": False,
    # Stronger here than anywhere else in this fleet. An owner-list server is idempotent
    # until the package is upgraded and the data changes under it; a live-service server
    # is idempotent only in the sense the specification means, while its answers move.
    # These are closed-form calculations: the same arguments give the same answer in
    # 2026 and in 2036. Where an answer does move — `when` left empty means now — it is
    # the argument defaulting, not the tool behaving differently.
    "idempotentHint": True,
    # Nothing leaves the machine, and nothing is read from it either. The ephemeris is
    # arithmetic, not a file and not a service.
    "openWorldHint": False,
}


@mcp.tool(annotations=_COMPUTED_ON_THIS_MACHINE)
def get_version_info() -> dict[str, Any]:
    """Get eme-mcp's version and the ephemeris series it computes from.

    Returns:
        service_name, service_version (PyPI), and spec_version (the series used).
    """
    return _version_info_payload()


@mcp.tool(name=f"{P}_moon_window", annotations=_COMPUTED_ON_THIS_MACHINE)
def moon_window(
    locator: str,
    hours: float | None = 24.0,
    step_minutes: float | None = 30.0,
    other_locator: str | None = "",
) -> dict[str, Any]:
    """Where the moon is from a grid square, and when both ends of a schedule can see it.

    Args:
        locator: Maidenhead locator, e.g. DN13 or DN13la.
        hours: How far ahead to look. Default 24, at most 336 (14 days).
        step_minutes: Sampling interval. Default 30, at least 1.
        other_locator: A second station's locator. Given one, the answer also
            carries the mutual window — the rows where the moon is above the
            horizon at both ends, which is the only time a contact is possible.

    Returns:
        Rows of time, azimuth, elevation and range, plus rise and set times and
        (with other_locator) the mutual window.
    """
    try:
        here = grid.place(locator)
    except grid.GridError as error:
        _err(str(error))
    there = None
    if other_locator:
        try:
            there = grid.place(other_locator)
        except grid.GridError as error:
            _err(str(error))

    span = _clamp(float(hours if hours is not None else 24.0), 0.0, MAX_HOURS)
    step = max(float(step_minutes if step_minutes is not None else 30.0), MIN_STEP_MINUTES)
    start = datetime.now(timezone.utc)

    rows: list[dict[str, Any]] = []
    steps = int(span * 60.0 / step) + 1
    for n in range(steps):
        moment = start + timedelta(minutes=step * n)
        look = moon.look_angle(_jd(moment), here.latitude, here.longitude)
        row: dict[str, Any] = {
            "time_utc": moment.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "azimuth_deg": round(look.azimuth, 2),
            "elevation_deg": round(look.elevation, 2),
            "distance_km": round(look.distance_km, 1),
        }
        if there is not None:
            far = moon.look_angle(_jd(moment), there.latitude, there.longitude)
            row["other_elevation_deg"] = round(far.elevation, 2)
            row["mutual"] = look.elevation > 0.0 and far.elevation > 0.0
        rows.append(row)

    up = [r for r in rows if r["elevation_deg"] > 0.0]
    answer: dict[str, Any] = {
        "locator": here.locator,
        "latitude": round(here.latitude, 4),
        "longitude": round(here.longitude, 4),
        "hours": span,
        "step_minutes": step,
        "rows": rows,
        "above_horizon_rows": len(up),
        "note": (
            "Geometric elevation: no atmospheric refraction, which lifts an "
            "object near the horizon by about half a degree."
        ),
    }
    if there is not None:
        mutual = [r for r in rows if r.get("mutual")]
        answer["other_locator"] = there.locator
        answer["mutual_rows"] = len(mutual)
        answer["mutual_from_utc"] = mutual[0]["time_utc"] if mutual else None
        answer["mutual_to_utc"] = mutual[-1]["time_utc"] if mutual else None
        if not mutual:
            answer["mutual_note"] = (
                "The moon is never above the horizon at both ends within this "
                "window. Try a longer one, or a different day."
            )
    return answer


@mcp.tool(name=f"{P}_path_loss", annotations=_COMPUTED_ON_THIS_MACHINE)
def path_loss(
    band: str | None = "70cm",
    frequency_mhz: float | None = None,
    locator: str | None = "",
    when: str | None = "",
) -> dict[str, Any]:
    """What the path to the moon and back costs, now or at a given time.

    Args:
        band: 2m, 70cm or 23cm. Ignored if frequency_mhz is given.
        frequency_mhz: An exact frequency, for a band this does not name.
        locator: Your grid square. Given one, the range is topocentric — from
            where you are, not from the Earth's centre, which differs by up to
            about 1.7% as the moon rises and sets.
        when: UTC time (ISO 8601). Default now.

    Returns:
        One-way, round-trip and echo path loss, with the range they came from.
    """
    moment = _parse_when(when)
    if moment is None:
        _err(f"{when!r} is not a time this understands. Use ISO 8601, e.g. 2026-10-12T00:00Z.")

    if frequency_mhz is not None:
        try:
            freq = float(frequency_mhz)
        except (TypeError, ValueError):
            _err("frequency_mhz must be a number.")
        if not 30.0 <= freq <= 25_000.0:
            _err("frequency_mhz must be between 30 and 25000 "
                 "(EME is worked from 6m to 24 GHz).")
        band_name = f"{freq:g} MHz"
    else:
        key = str(band or "70cm").lower()
        if key not in eme.BANDS_MHZ:
            _err(f"{band!r} is not a band this names. Use one of "
                        f"{', '.join(eme.BANDS_MHZ)}, or give frequency_mhz.")
        freq, band_name = eme.BANDS_MHZ[key], key

    jd = _jd(moment)
    if locator:
        try:
            here = grid.place(locator)
        except grid.GridError as error:
            _err(str(error))
        distance = moon.look_angle(jd, here.latitude, here.longitude).distance_km
        seen_from = here.locator
    else:
        distance = moon.position(jd).distance_km
        seen_from = None

    loss = eme.path_loss(distance, freq)
    return {
        "band": band_name,
        "frequency_mhz": freq,
        "time_utc": moment.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seen_from": seen_from,
        "distance_km": round(distance, 1),
        "one_way_db": round(loss.one_way_db, 2),
        "round_trip_db": round(loss.round_trip_db, 2),
        "echo_db": round(loss.echo_db, 2),
        "note": (
            "echo_db is the figure to budget a station with: the radar equation, "
            "accounting for the moon reflecting about 6.5% of what reaches it. "
            "round_trip_db is twice the free-space loss and ignores the moon."
        ),
    }


@mcp.tool(name=f"{P}_degradation", annotations=_COMPUTED_ON_THIS_MACHINE)
def degradation(locator: str | None = "", when: str | None = "") -> dict[str, Any]:
    """How much worse than the best case the moon is, now or at a given time.

    Args:
        locator: Your grid square, for a topocentric range. Optional.
        when: UTC time (ISO 8601). Default now.

    Returns:
        The distance term in dB against perigee, the moon's declination, and a
        statement that sky noise is not yet included.
    """
    moment = _parse_when(when)
    if moment is None:
        _err(f"{when!r} is not a time this understands. Use ISO 8601, e.g. 2026-10-12T00:00Z.")

    jd = _jd(moment)
    position = moon.position(jd)
    distance = position.distance_km
    seen_from = None
    if locator:
        try:
            here = grid.place(locator)
        except grid.GridError as error:
            _err(str(error))
        distance = moon.look_angle(jd, here.latitude, here.longitude).distance_km
        seen_from = here.locator

    result = eme.degradation(distance, position.declination)
    return {
        "time_utc": moment.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seen_from": seen_from,
        "distance_km": round(result.distance_km, 1),
        "degradation_db": round(result.distance_db, 2),
        "declination_deg": round(result.declination_deg, 2),
        "complete": result.complete,
        "note": result.note,
    }


@mcp.tool(name=f"{P}_calendar", annotations=_COMPUTED_ON_THIS_MACHINE)
def calendar(days: int | None = 30) -> dict[str, Any]:
    """The least degraded days ahead — when the moon is nearest.

    Args:
        days: How far ahead to look. Default 30, at most 365.

    Returns:
        A day-by-day table of the best (lowest) degradation each day, and the
        days that are best overall.
    """
    span = int(_clamp(float(days if days is not None else 30), 1, MAX_DAYS))
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    table: list[dict[str, Any]] = []
    for day in range(span):
        midnight = start + timedelta(days=day)
        # Six samples a day is enough to find the day's minimum: the moon's
        # range changes by at most a few hundred km in four hours.
        best = min(
            (moon.position(_jd(midnight + timedelta(hours=h))) for h in range(0, 24, 4)),
            key=lambda p: p.distance_km,
        )
        result = eme.degradation(best.distance_km, best.declination)
        table.append({
            "date": midnight.strftime("%Y-%m-%d"),
            "distance_km": round(best.distance_km, 1),
            "degradation_db": round(result.distance_db, 2),
            "declination_deg": round(best.declination, 2),
        })

    ranked = sorted(table, key=lambda row: row["degradation_db"])
    return {
        "days": span,
        "calendar": table,
        "best_days": ranked[:5],
        "complete": False,
        "note": (
            "Ranked on the distance term alone. Sky noise is not yet included "
            "(see eme_degradation), so a day that is quiet behind the moon may "
            "rank better than this says."
        ),
    }


USAGE = """\
usage: eme-mcp [--transport stdio|streamable-http] [--port N] [--version] [--help]

An MCP server: an AI app (Claude Desktop, Claude Code, ...) starts it and talks
to it over stdio. Run on its own it waits for that app; press Ctrl-C to stop.
Set up a client: https://github.com/qso-graph/eme-mcp#quick-start
"""


def main() -> None:
    """Run the server."""
    # Without this the script ignored both flags and bound stdio, so
    # `--help` left a user watching a banner and a hung terminal.
    if any(a in ("-h", "--help") for a in sys.argv[1:]):
        print(USAGE, end="")
        return
    if "--version" in sys.argv[1:]:
        print(f"eme-mcp {__version__}")
        return
    args = sys.argv[1:]
    transport, port = "stdio", 8020
    for i, arg in enumerate(args):
        if arg == "--transport" and i + 1 < len(args):
            transport = args[i + 1]
        if arg == "--port" and i + 1 < len(args):
            port = int(args[i + 1])
    # Written out rather than passed through: fastmcp takes a literal, and a
    # str that happens to hold the right word is not the same thing.
    if transport == "streamable-http":
        mcp.run(transport="streamable-http", port=port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
