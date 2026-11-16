"""Tests for narrative composition modules."""

from narrative.compose import (
    compose_city_narrative,
    compose_couple_narrative,
    compose_group_narrative,
    compose_itinerary,
    compose_personal_signature,
    compose_travel_narrative,
)


def test_city_narrative_is_deterministic_and_complete():
    first = compose_city_narrative(
        city_name="Lisbon",
        country="Portugal",
        focus="love",
        domain_scores={"Love": 4.5, "Career": 3.0, "Peace": 3.5, "Growth": 4.0},
        nearest_acg=[{"planet": "Venus", "angle": "DSC", "distance_km": 50}],
        relocated={"angles": {"asc": {"sign": " Libra"}, "mc": {"sign": "Cancer"}, "dsc": {"sign": "Aries"}, "ic": {"sign": "Capricorn"}}},
    )
    second = compose_city_narrative(
        city_name="Lisbon",
        country="Portugal",
        focus="love",
        domain_scores={"Love": 4.5, "Career": 3.0, "Peace": 3.5, "Growth": 4.0},
        nearest_acg=[{"planet": "Venus", "angle": "DSC", "distance_km": 50}],
        relocated={"angles": {"asc": {"sign": " Libra"}, "mc": {"sign": "Cancer"}, "dsc": {"sign": "Aries"}, "ic": {"sign": "Capricorn"}}},
    )
    assert first == second
    assert first["city"] == "Lisbon"
    assert first["headline"]
    assert first["catch_the_feeling"]["exercise"]
    assert first["disclaimer"]


def test_travel_narrative_maps_score_to_guidance():
    high = compose_travel_narrative(90, [], [], "2026-05-15", "Lisbon")
    low = compose_travel_narrative(40, [], ["Moon void of course"], "2026-05-16", "Lisbon")
    assert "strong day" in high["narrative"].lower()
    assert "slow down" in low["narrative"].lower()
    assert low["warnings"]


def test_itinerary_and_couple_group_are_free_of_sales_fields():
    itinerary = compose_itinerary([
        {"name": "Lisbon", "arrival_date": "2026-05-15", "length_days": 3, "score": 82}
    ])
    couple = compose_couple_narrative("Lisbon", "Portugal", ["Alex", "Sam"])
    group = compose_group_narrative("Lisbon", ["Alex", "Sam", "Taylor"])
    assert itinerary[0]["theme"]
    assert couple["relationship_gift"]
    assert group["per_person"][0]["name"] == "Alex"
    assert "payment" not in couple
    assert "affiliate" not in group


def test_personal_signature_uses_preferences():
    signature = compose_personal_signature("Alex", {"desired_feeling": "romance", "travel_style": "romantic"})
    assert "connection" in " ".join(signature["core_themes"]).lower()
    assert "beauty" in " ".join(signature["core_themes"]).lower()
    assert signature["travel_style"] == "romantic"