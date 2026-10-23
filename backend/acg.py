"""
Astrocartography (ACG) calculation and GeoJSON serialization.

Combines Moira's ``acg_from_chart`` (MC/IC meridians + ASC/DSC curves),
``subplanetary_from_chart`` (Zenith/Nadir points), node ACG (via ``acg_lines``),
``local_space_from_chart`` (birth-place rays) and ``natal_parans`` (crossings)
into a single GeoJSON-ish payload the globe can render directly.

Coordinates are emitted as GeoJSON ``[longitude, latitude]``. Antimeridian
crossings in ASC/DSC curves are split on the backend so the globe never draws
a line streaking across the whole Earth.
"""

from __future__ import annotations

from typing import Any

import geometry
from moira_engine import (
    BODIES,
    PLANET_COLORS,
    _HAS_CHIRON,
    jd_from_iso,
    moira_reader,
)


def _line_id(planet: str, angle: str) -> str:
    return f"{planet.lower().replace(' ', '-')}-{angle.lower()}"


def _circle_to_angle(circle: str) -> str:
    """Map Moira's mundane-circle name to our MC/IC/ASC/DSC angle code."""
    c = (circle or "").lower()
    if "ris" in c:
        return "ASC"
    if "set" in c:
        return "DSC"
    if "culm" in c or "mc" in c:
        return "MC"
    if "anti" in c or "ic" in c:
        return "IC"
    return circle


def _node_acg_lines(jd_ut: float, lat_step: float) -> list[Any]:
    """Compute ACG lines for the True Lunar Node via Moira's ``acg_lines``.

    The node is computed analytically (no planetary kernel needed): its
    ecliptic longitude is converted to RA/Dec, then run through the same ACG
    machinery Moira uses for planets.
    """
    try:
        from moira.astrocartography import acg_lines as _acg_lines
        from moira.coordinates import ecliptic_to_equatorial
        from moira.julian import apparent_sidereal_time_at
        from moira.nodes import true_node
        from moira.obliquity import true_obliquity

        nd = true_node(jd_ut)
        obliq = true_obliquity(jd_ut)
        ra, dec = ecliptic_to_equatorial(nd.longitude, 0.0, obliq)
        gmst_deg = apparent_sidereal_time_at(jd_ut, longitude=0.0)
        return _acg_lines(
            {"True Node": (ra, dec)}, gmst_deg, lat_step=lat_step, jd_ut=jd_ut
        )
    except Exception as exc:  # node math is best-effort; never block the chart
        print(f"[acg] node lines skipped: {exc}")
        return []


def _lilith_acg_lines(jd_ut: float, lat_step: float) -> list[Any]:
    """Compute ACG lines for Mean Black Moon Lilith via Moira's ``acg_lines``."""
    try:
        from moira.astrocartography import acg_lines as _acg_lines
        from moira.coordinates import ecliptic_to_equatorial
        from moira.julian import apparent_sidereal_time_at
        from moira.nodes import mean_lilith
        from moira.obliquity import true_obliquity

        ld = mean_lilith(jd_ut)
        obliq = true_obliquity(jd_ut)
        ra, dec = ecliptic_to_equatorial(ld.longitude, 0.0, obliq)
        gmst_deg = apparent_sidereal_time_at(jd_ut, longitude=0.0)
        return _acg_lines(
            {"Lilith": (ra, dec)}, gmst_deg, lat_step=lat_step, jd_ut=jd_ut
        )
    except Exception as exc:
        print(f"[acg] lilith lines skipped: {exc}")
        return []



def _local_space_list(chart: Any, lat: float, lon: float, bodies: list[str]) -> list[dict[str, Any]]:
    """Birth-place Local Space rays, one per body, as GeoJSON LineStrings."""
    from moira.local_space import local_space_from_chart

    results = local_space_from_chart(chart, lat, lon, bodies=bodies)
    out: list[dict[str, Any]] = []
    for r in results:
        dest_lat, dest_lon = geometry.destination_point(lat, lon, float(r.azimuth), 50.0)
        out.append(
            {
                "planet": r.body,
                "azimuth": round(float(r.azimuth), 2),
                "altitude": round(float(r.altitude), 2),
                "is_above": bool(r.is_above),
                "color": PLANET_COLORS.get(r.body, "#ffffff"),
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [round(lon, 6), round(lat, 6)],
                        [dest_lon, dest_lat],
                    ],
                },
            }
        )
    return out


