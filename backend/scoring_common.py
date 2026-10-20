"""
Shared domain-scoring tables for location recommendations.

Used by both `analysis.py` (per-click 5-domain star scores) and `cities.py`
(city ranking). Keeping the planet→domain and domain→house mappings here means
the two features can never drift out of sync.
"""

from __future__ import annotations

# Planets that feed each life domain.
DOMAIN_PLANETS: dict[str, set[str]] = {
    "Love": {"Venus", "Moon", "Sun", "Jupiter"},
    "Career": {"Sun", "Mars", "Jupiter", "Saturn", "Mercury"},
    "Home": {"Moon", "Venus", "Saturn", "Jupiter"},
    "Growth": {"Jupiter", "Sun", "Uranus", "Mercury"},
    "Peace": {"Moon", "Neptune", "Venus", "Jupiter", "Chiron"},
}

# Certain angles reinforce certain domains.
DOMAIN_ANGLE_BOOST: dict[str, dict[str, float]] = {
    "MC": {"Career": 0.5},
    "IC": {"Home": 0.5},
    "ASC": {"Love": 0.3, "Growth": 0.3},
    "DSC": {"Love": 0.5},
}

# Houses whose occupation by a domain planet strengthens the domain.
DOMAIN_HOUSES: dict[str, set[int]] = {
    "Love": {5, 7, 8},
    "Career": {2, 6, 10},
    "Home": {1, 4, 12},
    "Growth": {1, 9, 11},
    "Peace": {4, 9, 12},
}

# UI slider keys map onto the canonical domain names (canonical capitalisation).
SLIDER_TO_DOMAIN = {
    "love": "Love",
    "career": "Career",
    "home": "Home",
    "growth": "Growth",
    "peace": "Peace",
}


def line_domain_weight(planet: str, angle: str) -> dict[str, float]:
    """Per-domain weight (0–1 scale) for a single ACG line key.

    A planet in the domain's planet set scores 1.0; the line's angle can add a
    boost. Returns a dict of domain → weight so callers can blend with their
    own slider values.
    """
    weights: dict[str, float] = {}
    for domain, planets in DOMAIN_PLANETS.items():
        w = 1.0 if planet in planets else 0.15
        w += DOMAIN_ANGLE_BOOST.get(angle, {}).get(domain, 0.0)
        weights[domain] = round(w, 3)
    return weights
