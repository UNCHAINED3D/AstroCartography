"""
Moira compatibility shim over the Swiss Ephemeris engine (backend/swe_engine.py).

moira-astro only ships Windows ``cp313 win_amd64`` wheels, so it cannot install
on render.com (Linux, CPython 3.11). This shim re-exports the Moira-compatible
names the rest of the backend imports (``BODIES``, ``PLANET_COLORS``,
``_HAS_CHIRON``, ``jd_from_iso``, ``moira_reader``) from ``swe_engine``, which is
pure Python + pyswisseph manylinux wheels and works on every platform.

Chiron is now always present (swe_engine carries the Chiron ephemeris), so the
site renders Chiron ACG lines on render.com just like everywhere else.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from swe_engine import (
    BODIES,
    PLANET_COLORS,
    jd_from_iso,
    moira_reader,
)

_HAS_CHIRON = True

__all__ = ["BODIES", "PLANET_COLORS", "_HAS_CHIRON", "jd_from_iso", "moira_reader"]
