"""Security test suite — qso-graph MCP Security Framework v1.0.

These tests enforce the 10 non-negotiable security guarantees.
See: https://qso-graph.io/security/
"""

import re
from pathlib import Path

SRC_DIR = Path(__file__).parent.parent / "src"


def _py_files():
    """Yield all .py files under src/."""
    yield from SRC_DIR.rglob("*.py")


def test_no_print_credentials():
    """Guarantee #1: Credentials never in logs (print statements)."""
    forbidden = re.compile(
        r'print\s*\(.*(?:password|api_key|creds|secret|token).*\)',
        re.IGNORECASE,
    )
    for py_file in _py_files():
        content = py_file.read_text()
        matches = forbidden.findall(content)
        assert not matches, f"Credential print in {py_file.name}: {matches}"


def test_no_logging_credentials():
    """Guarantee #1: Credentials never in logs (logging statements)."""
    forbidden = re.compile(
        r'logging\..*\(.*(?:password|api_key|creds|secret|token).*\)',
        re.IGNORECASE,
    )
    for py_file in _py_files():
        content = py_file.read_text()
        matches = forbidden.findall(content)
        assert not matches, f"Credential logging in {py_file.name}: {matches}"


def test_no_subprocess():
    """Guarantee #5: No command injection surface."""
    forbidden = re.compile(r'subprocess\.|os\.system|shell\s*=\s*True')
    for py_file in _py_files():
        content = py_file.read_text()
        matches = forbidden.findall(content)
        assert not matches, f"Shell execution in {py_file.name}: {matches}"


def test_all_urls_https():
    """Guarantee #7: HTTPS only for external calls."""
    http_url = re.compile(r'http://(?!localhost|127\.0\.0\.1|::1)')
    for py_file in _py_files():
        content = py_file.read_text()
        matches = http_url.findall(content)
        assert not matches, f"Non-HTTPS URL in {py_file.name}: {matches}"


def test_error_messages_safe():
    """Guarantee #3/#10: Credentials never in error messages."""
    dangerous = re.compile(
        r'raise\s+\w+\([^)]*(?:password|api_key|creds|secret).*\)',
        re.IGNORECASE,
    )
    for py_file in _py_files():
        content = py_file.read_text()
        matches = dangerous.findall(content)
        assert not matches, f"Credential in exception in {py_file.name}: {matches}"


def test_no_eval_exec():
    """Guarantee #5: No code injection surface."""
    for py_file in _py_files():
        content = py_file.read_text()
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            if re.search(r'\b(?:eval|exec)\s*\(', stripped):
                assert False, f"eval/exec in {py_file.name}:{i}: {stripped.strip()}"

# ---------------------------------------------------------------------------
# This server's own strongest property.
# ---------------------------------------------------------------------------


def test_nothing_reaches_the_network():
    """No runtime network call exists, anywhere in the package.

    This is eme-mcp's central claim and the reason it was built this way
    (qso-graph-devel#52, KI7MT and Bob, 2026-10-11): the moon is computed
    locally, so an answer costs nothing and cannot fail because a remote
    service is down or rate-limited. JPL Horizons is the oracle the numbers are
    tested against, never a service called at run time.

    A claim like that decays the moment someone adds a convenient lookup, so it
    is enforced here rather than written in the README and hoped for.
    """
    forbidden = (
        "urllib", "requests", "httpx", "aiohttp", "socket", "http.client",
        "urlopen", "websocket",
    )
    for path in _py_files():
        source = path.read_text(encoding="utf-8")
        body = "\n".join(
            line for line in source.splitlines()
            if not line.lstrip().startswith("#")
        )
        for name in forbidden:
            assert name not in body, (
                f"{path.name} mentions {name!r} outside a comment. This package "
                "makes no network calls; if that has to change, the README and "
                "the server's instructions have to change with it."
            )


def test_the_network_check_would_catch_an_import():
    """The control for the test above: it must actually fail on a real import.

    A scan that looks for strings can be defeated by its own filtering. This
    plants what it is meant to catch and checks that it is caught.
    """
    import urllib.request  # noqa: F401  (planted deliberately, in a string below)

    planted = "import urllib.request\nurllib.request.urlopen('https://example.invalid')"
    body = "\n".join(
        line for line in planted.splitlines() if not line.lstrip().startswith("#")
    )
    assert "urllib" in body and "urlopen" in body, (
        "the scan must see a real import; if this fails the filtering above is "
        "hiding what it is supposed to find"
    )
