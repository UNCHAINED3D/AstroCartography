"""Smoke tests for report and narrative API payload contracts."""

from fastapi.testclient import TestClient

from api.main import app


def test_report_and_narrative_endpoints_return_expected_sections():
    client = TestClient(app)
    birth = {"datetime": "1990-05-15T14:30:00+10:00", "latitude": -27.4705, "longitude": 153.026}

    signature = client.post("/api/travel-signature", json={"birth": birth, "name": "Alex"})
    assert signature.status_code == 200
    body = signature.json()
    assert body["headline"]
    assert body["core_themes"]

    couple = client.post("/api/couple-narrative", json={
        "birth_a": birth,
        "birth_b": {"datetime": "1992-08-12T09:15:00+10:00", "latitude": -33.8688, "longitude": 151.2093},
        "name_a": "Alex",
        "name_b": "Sam",
        "city_name": "Lisbon",
        "country": "Portugal",
    })
    assert couple.status_code == 200
    assert couple.json()["relationship_gift"]

    group = client.post("/api/group-narrative", json={
        "births": [birth, {"datetime": "1992-08-12T09:15:00+10:00", "latitude": -33.8688, "longitude": 151.2093}],
        "names": ["Alex", "Sam"],
        "city_name": "Lisbon",
        "country": "Portugal",
    })
    assert group.status_code == 200
    assert group.json()["group_ritual"]

    report = client.post("/api/report", json={
        "birth": birth,
        "name": "Alex",
        "preferences": {"desired_feeling": "romance", "travel_style": "romantic", "interests": ["food", "art"]},
        "focus": "love",
        "top_city_limit": 3,
        "travel_days": 14,
        "travel_start": "2026-05-01",
        "selected_city": {"name": "Lisbon", "country": "Portugal", "latitude": 38.7223, "longitude": -9.1393},
    })
    assert report.status_code == 200
    body = report.json()
    assert body["meta"]["name"] == "Alex"
    assert body["signature"]["headline"]
    assert body["destinations"]
    assert body["selected_city"]["city"] == "Lisbon"
    assert body["travel_timing"]
    assert body["itinerary"] == []
    assert body["integration"]["prompts"]
    assert body["meta"]["disclaimer"]