"""
Moira engine bridge.

Wraps Moira's de-singletonized reader architecture: a single planetary kernel
(de440.bsp) is loaded once and injected via `use_reader_override` for the
duration of each calculation.

Moira is MIT licensed; the de440 kernel is JPL's public planetary ephemeris.
"""

from __future__ import annotations

import os
import re
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

from moira.spk_reader import KernelPool, SpkReader, use_reader_override
from moira._spk_body_kernel import SmallBodyKernel

# Prefer an explicit kernel path; otherwise fall back to the user download dir.
_KERNEL_PATH = os.environ.get("MOIRA_KERNEL_PATH") or str(
    Path.home() / ".moira" / "kernels" / "de440.bsp"
)

if not Path(_KERNEL_PATH).exists():
    raise FileNotFoundError(
        f"Moira planetary kernel not found at {_KERNEL_PATH}. "
        "Run: python -m moira.download_kernels  (or place de440.bsp there)."
    )

# Moira-compatible minor-body kernel (centaurs.bsp / minor_bodies.bsp) enables
# Chiron ACG lines. The NAIF asteroids.bsp is rejected by Moira's native reader,
# so Chiron is enabled only when a compatible kernel is actually present.
_MINOR_BODY_KERNELS = ("centaurs.bsp", "minor_bodies.bsp")
_MINOR_KERNEL_PATH = next(
    (Path.home() / ".moira" / "kernels" / name
     for name in _MINOR_BODY_KERNELS
     if (Path.home() / ".moira" / "kernels" / name).exists()),
    None,
)
_HAS_CHIRON = _MINOR_KERNEL_PATH is not None

# Loaded once for the process lifetime. The planetary reader is always the base.
# When a compatible minor-body kernel is present we expose it through a
# KernelPool so that ``reader.position(0, 2002060, jd)`` resolves Chiron by
# composing the heliocentric (center=10) small-body segment with the Sun's
# barycentric state. Without this, the de440-only reader raises for Chiron.
if _HAS_CHIRON:
    _READER: KernelPool = KernelPool(
        [SpkReader(_KERNEL_PATH), SmallBodyKernel(_MINOR_KERNEL_PATH)]
    )
else:
    _READER = SpkReader(_KERNEL_PATH)


@contextmanager
def moira_reader() -> Iterator[None]:
    """Route all Moira ephemeris calls to the de440 kernel for this block."""
    with use_reader_override(_READER):
        yield


# Bodies drawn on the globe. Names match Moira's Body enum strings.
# Chiron is a minor body and requires the optional asteroids.bsp kernel.
# The ten classical planets. Moira computes nodes/minor bodies via separate
# modules; those can be layered in later (ACG for the lunar node needs a
# dedicated path and a minor-body kernel for Chiron).
BODIES: list[str] = [
    "Sun",
    "Moon",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Pluto",
]

# Stable colours per planet (hex) for the globe legend/layers.
PLANET_COLORS: dict[str, str] = {
    "Sun": "#FFD700",
    "Moon": "#C5C5C5",
    "Mercury": "#FF6B35",
    "Venus": "#F7C948",
    "Mars": "#E63946",
    "Jupiter": "#4CC9F0",
    "Saturn": "#8D99AE",
    "Uranus": "#80FFDB",
    "Neptune": "#5A7FFF",
    "Pluto": "#9D4EDD",
    "Chiron": "#2EC4B6",
    "Lilith": "#FF3366",
    "True Node": "#FF70A6",
}


def jd_from_iso(iso_datetime: str) -> float:
    """Parse an ISO-8601 datetime (must be timezone-aware) into a UT Julian Day.

    Moira's ``jd_from_datetime`` converts to UTC, so callers must include an
    offset, e.g. ``"1990-05-15T14:30:00+10:00"``.
    """
    iso_fixed = re.sub(r'([+-]\d{2}):(\d{2})$', r'\1\2', iso_datetime)
    dt = datetime.fromisoformat(iso_fixed)
    if dt.tzinfo is None:
        raise ValueError(
            "birth.datetime must be timezone-aware (include a UTC offset), "
            "e.g. '1990-05-15T14:30:00+10:00'"
        )
    from moira.julian import jd_from_datetime

    return jd_from_datetime(dt)
