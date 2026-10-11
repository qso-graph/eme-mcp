"""eme-mcp — EME (Earth-Moon-Earth) prediction, computed locally."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _version

try:
    __version__ = _version("eme-mcp")
except PackageNotFoundError:  # running from a source tree without an install
    __version__ = "0.0.0"

# What the moon's position is computed from. Not a service version: there is
# no service. Reported by get_version_info so an answer can be traced to the
# series that produced it.
__spec_version__ = "Meeus ch. 47 (ELP-2000/82 abridged)"
