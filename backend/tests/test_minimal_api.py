"""API tests for the Minimal features + the two Minimal subsystems (FEAT-005)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_drilldown_count_endpoint_matches() -> None:
    r = client.get(
        "/minimal/drilldown",
        params={
            "metric": "negative_food",
            "kind": "count",
            "clicked_value": 0,
            "property_id": "mus-pineview",
            "aspect": "Food",
            "label": "negative",
        },
    )
    assert r.status_code == 200
    body = r.json()
    # Re-query with the actual count and assert the invariant holds.
    r2 = client.get(
        "/minimal/drilldown",
        params={
            "metric": "negative_food",
            "kind": "count",
            "clicked_value": body["count"],
            "property_id": "mus-pineview",
            "aspect": "Food",
            "label": "negative",
        },
    )
    assert r2.json()["count_matches"] is True


def test_impact_and_log_intervention() -> None:
    r = client.post(
        "/minimal/interventions",
        json={
            "property_id": "mus-pineview",
            "aspect": "Food",
            "description": "New breakfast vendor",
            "date": "2024-04-01",
        },
    )
    assert r.status_code == 200
    impact = r.json()["impact"]
    assert impact["sufficient_post_data"] is True
    assert impact["effect"] is not None


def test_forecast_endpoint() -> None:
    r = client.get("/minimal/forecast", params={"aspect": "Food"})
    assert r.status_code == 200
    body = r.json()
    assert body["forecasts"][0]["forecast"]


def test_authenticity_endpoint() -> None:
    r = client.get("/minimal/authenticity")
    assert r.status_code == 200
    assert r.json()["excluded_count"] > 0


def test_reply_draft_and_approve_flow() -> None:
    draft = client.post(
        "/minimal/replies/draft",
        json={
            "review_id": "rev-1",
            "property_id": "mus-pineview",
            "text": "the food was cold",
            "detected_language": "en",
            "negative_aspects": ["Food"],
        },
    ).json()["reply"]
    assert draft["state"] == "draft"
    approved = client.post(
        f"/minimal/replies/{draft['id']}/approve",
        json={"approver": "owner@pineview"},
    ).json()["reply"]
    assert approved["state"] == "ready_to_post"


def test_briefing_endpoint() -> None:
    r = client.post("/minimal/briefing", json={"opted_in_owners": ["+919800000900"]})
    assert r.status_code == 200
    briefing = r.json()["briefing"]
    assert briefing["within_cap"] is True
    assert briefing["delivered_to"] == ["+919800000900"]


# ---- Guest Compass accept/decline path (Req 28) ----
def test_guest_compass_recommend_and_outcome() -> None:
    recs = client.get("/guest-compass/recommendations/gc-honeymoon").json()
    assert not recs["suppressed"]
    item = recs["cards"][0]["item_id"]
    out = client.post(
        "/guest-compass/stays/gc-honeymoon/outcome",
        json={"item_id": item, "accepted": True, "revenue_inr": 2500},
    )
    assert out.status_code == 200
    body = out.json()
    assert body["outcome"]["accepted"] is True
    assert body["metrics"]["accepted"] >= 1
    assert body["metrics"]["ancillary_revenue_inr"] >= 2500


def test_guest_compass_suppresses_during_open_complaint() -> None:
    # stay-charlie carries a seeded open complaint in the Sentinel.
    recs = client.get("/guest-compass/recommendations/stay-charlie").json()
    assert "cards" in recs


# ---- Concierge handoff + complaint routing path (Req 29) ----
def test_concierge_grounded_answer_via_api() -> None:
    r = client.post("/concierge/message", json={"message": "What time is breakfast?"})
    assert r.status_code == 200
    result = r.json()["result"]
    assert result["fact_ids"] == ["fact-breakfast"]
    assert result["handed_off"] is False


def test_concierge_handoff_via_api() -> None:
    r = client.post(
        "/concierge/message",
        json={"message": "Can you arrange a submarine tour of the Himalayas?"},
    )
    result = r.json()["result"]
    assert result["handed_off"] is True


def test_concierge_complaint_routing_via_api() -> None:
    r = client.post(
        "/concierge/message",
        json={"message": "the room is dirty and the geyser is not working"},
    )
    result = r.json()["result"]
    assert result["is_complaint"] is True
    assert result["complaint_id"]


def test_concierge_fact_update_endpoint() -> None:
    r = client.post(
        "/concierge/facts/fact-wifi",
        json={"text": "Wifi password is MUSSOORIE2024 for all rooms."},
    )
    assert r.status_code == 200
    assert r.json()["fact"]["version"] >= 2
