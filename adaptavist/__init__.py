"""The root of Adaptavist package namespace."""

from __future__ import unicode_literals

from .adaptavist import Adaptavist

try:
    from importlib.metadata import PackageNotFoundError, version
except ImportError:
    from importlib_metadata import PackageNotFoundError, version  # type: ignore

try:
    __version__ = version("adaptavist")
except PackageNotFoundError:
    # package is not installed - e.g. pulled and run locally
    __version__ = "0.0.0"

__all__ = ("__version__", "Adaptavist")
