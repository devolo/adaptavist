# -*- coding: utf-8 -*-
"""The root of Adaptavist package namespace."""
from __future__ import unicode_literals

from pkg_resources import DistributionNotFound, get_distribution

from .adaptavist import Adaptavist

try:
    from importlib.metadata import PackageNotFoundError, version
except ImportError:
    from importlib_metadata import PackageNotFoundError, version) # type: ignore[misc]


try:
    __version__ = version("devolo_home_control_api")
except PackageNotFoundError:
    # package is not installed - e.g. pulled and run locally
    __version__ = "0.0.0"

__all__ = (
    "__version__",
    "Adaptavist"
)
