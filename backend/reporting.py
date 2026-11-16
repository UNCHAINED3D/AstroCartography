"""Backend report composition helpers."""

from __future__ import annotations

from typing import Any

from narrative.compose import (
    compose_city_narrative,
    compose_couple_narrative,
    compose_group_narrative,
    compose_itinerary,
    compose_personal_signature,
    compose_travel_narrative,
)


def _birth_dict(birth: Any) -> dict[str, Any]:
    if hasattr(birth, "model_dump"):
        return birth.model_dump()
    if isinstance(birth, dict):
        return dict(birth)
    return {}


def _birth_payload(birth: Any) -> dict[str, Any]:
    d = _birth_dict(birth)
    return {
        "datetime": d.get("datetime"),
        "latitude": d.get("latitude"),
        "longitude": d.get("longitude"),
    }


def build_report(
    req: Any,
    top_cities: list[dict[str, Any]],
    selected_analysis: dict[str, Any] | None = None,
    travel_days: list[dict[str, Any]] | None = None,
    trip_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    birth = _birth_payload(getattr(req, "birth", {}))
    name = str(getattr(req, "name", "") or "Traveler")
    preferences = getattr(req, "preferences", None) or {}
    if hasattr(preferences, "model_dump"):
        preferences = preferences.model_dump()
    focus = str(getattr(req, "focus", "all") or "all")
    selected_city = getattr(req, "selected_city", None)
    selected_name = ""
    selected_country = ""
    selected_lat = None
    selected_lon = None
    if hasattr(selected_city, "model_dump"):
        sc = selected_city.model_dump()
        selected_name = sc.get("name") or ""
        selected_country = sc.get("country") or ""
        selected_lat = sc.get("latitude")
        selected_lon = sc.get("longitude")
    elif isinstance(selected_city, dict):
        selected_name = selected_city.get("name") or ""
        selected_country = selected_city.get("country") or ""
        selected_lat = selected_city.get("latitude")
        selected_lon = selected_city.get("longitude")

    city_narratives: list[dict[str, Any]] = []
    for city in top_cities[: max(1, int(getattr(req, "top_city_limit", 10) or 10))]:
        city_narratives.append(
            compose_city_narrative(
                city_name=city.get("name") or "Destination",
                country=city.get("country") or "",
                region=city.get("region") or "",
                focus=focus,
                domain_scores=city.get("scores") or {},
                nearest_acg=city.get("primary_influences") or [],
                parans=city.get("parans") or [],
                relocated={"angles": city.get("relocated_angles") or {}},
                preferences=preferences,
            )
        )

    selected_narrative = None
    if selected_name:
        selected_narrative = compose_city_narrative(
            city_name=selected_name,
            country=selected_country,
            focus=focus,
            domain_scores=(selected_analysis or {}).get("domain_scores") if selected_analysis else None,
            nearest_acg=(selected_analysis or {}).get("nearest_acg") if selected_analysis else None,
            parans=(selected_analysis or {}).get("parans") if selected_analysis else None,
            relocated=(selected_analysis or {}).get("relocation") if selected_analysis else None,
            preferences=preferences,
        )

    second_birth = _birth_payload(getattr(req, "second_birth", None)) if getattr(req, "second_birth", None) else None
    companions = [_birth_payload(b) for b in (getattr(req, "companions", None) or [])]
    couple_narrative = None
    if second_birth:
        couple_narrative = compose_couple_narrative(selected_name, selected_country, [name, "Partner"])
    group_narrative = None
    if companions:
        group_narrative = compose_group_narrative(selected_name, [name] + [f"Traveler {i+2}" for i in range(len(companions))])

    travel_narratives = []
    for day in travel_days or []:
        travel_narratives.append(
            compose_travel_narrative(
                score=day.get("score", day.get("combined_score", 0)),
                influences=day.get("influences") or [],
                warnings=day.get("warnings") or [],
                date=day.get("date", ""),
                destination=selected_name,
            )
        )

    itinerary = compose_itinerary((trip_plan or {}).get("itinerary") or [], str(preferences.get("travel_style") or "balanced"), preferences.get("interests") or [])

    return {
        "meta": {
            "name": name,
            "birth": birth,
            "focus": focus,
            "generated_at": None,
            "disclaimer": "Astrology is used here as a reflective language for travel and self-awareness, not as a guarantee of events.",
        },
        "signature": compose_personal_signature(name, preferences),
        "destinations": city_narratives,
        "selected_city": selected_narrative,
        "couple": couple_narrative,
        "group": group_narrative,
        "travel_timing": travel_narratives,
        "itinerary": itinerary,
        "integration": {
            "headline": "Bring the feeling home as a practice.",
            "prompts": [
                "What did this place reveal that I want to keep?",
                "What habit made me feel more like myself?",
                "What will I stop doing when I return?",
                "What will I start doing differently?",
            ],
        },
        "travel_style": preferences.get("travel_style") or "balanced",
        "interests": preferences.get("interests") or [],
    }