"""Conformance with the Model Context Protocol, revision 2026-07-28.

We documented how to *publish* an MCP server in detail and never wrote down what makes
one *valid*, which is how missing ``isError`` and missing annotations reached every
server in the fleet.

This server's hints rest on a premise none of the others had:

* **Nothing is carried and nothing is fetched — everything is computed.** The owner-list
  servers answer ``openWorldHint: false`` because their data ships in the wheel; the
  live-service servers answer ``true`` because they call somebody's API. This one has no
  data at all. The moon's position comes from Meeus chapter 47, path loss from the
  free-space formula, degradation from the moon's distance. ``TestItIsAllArithmetic``
  asserts that: no socket, no file read, no bundled dataset.

* **``idempotentHint`` means more here than anywhere else in the fleet.** An owner-list
  server is idempotent until the package is upgraded and its data changes underneath;
  a live-service server is idempotent only in the sense the specification means, while
  its answers move. A closed-form calculation gives the same answer in 2026 and in 2036.
  ``TestTheSameArgumentsGiveTheSameAnswer`` holds it, and also holds the one case that
  looks like a counterexample and is not: ``when`` left empty means *now*, which is the
  argument defaulting rather than the tool behaving differently.

* **Nine call sites, one payload.** Issue #8 reports "2 occurrences"; measured, it is one
  ``{"error": message}`` construction reached from nine ``return _err(...)`` sites. The
  messages are the useful part — a bad locator, a frequency outside 30 MHz to 25 GHz, a
  band this server does not name, a time it cannot parse — and ``EM-C21`` holds that they
  survive the conversion.

Test IDs: EM-C01 onward.
"""

from __future__ import annotations

import asyncio

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from eme_mcp import server

ANNOTATION_HINTS = ("readOnlyHint", "destructiveHint", "idempotentHint", "openWorldHint")

TOOLS = {
    "get_version_info", "eme_moon_window", "eme_path_loss", "eme_degradation",
    "eme_calendar",
}


def _tools() -> dict[str, object]:
    return {t.name: t for t in asyncio.run(server.mcp.list_tools())}


def _wire(tool: object) -> dict[str, object]:
    annotations = getattr(tool, "annotations", None)
    assert annotations is not None, "tool declares no annotations"
    return annotations.model_dump(by_alias=True, exclude_none=True)


def call(name: str, args: dict | None = None):
    async def go():
        async with Client(server.mcp) as c:
            return (await c.call_tool(name, args or {})).data
    return asyncio.run(go())


def fails(name: str, args: dict | None = None) -> str:
    with pytest.raises(ToolError) as caught:
        call(name, args)
    return str(caught.value)


def _sources():
    import pathlib

    src = pathlib.Path(server.__file__).parent
    for py in src.rglob("*.py"):
        yield py, py.read_text()


class TestToolAnnotations:
    def test_every_tool_declares_all_four_hints(self) -> None:
        """EM-C01: the defaults are pessimistic, so silence is the wrong answer."""
        for name, tool in _tools().items():
            wire = _wire(tool)
            for hint in ANNOTATION_HINTS:
                assert hint in wire, f"{name} omits {hint}; got {sorted(wire)}"

    def test_all_five_are_read_only_closed_world_and_idempotent(self) -> None:
        """EM-C02: one answer for all five, because one reason covers all five."""
        for name, tool in _tools().items():
            wire = _wire(tool)
            assert wire["readOnlyHint"] is True, name
            assert wire["destructiveHint"] is False, name
            assert wire["idempotentHint"] is True, name
            assert wire["openWorldHint"] is False, name


class TestItIsAllArithmetic:
    """The premise under the hints, and it is this server's own rather than a sibling's.

    An owner-list server answers `openWorldHint: false` because its data ships in the
    wheel. This one has no data: the ephemeris is Meeus chapter 47 evaluated at a moment,
    path loss is the free-space formula. There is nothing to fetch and nothing to read.
    """

    def test_nothing_in_the_package_opens_a_socket(self) -> None:
        """EM-C10: `openWorldHint: false` depends on this."""
        offenders = [
            f"{py.name}:{i}: {line.strip()}"
            for py, text in _sources()
            for i, line in enumerate(text.splitlines(), 1)
            if any(t in line for t in ("urlopen", "urllib", "http.client", "socket.",
                                       "requests.", "httpx."))
        ]
        assert not offenders, (
            "something here reaches the network, so openWorldHint: false is wrong — and "
            "an outbound HTTPS call needs certifi (qso-graph-devel#73):\n"
            + "\n".join(offenders)
        )

    def test_nothing_in_the_package_writes(self) -> None:
        """EM-C11: `readOnlyHint: true` depends on this."""
        offenders = [
            f"{py.name}:{i}: {line.strip()}"
            for py, text in _sources()
            for i, line in enumerate(text.splitlines(), 1)
            if any(t in line for t in ("write_text(", ".write(", "mkdir("))
        ]
        assert not offenders, "something here writes:\n" + "\n".join(offenders)

    def test_the_package_carries_no_data_either(self) -> None:
        """EM-C12: what makes this server's reason different from its siblings'.

        cq-zones, itu-zones and darc-dok answer from JSON shipped beside the code, so
        their `idempotentHint` is only as stable as the package version. This one reads
        nothing: no data directory, and no file opened at run time. If a dataset ever
        appears, the stronger claim in EM-C20 stops being true and somebody should know.
        """
        import pathlib

        src = pathlib.Path(server.__file__).parent
        assert not (src / "data").exists(), "a data directory appeared; see EM-C20"
        offenders = [
            f"{py.name}:{i}: {line.strip()}"
            for py, text in _sources()
            for i, line in enumerate(text.splitlines(), 1)
            if "open(" in line and "urlopen" not in line
        ]
        assert not offenders, "something here reads a file:\n" + "\n".join(offenders)