def _paran_list(
    polylines: dict[tuple[str, str], list[list[float]]],
    jd_ut: float,
    lat: float,
    lon: float,
    bodies: list[str],
) -> list[dict[str, Any]]:
    """Active natal parans, each placed at the intersection of its two ACG lines."""
    from moira.parans import natal_parans

    try:
        prs = natal_parans(bodies, jd_ut, lat, lon, orb_minutes=4.0)
    except Exception as exc:
        print(f"[acg] parans skipped: {exc}")
        return []

    out: list[dict[str, Any]] = []
    for p in prs:
        a = polylines.get((p.body1, _circle_to_angle(p.circle1)))
        b = polylines.get((p.body2, _circle_to_angle(p.circle2)))
        pt = geometry.intersect_lines(a, b) if (a and b) else None
        if not pt:
            pt = [round(lon, 6), round(lat, 6)]
        out.append(
            {
                "planet_a": p.body1,
                "circle_a": p.circle1,
                "planet_b": p.body2,
                "circle_b": p.circle2,
                "orb_min": round(p.orb_min, 2),
                "latitude": pt[1],
                "longitude": pt[0],
            }
        )
    return out


def generate_acg(
    iso_datetime: str,
    latitude: float,
    longitude: float,
    bodies: list[str] | None = None,
    lat_step: float = 1.0,
) -> dict[str, Any]:
    """Compute ACG lines + subplanetary points + local space + parans.

    Returns::

        {
          "lines": [ {id, planet, angle, color, geometry} ],
          "subplanetary_points": [ {planet, type, latitude, longitude, color} ],
          "local_space": [ {planet, azimuth, altitude, is_above, color, geometry} ],
          "parans": [ {planet_a, circle_a, planet_b, circle_b, orb_min, latitude, longitude} ]
        }
    """
    bodies = bodies or list(BODIES)
    calc_bodies = list(bodies)
    if _HAS_CHIRON and "Chiron" not in calc_bodies:
        calc_bodies.append("Chiron")

    # Subplanetary (Zenith/Nadir) points and local-space rays route through
    # ``planet_at``, which Moira restricts to non-minor bodies. Chiron is kept in
    # ``calc_bodies`` for the ACG line generation (which supports it) but is
    # excluded from those two sub-calls so it never blocks the chart.
    _minor_bodies = {b for b in calc_bodies if b not in BODIES}
    _planet_bodies = [b for b in calc_bodies if b not in _minor_bodies]

    from moira.astrocartography import acg_from_chart, subplanetary_from_chart
    from moira.chart import create_chart

    jd_ut = jd_from_iso(iso_datetime)

    with moira_reader():
        chart = create_chart(jd_ut, latitude, longitude, bodies=calc_bodies)
        acg_lines_main = acg_from_chart(chart, bodies=calc_bodies, lat_step=lat_step)
        subpoints = subplanetary_from_chart(chart, bodies=_planet_bodies)
        node_lines = _node_acg_lines(jd_ut, lat_step)
        lilith_lines = _lilith_acg_lines(jd_ut, lat_step)
        local_space = _local_space_list(chart, latitude, longitude, _planet_bodies)

        # Merge planet lines + node lines; build the globe features and keep the
        # unsplit polylines for paran intersection.
        all_acg = list(acg_lines_main) + node_lines + lilith_lines
        lines_out: list[dict[str, Any]] = []
        polylines: dict[tuple[str, str], list[list[float]]] = {}

        for line in all_acg:
            color = PLANET_COLORS.get(line.planet, "#ffffff")
            if line.line_type in ("MC", "IC"):
                coords = geometry.longitude_line(line.longitude, lat_step=lat_step)
                polylines[(line.planet, line.line_type)] = coords
            else:
                # Preserve the full (unsplit) polyline for intersection.
                full = [
                    [geometry._normalize_lon(pt_lon), round(pt_lat, 6)]
                    for pt_lat, pt_lon in line.points
                ]
                polylines[(line.planet, line.line_type)] = full
                segments = geometry.split_antimeridian(line.points)
                for idx, seg in enumerate(segments):
                    lines_out.append(
                        {
                            "id": f"{_line_id(line.planet, line.line_type)}-{idx}"
                            if len(segments) > 1
                            else _line_id(line.planet, line.line_type),
                            "planet": line.planet,
                            "angle": line.line_type,
                            "color": color,
                            "geometry": {"type": "LineString", "coordinates": seg},
                        }
                    )
                continue

            lines_out.append(
                {
                    "id": _line_id(line.planet, line.line_type),
                    "planet": line.planet,
                    "angle": line.line_type,
                    "color": color,
                    "geometry": {"type": "LineString", "coordinates": coords},
                }
            )

        sub_out: list[dict[str, Any]] = []
        for sp in subpoints:
            sub_out.append(
                {
                    "planet": sp.planet,
                    "type": sp.point_type,  # "Zenith" | "Nadir"
                    "latitude": round(sp.latitude, 6),
                    "longitude": round(sp.longitude, 6),
                    "color": PLANET_COLORS.get(sp.planet, "#ffffff"),
                }
            )

        # Parans need the ephemeris reader too, so compute inside this context.
        parans = _paran_list(polylines, jd_ut, latitude, longitude, bodies)

    return {
        "lines": lines_out,
        "subplanetary_points": sub_out,
        "local_space": local_space,
        "parans": parans,
    }


