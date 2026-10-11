<!-- mcp-name: io.github.qso-graph/eme-mcp -->
# eme-mcp

[![PyPI](https://img.shields.io/pypi/v/eme-mcp?label=PyPI&color=blue)](https://pypi.org/project/eme-mcp/)
[![MCP Registry](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fregistry.modelcontextprotocol.io%2Fv0%2Fservers%3Fsearch%3Dio.github.qso-graph%2Feme-mcp%26version%3Dlatest&query=%24.servers%5B0%5D.server.version&label=MCP%20Registry&color=blue)](https://registry.modelcontextprotocol.io/v0/servers?search=io.github.qso-graph/eme-mcp&version=latest)

MCP server for **EME** — Earth-Moon-Earth, moonbounce. When the moon is up from your
grid, when it is up from both ends of a schedule at once, what the path costs on 2m,
70cm and 23cm, and which days ahead are least degraded.

Part of the [qso-graph](https://qso-graph.io/) project. **No network, no authentication.**

## Why it needs nothing from the network

The moon's position is **computed here**, from the abridged ELP-2000/82 series as Meeus
tabulates it (*Astronomical Algorithms*, chapter 47). That is around 250 lines of
standard library and a coefficient table. It is also what WSJT-X does, and the norm for
EME software.

That matters for more than tidiness. Moonrise and moonset are different for every grid
square, so a service-backed answer means a request per location per query — and a planning
tool that stalls, rate-limits, or goes dark when a remote service does.

**JPL Horizons is still here — as the test oracle.** Recorded Horizons responses are
fixtures, so every CI run checks these numbers against NASA's rather than against
themselves. Measured against Horizons for a Boise grid:

| | agreement |
|---|---|
| Azimuth | within **0.01°** |
| Elevation | within **0.003°** |
| Range | within **9 km** of ~392,000 (0.002%) |

Thirty arcseconds, against a 432 MHz array that is degrees wide.

## Install

```bash
uvx eme-mcp            # run it; nothing to install
```

## Tools

| Tool | Description |
|------|-------------|
| `eme_moon_window` | Moon azimuth, elevation and range from a grid square over time — and, given a second locator, the mutual window when both stations can see it |
| `eme_path_loss` | One-way, round-trip and echo path loss on 2m / 70cm / 23cm, or any frequency |
| `eme_degradation` | How much worse than perigee this moment is, with the moon's declination |
| `eme_calendar` | The least degraded days ahead |
| `get_version_info` | Service version and the ephemeris series used |

### What this does not yet do

**Sky noise is not included.** The full degradation figure an EME operator plans with
combines the distance term with the galactic background behind the moon, from the Haslam
408 MHz all-sky map. That map is not yet carried and pinned, so `eme_degradation` and
`eme_calendar` report the distance term and **say so in every answer** rather than
returning a number that looks complete and is not. Tracked in
[qso-graph-devel#52](https://github.com/qso-graph/qso-graph-devel/issues/52).

Elevations are geometric: no atmospheric refraction, which lifts an object near the
horizon by about half a degree.

## The two path-loss figures

They answer different questions and are often confused, so both are returned:

- **`echo_db`** is the one to budget a station with — the radar equation, accounting for
  the moon reflecting about 6.5% of what reaches it. Near 252 dB on 2m, 262 on 70cm and
  271 on 23cm at mean distance, which are the numbers EME operators know.
- **`round_trip_db`** is twice the free-space loss. It ignores the moon entirely.

## Licence

GPL-3.0-or-later. See [LICENSE](LICENSE).

The algorithms are from Jean Meeus, *Astronomical Algorithms* (2nd edition, Willmann-Bell,
1998), chapters 7, 11, 12, 22, 40 and 47 — cited in the source where each is used. The
implementation is ours; the mathematics is his and is not claimed.
