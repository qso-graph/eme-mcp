# Changelog

All notable changes to `eme-mcp` are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.2] — 2026-10-26

### Fixed

- `--version` and `--help` now print and exit. They were ignored, so the
  command started the MCP server on stdio and waited for JSON-RPC — leaving a
  FastMCP banner on screen and an apparently hung terminal. Seven servers in
  this fleet already behaved correctly; this brings the rest in line, and a
  test asserts it.

## [0.2.1] — 2026-10-26

- Move every Node 20 action to its first Node 24 major
- The locked-dependency audit blocked every release
- Four upgrades arrived as 57 pull requests
- Nothing was auditing the lockfile
- Close every open security advisory in the lockfile
- A release is a workflow, not a merge

## [0.2.0] — 2026-10-25

**Upgrading:** a tool that rejects your input now returns `isError: true` instead of a successful
result whose payload carried an `error` key. Anything reading `result["error"]` should read the
error flag instead. The messages are unchanged.

### MCP specification 2026-07-28 (#8)

- **Tool errors are flagged `isError`.** `_err` built `{"error": message}` and **nine** call sites
  returned it, so on the wire a refusal arrived as a *successful* result. It raises `ToolError`
  now, typed `NoReturn`. The issue reports "2 occurrences"; measured, it is **one** payload
  construction reached from nine sites.
- **All five tools declare the four annotation hints**, sharing one block.
- **The reason for the block is this server's own, not a sibling's.** The owner-list servers answer
  `openWorldHint: false` because their data ships in the wheel; the live-service servers answer
  `true` because they call somebody's API. **This one has no data at all** — the moon's position is
  Meeus chapter 47 evaluated at a moment, path loss is the free-space formula. `EM-C12` asserts
  that: no data directory, and no file opened at run time.
- **`idempotentHint` is a stronger claim here than anywhere else in the fleet.** An owner-list
  server is idempotent only until the package is upgraded and its data changes underneath. A
  closed-form calculation gives the same answer in 2026 and in 2036. `EM-C20` pins a moment and
  checks two calls agree; `EM-C21` holds the case that looks like a counterexample and is not —
  `when` left empty means *now*, which is the argument defaulting rather than the tool behaving
  differently. It also records plainly that `eme_moon_window` takes no `when` and so cannot be
  pinned at all, which is why the stronger claim is demonstrated on the tools that accept a moment.
- **The refusal messages are the useful half, and they survive.** A frequency outside 30 MHz to
  25 GHz, a band this server does not name, a time it cannot parse — `EM-C31` checks each still
  says what to send instead, including that a refused band names the ones it knows.
- `tests/test_mcp_conformance.py` (EM-C01 onward, 14 tests). Every check falsified — **11 of 11**.
- **Nothing moved on the wire but the annotations.** Every name, description, `inputSchema` and
  `outputSchema` dumped through a real `fastmcp.Client` before and after: byte-identical.

### Lint (#7)

- **`E501` is adopted.** Four lines, not one a defect.
- **Every tool description came out byte-identical**, because none of the long lines was in a
  docstring — unlike the owner-list servers, where reflowing a summary line reached a client.
- The publisher-name exemption the issue was filed for does not apply: this server names no
  publisher's field, because it serves no publisher's list. Zero exemptions; the only `noqa` is a
  pre-existing `F401` on a deliberately planted import in `test_security.py`.
- Falsified: a long line planted in `src/`, caught.

### Not applicable here

- **No `certifi` work and no issue for it** (qso-graph-devel#73): there is no outbound call of any
  kind anywhere in the package. `EM-C10` keeps it that way and names `certifi` in its failure
  message.

## [0.1.1] — 2026-10-11

- **The MCP Registry refused 0.1.0**: `server.json`'s description was 133 characters and the
  Registry's limit is 100. PyPI had already accepted the upload by then, so 0.1.0 exists there
  but was never registered or tagged. The description is now 91 characters, and a test asserts
  the limit so it cannot be found by a failing publish again. Every other server in the fleet
  sits between 72 and 93 characters; this one was the outlier.

## [0.1.0] — 2026-10-11

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
