"""
Electional travel timing.

Given a destination and a date range, score each day (and best hour) on how
favourable the transit + relocated conditions are for travel / arrival.

Scoring is intentionally transparent: each day gets a 0-100 score plus a short
list of the best influences that drove it, so the user can see *why* a day
ranked highly.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any

from moira.chart import create_chart
from moira_engine import BODIES, jd_from_iso, moira_reader
from moira.nodes import nodes_and_apsides_at
try:
    from moira import is_void_of_course as _is_voc
except Exception:  # pragma: no cover - optional on some moira builds
    def _is_voc(jd, reader=None, modern=False):
        return False

# ---- Scoring weights -------------------------------------------------------
BENEFICIANS = {'Jupiter', 'Venus', 'Sun'}
MALEFICIANS = {'Saturn', 'Mars', 'Pluto'}

_ORB = {
    'conjunction': 4.0,
    'trine': 5.0,
    'sextile': 5.0,
    'square': 4.0,
    'opposition': 4.0,
}

_TRAVEL_ANGLES = ('ASC', 'MC', 'DSC', 'IC')


def _iso_to_jd(iso: str) -> float:
    # Accept either a plain date or a full ISO datetime.
    s = iso.strip()
    if 'T' not in s:
        s = s + 'T12:00:00+00:00'
    return jd_from_iso(s)


def _jd_to_datetime(jd_ut: float) -> datetime:
    _J2000 = datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    return _J2000 + timedelta(days=jd_ut - 2451545.0)


def _angular_distance(a: float, b: float) -> float:
    d = abs(a - b) % 360.0
    return d if d <= 180 else 360 - d


def _house_of(longitude: float, cusps: tuple[float, ...]) -> int:
    lon = longitude % 360.0
    n = len(cusps)
    for h in range(1, n + 1):
        start = cusps[h - 1] % 360.0
        end = cusps[h % n] % 360.0
        if start <= end:
            if start <= lon < end:
                return h
        else:
            if lon >= start or lon < end:
                return h
    return n


TRAVEL_BODIES: list[str] = [
    "Sun", "Moon", "Mercury", "Venus", "Mars",
    "Jupiter", "Saturn", "Pluto",
]


def _chart_planets(jd_ut: float, lat: float, lon: float, reader: Any = None, bodies: list[str] | None = None) -> dict[str, Any]:
    """Return (planet longitudes dict, chart) for a moment/location."""
    chart = create_chart(jd_ut, lat, lon, bodies=list(bodies or BODIES), reader=reader)
    return {name: pd for name, pd in chart.planets.items()}, chart


def _south_node_lon(jd_ut: float, reader: Any = None) -> float:
    try:
        nd = nodes_and_apsides_at('Moon', jd_ut, reader=reader)
        return float(nd.descending_node_lon) % 360.0
    except Exception:
        return 0.0


def _classify_aspect(a: float, b: float):
    """Return (aspect_name, orb_used) or (None, None)."""
    d = _angular_distance(a, b)
    # conjunction
    if d <= _ORB['conjunction']:
        return 'conjunction', _ORB['conjunction']
    # opposition
    if _angular_distance(d, 180.0) <= _ORB['opposition']:
        return 'opposition', _ORB['opposition']
    # square
    if _angular_distance(d, 90.0) <= _ORB['square']:
        return 'square', _ORB['square']
    # trine
    if _angular_distance(d, 120.0) <= _ORB['trine']:
        return 'trine', _ORB['trine']
    # sextile
    if _angular_distance(d, 60.0) <= _ORB['sextile']:
        return 'sextile', _ORB['sextile']
    return None, None


def _natal_longitudes(birth_iso: str, birth_lat: float, birth_lon: float) -> dict[str, float]:
    jd = _iso_to_jd(birth_iso)
    with moira_reader():
        planets, _ = _chart_planets(jd, birth_lat, birth_lon, bodies=TRAVEL_BODIES)
    return {name: pd.longitude for name, pd in planets.items()}


def _score_hour(
    jd_hour: float,
    dest_lat: float,
    dest_lon: float,
    natal_lons: dict[str, float],
    reader: Any,
) -> tuple[float, list[str], list[str]]:
    """Return (score, influences, warnings) for a single hour sample."""
    planets, chart = _chart_planets(jd_hour, dest_lat, dest_lon, reader=reader, bodies=TRAVEL_BODIES)
    transits = {name: pd.longitude for name, pd in planets.items()}
    # retrograde map
    retro = {name: bool(pd.retrograde) for name, pd in planets.items()}

    houses = chart.houses
    asc = float(houses.asc)
    mc = float(houses.mc)
    angles = {
        'ASC': asc % 360.0,
        'MC': mc % 360.0,
        'DSC': (asc + 180.0) % 360.0,
        'IC': (mc + 180.0) % 360.0,
    }

    score = 50.0
    influences: list[str] = []
    warnings: list[str] = []

    # 1. Transit conjunctions to relocated angles
    for planet, t_lon in transits.items():
        for angle_name, a_lon in angles.items():
            dist = _angular_distance(t_lon, a_lon)
            if dist <= 4.0:
                orb_quality = 1.0 - (dist / 4.0)
                if planet in BENEFICIANS:
                    pts = 12.0 * orb_quality
                    score += pts
                    influences.append(
                        f'✦ {planet} conjunct relocated {angle_name} ({dist:.1f}° orb)'
                    )
                elif planet in MALEFICIANS:
                    pts = 10.0 * orb_quality
                    score -= pts
                    influences.append(
                        f'✧ {planet} conjunct relocated {angle_name} ({dist:.1f}° orb)'
                    )

    # 2. Aspects between transits and natal (relocated) planets
    for tp, t_lon in transits.items():
        for np_, n_lon in natal_lons.items():
            aspect, orb_used = _classify_aspect(t_lon, n_lon)
            if aspect is None:
                continue
            orb = _angular_distance(t_lon, n_lon)
            # remap orb for non-conjunction aspects
            if aspect != 'conjunction':
                orb = min(
                    _angular_distance(t_lon, n_lon),
                    _angular_distance(t_lon, n_lon),
                )
            quality = max(0.0, 1.0 - (orb / orb_used))
            if tp in BENEFICIANS and aspect in ('conjunction', 'trine', 'sextile'):
                base = {'conjunction': 8.0, 'trine': 6.0, 'sextile': 4.0}[aspect]
                score += base * quality
                influences.append(
                    f'✦ {tp} {aspect} natal {np_} ({orb:.1f}°)'
                )
            elif tp in MALEFICIANS and aspect in ('conjunction', 'square', 'opposition'):
                base = {'conjunction': 8.0, 'square': 7.0, 'opposition': 6.0}[aspect]
                score -= base * quality
                influences.append(
                    f'✧ {tp} {aspect} natal {np_} ({orb:.1f}°)'
                )

    # 3. South Node (malefic) conjunctions to angles
    sn = _south_node_lon(jd_hour, reader=reader)
    for angle_name, a_lon in angles.items():
        dist = _angular_distance(sn, a_lon)
        if dist <= 4.0:
            q = 1.0 - dist / 4.0
            score -= 6.0 * q
            influences.append(f'✧ South Node conjunct relocated {angle_name} ({dist:.1f}°)')

    # 4. Moon layer
    moon_lon = transits.get('Moon', 0.0)
    sun_lon = transits.get('Sun', 0.0)
    elong = (moon_lon - sun_lon) % 360.0
    if elong <= 180.0:
        score += 2.0
    else:
        score -= 1.0
    try:
        if _is_voc(jd_hour, reader=reader):
            score -= 8.0
            influences.append('✧ Moon void of course')
            warnings.append('Moon void of course')
    except Exception:
        pass
    mhouse = _house_of(moon_lon, tuple(houses.cusps))
    if mhouse in (9, 10):
        score += 3.0
        influences.append(f'✦ Moon in house {mhouse}')
    elif mhouse in (8, 12):
        score -= 2.0

    # 5. Mercury retrograde
    if retro.get('Mercury', False):
        score -= 2.0
        warnings.append('Mercury retrograde')

    # 6. Eclipse season
    node_lon = sn  # ascending = +180 (reuses value from step 3)
    asc_node = (node_lon + 180.0) % 360.0
    if _angular_distance(sun_lon, asc_node) <= 5.0 or _angular_distance(sun_lon, node_lon) <= 5.0:
        warnings.append('Eclipse season (Sun near node)')
    if _angular_distance(moon_lon, asc_node) <= 5.0 or _angular_distance(moon_lon, node_lon) <= 5.0:
        warnings.append('Eclipse season (Moon near node)')

    # 7. Saturn/Pluto hard-aspect warning to angles (already scored via conjunctions above)
    for p in ('Saturn', 'Pluto'):
        if p in transits:
            for an, al in angles.items():
                d = _angular_distance(transits[p], al)
                if d <= 4.0 or _angular_distance(d, 90.0) <= 3.0 or _angular_distance(d, 180.0) <= 3.0:
                    warnings.append(f'{p} hard aspect to relocated {an}')

    score = max(0.0, min(100.0, score))
    # de-dupe warnings
    warnings = list(dict.fromkeys(warnings))
    return score, influences[:6], warnings[:6]


def rate_travel_window(
    birth_iso: str,
    birth_lat: float,
    birth_lon: float,
    dest_lat: float,
    dest_lon: float,
    start_date: str,
    days: int = 30,
    hour_step: int = 8,
    stay_days: int = 3,
    include_warnings: bool = True,
) -> list[dict[str, Any]]:
    """Score each day in the window for travel favourability.

    Returns a list of dicts with date, score (best hour), best_hour, hourly,
    influences, arrival_score, stay_score, warnings.
    """
    start_jd = _iso_to_jd(start_date)
    natal_lons = _natal_longitudes(birth_iso, birth_lat, birth_lon)

    results: list[dict[str, Any]] = []
    with moira_reader() as reader:
        for day_offset in range(days):
            base_jd = start_jd + day_offset
            # sample hours
            hours = list(range(0, 24, max(1, hour_step)))
            if 23 not in hours:
                hours.append(23)
            hourly_scores: list[tuple[int, float, list[str], list[str]]] = []
            for h in hours:
                jd_hour = base_jd + (h / 24.0)
                s, infs, warns = _score_hour(jd_hour, dest_lat, dest_lon, natal_lons, reader)
                hourly_scores.append((h, s, infs, warns))

            # best hour
            best = max(hourly_scores, key=lambda x: x[1])
            best_hour, best_score, best_infs, best_warns = best
            # stay score: mean of top-3 hourly
            sorted_scores = sorted((x[1] for x in hourly_scores), reverse=True)
            top3 = sorted_scores[:3]
            stay_score = sum(top3) / len(top3) if top3 else best_score

            dt = _jd_to_datetime(base_jd)
            date_str = dt.strftime('%Y-%m-%d')

            results.append({
                'date': date_str,
                'score': round(best_score, 1),
                'best_hour': best_hour,
                'hourly': [{'hour': h, 'score': round(s, 1)} for h, s, _, _ in hourly_scores],
                'influences': best_infs,
                'arrival_score': round(best_score, 1),
                'stay_score': round(stay_score, 1),
                'departure_score': None,
                'warnings': best_warns if include_warnings else [],
            })

    return results
