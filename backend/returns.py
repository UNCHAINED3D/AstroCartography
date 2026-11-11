"""
Solar Return and Lunar Return ACG maps.

A solar return chart is cast for the moment the transited Sun returns to the
natal Sun's longitude each year — classically used to map "where to spend your
birthday". A lunar return is the same idea with the Moon (~27.3-day cycle).

We find the return Julian Date by scanning the Swiss Ephemeris for the moment
the transiting Sun/Moon longitude equals the natal longitude, then run the
existing ``generate_acg`` machinery against that moment. The result is a normal
ACG line payload the globe can render as an overlay.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from swe_engine import (
    BODIES,
    _calc,
    create_chart,
    jd_from_iso,
    moira_reader,
)

from acg import generate_acg

_J2000 = datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
_JD_J2000 = 2451545.0


def _jd_to_iso(jd_ut: float) -> str:
    delta = jd_ut - _JD_J2000
    dt = _J2000 + timedelta(days=delta)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _norm_signed(lon: float) -> float:
    return ((lon + 180.0) % 360.0) - 180.0


def _body_lon(jd_ut: float, body: str) -> float:
    pd = _calc(body, jd_ut)
    if pd is None:
        raise ValueError(f"could not compute {body} position")
    return pd.longitude


def _natal_longitude(
    jd_ut: float, lat: float, lon: float, body: str, reader: Any = None,
) -> float:
    chart = create_chart(jd_ut, lat, lon, bodies=list(BODIES), reader=reader)
    return chart.planets[body].longitude


def _find_return(
    body: str, natal_lon: float, start_jd: float, scan_days: float,
) -> float | None:
    """First JD at/after ``start_jd`` where ``body`` longitude returns to ``natal_lon``."""
    step = 1.0 / 24.0  # one hour
    t = start_jd
    prev = _norm_signed(_body_lon(t, body) - natal_lon)
    steps = int(scan_days * 24) + 1
    for _ in range(steps):
        t2 = t + step
        diff = _norm_signed(_body_lon(t2, body) - natal_lon)
        if abs(diff) < 1e-7:
            return t2
        if prev * diff < 0:
            a, b, da, db = t, t2, prev, diff
            for _ in range(50):
                m = (a + b) / 2.0
                dm = _norm_signed(_body_lon(m, body) - natal_lon)
                if abs(dm) < 1e-9:
                    return m
                if da * dm <= 0:
                    b, db = m, dm
                else:
                    a, da = m, dm
            return (a + b) / 2.0
        t, prev = t2, diff
    return None


def _start_of_year_jd(year: int) -> float:
    return jd_from_iso(f"{year}-01-01T00:00:00+00:00")


def generate_solar_return_acg(
    iso_datetime: str,
    birth_lat: float,
    birth_lon: float,
    year: int,
    bodies: list[str] | None = None,
    lat_step: float = 1.0,
) -> dict[str, Any]:
    """ACG lines for the solar return that falls in *year*."""
    jd_birth = jd_from_iso(iso_datetime)
    with moira_reader() as reader:
        sun_lon = _natal_longitude(jd_birth, birth_lat, birth_lon, "Sun", reader=reader)
        start_jd = _start_of_year_jd(year)
        return_jd = _find_return("Sun", sun_lon, start_jd, 366.0)
        if return_jd is None:
            raise ValueError(f"Solar return calculation failed: no Sun return in {year}")
        return_iso = _jd_to_iso(return_jd)
        acg = generate_acg(return_iso, birth_lat, birth_lon, bodies=bodies, lat_step=lat_step)
    acg["return_type"] = "solar"
    acg["return_year"] = year
    acg["return_moment_iso"] = return_iso
    acg["return_body"] = "Sun"
    return acg


def generate_lunar_return_acg(
    iso_datetime: str,
    birth_lat: float,
    birth_lon: float,
    month: int | None = None,
    year: int | None = None,
    bodies: list[str] | None = None,
    lat_step: float = 1.0,
) -> dict[str, Any]:
    """ACG lines for the next lunar return."""
    jd_birth = jd_from_iso(iso_datetime)
    with moira_reader() as reader:
        moon_lon = _natal_longitude(jd_birth, birth_lat, birth_lon, "Moon", reader=reader)
        if month is not None and year is not None:
            jd_start = jd_from_iso(f"{year}-{month:02d}-01T00:00:00+00:00")
        else:
            jd_start = jd_birth
        return_jd = _find_return("Moon", moon_lon, jd_start, 90.0)
        if return_jd is None:
            raise ValueError("Lunar return calculation failed: no Moon return found")
        return_iso = _jd_to_iso(return_jd)
        acg = generate_acg(return_iso, birth_lat, birth_lon, bodies=bodies, lat_step=lat_step)
    acg["return_type"] = "lunar"
    acg["return_moment_iso"] = return_iso
    acg["return_body"] = "Moon"
    if month is not None:
        acg["return_month"] = month
    if year is not None:
        acg["return_year"] = year
    return acg