# ---------------------------------------------------------------------------
# Shared helpers for the advanced overlays (transit / progressed / geodetic /
# fixed-star / midpoint ACG).  All overlay generators are best-effort: they
# return `{"lines": []}` on any failure so the frontend degrades gracefully.
# ---------------------------------------------------------------------------


def _jd_tt(jd_ut: float) -> float:
    """Approximate TT Julian Day from UT (good enough for ACG geometry)."""
    return jd_ut + 69.184 / 86400.0


def _emit_lines(all_acg: list[Any], lat_step: float = 1.0) -> list[dict[str, Any]]:
    """Convert Moira ``ACGLine`` objects into the GeoJSON-ish line payload."""
    lines_out: list[dict[str, Any]] = []
    for line in all_acg:
        color = PLANET_COLORS.get(line.planet, "#ffffff")
        if line.line_type in ("MC", "IC"):
            coords = geometry.longitude_line(line.longitude, lat_step=lat_step)
            lines_out.append(
                {
                    "id": _line_id(line.planet, line.line_type),
                    "planet": line.planet,
                    "angle": line.line_type,
                    "color": color,
                    "geometry": {"type": "LineString", "coordinates": coords},
                }
            )
        else:
            segments = geometry.split_antimeridian(line.points)
            for idx, seg in enumerate(segments):
                lines_out.append(
                    {
                        "id": (
                            f"{_line_id(line.planet, line.line_type)}-{idx}"
                            if len(segments) > 1
                            else _line_id(line.planet, line.line_type)
                        ),
                        "planet": line.planet,
                        "angle": line.line_type,
                        "color": color,
                        "geometry": {"type": "LineString", "coordinates": seg},
                    }
                )
    return lines_out


def _meridian_line(
    planet: str, angle: str, longitude: float, color: str | None = None
) -> dict[str, Any]:
    """A constant-longitude meridian (used by geodetic overlays)."""
    color = color or PLANET_COLORS.get(planet, "#8ab4ff")
    return {
        "id": _line_id(planet, angle),
        "planet": planet,
        "angle": angle,
        "color": color,
        "geometry": {
            "type": "LineString",
            "coordinates": geometry.longitude_line(longitude, lat_step=1.0),
        },
    }


def _shorter_arc_midpoint(lon_a: float, lon_b: float) -> float:
    """Shorter-arc midpoint between two ecliptic longitudes, in [0, 360)."""
    a, b = lon_a % 360, lon_b % 360
    diff = abs(a - b)
    if diff <= 180:
        return (a + b) / 2 % 360
    return ((a + b) / 2 + 180) % 360


