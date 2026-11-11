"""
Swiss Ephemeris engine for the Astrocartography backend.

Cross-platform replacement for moira-astro (which only ships Windows
``cp313 win_amd64`` wheels and cannot install on render.com's Linux/Python 3.11
runtime). Uses pyswisseph (manylinux/cos wheels for cp311 and cp313) plus a
small, freely redistributable bundle of Swiss Ephemeris ``.se1`` files committed
under ``backend/ephe/``. No kernel downloads, no C compiler, no platform
specific binary.

Provides a Moira-compatible API so the rest of the backend (acg.py, analysis.py,
cities.py, electional.py, returns.py, trip_planner.py) keeps working while
gaining Chiron (and every other minor body) on every platform.
"""

from __future__ import annotations

import math
import os
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterator

import swisseph as swe

_HERE = os.path.dirname(os.path.abspath(__file__))
_EPHE_DIR = os.path.join(_HERE, "ephe")
swe.set_ephe_path(_EPHE_DIR)

_PLANET_ID: dict[str, int] = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Uranus": swe.URANUS,
    "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO,
    "Chiron": swe.CHIRON,
    "True Node": swe.TRUE_NODE,
    "North Node": swe.TRUE_NODE,
    "Mean Node": swe.MEAN_NODE,
    "South Node": swe.TRUE_NODE,
    "Lilith": swe.MEAN_APOG,
    "Mean Lilith": swe.MEAN_APOG,
    "Black Moon Lilith": swe.MEAN_APOG,
}

_BODIES: list[str] = [
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
    "Chiron",
]

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

_HAS_CHIRON = True

_ZODIAC = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

_J2000 = datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
_JD_J2000 = 2451545.0

_FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED


def _norm(lon: float) -> float:
    return lon % 360.0


def _norm_signed(lon: float) -> float:
    return ((lon + 180.0) % 360.0) - 180.0


def jd_from_iso(iso_datetime: str) -> float:
    """Parse an ISO-8601 datetime (timezone-aware) into a UT Julian Day."""
    iso_fixed = iso_datetime
    if iso_datetime.endswith("Z"):
        iso_fixed = iso_datetime[:-1] + "+00:00"
    dt = datetime.fromisoformat(iso_fixed)
    if dt.tzinfo is None:
        raise ValueError(
            "birth.datetime must be timezone-aware (include a UTC offset), "
            "e.g. '1990-05-15T14:30:00+10:00'"
        )
    utc = dt.astimezone(timezone.utc)
    h = utc.hour + utc.minute / 60.0 + utc.second / 3600.0 + utc.microsecond / 3600000.0
    return swe.julday(utc.year, utc.month, utc.day, h)


def _iso_to_jd(iso: str) -> float:
    s = iso.strip()
    if "T" not in s:
        s = s + "T12:00:00+00:00"
    return jd_from_iso(s)


def _jd_to_datetime(jd_ut: float) -> datetime:
    return _J2000 + timedelta(days=jd_ut - _JD_J2000)


def _jd_to_iso(jd_ut: float) -> str:
    dt = _J2000 + timedelta(days=jd_ut - _JD_J2000)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def gmst_deg(jd_ut: float) -> float:
    """Greenwich (mean) sidereal time in degrees at the given UT instant."""
    d = jd_ut - _JD_J2000
    t = d / 36525.0
    g = (
        280.46061837
        + 360.98564736629 * d
        + 0.000387933 * t * t
        - (t ** 3) / 38710000.0
    )
    return _norm(g)


def apparent_sidereal_time_at(jd_ut: float, longitude: float = 0.0) -> float:
    """Local sidereal time (degrees) at ``longitude`` (east positive)."""
    return _norm(gmst_deg(jd_ut) + longitude)


def true_obliquity(jd_ut: float) -> float:
    """Mean obliquity of the ecliptic (degrees)."""
    d = jd_ut - _JD_J2000
    t = d / 36525.0
    return (
        23.43929111
        - 0.0130041667 * t
        - 0.0000001639 * t * t
        + 0.0000005036 * t ** 3
    )


def ecliptic_to_equatorial(lon: float, lat: float, obliq: float) -> tuple[float, float]:
    """Convert ecliptic lon/lat to equatorial RA/Dec (degrees)."""
    ol = math.radians(lon)
    ob = math.radians(obliq)
    ra = math.degrees(
        math.atan2(math.sin(ol) * math.cos(ob) - math.tan(math.radians(lat)) * math.sin(ob), math.cos(ol))
    )
    dec = math.degrees(
        math.asin(math.sin(math.radians(lat)) * math.cos(ob) + math.cos(math.radians(lat)) * math.sin(ob) * math.sin(ol))
    )
    return _norm(ra), dec


