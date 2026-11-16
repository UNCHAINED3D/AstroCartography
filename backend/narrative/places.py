"""Local place profiles for narrative travel content."""

from __future__ import annotations

from typing import Any

_PLACE_PROFILES: dict[tuple[str, str], dict[str, Any]] = {
    ("Lisbon", "Portugal"): {
        "city": "Lisbon",
        "country": "Portugal",
        "geographic_personality": "coastal, hilly, historic, warm, atmospheric",
        "sensory_profile": {
            "light": "golden and reflective",
            "sound": "trams, conversation, and occasional music",
            "texture": "tiles, stone, river air, and soft fabric",
            "pace": "unhurried with social evenings",
        },
        "symbolic_associations": ["longing", "beauty", "sea light", "music", "affection"],
        "best_for": ["romance", "art", "food", "slow travel", "social ease"],
        "neighborhood_types": ["walkable historic districts", "viewpoints", "riverside cafes", "quiet residential streets"],
        "activity_types": ["cafe sitting", "sunset walks", "music venues", "small museums", "day trips"],
        "shadow_themes": ["nostalgia", "overindulgence", "romantic idealization"],
        "integration_prompts": ["Bring back a slower evening ritual.", "Notice what beauty you want without needing an audience."],
    },
    ("Paris", "France"): {
        "city": "Paris",
        "country": "France",
        "geographic_personality": "urban, historic, aesthetic, romantic, cultural",
        "sensory_profile": {
            "light": "soft, flattering, and cinematic",
            "sound": "conversation, music, and street life",
            "texture": "stone, gardens, pastries, and tailored style",
            "pace": "elegant but can become performative",
        },
        "symbolic_associations": ["beauty", "romance", "taste", "art", "self-presentation"],
        "best_for": ["romance", "art", "fashion", "food", "creative work"],
        "neighborhood_types": ["garden-lined streets", "gallery districts", "cafe terraces", "historic quarters"],
        "activity_types": ["museum visits", "long lunches", "evening walks", "bookshops", "people-watching"],
        "shadow_themes": ["comparison", "appearance pressure", "over-romanticizing"],
        "integration_prompts": ["Let beauty be nourishing rather than corrective.", "Choose experiences that make you feel more like yourself."],
    },
    ("Tokyo", "Japan"): {
        "city": "Tokyo",
        "country": "Japan",
        "geographic_personality": "dense, futuristic, ritualistic, precise, layered",
        "sensory_profile": {
            "light": "clean neon, soft interiors, and seasonal shifts",
            "sound": "trains, quiet announcements, and hidden music",
            "texture": "precision, packaging, small details, and calm interiors",
            "pace": "fast outside, deeply focused inside",
        },
        "symbolic_associations": ["ritual", "mastery", "surprise", "discipline", "hidden meaning"],
        "best_for": ["growth", "learning", "career", "creativity", "solo exploration"],
        "neighborhood_types": ["quiet residential lanes", "technology districts", "garden spaces", "tiny restaurants"],
        "activity_types": ["classes", "focused cafe work", "design museums", "food exploration", "night walks"],
        "shadow_themes": ["overstimulation", "perfectionism", "emotional distance"],
        "integration_prompts": ["Bring back one ritual of focus and care.", "Do not confuse precision with emotional safety."],
    },
    ("New York", "United States"): {
        "city": "New York",
        "country": "United States",
        "geographic_personality": "fast, visible, ambitious, electric, public",
        "sensory_profile": {
            "light": "bright, vertical, and restless",
            "sound": "traffic, music, voices, and momentum",
            "texture": "concrete, glass, fashion, and late nights",
            "pace": "fast and opportunity-driven",
        },
        "symbolic_associations": ["visibility", "ambition", "reinvention", "performance", "desire"],
        "best_for": ["career", "visibility", "social connection", "creative risk", "wealth"],
        "neighborhood_types": ["creative districts", "rooftop and skyline viewpoints", "late-night food streets", "gallery areas"],
        "activity_types": ["networking", "shows", "creative workshops", "walking neighborhoods", "high-energy evenings"],
        "shadow_themes": ["burnout", "comparison", "visibility addiction", "overwork"],
        "integration_prompts": ["Notice whether you want recognition or meaningful impact.", "Do one thing nobody else needs to see."],
    },
    ("London", "United Kingdom"): {
        "city": "London",
        "country": "United Kingdom",
        "geographic_personality": "historic, global, structured, cultural, restless",
        "sensory_profile": {
            "light": "soft grey with flashes of color",
            "sound": "multilingual conversation, transit, and music",
            "texture": "brick, rain, archives, pubs, and gardens",
            "pace": "steady and ambitious",
        },
        "symbolic_associations": ["career", "culture", "communication", "tradition", " reinvention".strip()],
        "best_for": ["career", "learning", "culture", "networking", "writing"],
        "neighborhood_types": ["museum districts", "pub-lined streets", "creative hubs", "riverside walks"],
        "activity_types": ["museum visits", "writing sessions", "theater", "long conversations", "market wandering"],
        "shadow_themes": ["emotional reserve", "overthinking", "status pressure"],
        "integration_prompts": ["Say the feeling instead of explaining it perfectly.", "Let yourself be a beginner somewhere."],
    },
    ("Bali (Ubud)", "Indonesia"): {
        "city": "Bali (Ubud)",
        "country": "Indonesia",
        "geographic_personality": "spiritual, lush, soft, intuitive, restorative",
        "sensory_profile": {
            "light": "green, warm, and diffused",
            "sound": "water, insects, ceremonies, and quiet mornings",
            "texture": "plants, stone, textiles, and incense",
            "pace": "slow and inward",
        },
        "symbolic_associations": ["healing", "spirituality", "imagination", "rest", "surrender"],
        "best_for": ["healing", "rest", "spirituality", "creativity", "peace"],
        "neighborhood_types": ["garden stays", "river paths", "temple areas", "quiet hills"],
        "activity_types": ["meditation", "journaling", "gentle walks", "creative retreats", "early nights"],
        "shadow_themes": ["spiritual bypassing", "blurry boundaries", "avoidance"],
        "integration_prompts": ["Take the calm home as a practice, not a performance.", "Notice what you are using peace to avoid."],
    },
    ("Rome", "Italy"): {
        "city": "Rome",
        "country": "Italy",
        "geographic_personality": "historic, sensual, public, enduring, communal",
        "sensory_profile": {
            "light": "warm and dramatic",
            "sound": "conversation, fountains, traffic, and music",
            "texture": "ancient stone, food, fabric, and sun-warmed walls",
            "pace": "social and indulgent",
        },
        "symbolic_associations": ["history", "family", "pleasure", "endurance", "public life"],
        "best_for": ["romance", "food", "culture", "family", "visibility"],
        "neighborhood_types": ["piazzas", "historic streets", "family-run restaurants", "garden viewpoints"],
        "activity_types": ["long dinners", "history walks", "people-watching", "markets", "slow afternoons"],
        "shadow_themes": ["excess", "rigidity", "getting stuck in old patterns"],
        "integration_prompts": ["Enjoy the feast without losing your own rhythm.", "Notice which traditions you want to keep and which you want to change."],
    },
}

