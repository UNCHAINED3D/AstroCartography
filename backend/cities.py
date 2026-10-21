"""
City dataset and scoring engine for Astrocartography location recommendations.

Ranks global cities against a birth chart using three blended signals:
  1. ACG line proximity (weighted per planet/angle for the chosen focus)
  2. Relocated-chart house placements (domain planets in domain houses)
  3. Paran latitude proximity (paran blending near the city)

Cities can optionally be extended by dropping a JSON file at
``backend/data/world_cities.json`` containing a list of
``{"name", "country", "lat", "lng", "region"}`` objects — the engine picks it
up automatically and falls back to the built-in dataset otherwise.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from acg import generate_acg
from moira_engine import jd_from_iso
import geometry
from scoring_common import (
    DOMAIN_HOUSES,
    DOMAIN_PLANETS,
    SLIDER_TO_DOMAIN,
    line_domain_weight,
)

# Built-in dataset of major world cities across all continents & travel hotspots
WORLD_CITIES = [
    # North America
    {"name": "New York", "country": "United States", "lat": 40.7128, "lng": -74.0060, "region": "North America"},
    {"name": "Los Angeles", "country": "United States", "lat": 34.0522, "lng": -118.2437, "region": "North America"},
    {"name": "Chicago", "country": "United States", "lat": 41.8781, "lng": -87.6298, "region": "North America"},
    {"name": "Miami", "country": "United States", "lat": 25.7617, "lng": -80.1918, "region": "North America"},
    {"name": "San Francisco", "country": "United States", "lat": 37.7749, "lng": -122.4194, "region": "North America"},
    {"name": "Seattle", "country": "United States", "lat": 47.6062, "lng": -122.3321, "region": "North America"},
    {"name": "Toronto", "country": "Canada", "lat": 43.6532, "lng": -79.3832, "region": "North America"},
    {"name": "Vancouver", "country": "Canada", "lat": 49.2827, "lng": -123.1207, "region": "North America"},
    {"name": "Mexico City", "country": "Mexico", "lat": 19.4326, "lng": -99.1332, "region": "North America"},
    {"name": "Cancún", "country": "Mexico", "lat": 21.1619, "lng": -86.8515, "region": "North America"},
    {"name": "Honolulu", "country": "United States", "lat": 21.3069, "lng": -157.8583, "region": "North America"},
    {"name": "Austin", "country": "United States", "lat": 30.2672, "lng": -97.7431, "region": "North America"},

    # Europe
    {"name": "London", "country": "United Kingdom", "lat": 51.5074, "lng": -0.1278, "region": "Europe"},
    {"name": "Paris", "country": "France", "lat": 48.8566, "lng": 2.3522, "region": "Europe"},
    {"name": "Amsterdam", "country": "Netherlands", "lat": 52.3676, "lng": 4.9041, "region": "Europe"},
    {"name": "Berlin", "country": "Germany", "lat": 52.5200, "lng": 13.4050, "region": "Europe"},
    {"name": "Rome", "country": "Italy", "lat": 41.9028, "lng": 12.4964, "region": "Europe"},
    {"name": "Florence", "country": "Italy", "lat": 43.7696, "lng": 11.2558, "region": "Europe"},
    {"name": "Barcelona", "country": "Spain", "lat": 41.3851, "lng": 2.1734, "region": "Europe"},
    {"name": "Madrid", "country": "Spain", "lat": 40.4168, "lng": -3.7038, "region": "Europe"},
    {"name": "Lisbon", "country": "Portugal", "lat": 38.7223, "lng": -9.1393, "region": "Europe"},
    {"name": "Vienna", "country": "Austria", "lat": 48.2082, "lng": 16.3738, "region": "Europe"},
    {"name": "Prague", "country": "Czechia", "lat": 50.0755, "lng": 14.4378, "region": "Europe"},
    {"name": "Athens", "country": "Greece", "lat": 37.9838, "lng": 23.7275, "region": "Europe"},
    {"name": "Reykjavik", "country": "Iceland", "lat": 64.1466, "lng": -21.9426, "region": "Europe"},
    {"name": "Dublin", "country": "Ireland", "lat": 53.3498, "lng": -6.2603, "region": "Europe"},
    {"name": "Stockholm", "country": "Sweden", "lat": 59.3293, "lng": 18.0686, "region": "Europe"},
    {"name": "Copenhagen", "country": "Denmark", "lat": 55.6761, "lng": 12.5683, "region": "Europe"},
    {"name": "Zurich", "country": "Switzerland", "lat": 47.3769, "lng": 8.5417, "region": "Europe"},

    # Asia & Pacific
    {"name": "Tokyo", "country": "Japan", "lat": 35.6762, "lng": 139.6503, "region": "Asia"},
    {"name": "Kyoto", "country": "Japan", "lat": 35.0116, "lng": 135.7681, "region": "Asia"},
    {"name": "Seoul", "country": "South Korea", "lat": 37.5665, "lng": 126.9780, "region": "Asia"},
    {"name": "Bangkok", "country": "Thailand", "lat": 13.7563, "lng": 100.5018, "region": "Asia"},
    {"name": "Chiang Mai", "country": "Thailand", "lat": 18.7883, "lng": 98.9853, "region": "Asia"},
    {"name": "Bali (Ubud)", "country": "Indonesia", "lat": -8.5069, "lng": 115.2625, "region": "Asia"},
    {"name": "Singapore", "country": "Singapore", "lat": 1.3521, "lng": 103.8198, "region": "Asia"},
    {"name": "Hong Kong", "country": "Hong Kong", "lat": 22.3193, "lng": 114.1694, "region": "Asia"},
    {"name": "Taipei", "country": "Taiwan", "lat": 25.0330, "lng": 121.5654, "region": "Asia"},
    {"name": "Mumbai", "country": "India", "lat": 19.0760, "lng": 72.8777, "region": "Asia"},
    {"name": "New Delhi", "country": "India", "lat": 28.6139, "lng": 77.2090, "region": "Asia"},
    {"name": "Sydney", "country": "Australia", "lat": -33.8688, "lng": 151.2093, "region": "Oceania"},
    {"name": "Melbourne", "country": "Australia", "lat": -37.8136, "lng": 144.9631, "region": "Oceania"},
    {"name": "Auckland", "country": "New Zealand", "lat": -36.8485, "lng": 174.7633, "region": "Oceania"},

    # Latin America
    {"name": "Buenos Aires", "country": "Argentina", "lat": -34.6037, "lng": -58.3816, "region": "South America"},
    {"name": "Rio de Janeiro", "country": "Brazil", "lat": -22.9068, "lng": -43.1729, "region": "South America"},
    {"name": "São Paulo", "country": "Brazil", "lat": -23.5505, "lng": -46.6333, "region": "South America"},
    {"name": "Lima", "country": "Peru", "lat": -12.0463, "lng": -77.0428, "region": "South America"},
    {"name": "Santiago", "country": "Chile", "lat": -33.4489, "lng": -70.6693, "region": "South America"},
    {"name": "Bogotá", "country": "Colombia", "lat": 4.7110, "lng": -74.0721, "region": "South America"},
    {"name": "Medellín", "country": "Colombia", "lat": 6.2442, "lng": -75.5812, "region": "South America"},

    # Middle East & Africa
    {"name": "Dubai", "country": "United Arab Emirates", "lat": 25.2048, "lng": 55.2708, "region": "Middle East"},
    {"name": "Tel Aviv", "country": "Israel", "lat": 32.0853, "lng": 34.7818, "region": "Middle East"},
    {"name": "Cairo", "country": "Egypt", "lat": 30.0444, "lng": 31.2357, "region": "Africa"},
    {"name": "Cape Town", "country": "South Africa", "lat": -33.9249, "lng": 18.4241, "region": "Africa"},
    {"name": "Marrakech", "country": "Morocco", "lat": 31.6295, "lng": -7.9811, "region": "Africa"},
]

# Planet influence weights for different life domains
CATEGORY_WEIGHTS: dict[str, dict[str, float]] = {
    "love": {
        "Venus-asc": 10.0, "Venus-dsc": 10.0, "Venus-mc": 8.0, "Venus-ic": 7.0,
        "Moon-dsc": 8.0, "Moon-asc": 7.0, "Sun-dsc": 7.0, "Jupiter-dsc": 8.0,
        "Neptune-dsc": 5.0, "Mars-dsc": 6.0,
    },
    "career": {
        "Sun-mc": 10.0, "Mars-mc": 9.0, "Jupiter-mc": 9.0, "Saturn-mc": 7.0,
        "Mercury-mc": 8.0, "Sun-asc": 7.0, "Pluto-mc": 6.0, "Mars-asc": 7.0,
    },
    "wealth": {
        "Jupiter-mc": 10.0, "Venus-mc": 9.0, "Jupiter-asc": 9.0, "Sun-mc": 8.0,
        "Pluto-mc": 7.0, "Mercury-mc": 6.0, "Venus-asc": 7.0,
    },
    "peace": {
        "Moon-ic": 10.0, "Neptune-ic": 9.0, "Venus-ic": 8.0, "Jupiter-ic": 8.0,
        "Sun-ic": 7.0, "Chiron-ic": 6.0, "Moon-asc": 7.0,
    },
    "growth": {
        "Jupiter-asc": 10.0, "Sun-asc": 9.0, "Uranus-asc": 7.0, "Mercury-asc": 8.0,
        "Chiron-asc": 7.0, "Pluto-asc": 6.0, "Jupiter-mc": 8.0,
    },
    "all": {
        "Venus-dsc": 8.0, "Sun-mc": 8.0, "Jupiter-mc": 9.0, "Jupiter-asc": 8.0,
        "Venus-asc": 8.0, "Moon-ic": 7.0, "Mars-mc": 6.0, "Mercury-mc": 6.0,
    }
}


import os as _os

_data_dir = _os.environ.get("ASTRO_DATA_DIR")
if _data_dir:
    _DATA_JSON = Path(_data_dir) / "world_cities.json"
else:
    _DATA_JSON = Path(__file__).resolve().parent / "data" / "world_cities.json"


def load_world_cities() -> list[dict[str, Any]]:
    """City dataset: JSON override file if present, else the built-in list."""
    if _DATA_JSON.is_file():
        try:
            data = json.loads(_DATA_JSON.read_text(encoding="utf-8"))
            if isinstance(data, list) and data:
                return data
        except (json.JSONDecodeError, OSError) as exc:
            print(f"[cities] could not load {(_DATA_JSON)}: {exc} — using built-in list")
    return WORLD_CITIES


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


def _city_distance_to_line(clat: float, clng: float, coords: list) -> float:
    """Minimum great-circle distance (km) from a city to an ACG polyline."""
    if not coords:
        return float("inf")
    try:
        return geometry.distance_to_line(clat, clng, coords)
    except Exception:
        # Fall back to point-by-point comparison on any geometry edge case.
        best = float("inf")
        for pt in coords:
            if len(pt) >= 2:
                d = geometry.haversine_km(clat, clng, pt[1], pt[0])
                if d < best:
                    best = d
        return best


def rank_cities_for_birth(
    iso_datetime: str,
    birth_lat: float,
    birth_lon: float,
    focus: str = "all",
    limit: int = 15,
    weights: dict[str, float] | None = None,
    include_breakdown: bool = True,
    region: str | None = None,
    center_lat: float | None = None,
    center_lon: float | None = None,
    radius_km: float | None = None,
    bbox: list | None = None,
    max_distance_from_birth_km: float | None = None,
) -> list[dict[str, Any]]:
    """Rank global cities for a birth chart.

    ``focus`` selects a preset emphasis; ``weights`` is an optional per-domain
    slider map ({"love": 0..10, "career": 0..10, ...}) blended on top. Each
    city is scored on ACG line proximity, relocated-chart house placements and
    paran latitude proximity.
    """
    focus_key = focus.lower() if focus.lower() in CATEGORY_WEIGHTS else "all"
    preset_weights = CATEGORY_WEIGHTS[focus_key]

    # Normalise the slider weights (0-10 each) onto a 0-1 emphasis factor.
    sliders: dict[str, float] = {}
    if weights:
        for k, v in weights.items():
            domain = SLIDER_TO_DOMAIN.get(str(k).lower())
            if domain is not None:
                try:
                    sliders[domain] = max(0.0, min(10.0, float(v))) / 10.0
                except (TypeError, ValueError):
                    continue
    use_sliders = bool(sliders) and any(v > 0 for v in sliders.values())

    # Compute birth ACG lines + parans
    acg = generate_acg(iso_datetime, birth_lat, birth_lon, lat_step=1.0)
    lines = acg.get("lines", [])
    parans = acg.get("parans", [])

    # Relocated chart per city: built once, reused for all house scoring.
    # Compute filtered city list first so relocated charts only built for candidates.
    _all_cities = load_world_cities()
    filtered_cities = []
    for _c in _all_cities:
        if region and str(_c.get("region", "")).lower() != region.lower():
            continue
        _clat = _c["lat"]; _clng = _c["lng"]
        if center_lat is not None and center_lon is not None and radius_km is not None:
            if geometry.haversine_km(center_lat, center_lon, _clat, _clng) > radius_km:
                continue
        if bbox and len(bbox) == 2:
            (la1, lo1), (la2, lo2) = bbox
            if not (min(la1, la2) <= _clat <= max(la1, la2) and min(lo1, lo2) <= _clng <= max(lo1, lo2)):
                continue
        if max_distance_from_birth_km is not None:
            if geometry.haversine_km(birth_lat, birth_lon, _clat, _clng) > max_distance_from_birth_km:
                continue
        filtered_cities.append(_c)
    cities = filtered_cities if filtered_cities else _all_cities

    relocated: dict[str, dict[str, Any]] = {}
    try:
        from moira.chart import create_chart
        from moira_engine import jd_from_iso, moira_reader

        jd_ut = jd_from_iso(iso_datetime)
        with moira_reader():
            for city in cities:
                try:
                    chart = create_chart(jd_ut, city["lat"], city["lng"])
                    houses = chart.houses
                    relocated[city["name"]] = {
                        "cusps": tuple(houses.cusps),
                        "planets": {
                            name: pd.longitude for name, pd in chart.planets.items()
                        },
                    }
                except Exception:
                    continue  # city without a relocated chart just loses house points
    except Exception as exc:
        print(f"[cities] relocated charts skipped: {exc}")

    def _effective_weight(planet: str, angle: str) -> float:
        """Blend focus preset + sliders into one weight for a line."""
        key = f"{planet}-{angle.lower()}"
        if use_sliders:
            domain_weights = line_domain_weight(planet, angle)
            blended = 0.0
            for domain, slider in sliders.items():
                if slider <= 0:
                    continue
                blended += slider * domain_weights.get(domain, 0.0)
            return round(blended, 3)
        return preset_weights.get(key, 2.0 if focus_key == "all" else 0.5)

    results: list[dict[str, Any]] = []
    # cities already filtered above
    for city in cities:
        clat = city["lat"]
        clng = city["lng"]

        acg_points = 0.0
        house_points = 0.0
        paran_points = 0.0
        nearby_influences: list[dict[str, Any]] = []

        # --- Signal 1: ACG line proximity --------------------------------
        for line in lines:
            planet = line.get("planet", "")
            angle = line.get("angle", "")
            weight = _effective_weight(planet, angle)
            if weight <= 0:
                continue

            coords = line.get("geometry", {}).get("coordinates", [])
            min_dist = _city_distance_to_line(clat, clng, coords)

            # Proximity scoring window (up to 750km orb)
            if min_dist <= 750.0:
                proximity_factor = math.pow(1.0 - (min_dist / 750.0), 1.5)
                influence_points = weight * 4.5 * proximity_factor
                acg_points += influence_points
                nearby_influences.append({
                    "planet": planet,
                    "angle": angle,
                    "color": line.get("color", "#ffaa00"),
                    "distance_km": round(min_dist),
                    "score_contribution": round(influence_points, 1),
                })

        # --- Signal 2: relocated-chart house placements -------------------
        rel = relocated.get(city["name"])
        house_placements: list[dict[str, Any]] = []
        if rel:
            for name, lon in rel["planets"].items():
                house = _house_of(lon, rel["cusps"])
                for domain, planets in DOMAIN_PLANETS.items():
                    if name in planets and house in DOMAIN_HOUSES.get(domain, set()):
                        slider = sliders.get(domain, 0.5 if not use_sliders else 0.0)
                        pts = 1.5 * (slider if use_sliders else 1.0)
                        house_points += pts
                        house_placements.append({
                            "planet": name,
                            "house": house,
                            "domain": domain,
                            "points": round(pts, 2),
                        })
        house_points = min(house_points, 15.0)  # cap so it can't dominate

        # --- Signal 3: paran latitude proximity ---------------------------
        city_paran_names: list[str] = []
        for p in parans:
            try:
                plat = float(p.get("latitude", 0.0))
            except (TypeError, ValueError):
                continue
            d = abs(plat - clat)
            if d <= 6.0:  # ~6° latitude orb for a paran band
                pts = 3.0 * (1.0 - (d / 6.0))
                if use_sliders:
                    pts *= max(sliders.values()) if sliders else 1.0
                paran_points += pts
                city_paran_names.append(
                    f"{p.get('planet_a', '?')} × {p.get('planet_b', '?')}"
                )
        paran_points = min(paran_points, 8.0)

        # --- Combine ------------------------------------------------------
        city_score = 45.0 + acg_points + house_points + paran_points
        nearby_influences.sort(key=lambda x: x["distance_km"])
        top_influences = nearby_influences[:4]

        # Calculate category scores
        love_score = min(99, round(city_score * 0.95 + (10 if any(i["planet"] in ["Venus", "Moon"] for i in top_influences) else 0)))
        career_score = min(99, round(city_score * 0.92 + (10 if any(i["planet"] in ["Sun", "Mars", "Jupiter"] for i in top_influences) else 0)))
        peace_score = min(99, round(city_score * 0.88 + (10 if any(i["planet"] in ["Neptune", "Moon"] for i in top_influences) else 0)))
        growth_score = min(99, round(city_score * 0.90 + (10 if any(i["planet"] in ["Jupiter", "Sun"] for i in top_influences) else 0)))

        overall_score = min(99, max(45, round(city_score)))

        # Primary summary reason
        if top_influences:
            best_inf = top_influences[0]
            summary = f"Strong {best_inf['planet']} {best_inf['angle']} influence within {best_inf['distance_km']} km."
        elif city_paran_names:
            summary = f"Paran blending of {city_paran_names[0]} near this latitude."
        elif house_placements:
            top_hp = house_placements[0]
            summary = f"Relocated {top_hp['planet']} in house {top_hp['house']} ({top_hp['domain']} region)."
        else:
            summary = "Harmonious ambient energy location."

        result: dict[str, Any] = {
            "name": city["name"],
            "country": city["country"],
            "region": city["region"],
            "latitude": clat,
            "longitude": clng,
            "overall_score": overall_score,
            "scores": {
                "love": love_score,
                "career": career_score,
                "peace": peace_score,
                "growth": growth_score,
            },
            "primary_influences": top_influences,
            "summary": summary,
        }
        if include_breakdown:
            result["score_breakdown"] = {
                "acg": round(acg_points, 1),
                "houses": round(house_points, 1),
                "parans": round(paran_points, 1),
            }
            result["house_placements"] = house_placements[:4]
        results.append(result)

    # Sort cities by overall score descending
    results.sort(key=lambda c: c["overall_score"], reverse=True)
    return results[:limit]


_BENEFICS = {"Venus", "Moon", "Jupiter", "Sun"}


def rank_cities_for_couple(
    iso_a: str, lat_a: float, lon_a: float,
    iso_b: str, lat_b: float, lon_b: float,
    focus: str = "all",
    limit: int = 15,
    weights: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Rank cities for two people planning a life together.

    Score = 45% person A + 45% person B + a synastry bonus when the city sits
    on benefic lines for *both* charts (e.g. A's Venus line and B's Moon line
    crossing near the same place).
    """
    full_limit = len(load_world_cities())
    ranks_a = rank_cities_for_birth(
        iso_a, lat_a, lon_a, focus=focus, limit=full_limit, weights=weights,
    )
    ranks_b = rank_cities_for_birth(
        iso_b, lat_b, lon_b, focus=focus, limit=full_limit, weights=weights,
    )

    max_a = max((c["overall_score"] for c in ranks_a), default=1) or 1
    max_b = max((c["overall_score"] for c in ranks_b), default=1) or 1
    by_a = {c["name"]: c for c in ranks_a}
    by_b = {c["name"]: c for c in ranks_b}

    results: list[dict[str, Any]] = []
    for name, ca in by_a.items():
        cb = by_b.get(name)
        if cb is None:
            continue
        na = ca["overall_score"] / max_a
        nb = cb["overall_score"] / max_b

        # Synastry bonus: benefic influence present for both people.
        benefic_a = any(i["planet"] in _BENEFICS for i in ca["primary_influences"])
        benefic_b = any(i["planet"] in _BENEFICS for i in cb["primary_influences"])
        bonus = 6.0 if (benefic_a and benefic_b) else 0.0

        combined = round(min(99, max(45, (0.45 * na + 0.45 * nb) * 100 + bonus * 1.5)))
        # Blend influence lists so the UI can show both people's lines.
        influences = sorted(
            ca["primary_influences"] + cb["primary_influences"],
            key=lambda i: i["distance_km"],
        )[:4]

        best = influences[0] if influences else None
        summary = (
            f"Shared {best['planet']} {best['angle']} energy within {best['distance_km']} km."
            if best else
            ("Balanced energies for both partners." if bonus else
             "Workable for both, no dominant shared lines.")
        )
        if bonus:
            summary += " Benefic lines for both partners overlap here."

        results.append({
            "name": name,
            "country": ca["country"],
            "region": ca["region"],
            "latitude": ca["latitude"],
            "longitude": ca["longitude"],
            "overall_score": combined,
            "scores": {
                "love": round((ca["scores"]["love"] + cb["scores"]["love"]) / 2),
                "career": round((ca["scores"]["career"] + cb["scores"]["career"]) / 2),
                "peace": round((ca["scores"]["peace"] + cb["scores"]["peace"]) / 2),
                "growth": round((ca["scores"]["growth"] + cb["scores"]["growth"]) / 2),
            },
            "primary_influences": influences,
            "summary": summary,
        })

    results.sort(key=lambda c: c["overall_score"], reverse=True)
    return results[:limit]