class TestTheSameArgumentsGiveTheSameAnswer:
    """`idempotentHint: true`, and here it is a stronger claim than elsewhere."""

    def test_a_fixed_moment_gives_a_fixed_answer(self) -> None:
        """EM-C20: closed-form arithmetic, so the answer does not drift."""
        args = {"band": "2m", "locator": "DN13", "when": "2026-10-12T00:00Z"}
        first = call("eme_path_loss", args)
        second = call("eme_path_loss", args)
        assert first == second
        assert first["distance_km"] > 0

    def test_an_empty_when_is_the_argument_defaulting_not_the_tool_moving(self) -> None:
        """EM-C21: the case that looks like a counterexample and is not.

        `when=""` means now, so two calls a minute apart differ. That is the argument
        changing, not the tool: pin the moment and the answer is fixed. Recorded because
        it is exactly the observation that would lead a later reader to "correct"
        `idempotentHint` to false.

        Worth saying plainly that `eme_moon_window` cannot be pinned at all — it takes
        no `when` and always starts from now — so EM-C20's stronger "same arguments,
        same answer" claim is demonstrated on the tools that accept a moment. The hint
        is still right for all five, because it is about the tool changing nothing.
        """
        pinned = {"band": "2m", "when": "2026-10-12T00:00Z"}
        assert call("eme_path_loss", pinned) == call("eme_path_loss", pinned)
        assert _wire(_tools()["eme_path_loss"])["idempotentHint"] is True


class TestBadInputIsFlagged:
    def test_every_kind_of_refusal_raises(self) -> None:
        """EM-C30: the four kinds of bad input, not a sample of them."""
        for name, args in (
            ("eme_path_loss", {"band": "11m"}),
            ("eme_path_loss", {"frequency_mhz": 1.0}),
            ("eme_path_loss", {"frequency_mhz": 99_999.0}),
            ("eme_path_loss", {"band": "2m", "when": "yesterday"}),
            ("eme_degradation", {"when": "not-a-time"}),
            ("eme_moon_window", {"locator": "nonsense"}),
        ):
            fails(name, args)

    def test_the_messages_say_what_to_send_instead(self) -> None:
        """EM-C31: nine call sites, and the message is the useful half of each."""
        assert "30 and 25000" in fails("eme_path_loss", {"frequency_mhz": 1.0})
        assert "ISO 8601" in fails("eme_path_loss", {"band": "2m", "when": "yesterday"})
        assert "ISO 8601" in fails("eme_degradation", {"when": "not-a-time"})
        band = fails("eme_path_loss", {"band": "11m"})
        assert "11m" in band and "2m" in band, "a refused band should name the ones it knows"

    def test_no_error_payload_remains_in_the_source(self) -> None:
        """EM-C32: the conversion is complete, not partial.

        Reads the parse tree for a dict literal with an ``"error"`` key. A text search
        matches ``_err``'s own docstring, which quotes the old shape; stripping string
        literals to fix that deletes the key as well, since the key *is* a literal — the
        version that shipped in cq-zones-mcp 0.2.0 and could never fail.
        """
        import ast

        offenders = [
            f"{py.name}:{node.lineno}"
            for py, text in _sources()
            for node in ast.walk(ast.parse(text))
            if isinstance(node, ast.Dict)
            and any(isinstance(k, ast.Constant) and k.value == "error" for k in node.keys)
        ]
        assert not offenders, f"error payloads remain at: {offenders}"


class TestAnEmptyAnswerIsNotAnError:
    def test_a_moon_below_the_horizon_is_a_successful_call(self) -> None:
        """EM-C40: the distinction the specification draws.

        A window with no mutual visibility is an answer — the moon is where it is. Only
        an unusable *request* is an error.
        """
        answer = call("eme_moon_window", {
            "locator": "DN13", "hours": 1, "step_minutes": 60,
        })
        assert isinstance(answer, dict)
        assert "above_horizon_rows" in answer


class TestVersionInfoShape:
    def test_it_matches_the_shape_the_fleet_returns(self) -> None:
        """EM-C50: the convention that drifted because nobody asserted it."""
        info = call("get_version_info")
        assert info["service_name"] == "eme-mcp"
        assert info["service_version"]
        assert info["spec_version"]


class TestRegistration:
    def test_the_names_a_client_sees_are_prefixed(self) -> None:
        """EM-C60: issue #8 lists the function names, not these."""
        assert set(_tools()) == TOOLS

    def test_the_module_attribute_is_not_the_registered_name(self) -> None:
        """EM-C61: the trap that follows from prefixing, pinned."""
        assert not hasattr(server, "eme_path_loss")
        assert hasattr(server, "path_loss")