def _ra_dec_for_longitude(
    longitude: float, latitude: float, jd_tt: float
) -> tuple[float, float]:
    from moira.coordinates import ecliptic_to_equatorial
    from moira.obliquity import true_obliquity

    obliq = true_obliquity(jd_tt)
    return ecliptic_to_equatorial(longitude, latitude, obliq)


def _gmst_deg(jd_ut: float) -> float:
    from moira.julian import apparent_sidereal_time_at

    return apparent_sidereal_time_at(jd_ut, longitude=0.0)


def generate_transit_acg(
    birth_iso: str,
    birth_lat: float,
    birth_lon: float,
    transit_iso: str,
    bodies: list[str] | None = None,
    lat_step: float = 1.0,
) -> dict[str, Any]:
    """ACG lines for a second (transit) moment at the same birth location."""
    bodies = bodies or list(BODIES)
    calc_bodies = list(bodies)
    if _HAS_CHIRON and "Chiron" not in calc_bodies:
        calc_bodies.append("Chiron")
    try:
        from moira.astrocartography import acg_from_chart
        from moira.chart import create_chart

        jd_ut = jd_from_iso(transit_iso)
        with moira_reader():
            chart = create_chart(jd_ut, birth_lat, birth_lon, bodies=calc_bodies)
            lines = acg_from_chart(chart, bodies=calc_bodies, lat_step=lat_step)
        return {"lines": _emit_lines(lines, lat_step)}
    except Exception as exc:
        print(f"[acg] transit lines skipped: {exc}")
        return {"lines": []}


def generate_progressed_acg(
    birth_iso: str,
    birth_lat: float,
    birth_lon: float,
    age_years: float,
    bodies: list[str] | None = None,
    lat_step: float = 1.0,
) -> dict[str, Any]:
    """Secondary-progression ACG: progressed JD = birth_jd + age_years (days)."""
    bodies = bodies or list(BODIES)
    calc_bodies = list(bodies)
    if _HAS_CHIRON and "Chiron" not in calc_bodies:
        calc_bodies.append("Chiron")
    try:
        from moira.astrocartography import acg_lines
        from moira.planets import sky_position_at

        birth_jd = jd_from_iso(birth_iso)
        prog_jd = birth_jd + float(age_years)
        with moira_reader():
            planet_ra_dec: dict[str, tuple[float, float]] = {}
            for b in calc_bodies:
                sky = sky_position_at(
                    b, prog_jd, observer_lat=birth_lat, observer_lon=birth_lon
                )
                planet_ra_dec[b] = (sky.right_ascension, sky.declination)
            gmst = _gmst_deg(prog_jd)
            lines = acg_lines(planet_ra_dec, gmst, lat_step=lat_step, jd_ut=prog_jd)
        return {"lines": _emit_lines(lines, lat_step)}
    except Exception as exc:
        print(f"[acg] progressed lines skipped: {exc}")
        return {"lines": []}


# Classical fixed stars used for the Fixed-Star ACG overlay.  Not all names
# resolve in every Moira catalog build, so each is attempted individually and
# failures are skipped (graceful degradation).
_FIXED_STAR_NAMES: list[str] = [
    "Sirius", "Canopus", "Arcturus", "Vega", "Capella", "Rigel",
    "Procyon", "Betelgeuse", "Altair", "Aldebaran", "Spica", "Antares",
    "Pollux", "Fomalhaut", "Deneb", "Regulus", "Algol", "Alnilam",
    "Bellatrix", "Castor",
]


