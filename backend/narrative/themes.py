"""Emotional and psychological language for narrative composition."""

from __future__ import annotations

PLANET_THEMES: dict[str, dict[str, str]] = {
    "Sun": {"core": "visibility, vitality, and self-expression", "feeling": "more alive and seen", "shadow": "tying your worth to recognition"},
    "Moon": {"core": "emotion, safety, belonging, and instinct", "feeling": "more emotionally receptive", "shadow": "moodiness or retreat"},
    "Mercury": {"core": "thought, language, learning, and exchange", "feeling": "more mentally alert and curious", "shadow": "overthinking or scattered communication"},
    "Venus": {"core": "love, beauty, pleasure, and values", "feeling": "more receptive to beauty and affection", "shadow": "people-pleasing or overindulgence"},
    "Mars": {"core": "drive, courage, desire, and action", "feeling": "more assertive and physically energized", "shadow": "irritability or burnout"},
    "Jupiter": {"core": "growth, faith, generosity, and opportunity", "feeling": "more expansive and optimistic", "shadow": "excess or overpromising"},
    "Saturn": {"core": "structure, maturity, boundaries, and commitment", "feeling": "more serious and focused", "shadow": "heaviness or harsh self-judgment"},
    "Uranus": {"core": "freedom, originality, disruption, and awakening", "feeling": "more independent and restless", "shadow": "instability or rebellion for its own sake"},
    "Neptune": {"core": "imagination, spirituality, compassion, and blur", "feeling": "more dreamy and impressionable", "shadow": "idealization or avoidance"},
    "Pluto": {"core": "power, depth, transformation, and intensity", "feeling": "more intense and transformative", "shadow": "control or emotional overwhelm"},
    "Chiron": {"core": "healing, wounds, teaching, and sensitivity", "feeling": "more tender and self-aware", "shadow": "reopening old hurt"},
    "True Node": {"core": "direction, destiny, and growth", "feeling": "more aware of your path", "shadow": "forcing meaning too quickly"},
    "Lilith": {"core": "authentic desire, refusal, and wildness", "feeling": "more honest about what you want", "shadow": "rebellion or self-sabotage"},
}

ANGLE_THEMES: dict[str, dict[str, str]] = {
    "MC": {"domain": "career, reputation, and public direction", "feeling": "more visible and purpose-focused", "shadow": "overworking your image"},
    "IC": {"domain": "home, roots, family, and private life", "feeling": "more inward and rooted", "shadow": "withdrawal or family tension"},
    "ASC": {"domain": "identity, body, and first impressions", "feeling": "more present and self-aware", "shadow": "over-focusing on how you appear"},
    "DSC": {"domain": "partnership, attraction, and other people", "feeling": "more relational and open to others", "shadow": "losing yourself in others"},
}

HOUSE_THEMES: dict[int, dict[str, str]] = {
    1: {"theme": "identity and new beginnings", "feeling": "more like you are meeting yourself again"},
    2: {"theme": "money, values, and self-worth", "feeling": "more aware of what you value"},
    3: {"theme": "communication, learning, and short journeys", "feeling": "more curious and conversational"},
    4: {"theme": "home, family, and emotional foundations", "feeling": "more inward and rooted"},
    5: {"theme": "creativity, romance, and play", "feeling": "more expressive and playful"},
    6: {"theme": "work, health, and daily rhythm", "feeling": "more focused on routine and service"},
    7: {"theme": "partnership and one-to-one connection", "feeling": "more aware of other people"},
    8: {"theme": "intimacy, shared resources, and transformation", "feeling": "more intense and private"},
    9: {"theme": "travel, study, belief, and expansion", "feeling": "more open to bigger meaning"},
    10: {"theme": "career, public life, and achievement", "feeling": "more ambitious and visible"},
    11: {"theme": "friends, community, and future hopes", "feeling": "more social and future-facing"},
    12: {"theme": "rest, subconscious, and spiritual retreat", "feeling": "more quiet and inward"},
}

EMOTIONAL_WEATHER_BY_DOMAIN = {
    "Love": "warm, receptive, relationally charged",
    "Career": "focused, visible, achievement-oriented",
    "Home": "grounded, private, and rooted",
    "Growth": "expansive, curious, and forward-looking",
    "Peace": "quiet, reflective, and restorative",
}

DOMAIN_ACTIVITIES = {
    "Love": ["romantic walk", "intimate meal", "art or music experience", "meaningful conversation"],
    "Career": ["focused work session", "professional conversation", "cultural site", "visible creative project"],
    "Home": ["slow morning", "familiar food", "quiet neighborhood walk", "journaling"],
    "Growth": ["class or museum", "new neighborhood", "conversation with someone new", "solo adventure"],
    "Peace": ["rest block", "nature time", "spiritual practice", "gentle evening"],
}

DOMAIN_AVOID = {
    "Love": ["rushed decisions", "people-pleasing", "mistaking intensity for compatibility"],
    "Career": ["overworking", "status comparison", "making big decisions from pressure"],
    "Home": ["isolation", "old family patterns", "refusing help"],
    "Growth": ["overpacking the schedule", "constant input", "forcing every moment to be meaningful"],
    "Peace": ["overstimulation", "too many plans", "avoiding necessary rest"],
}

CATCH_FEELINGS = {
    "Love": ("I am allowed to receive affection without performing for it.", "Do one beautiful thing alone and let yourself enjoy it before documenting it."),
    "Career": ("I can be visible without proving my worth through exhaustion.", "Take one meaningful professional action and notice how it feels in your body."),
    "Home": ("I can create belonging without shrinking myself.", "Find a place that feels safe enough to slow down and be honest."),
    "Growth": ("I can expand without abandoning my own pace.", "Say yes to one unfamiliar experience, then journal about what it awakened."),
    "Peace": ("Rest is not a reward. It is information.", "Sit somewhere quiet for ten minutes and name what you feel before trying to fix it."),
}