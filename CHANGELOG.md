# Changelog

All notable changes to `eme-mcp` are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

- First release. EME planning: moon windows for a grid square, mutual windows between two
  stations, path loss on 2m/70cm/23cm, degradation, and the least degraded days ahead
  (qso-graph-devel#52).
- **The moon is computed locally** from the abridged ELP-2000/82 series as Meeus tabulates it
  (*Astronomical Algorithms*, ch. 47), so the server makes **no network call at run time**.
  KI7MT and Bob settled this on 2026-10-11, against an earlier suggestion of calling JPL
  Horizons: moonrise and moonset are per-location, so a service-backed answer means a request
  per grid per query, and a planning tool that stalls when a remote service does.
- **JPL Horizons is the test oracle instead.** Recorded Horizons responses are fixtures, so
  every run checks these numbers against NASA's rather than against themselves. Measured for a
  Boise grid: azimuth within 0.01°, elevation within 0.003°, range within 9 km of 392,000.
- Echo path loss lands on the figures EME literature carries — about 252 dB on 2m, 262 on
  70cm, 271 on 23cm at mean distance — and is returned beside round-trip loss, which ignores
  the moon and is not what a station is budgeted with.
- **Sky noise is not included yet.** The galactic background behind the moon needs the Haslam
  408 MHz map, which is not yet carried and pinned, so `eme_degradation` and `eme_calendar`
  report the distance term and say so in every answer rather than returning a number that
  looks complete.
