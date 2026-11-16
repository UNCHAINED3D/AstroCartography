"""Narrative composition functions."""

from __future__ import annotations

from typing import Any

from .places import get_place_profile
from .themes import (
    ANGLE_THEMES,
    CATCH_FEELINGS,
    DOMAIN_ACTIVITIES,
    DOMAIN_AVOID,
    EMOTIONAL_WEATHER_BY_DOMAIN,
    HOUSE_THEMES,
    PLANET_THEMES,
)

_DEFAULT_CONCIERGE = "Astrology is a reflective language, not a guarantee of events."


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.strip()
        if key and key not in seen:
            seen.add(key)
            out.append(key)
    return out


def _primary_domain(scores: dict[str, float] | None) -> str:
    if not scores:
        return "Growth"
    return max(scores.items(), key=lambda kv: float(kv[1] or 0))[0]


def _top_planets(influences: list[dict[str, Any]] | None, limit: int = 3) -> list[str]:
    out: list[str] = []
    for inf in influences or []:
        p = str(inf.get("planet") or "").strip()
        if p and p not in out:
            out.append(p)
        if len(out) >= limit:
            break
    return out


def compose_city_narrative(
    city_name: str,
    country: str = "",
    region: str = "",
    focus: str = "all",
    domain_scores: dict[str, float] | None = None,
    nearest_acg: list[dict[str, Any]] | None = None,
    parans: list[dict[str, Any]] | None = None,
    relocated: dict[str, Any] | None = None,
    preferences: dict[str, Any] | None = None,
) -> dict[str, Any]:
    prefs = preferences or {}
    profile = get_place_profile(city_name, country, region)
    planets = _top_planets(nearest_acg)
    domain = _primary_domain(domain_scores)
    planet_theme = PLANET_THEMES.get(planets[0] if planets else "Sun", PLANET_THEMES["Sun"])
    angle_theme = ANGLE_THEMES.get(str((nearest_acg or [{}])[0].get("angle") or "ASC"), ANGLE_THEMES["ASC"])

    relocated_angles = ((relocated or {}).get("angles") or {})
    asc_sign = (relocated_angles.get("asc") or {}).get("sign") if relocated_angles else None
    house = None
    for p in (relocated or {}).get("planets", []) if isinstance(relocated, dict) else []:
        if p.get("notable"):
            house = p.get("house")
            break
    house_theme = HOUSE_THEMES.get(int(house or 7), HOUSE_THEMES[7])

    headline = f"A place that may awaken {planet_theme['core']}."
    if focus and focus.lower() not in {"all", "growth"}:
        focus_text = f" Your {focus} theme may become more noticeable here."
        headline += focus_text

    feeling = planet_theme["feeling"]
    if house_theme.get("feeling"):
        feeling += f", with a stronger sense of {house_theme['theme']}."

    shadow = planet_theme["shadow"]
    if parans:
        shadow += " Stronger emotional cross-currents may appear."

    may_feel = _unique([
        feeling,
        angle_theme["feeling"],
        f"more aware of {angle_theme['domain']}",
        f"more tuned to {house_theme['theme']}",
    ])
    may_notice = _unique([
        f"moments that emphasize {planet_theme['core']}",
        f"people or situations connected to {angle_theme['domain']}",
        f"a pull toward {', '.join(profile['activity_types'][:3])}",
    ])
    may_resist = _unique([
        DOMAIN_AVOID.get(domain, DOMAIN_AVOID["Growth"])[0],
        f"environments that ignore {angle_theme['domain']}",
        profile["shadow_themes"][0] if profile.get("shadow_themes") else "overstimulation",
    ])
    best_for = _unique([focus] + profile.get("best_for", []) + [domain.lower()])
    growth = f"Use this place to practice {planet_theme['core']} without letting {shadow} take over."
    practice = CATCH_FEELINGS.get(domain, CATCH_FEELINGS["Growth"])
    activity = DOMAIN_ACTIVITIES.get(domain, DOMAIN_ACTIVITIES["Growth"])
    avoid = DOMAIN_AVOID.get(domain, DOMAIN_AVOID["Growth"])
    integration = profile.get("integration_prompts", ["Bring home one habit that made you feel more alive."])

    return {
        "city": city_name or "This place",
        "country": country,
        "region": region,
        "headline": headline,
        "emotional_weather": EMOTIONAL_WEATHER_BY_DOMAIN.get(domain, "responsive and changeable"),
        "focus_domain": domain,
        "dominant_planets": planets,
        "dominant_angle": str((nearest_acg or [{}])[0].get("angle") or ""),
        "may_feel": may_feel,
        "may_notice": may_notice,
        "may_resist": may_resist,
        "shadow_pattern": shadow,
        "growth_invitation": growth,
        "best_for": best_for,
        "conscious_practice": practice[1],
        "journal_prompts": [
            "What am I noticing in myself here that I usually ignore at home?",
            "What kind of person do I become in this city?",
            "What do I want more of after visiting this place?",
        ],
        "catch_the_feeling": {
            "feeling": practice[0],
            "exercise": practice[1],
        },
        "activities": activity + profile.get("activity_types", [])[:3],
        "atmosphere": profile.get("sensory_profile", {}),
        "neighborhoods": profile.get("neighborhood_types", []),
        "travel_advice": "Choose atmosphere over checklist tourism, and leave room for one unplanned experience.",
        "return_integration": integration[0] if integration else "Bring home one ritual that helped you feel more like yourself.",
        "ascendant_sign": asc_sign,
        "relocated_house_theme": house_theme,
        "disclaimer": _DEFAULT_CONCIERGE,
    }


