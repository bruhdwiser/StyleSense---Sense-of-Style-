"""StyleSense AI — API Endpoints Integration Tests.

Validates REST API endpoints across all engines:
- StyleDNA Engine (/api/styledna)
- Rule Engine (/api/rules)
- Recommendation Engine (/api/recommendations)
- Feedback Engine (/api/events)
- Catalogue (/api/products, /api/catalog)
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import init_db

@pytest.fixture(scope="module")
def client():
    init_db()
    with TestClient(app) as c:
        yield c

def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "engines" in data
    assert data["engines"]["styledna"] == "active"
    assert data["engines"]["rules"] == "active"
    assert data["engines"]["recommendation"] == "active"
    assert data["engines"]["feedback"] == "active"
    assert data["engines"]["catalogue"] == "active"

def test_rules_validate_outfit_endpoint_pass(client):
    payload = {
        "items": [
            {"role": "top", "price": 1200, "occasion_tags": ["casual"], "season_tags": ["summer"]},
            {"role": "bottom", "price": 1800, "occasion_tags": ["casual"], "season_tags": ["summer"]},
            {"role": "shoes", "price": 2000, "occasion_tags": ["casual"], "season_tags": ["summer"]},
        ],
        "budget": 6000,
        "occasion": "casual",
        "climate": "summer",
    }
    res = client.post("/api/rules/validate-outfit", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["passed"] is True
    assert len(data["violations"]) == 0
    assert len(data["details"]) == 4

def test_rules_validate_outfit_endpoint_fail(client):
    payload = {
        "items": [
            {"role": "top", "price": 4000},
            {"role": "bottom", "price": 4000},

        ],
        "budget": 5000,
        "occasion": "casual",
    }
    res = client.post("/api/rules/validate-outfit", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["passed"] is False
    assert len(data["violations"]) >= 2

def test_rules_list_endpoint(client):
    res = client.get("/api/rules/list")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 4
    rule_names = {r["name"] for r in data}
    assert "budget_check" in rule_names
    assert "completeness_check" in rule_names
    assert "unique_roles_check" in rule_names

def test_styledna_compute_and_get_summary(client):
    user_id = "test_user_api_1"
    payload = {
        "user_id": user_id,
        "aesthetics": ["minimalist", "streetwear"],
        "favorite_colors": ["black", "navy"],
        "preferred_fit": "relaxed_fit",
        "body_type": "athletic",
    }
    compute_res = client.post("/api/styledna/compute", json=payload)
    assert compute_res.status_code == 200
    computed_data = compute_res.json()
    assert computed_data["user_id"] == user_id
    assert computed_data["weights"]["minimalist"] == 1.0

    get_res = client.get(f"/api/styledna/{user_id}")
    assert get_res.status_code == 200
    assert get_res.json()["user_id"] == user_id

    sum_res = client.get(f"/api/styledna/{user_id}/summary")
    assert sum_res.status_code == 200
    assert "summary" in sum_res.json()
    assert len(sum_res.json()["dominant_tags"]) > 0

def test_events_ingestion_202_accepted(client):
    payload = {
        "session_id": "session_api_test",
        "user_id": "test_user_api_1",
        "events": [
            {
                "event_type": "like",
                "target_type": "product",
                "target_id": "test_top_1",
                "payload": {"position": 1, "dwell_time_ms": 2500},
            },
            {
                "event_type": "click",
                "target_type": "product",
                "target_id": "test_shoes_1",
                "payload": {"position": 3},
            },
        ],
    }
    res = client.post("/api/events", json=payload)
    assert res.status_code == 202
    data = res.json()
    assert data["accepted"] == 2

def test_events_get_session(client):
    res = client.get("/api/events?session_id=session_api_test")
    assert res.status_code == 200
    data = res.json()
    assert "events" in data
    assert data["session_id"] == "session_api_test"

def test_recommendations_endpoint(client):
    payload = {
        "occasion": "casual",
        "budget": 10000,
        "climate": "summer",
        "aesthetic": "streetwear",
        "user_id": "test_user_api_1",
    }
    res = client.post("/api/recommendations", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "outfits" in data
    assert data["count"] <= 3
    if data["count"] > 0:
        first = data["outfits"][0]
        assert "explanation" in first
        assert first["total_price"] <= 10000

def test_recommendations_candidates_inspection(client):
    payload = {
        "occasion": "casual",
        "budget": 10000,
        "climate": "summer",
    }
    res = client.post("/api/recommendations/candidates", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "candidates" in data
    assert data["count"] >= 5

def test_products_list_and_stats(client):
    res = client.get("/api/products?limit=5")
    assert res.status_code == 200
    data = res.json()
    assert "products" in data
    assert len(data["products"]) <= 5

    stats_res = client.get("/api/catalog/stats")
    assert stats_res.status_code == 200
    stats_data = stats_res.json()
    assert "total_products" in stats_data
    assert "categories" in stats_data
