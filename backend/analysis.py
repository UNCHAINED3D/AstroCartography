"""
Location analysis — answers every locational question for a clicked point.

Composes the birth ACG (lines / parans / local space) with a relocated chart at
the clicked location, then adds plain-English interpretations. One call powers
the right-side panel of the globe UI.
"""

from __future__ import annotations

from typing import Any

import geometry
from acg import generate_acg, _local_space_list
from interpretations import (
    ANGLE_MEANING,
    HOUSE_MEANING,
    PLANET_MEANING,
    house_region_sentence,
    line_sentence,
    paran_sentence,
    relocation_sentence,
    strength_from_distance,
)
from moira_engine import BODIES, _HAS_CHIRON, jd_from_iso
from scoring_common import DOMAIN_ANGLE_BOOST, DOMAIN_HOUSES, DOMAIN_PLANETS

_NEAR_KM = 1000.0  # only report lines/parans within this radius of the click


def _circle_to_angle(circle: str) -> str:
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


def _house_of(longitude: float, cusps: tuple[float, ...]) -> int:
    """Return the 1-based house containing an ecliptic longitude."""
    lon = longitude % 360.0
    n = len(cusps)
    for h in range(1, n + 1):
        start = cusps[h - 1] % 360.0
        end = cusps[h % n] % 360.0
        if start <= end:
            if start <= lon < end:
                return h
        else:  # wraps past 360
            if lon >= start or lon < end:
                return h
    return n  # fallback: last house


def generate_analysis(
    iso_datetime: str,
    birth_lat: float,
    birth_lon: float,
    location_lat: float,
    location_lng: float,
    bodies: list[str] | None = None,
    house_system: str = "P",
) -> dict[str, Any]:
    """Full location analysis for a clicked point.

    Returns everything the right-side panel needs: relocated chart, nearest ACG
    lines, local-space directions, nearby parans, house region, and the
    interpreted "why" text for each.
    """
    bodies = bodies or list(BODIES)
    calc_bodies = list(bodies)
    if _HAS_CHIRON and "Chiron" not in calc_bodies:
        calc_bodies.append("Chiron")
    _minor = {b for b in calc_bodies if b not in BODIES}
    _planet_bodies = [b for b in calc_bodies if b not in _minor]

    jd_ut = jd_from_iso(iso_datetime)

    # 1. Birth ACG: lines, subpoints, local space, parans.
    acg = generate_acg(
        iso_datetime, birth_lat, birth_lon, bodies=calc_bodies, lat_step=1.0
    )

    from moira.chart import create_chart
    from moira.constants import sign_of

    with _reader():
        # 2. Relocated chart at the clicked location (same moment/planets).
        chart = create_chart(
            jd_ut, location_lat, location_lng,
            bodies=calc_bodies, house_system=house_system,
        )
        houses = chart.houses
        asc_sign = sign_of(houses.asc)[0]
        mc_sign = sign_of(houses.mc)[0]
        dsc_sign = sign_of(houses.dsc)[0]
        ic_sign = sign_of(houses.ic)[0]

        planet_houses = []
        for name, pd in chart.planets.items():
            h = _house_of(pd.longitude, houses.cusps)
            planet_houses.append(
                {
                    "name": name,
                    "longitude": round(pd.longitude, 4),
                    "sign": pd.sign,
                    "house": h,
                    "notable": h in (1, 4, 7, 10)
                    or name in ("Sun", "Moon", "Venus", "Jupiter"),
                }
            )

        # 4. Local-space directions FROM the clicked location.
        local_space = _local_space_list(
            chart, location_lat, location_lng, _planet_bodies
        )

    # 3. Nearest ACG lines to the click.
    nearest: list[dict[str, Any]] = []
    for line in acg["lines"]:
        d = geometry.distance_to_line(
            location_lat, location_lng, line["geometry"]["coordinates"]
        )
        if d <= _NEAR_KM:
            nearest.append(
                {
                    "planet": line["planet"],
                    "angle": line["angle"],
                    "distance_km": round(d),
                    "strength": strength_from_distance(d),
                    "color": line["color"],
                }
            )
    nearest.sort(key=lambda x: x["distance_km"])

    # 5. Parans near the click.
    near_parans: list[dict[str, Any]] = []
    for p in acg["parans"]:
        d = geometry.haversine_km(location_lat, location_lng, p["latitude"], p["longitude"])
        if d <= _NEAR_KM:
            near_parans.append(
                {
                    "planet_a": p["planet_a"],
                    "circle_a": p["circle_a"],
                    "planet_b": p["planet_b"],
                    "circle_b": p["circle_b"],
                    "distance_km": round(d),
                }
            )
    near_parans.sort(key=lambda x: x["distance_km"])

    # 6. House region (approximate local-space sector from birth).
    bearing = geometry.bearing_deg(birth_lat, birth_lon, location_lat, location_lng)
    house = geometry.point_to_house_sector(bearing)

    # 7. Interpretations.
    reloc_text = relocation_sentence(asc_sign, planet_houses)
    nearest_text = [line_sentence(n["planet"], n["angle"], n["distance_km"]) for n in nearest]
    paran_text = [
        paran_sentence(p["planet_a"], p["circle_a"], p["planet_b"], p["circle_b"])
        for p in near_parans
    ]
    overall = _overall_sentence(nearest, near_parans, house)

    return {
        "location": {
            "latitude": round(location_lat, 4),
            "longitude": round(location_lng, 4),
        },
        "relocation": {
            "angles": {
                "asc": {"sign": asc_sign, "longitude": round(houses.asc, 4)},
                "mc": {"sign": mc_sign, "longitude": round(houses.mc, 4)},
                "dsc": {"sign": dsc_sign, "longitude": round(houses.dsc, 4)},
                "ic": {"sign": ic_sign, "longitude": round(houses.ic, 4)},
            },
            "planets": planet_houses,
            "summary": reloc_text,
        },
        "nearest_acg": nearest,
        "local_space": local_space,
        "parans": near_parans,
        "house_region": {
            "house": house,
            "theme": HOUSE_MEANING.get(house, ""),
            "sentence": house_region_sentence(house),
        },
        "domain_scores": _domain_scores(nearest, near_parans, planet_houses),
        "interpretations": {
            "relocation": reloc_text,
            "nearest_acg": nearest_text,
            "parans": paran_text,
            "overall": overall,
        },
    }