def compose_personal_signature(birth_name: str = "", preferences: dict[str, Any] | None = None) -> dict[str, Any]:
    prefs = preferences or {}
    desired = str(prefs.get("desired_feeling") or "healing").lower()
    style = str(prefs.get("travel_style") or "balanced").lower()
    themes = {
        "romance": ["connection", "beauty", "visible affection"],
        "healing": ["rest", "emotional safety", "renewal"],
        "career": ["visibility", "discipline", "impact"],
        "adventure": ["surprise", "independence", "discovery"],
        "rest": ["quiet", "body awareness", "boundaries"],
        "creativity": ["expression", "play", "artistic risk"],
    }.get(desired, ["growth", "self-understanding", "meaningful experience"])
    return {
        "name": birth_name or "Traveler",
        "headline": f"You may travel best when the place supports {', '.join(themes[:3])}.",
        "core_themes": themes,
        "emotional_needs": ["atmosphere", "emotional safety", "meaningful connection", "space to reflect"],
        "travel_style": style,
        "driving_planets": ["Venus", "Moon", "Jupiter"],
        "what_to_seek": ["beautiful places", "walkable neighborhoods", "restorative nature", "spaces with cultural depth"],
        "what_to_balance": ["overplanning", "emotional overextension", "mistaking intensity for meaning"],
        "journal_prompts": [
            "What kind of place helps me feel most like myself?",
            "What do I want to bring home from this trip?",
            "What am I hoping to feel, and what might get in the way?",
        ],
    }


