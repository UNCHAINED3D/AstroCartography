"""
Electional travel timing.

Given a destination and a date range, score each day on how favourable the
transit + relocated conditions are for travel / arrival. This is the
"when should I arrive in Berlin?" feature.

Scoring is intentionally transparent: each day gets a 0–100 score plus a
short list of the best influences that drove it, so the user can see *why*
a day ranked highly.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from moira.chart import create_chart
from moira_engine import BODIES, jd_from_iso, moira_reader

# ---- Scoring weights -------------------------------------------------------
# Positive influences (add points), negative influences (subtract points).
BENEFICIANS = {'Jupiter', 'Venus', 'Sun'}
MALEFICIANS = {'Saturn', 'Mars', 'Pluto', 'South Node'}

# Transit orb within which a planet hitting a relocated angle scores.
_ORB_DEG = 4.0

# Relocated angles we care about for travel.
_TRAVEL_ANGLES = ('ASC', 'MC', 'DSC', 'IC')


def _iso_to_jd(iso: str) -> float:
    return jd_from_iso(iso)


def _jd_to_datetime(jd_ut: float) -> datetime:
    _J2000 = datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    return _J2000 + timedelta(days=jd_ut - 2451545.0)


def _transit_longitudes(jd_ut: float, lat: float, lon: float, reader: Any = None) -> dict[str, float]:
    """Return transit planet longitudes for the given moment + location."""
    chart = create_chart(jd_ut, lat, lon, bodies=list(BODIES), reader=reader)
    return {name: pd.longitude for name, pd in chart.planets.items()}


def _relocated_angles(jd_ut: float, lat: float, lon: float, reader: Any = None) -> dict[str, float]:
    """Return the relocated ASC/MC/DSC/IC longitudes for the given moment.

    Moira's ``Chart`` object exposes house cusps via ``chart.houses`` (a
    ``HouseCusps`` object with a ``cusps`` tuple and direct ``asc`` / ``mc``
    attributes). We derive DSC and IC as the opposite points (+180°).
    """
    chart = create_chart(jd_ut, lat, lon, bodies=list(BODIES), reader=reader)
    houses = getattr(chart, 'houses', None)
    if houses is None:
        return {}

    # HouseCusps has direct .asc and .mc attributes (in degrees).
    asc = float(houses.asc) if hasattr(houses, 'asc') else None
    mc = float(houses.mc) if hasattr(houses, 'mc') else None

    # Fallback: derive from the cusps tuple (index 0 = ASC, index 9 = MC).
    if asc is None or mc is None:
        cusp_list = getattr(houses, 'cusps', None)
        if isinstance(cusp_list, (list, tuple)) and len(cusp_list) >= 12:
            if asc is None:
                asc = float(cusp_list[0])
            if mc is None:
                mc = float(cusp_list[9])

    if asc is None or mc is None:
        return {}

    return {
        'ASC': asc % 360.0,
        'MC': mc % 360.0,
        'DSC': (asc + 180.0) % 360.0,
        'IC': (mc + 180.0) % 360.0,
    }


def _angular_distance(a: float, b: float) -> float:
    """Shortest distance between two longitudes in degrees (0–180)."""
    d = abs(a - b) % 360.0
    return d if d <= 180 else 360 - d


def rate_travel_window(
    birth_iso: str,
    birth_lat: float,
    birth_lon: float,
    dest_lat: float,
    dest_lon: float,
    start_date: str,
    days: int = 30,
) -> list[dict[str, Any]]:
    """Score each day in the window for travel favourability.

    *start_date* is ``YYYY-MM-DD`` (UTC assumed, noon). Returns a list of
    ``{date, score, influences}`` dicts, one per day, sorted chronologically.
    Score is 0–100 (higher = more favourable).
    """
    # ``start_date`` is a plain date string ("YYYY-MM-DD"), not a full ISO
    # datetime. jd_from_iso needs a time component, so append noon UTC.
    start_jd = _iso_to_jd(f'{start_date}T12:00:00+00:00')
    results: list[dict[str, Any]] = []

    with moira_reader() as reader:
        for day_offset in range(days):
            jd = start_jd + day_offset
            dt = _jd_to_datetime(jd)
            date_str = dt.strftime('%Y-%m-%d')

            transits = _transit_longitudes(jd, dest_lat, dest_lon, reader=reader)
            angles = _relocated_angles(jd, dest_lat, dest_lon, reader=reader)

            score = 50.0  # neutral baseline
            influences: list[str] = []

            for planet, t_lon in transits.items():
                for angle_name, a_lon in angles.items():
                    dist = _angular_distance(t_lon, a_lon)
                    if dist <= _ORB_DEG:
                        orb_quality = 1.0 - (dist / _ORB_DEG)
                        if planet in BENEFICIANS:
                            pts = 12 * orb_quality
                            score += pts
                            influences.append(
                                f'✦ {planet} conjunct relocated {angle_name} '
                                f'({dist:.1f}° orb)'
                            )
                        elif planet in MALEFICIANS:
                            pts = 10 * orb_quality
                            score -= pts
                            influences.append(
                                f'✧ {planet} conjunct relocated {angle_name} '
                                f'({dist:.1f}° orb)'
                            )

            score = max(0.0, min(100.0, score))
            results.append({
                'date': date_str,
                'score': round(score, 1),
                'influences': influences[:5],  # cap to top 5
            })

    return results
