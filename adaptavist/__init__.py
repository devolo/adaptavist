# -*- coding: utf-8 -*-
"""The root of Adaptavist package namespace."""
from __future__ import unicode_literals
from pbr.version import VersionInfo

_v = VersionInfo("adaptavist").semantic_version()
__version__ = _v.release_string()
version_info = _v.version_tuple()

from adaptavist.adaptavist import Adaptavist

__all__ = (
    "__version__",
    "Adaptavist"
)