_GENERIC_PROFILE = {
    "geographic_personality": "distinctive, place-based, and shaped by local rhythm",
    "sensory_profile": {
        "light": "shaped by the local climate and season",
        "sound": "the rhythm of streets, transit, conversation, and nature",
        "texture": "local architecture, food, fabric, and landscape",
        "pace": "a blend of local routine and your travel style",
    },
    "symbolic_associations": ["discovery", "perspective", "memory", "belonging", "change"],
    "best_for": ["exploration", "rest", "culture", "connection", "personal growth"],
    "neighborhood_types": ["walkable districts", "quiet viewpoints", "local cafes", "cultural areas"],
    "activity_types": ["walking", "museum or market visits", "shared meals", "rest blocks", "journaling"],
    "shadow_themes": ["overplanning", "homesickness", "overstimulation"],
    "integration_prompts": ["Bring home one habit that made you feel more alive.", "Notice what this place revealed that you want to keep."],
}


def _norm(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


def get_place_profile(city_name: str = "", country: str = "", region: str = "") -> dict[str, Any]:
    key = (_norm(city_name), _norm(country))
    profile = dict(_PLACE_PROFILES.get(key, _GENERIC_PROFILE))
    profile["city"] = city_name or "This place"
    profile["country"] = country
    if region and not profile.get("region"):
        profile["region"] = region
    return profile