# --------------------------------------------------------------------------- #
# Group + grid helpers
# --------------------------------------------------------------------------- #


def rank_cities_for_group(
    births, focus="all", limit=15, weights=None, combine="avg",
    region=None, center_lat=None, center_lon=None, radius_km=None,
):
    full = len(load_world_cities())
    ranks_per = []
    for b in births:
        ranks_per.append(rank_cities_for_birth(
            b["datetime"], b["latitude"], b["longitude"],
            focus=focus, limit=full, weights=weights,
            region=region, center_lat=center_lat, center_lon=center_lon, radius_km=radius_km,
        ))
    by_name_sets = [{c["name"]: c for c in r} for r in ranks_per]
    names = list(by_name_sets[0].keys()) if by_name_sets else []
    results = []
    for name in names:
        if not all(name in bs for bs in by_name_sets):
            continue
        per = [bs[name] for bs in by_name_sets]
        scores = [p["overall_score"] for p in per]
        if combine == "min":
            combined = min(scores)
        elif combine == "consensus":
            mean = sum(scores) / len(scores)
            spread = max(scores) - min(scores)
            combined = mean - spread * 0.25
        else:
            combined = sum(scores) / len(scores)
        benefic_count = sum(
            1 for p in per
            if any(i["planet"] in {"Venus", "Moon", "Jupiter", "Sun"}
                   for i in p.get("primary_influences", []))
        )
        bonus = 6.0 if benefic_count >= 2 else 0.0
        penalty = 0.0
        for p in per:
            if any(i["planet"] in {"Saturn", "Mars", "Pluto"}
                   for i in p.get("primary_influences", [])):
                penalty += 3.0
        combined = combined + bonus - penalty
        combined = min(99, max(45, round(combined)))
        influences = []
        for j, p in enumerate(per):
            for inf in p.get("primary_influences", []):
                tagged = dict(inf)
                tagged["person_index"] = j
                influences.append(tagged)
        influences.sort(key=lambda x: x["distance_km"])
        influences = influences[:4]
        best = influences[0] if influences else None
        summary = (
            f"Shared {best['planet']} {best['angle']} energy within {best['distance_km']} km."
            if best else "Balanced energies for the group."
        )
        if bonus:
            summary += " Benefic lines overlap for multiple members."
        c0 = per[0]
        result = {
            "name": c0["name"],
            "country": c0["country"],
            "region": c0["region"],
            "latitude": c0["latitude"],
            "longitude": c0["longitude"],
            "overall_score": combined,
            "scores": {
                "love": round(sum(p["scores"]["love"] for p in per) / len(per)),
                "career": round(sum(p["scores"]["career"] for p in per) / len(per)),
                "peace": round(sum(p["scores"]["peace"] for p in per) / len(per)),
                "growth": round(sum(p["scores"]["growth"] for p in per) / len(per)),
            },
            "primary_influences": influences,
            "summary": summary,
        }
        results.append(result)
    results.sort(key=lambda c: c["overall_score"], reverse=True)
    return results[:limit]