def true_node(jd_ut: float) -> float:
    pos, _ = swe.calc_ut(jd_ut, swe.TRUE_NODE, _FLAGS)
    return _norm(pos[0])


def mean_lilith(jd_ut: float) -> float:
    pos, _ = swe.calc_ut(jd_ut, swe.MEAN_APOG, _FLAGS)
    return _norm(pos[0])


def sign_of(longitude: float) -> str:
    return _ZODIAC[int(_norm(longitude) // 30) % 12]


@dataclass
class _PlanetData:
    name: str
    longitude: float
    latitude: float
    distance: float
    speed_long: float
    retrograde: bool
    sign: str
    right_ascension: float
    declination: float


@dataclass
class _Houses:
    asc: float
    mc: float
    dsc: float
    ic: float
    cusps: tuple[float, ...]


@dataclass
class Chart:
    jd_ut: float
    lat: float
    lon: float
    planets: dict[str, _PlanetData]
    houses: _Houses


@dataclass
class ACGLine:
    planet: str
    line_type: str
    longitude: float | None
    points: list[tuple[float, float]] | None


@dataclass
class SubPoint:
    planet: str
    point_type: str
    latitude: float
    longitude: float


@dataclass
class LocalSpaceResult:
    body: str
    azimuth: float
    altitude: float
    is_above: bool


@dataclass
class Paran:
    body1: str
    circle1: str
    body2: str
    circle2: str
    orb_min: float


@dataclass
class SkyPosition:
    right_ascension: float
    declination: float


def _calc(name: str, jd_ut: float) -> _PlanetData | None:
    pid = _PLANET_ID.get(name)
    if pid is None:
        return None
    # Re-affirm the ephemeris path on every call: pyswisseph does not carry the
    # path set at import time into worker threads (FastAPI/uvicorn run sync
    # endpoints in a thread pool), so calc_ut would otherwise fall back to the
    # default path and fail to find the bundled ``.se1`` files.
    swe.set_ephe_path(_EPHE_DIR)
    pos, _ = swe.calc_ut(jd_ut, pid, _FLAGS)
    lon, lat, dist, speed = pos[0], pos[1], pos[2], pos[3]
    ra, dec = ecliptic_to_equatorial(_norm(lon), lat, true_obliquity(jd_ut))
    retrograde = speed < 0
    return _PlanetData(
        name=name,
        longitude=_norm(lon),
        latitude=lat,
        distance=dist,
        speed_long=speed,
        retrograde=retrograde,
        sign=sign_of(lon),
        right_ascension=_norm(ra),
        declination=dec,
    )


def houses_for(jd_ut: float, lat: float, lon: float, house_system: str = "P") -> _Houses:
    swe.set_ephe_path(_EPHE_DIR)
    cusps, ascmc = swe.houses(jd_ut, lat, lon, house_system.encode())
    asc, mc, dsc, ic = ascmc[0], ascmc[1], ascmc[2], ascmc[3]
    return _Houses(
        asc=_norm(asc), mc=_norm(mc), dsc=_norm(dsc), ic=_norm(ic),
        cusps=tuple(_norm(c) for c in cusps[:12]),
    )


def create_chart(
    jd_ut: float,
    latitude: float,
    longitude: float,
    bodies: list[str] | None = None,
    house_system: str = "P",
    reader: Any = None,
) -> Chart:
    bodies = bodies or list(_BODIES)
    planet_data: dict[str, _PlanetData] = {}
    for name in bodies:
        pd = _calc(name, jd_ut)
        if pd is not None:
            planet_data[name] = pd
    return Chart(
        jd_ut=jd_ut, lat=latitude, lon=longitude,
        planets=planet_data, houses=houses_for(jd_ut, latitude, longitude, house_system),
    )


def _acg_curves(
    planet: str, ra: float, dec: float, gmst: float, lat_step: float,
) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """ASC (rising) and DSC (setting) curves as (lat, lon) points."""
    asc_pts: list[tuple[float, float]] = []
    dsc_pts: list[tuple[float, float]] = []
    if math.cos(math.radians(dec)) == 0:
        return asc_pts, dsc_pts
    tan_dec = math.tan(math.radians(dec))
    lat = -90.0
    while lat <= 90.0 + 1e-9:
        arg = -math.tan(math.radians(lat)) * tan_dec
        arg = max(-1.0, min(1.0, arg))
        h0 = math.degrees(math.acos(arg))
        asc_lon = _norm(ra - h0 - gmst)
        dsc_lon = _norm(ra + h0 - gmst)
        asc_pts.append((lat, asc_lon))
        dsc_pts.append((lat, dsc_lon))
        lat += lat_step
    return asc_pts, dsc_pts


def acg_lines(
    planet_ra_dec: dict[str, tuple[float, float]],
    gmst_deg: float,
    lat_step: float = 1.0,
    jd_ut: float | None = None,
) -> list[ACGLine]:
    """ACG lines (MC/IC meridians + ASC/DSC curves) for {planet: (ra, dec)}."""
    lines: list[ACGLine] = []
    for planet, (ra, dec) in planet_ra_dec.items():
        ra = _norm(ra)
        mc_lon = _norm(ra - gmst_deg)
        ic_lon = _norm(mc_lon + 180.0)
        lines.append(ACGLine(planet=planet, line_type="MC", longitude=mc_lon, points=None))
        lines.append(ACGLine(planet=planet, line_type="IC", longitude=ic_lon, points=None))
        asc_pts, dsc_pts = _acg_curves(planet, ra, dec, gmst_deg, lat_step)
        if asc_pts:
            lines.append(ACGLine(planet=planet, line_type="ASC", longitude=None, points=asc_pts))
        if dsc_pts:
            lines.append(ACGLine(planet=planet, line_type="DSC", longitude=None, points=dsc_pts))
    return lines


def acg_from_chart(chart: Chart, bodies: list[str] | None = None, lat_step: float = 1.0) -> list[ACGLine]:
    bodies = bodies or list(chart.planets.keys())
    ra_dec = {name: (chart.planets[name].right_ascension, chart.planets[name].declination) for name in bodies if name in chart.planets}
    gmst = gmst_deg(chart.jd_ut)
    return acg_lines(ra_dec, gmst, lat_step, chart.jd_ut)


def subplanetary_from_chart(chart: Chart, bodies: list[str] | None = None) -> list[SubPoint]:
    bodies = bodies or list(chart.planets.keys())
    gmst = gmst_deg(chart.jd_ut)
    out: list[SubPoint] = []
    for name in bodies:
        pd = chart.planets.get(name)
        if pd is None:
            continue
        lon = _norm(pd.right_ascension - gmst)
        out.append(SubPoint(planet=name, point_type="Zenith", latitude=pd.declination, longitude=lon))
        out.append(SubPoint(planet=name, point_type="Nadir", latitude=-pd.declination, longitude=_norm(lon + 180.0)))
    return out


def local_space_from_chart(chart: Chart, lat: float, lon: float, bodies: list[str] | None = None) -> list[LocalSpaceResult]:
    bodies = bodies or list(chart.planets.keys())
    gmst = gmst_deg(chart.jd_ut)
    lst = _norm(gmst + lon)
    out: list[LocalSpaceResult] = []
    lat_r = math.radians(lat)
    for name in bodies:
        pd = chart.planets.get(name)
        if pd is None:
            continue
        h = _norm_signed(lst - pd.right_ascension)
        alt_r = math.asin(
            math.sin(lat_r) * math.sin(math.radians(pd.declination))
            + math.cos(lat_r) * math.cos(math.radians(pd.declination)) * math.cos(math.radians(h))
        )
        alt = math.degrees(alt_r)
        cos_alt = math.cos(alt_r)
        if abs(cos_alt) < 1e-9:
            az = 0.0
        else:
            sin_az = -math.cos(math.radians(pd.declination)) * math.sin(math.radians(h)) / cos_alt
            den = cos_alt * math.cos(lat_r)
            cos_az = (
                math.sin(math.radians(pd.declination)) - math.sin(alt_r) * math.sin(lat_r)
            ) / den if abs(den) > 1e-9 else 0.0
            sin_az = max(-1.0, min(1.0, sin_az))
            cos_az = max(-1.0, min(1.0, cos_az))
            az = _norm(math.degrees(math.atan2(sin_az, cos_az)))
        out.append(LocalSpaceResult(body=name, azimuth=az, altitude=round(alt, 6), is_above=alt > 0))
    return out


def _scan_angles(jd_ut: float, lat: float, lon: float, bodies: list[str]) -> dict[str, str | None]:
    gmst = gmst_deg(jd_ut)
    lst = _norm(gmst + lon)
    out: dict[str, str | None] = {}
    for name in bodies:
        pd = _calc(name, jd_ut)
        if pd is None:
            out[name] = None
            continue
        dec = pd.declination
        h = _norm_signed(lst - pd.right_ascension)
        if math.cos(math.radians(dec)) == 0:
            out[name] = None
            continue
        tan_dec = math.tan(math.radians(dec))
        arg = -math.tan(math.radians(lat)) * tan_dec
        arg = max(-1.0, min(1.0, arg))
        h0 = math.degrees(math.acos(arg))
        dist_mc = abs(_norm_signed(h))
        dist_ic = abs(_norm_signed(h - 180.0))
        dist_asc = abs(_norm_signed(h + h0))
        dist_dsc = abs(_norm_signed(h - h0))
        best = min(
            ("MC", dist_mc), ("IC", dist_ic), ("ASC", dist_asc), ("DSC", dist_dsc),
            key=lambda x: x[1],
        )
        out[name] = best[0] if best[1] <= 3.0 else None
    return out


def natal_parans(
    bodies: list[str], jd_ut: float, lat: float, lon: float, orb_minutes: float = 4.0,
) -> list[Paran]:
    """Best-effort natal parans: two bodies on angles within a small time window."""
    out: list[Paran] = []
    try:
        half_span = 0.5  # days (+/- 12 hours around birth)
        step = 2.0 / 24.0 / 60.0  # 2 minutes in days
        t = jd_ut - half_span
        seen: set[tuple[str, str, str, str]] = set()
        while t <= jd_ut + half_span + 1e-9:
            on_angle = _scan_angles(t, lat, lon, bodies)
            names = [n for n, c in on_angle.items() if c is not None]
            for i in range(len(names)):
                for j in range(i + 1, len(names)):
                    a, b = names[i], names[j]
                    ca, cb = on_angle[a], on_angle[b]
                    key = tuple(sorted((a, ca, b, cb)))
                    if key in seen:
                        continue
                    seen.add(key)
                    out.append(Paran(body1=a, circle1=ca, body2=b, circle2=cb, orb_min=0.0))
            t += step
        return out[:200]
    except Exception:
        return []


def sky_position_at(body: str, jd_ut: float, observer_lat: float = 0.0, observer_lon: float = 0.0) -> SkyPosition:
    pd = _calc(body, jd_ut)
    if pd is None:
        return SkyPosition(right_ascension=0.0, declination=0.0)
    return SkyPosition(right_ascension=pd.right_ascension, declination=pd.declination)


_FIXED_STAR_COORDS: dict[str, tuple[float, float]] = {
    "Sirius": (101.287, -16.716), "Canopus": (95.371, -52.697), "Arcturus": (213.915, 19.182),
    "Vega": (279.234, 38.784), "Capella": (79.171, 45.998), "Rigel": (78.534, -8.211),
    "Procyon": (114.825, 5.225), "Betelgeuse": (88.793, 7.407), "Altair": (297.686, 8.856),
    "Aldebaran": (68.676, 16.317), "Spica": (201.298, -11.161), "Antares": (247.342, -26.432),
    "Pollux": (116.329, 27.973), "Fomalhaut": (344.414, -29.622), "Deneb": (313.221, 45.293),
    "Regulus": (149.711, 11.967), "Algol": (70.634, 20.869), "Alnilam": (85.284, -1.184),
    "Bellatrix": (81.291, 6.351), "Castor": (113.651, 31.888),
}


def star_at(name: str, jd_tt: float):
    coords = _FIXED_STAR_COORDS.get(name)
    if coords is None:
        return None
    lon, lat = coords
    ra, dec = ecliptic_to_equatorial(lon, lat, true_obliquity(jd_tt))

    class _Star:
        longitude = lon
        latitude = lat
    return _Star()


class _NodesApsides:
    def __init__(self, jd_ut: float):
        self.ascending_node_lon = true_node(jd_ut)
        self.descending_node_lon = _norm(self.ascending_node_lon + 180.0)


def nodes_and_apsides_at(body: str, jd_ut: float, reader: Any = None) -> _NodesApsides:
    return _NodesApsides(jd_ut)


def is_void_of_course(jd_ut: float, reader: Any = None, modern: bool = False) -> bool:
    """Best-effort: Moon's last major aspect before leaving its current sign."""
    try:
        moon = _calc("Moon", jd_ut)
        if moon is None:
            return False
        moon_lon = moon.longitude
        sign_end = (int(moon_lon // 30) + 1) * 30.0
        aspects = (0.0, 60.0, 90.0, 120.0, 180.0)
        for other in ("Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"):
            od = _calc(other, jd_ut)
            if od is None:
                continue
            for asp in aspects:
                if abs(_norm_signed(od.longitude - moon_lon) - asp) <= 8.0:
                    return False
        return True
    except Exception:
        return False


@contextmanager
def moira_reader() -> Iterator[None]:
    """No-op context manager kept for Moira API compatibility."""
    yield

BODIES: list[str] = list(_BODIES)