def compose_travel_narrative(
    score: float,
    influences: list[str] | None = None,
    warnings: list[str] | None = None,
    date: str = "",
    destination: str = "",
) -> dict[str, Any]:
    n = float(score or 0)
    if n >= 80:
        mood = "expansive and supportive"
        narrative = "This may be a strong day for arrival, connection, and experiences that feel meaningful."
        best_for = ["arrival", "romance", "creative plans", "social exploration"]
        avoid = ["overloading the day", "ignoring your energy limits"]
        ritual = "Notice what feels easy and let that guide one choice."
    elif n >= 60:
        mood = "balanced and workable"
        narrative = "This day may support travel and exploration, with room for flexibility."
        best_for = ["travel", "walking", "light plans", "reflection"]
        avoid = ["rigid expectations", "major confrontations"]
        ritual = "Choose one priority and let the rest be optional."
    else:
        mood = "tender or low-clarity"
        narrative = "This may be a day to slow down, reduce friction, and avoid forcing outcomes."
        best_for = ["rest", "journaling", "gentle movement", "simple meals"]
        avoid = ["rushed logistics", "major decisions", "overstimulation"]
        ritual = "Give yourself one fewer plan than usual."
    warning_text = list(warnings or [])
    if warning_text:
        narrative += " Pay attention to the timing notes rather than treating them as a verdict."
    return {
        "date": date,
        "destination": destination,
        "score": round(n, 1),
        "mood": mood,
        "narrative": narrative,
        "best_for": best_for,
        "avoid": avoid,
        "ritual": ritual,
        "influences": influences or [],
        "warnings": warning_text,
    }


def compose_itinerary(itinerary: list[dict[str, Any]], travel_style: str = "balanced", interests: list[str] | None = None) -> list[dict[str, Any]]:
    interests = interests or []
    out: list[dict[str, Any]] = []
    for idx, stop in enumerate(itinerary, start=1):
        city = stop.get("name") or f"Stop {idx}"
        profile = get_place_profile(city, "")
        theme = f"Day {idx}: {city} may invite {profile.get('symbolic_associations', ['discovery'])[0]}."
        out.append({
            "day": idx,
            "city": city,
            "theme": theme,
            "emotional_focus": profile.get("sensory_profile", {}).get("pace", "your own pace"),
            "morning_intention": f"Begin with one thing that helps you feel present in {city}.",
            "activity_type": ", ".join(_unique(interests + profile.get("activity_types", [])[:3])),
            "conscious_task": "Notice what you feel before deciding what to do next.",
            "evening_reflection": "What did this place reveal, and what do I want to bring home?",
            "avoid": "Overplanning every hour or treating the itinerary as a test.",
            "arrival_date": stop.get("arrival_date"),
            "length_days": stop.get("length_days"),
            "score": stop.get("score"),
        })
    return out


def compose_couple_narrative(city_name: str = "", country: str = "", partner_names: list[str] | None = None) -> dict[str, Any]:
    names = partner_names or ["You", "Partner"]
    label = " and ".join(names[:2]) if len(names) >= 2 else "You"
    return {
        "headline": f"{label} may experience {city_name or 'this place'} through a shared relational lens.",
        "shared_themes": ["connection", "beauty", "communication", "mutual visibility"],
        "relationship_gift": "More shared experiences, warmth, and opportunities to see each other differently.",
        "relationship_shadow": "One person may initiate while the other waits; old timing patterns can surface.",
        "best_activities": ["beautiful dinner", "unstructured walk", "creative date", "conversation about freedom and commitment"],
        "conflict_forecast": "Small comments may land harder. Avoid making major relationship decisions in the first two days.",
        "ritual": "Each morning, share one hope for the day. Each evening, share one thing you actually felt.",
        "disclaimer": _DEFAULT_CONCIERGE,
    }


def compose_group_narrative(city_name: str = "", people: list[str] | None = None) -> dict[str, Any]:
    names = people or []
    return {
        "headline": f"The group may experience {city_name or 'this place'} through shared curiosity and different needs.",
        "group_themes": ["shared discovery", "friendship", "flexibility", "mutual pacing"],
        "per_person": [
            {
                "name": name,
                "need": "space to participate in a way that feels natural",
                "may_overstimulate": "crowds, rigid schedules, or emotional pressure",
                "role": "co-creator of the day",
            }
            for name in names
        ],
        "shared_activities": ["long meal", "walk with no destination", "museum or market visit", "rest block"],
        "avoid": ["over-scheduling", "letting one person decide everything"],
        "group_ritual": "At the end of each day, each person names one thing that felt good and one thing they need tomorrow.",
        "disclaimer": _DEFAULT_CONCIERGE,
    }