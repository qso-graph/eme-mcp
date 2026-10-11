"""server.json has to satisfy the MCP Registry before a release, not during one.

The Registry rejected this package's first publish with a 422: its description
was 133 characters and the limit is 100. PyPI had already accepted the upload
by then, so the release was half-done — on PyPI, absent from the Registry, and
untagged. A limit that is only discovered by a failing publish is a limit that
costs a version number every time.
"""

from __future__ import annotations

import json
import pathlib

SERVER_JSON = pathlib.Path(__file__).resolve().parent.parent / "server.json"

# The Registry's own limit, from the 422 it returns:
#   {"message": "expected length <= 100", "location": "body._meta.io.description"}
DESCRIPTION_LIMIT = 100


def test_description_is_within_the_registry_limit() -> None:
    """The check that would have caught the failed release."""
    description = json.loads(SERVER_JSON.read_text())["description"]
    assert len(description) <= DESCRIPTION_LIMIT, (
        f"server.json description is {len(description)} characters; the MCP "
        f"Registry refuses anything over {DESCRIPTION_LIMIT} and the publish "
        "fails after PyPI has already accepted the upload."
    )


def test_server_json_names_this_package() -> None:
    """A copied server.json naming another package would publish under it."""
    data = json.loads(SERVER_JSON.read_text())
    assert data["name"] == "io.github.qso-graph/eme-mcp"
    assert data["packages"][0]["identifier"] == "eme-mcp"


def test_versions_agree_with_each_other() -> None:
    """server.json carries the version twice; they must not drift apart."""
    data = json.loads(SERVER_JSON.read_text())
    assert data["version"] == data["packages"][0]["version"]