def generate_fixed_star_lines(
    iso_datetime: str,
    birth_lat: float,
    birth_lon: float,
    names: list[str] | None = None,
) -> dict[str, Any]:
    """MC/IC/ASC/DSC ACG lines for the brightest classical fixed stars."""
    names = names or _FIXED_STAR_NAMES
    try:
        from moira.astrocartography import acg_lines
        from moira.stars import star_at

        jd_ut = jd_from_iso(iso_datetime)
        jd_tt = _jd_tt(jd_ut)
        with moira_reader():
            planet_ra_dec: dict[str, tuple[float, float]] = {}
            for name in names:
                try:
                    star = star_at(name, jd_tt)
                except Exception:
                    continue
                if star is None:
                    continue
                ra, dec = _ra_dec_for_longitude(
                    star.longitude, star.latitude, jd_tt
                )
                planet_ra_dec[name] = (ra, dec)
            if not planet_ra_dec:
                return {"lines": []}
            gmst = _gmst_deg(jd_ut)
            lines = acg_lines(planet_ra_dec, gmst, lat_step=1.0, jd_ut=jd_ut)
        out = _emit_lines(lines, 1.0)
        for ln in out:
            ln["color"] = "#c9a0ff"
        return {"lines": out}
    except Exception as exc:
        print(f"[acg] fixed-star lines skipped: {exc}")
        return {"lines": []}


def generate_midpoint_lines(
    iso_datetime: str,
    birth_lat: float,
    birth_lon: float,
    pairs: list[list[str]] | None = None,
) -> dict[str, Any]:
    """ACG lines for composite midpoints of key planet pairs.

    Each pair's shorter-arc ecliptic midpoint is converted to RA/Dec and run
    through the standard ACG machinery.
    """
    default_pairs = [
        ["Venus", "Jupiter"],
        ["Sun", "Moon"],
        ["Mars", "Saturn"],
        ["Sun", "Venus"],
        ["Moon", "Jupiter"],
        ["Mercury", "Venus"],
        ["Jupiter", "Uranus"],
    ]
    pairs = pairs or default_pairs
    try:
        from moira.astrocartography import acg_lines
        from moira.chart import create_chart

        jd_ut = jd_from_iso(iso_datetime)
        jd_tt = _jd_tt(jd_ut)
        with moira_reader():
            chart = create_chart(jd_ut, birth_lat, birth_lon, bodies=list(BODIES))
            longitudes = {
                name: pd.longitude for name, pd in chart.planets.items()
            }
            planet_ra_dec: dict[str, tuple[float, float]] = {}
            for a, b in pairs:
                if a in longitudes and b in longitudes:
                    mlon = _shorter_arc_midpoint(longitudes[a], longitudes[b])
                    ra, dec = _ra_dec_for_longitude(mlon, 0.0, jd_tt)
                    planet_ra_dec[f"{a}/{b}"] = (ra, dec)
            if not planet_ra_dec:
                return {"lines": []}
            gmst = _gmst_deg(jd_ut)
            lines = acg_lines(planet_ra_dec, gmst, lat_step=1.0, jd_ut=jd_ut)
        return {"lines": _emit_lines(lines, 1.0)}
    except Exception as exc:
        print(f"[acg] midpoint lines skipped: {exc}")
        return {"lines": []}