def _domain_scores(
    nearest: list[dict],
    near_parans: list[dict],
    planet_houses: list[dict],
) -> dict[str, float]:
    """Score five life domains (0–5) from nearby ACG lines, parans and houses.

    Each domain accumulates weighted contributions:
      - nearby ACG lines of domain-relevant planets (strength-scaled)
      - relocated planets sitting in the domain's natural houses
      - paran presence blending the energies
    The result is clamped to [0, 5] and rounded to the nearest 0.5.
    """
    # Domain tables (planets / angle boosts / houses) live in scoring_common
    # so the city-ranking engine shares the exact same mappings.
    domain_planets: dict[str, set[str]] = DOMAIN_PLANETS
    # Angle emphasis: certain angles reinforce certain domains.
    angle_boost: dict[str, dict[str, float]] = DOMAIN_ANGLE_BOOST
    # Houses whose occupation by a domain planet adds a point.
    domain_houses: dict[str, set[int]] = DOMAIN_HOUSES
    strength_weight = {"strong": 2.0, "moderate": 1.0, "light": 0.4}

    scores: dict[str, float] = {d: 1.0 for d in domain_planets}
    for n in nearest:
        planet = n.get("planet")
        angle = n.get("angle")
        strength = n.get("strength", "light")
        w = strength_weight.get(strength, 0.4)
        for domain, planets in domain_planets.items():
            if planet in planets:
                scores[domain] += w
                scores[domain] += angle_boost.get(angle, {}).get(domain, 0.0)
    # Relocated-chart house placements.
    for ph in planet_houses:
        if not ph.get("notable"):
            continue
        for domain, planets in domain_planets.items():
            if ph.get("name") in planets and ph.get("house") in domain_houses.get(domain, set()):
                scores[domain] += 1.0
    # Paran presence lifts every domain slightly (energies are blending).
    if near_parans:
        for domain in scores:
            scores[domain] += 0.5

    out: dict[str, float] = {}
    for domain, val in scores.items():
        clamped = max(0.0, min(5.0, val))
        out[domain] = round(clamped * 2) / 2  # nearest 0.5
    return out


def _overall_sentence(
    nearest: list[dict], parans: list[dict], house: int
) -> str:
    if nearest:
        top = nearest[0]
        base = (
            f"Your strongest line here is {top['planet']} {top['angle']} "
            f"({top['strength']}), tied to {ANGLE_MEANING.get(top['angle'], top['angle'])}."
        )
    else:
        base = "No major ACG lines pass very close, but this is still in your "
        f"{house}{_ordinal(house)} house region of {HOUSE_MEANING.get(house, 'life')}."
    if parans:
        base += (
            f" A paran ({parans[0]['planet_a']} {parans[0]['circle_a']} × "
            f"{parans[0]['planet_b']} {parans[0]['circle_b']}) is nearby, blending two energies."
        )
    return base


def _ordinal(n: int) -> str:
    if 10 <= n % 100 < 20:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


from contextlib import contextmanager


@contextmanager
def _reader():
    from moira_engine import moira_reader

    with moira_reader():
        yield