def rank_grid_in_area(
    iso_datetime, birth_lat, birth_lon, focus="all", bbox=None,
    center_lat=None, center_lon=None, radius_km=None, step_deg=1.0,
    limit=15, weights=None,
):
    if center_lat is not None and center_lon is not None and radius_km is not None:
        deg = radius_km / 111.0
        la_min, la_max = center_lat - deg, center_lat + deg
        lo_min, lo_max = center_lon - deg, center_lon + deg
    elif bbox and len(bbox) == 2:
        (la1, lo1), (la2, lo2) = bbox
        la_min, la_max = min(la1, la2), max(la1, la2)
        lo_min, lo_max = min(lo1, lo2), max(lo1, lo2)
    else:
        return []
    points = []
    la = la_min
    while la <= la_max:
        lo = lo_min
        while lo <= lo_max:
            if center_lat is not None and radius_km is not None:
                if geometry.haversine_km(center_lat, center_lon, la, lo) > radius_km:
                    lo += step_deg
                    continue
            points.append((la, lo))
            lo += step_deg
        la += step_deg
    points = points[:400]
    from acg import generate_acg
    acg = generate_acg(iso_datetime, birth_lat, birth_lon, lat_step=1.0)
    lines = acg.get("lines", [])
    results = []
    for (la, lo) in points:
        acg_points = 0.0
        nearby = []
        for line in lines:
            planet = line.get("planet", "")
            angle = line.get("angle", "")
            coords = line.get("geometry", {}).get("coordinates", [])
            best = float("inf")
            for pt in coords:
                if len(pt) >= 2:
                    d = geometry.haversine_km(la, lo, pt[1], pt[0])
                    if d < best:
                        best = d
            if best <= 750.0:
                prox = (1.0 - best / 750.0) ** 1.5
                acg_points += 4.5 * 2.0 * prox
                nearby.append({"planet": planet, "angle": angle, "distance_km": round(best)})
        score = min(99, max(45, round(45 + acg_points)))
        results.append({
            "name": f"Grid {la:.2f},{lo:.2f}",
            "country": "",
            "region": "grid",
            "latitude": la,
            "longitude": lo,
            "overall_score": score,
            "scores": {"love": score, "career": score, "peace": score, "growth": score},
            "primary_influences": nearby[:3],
            "summary": "Grid-sampled location.",
        })
    results.sort(key=lambda c: c["overall_score"], reverse=True)
    return results[:limit]
