"""
Solar Return and Lunar Return ACG maps.

A solar return chart is cast for the moment the transited Sun returns to the
natal Sun's longitude each year — classically used to map "where to spend your
birthday". A lunar return is the same idea with the Moon (~27.3-day cycle).

We lean on Moira's ``batch_returns`` to find the exact return Julian Date, then
run the existing ``generate_acg`` machinery against that moment. The result is
a normal ACG line payload the globe can render as an overlay.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import moira.batch
from moira.chart import create_chart
from moira_engine import BODIES, jd_from_iso, moira_reader

from acg import generate_acg

# J2000.0 epoch as a UTC datetime — the anchor for Julian Date <-> calendar.
_J2000 = datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
_JD_J2000 = 2451545.0


def _jd_to_iso(jd_ut: float) -> str:
    """Convert a Julian Date to an ISO-8601 UTC string (``YYYY-MM-DDTHH:MM:SSZ``)."""
    delta = jd_ut - _JD_J2000
    dt = _J2000 + timedelta(days=delta)
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def _natal_longitude(
    jd_ut: float, lat: float, lon: float, body: str, reader: Any = None,
) -> float:
    """Return the ecliptic longitude of *body* at the given moment."""
    chart = create_chart(jd_ut, lat, lon, bodies=list(BODIES), reader=reader)
    return chart.planets[body].longitude


def generate_solar_return_acg(
    iso_datetime: str,
    birth_lat: float,
    birth_lon: float,
    year: int,
    bodies: list[str] | None = None,
    lat_step: float = 1.0,
) -> dict[str, Any]:
    """ACG lines for the solar return that falls in *year*.

    Returns the return moment (ISO) plus a standard ACG payload the globe can
    render as an overlay.
    """
    jd_birth = jd_from_iso(iso_datetime)
    with moira_reader() as reader:
        sun_lon = _natal_longitude(jd_birth, birth_lat, birth_lon, 'Sun', reader=reader)
        req = moira.batch.ReturnBatchRequest(kind='solar_return', natal_lon=sun_lon, year=year)
        result = moira.batch.batch_returns((req,), reader=reader)[0]
        if result.failure is not None or result.jd_ut is None:
            raise ValueError(f'Solar return calculation failed: {result.failure}')
        return_jd = result.jd_ut
        return_iso = _jd_to_iso(return_jd)
        acg = generate_acg(return_iso, birth_lat, birth_lon, bodies=bodies, lat_step=lat_step)
    acg['return_type'] = 'solar'
    acg['return_year'] = year
    acg['return_moment_iso'] = return_iso
    acg['return_body'] = 'Sun'
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
    """ACG lines for the next lunar return.

    If *month* and *year* are given, returns the lunar return falling in that
    calendar month; otherwise returns the first lunar return after the birth
    moment (useful for "this month's lunar return").

    Returns the return moment (ISO) plus a standard ACG payload.
    """
    jd_birth = jd_from_iso(iso_datetime)
    with moira_reader() as reader:
        moon_lon = _natal_longitude(jd_birth, birth_lat, birth_lon, 'Moon', reader=reader)
        if month is not None and year is not None:
            # Start searching from the 1st of the target month so the return
            # lands in that calendar month.
            from datetime import datetime, timezone
            start_dt = datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)
            jd_start = _JD_J2000 + (start_dt - _J2000).total_seconds() / 86400.0
        else:
            jd_start = jd_birth
        req = moira.ReturnBatchRequest(
            kind='lunar_return',
            natal_lon=moon_lon,
            jd_start=jd_start,
        )
        result = moira.batch_returns((req,), reader=reader)[0]
        if result.failure is not None or result.jd_ut is None:
            raise ValueError(f'Lunar return calculation failed: {result.failure}')
        return_jd = result.jd_ut
        return_iso = _jd_to_iso(return_jd)
        acg = generate_acg(return_iso, birth_lat, birth_lon, bodies=bodies, lat_step=lat_step)
    acg['return_type'] = 'lunar'
    acg['return_moment_iso'] = return_iso
    acg['return_body'] = 'Moon'
    if month is not None:
        acg['return_month'] = month
    if year is not None:
        acg['return_year'] = year
    return acg