def generate_crossings(
    iso_datetime: str,
    birth_lat: float,
    birth_lon: float,
    bodies: list[str] | None = None,
    max_crossings: int = 80,
) -> dict[str, Any]:
    """Power places: where natal ACG lines cross each other.

    Classically the strongest crossings are between a meridian line (MC/IC —
    a planet on the vertical axis) and an ASC/DSC curve (a planet on the
    horizon). Each crossing is emitted as a clickable marker with a plain-
    English interpretation built from the existing planet/angle meanings.
    Natal parans are included as ``type: "paran"`` markers so the panel can
    show both kinds of blended-energy hotspots in one list.
    """
    acg = generate_acg(iso_datetime, birth_lat, birth_lon, bodies=bodies, lat_step=1.0)
    lines = acg.get("lines", [])
    parans = acg.get("parans", [])

    meridians = [l for l in lines if l.get("angle") in ("MC", "IC")]
    curves = [l for l in lines if l.get("angle") in ("ASC", "DSC")]

    from interpretations import ANGLE_MEANING, PLANET_MEANING, paran_pair_meaning

    def _interpret(pa: str, aa: str, pb: str, ab: str) -> str:
        pair = paran_pair_meaning(pa, pb)
        base = f"{pa} {ANGLE_MEANING.get(aa, aa)} meets {pb} {ANGLE_MEANING.get(ab, ab)}."
        if pair:
            base += f" {pair}"
        return base

    crossings: list[dict[str, Any]] = []
    seen: set[tuple[int, int]] = set()

    for m in meridians:
        mcoords = m.get("geometry", {}).get("coordinates", [])
        if not mcoords:
            continue
        mlon = mcoords[0][0]
        for c in curves:
            ccoords = c.get("geometry", {}).get("coordinates", [])
            for i in range(len(ccoords) - 1):
                lon1, lat1 = ccoords[i][0], ccoords[i][1]
                lon2, lat2 = ccoords[i + 1][0], ccoords[i + 1][1]
                # Skip segments that jump the antimeridian.
                if abs(lon2 - lon1) > 180:
                    continue
                d1, d2 = lon1 - mlon, lon2 - mlon
                if d1 == 0:
                    t = 0.0
                elif d1 * d2 <= 0 and d1 != d2:
                    t = d1 / (d1 - d2)
                else:
                    continue
                lat = lat1 + t * (lat2 - lat1)
                key = (round(lat), round(mlon))
                if key in seen:
                    continue
                seen.add(key)
                crossings.append({
                    "type": "line-cross",
                    "planet_a": m["planet"],
                    "angle_a": m["angle"],
                    "planet_b": c["planet"],
                    "angle_b": c["angle"],
                    "color_a": m.get("color", "#ffaa00"),
                    "color_b": c.get("color", "#ffaa00"),
                    "latitude": round(lat, 4),
                    "longitude": round(mlon, 4),
                    "interpretation": _interpret(
                        m["planet"], m["angle"], c["planet"], c["angle"]
                    ),
                })
                break  # one crossing per meridian×curve pair

    # Paran markers ride along in the same list (they already carry lat/lng).
    # Skip parans at (0,0) — those are placeholders where the paran latitude
    # couldn't be computed for this chart.
    for p in parans:
        p_lat = p.get('latitude', 0.0)
        p_lng = p.get('longitude', 0.0)
        if abs(p_lat) < 0.01 and abs(p_lng) < 0.01:
            continue
        crossings.append({
            "type": "paran",
            "planet_a": p.get("planet_a", "?"),
            "angle_a": p.get("circle_a", "?"),
            "planet_b": p.get("planet_b", "?"),
            "angle_b": p.get("circle_b", "?"),
            "latitude": p.get("latitude", 0.0),
            "longitude": p.get("longitude", 0.0),
            "interpretation": _interpret(
                p.get("planet_a", ""), p.get("circle_a", ""),
                p.get("planet_b", ""), p.get("circle_b", ""),
            ),
        })

    # Sort by latitude |distance| from birth for a stable, meaningful order.
    crossings.sort(key=lambda c: abs(c["latitude"] - birth_lat))
    return {"crossings": crossings[:max_crossings]}


def generate_geodetic(
    iso_datetime: str,
    birth_lat: float,
    birth_lon: float,
) -> dict[str, Any]:
    """Geodetic astrology: map the zodiac (0° Aries = 0° longitude) onto Earth.

    Produces one meridian line per natal planet at its geodetic longitude, plus
    the 12 sign-boundary meridians.
    """
    try:
        from moira.chart import create_chart

        jd_ut = jd_from_iso(iso_datetime)
        with moira_reader():
            chart = create_chart(jd_ut, birth_lat, birth_lon, bodies=list(BODIES))
            longitudes = {
                name: pd.longitude for name, pd in chart.planets.items()
            }
        lines: list[dict[str, Any]] = []
        # 12 sign-boundary meridians (0°, 30°, … 330°).
        for i in range(12):
            lon = float(i * 30)
            lines.append(_meridian_line(f"Sign {i * 30}°", "GEO", lon, "#6ea8ff"))
        # One meridian per natal planet at its geodetic longitude.
        for name, lon in longitudes.items():
            lines.append(_meridian_line(name, "GEO", float(lon)))
        return {"lines": lines}
    except Exception as exc:
        print(f"[acg] geodetic lines skipped: {exc}")
        return {"lines": []}
