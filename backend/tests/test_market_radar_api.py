"""API tests for the Market Radar routers."""

from __future__ import annotations

import io
import json

from fastapi.testclient import TestClient

from app.main import create_app

_client = TestClient(create_app())


def test_review_counts_cover_cluster() -> None:
    resp = _client.get("/market-radar/review-counts")
    assert resp.status_code == 200
    properties = resp.json()["properties"]
    assert len(properties) >= 5
    assert all("per_platform" in p for p in properties)
    assert sum(p["total"] for p in properties) == 30


def test_property_reviews_and_source_url_handling() -> None:
    resp = _client.get("/market-radar/properties/mus-cloudvalley/reviews")
    assert resp.status_code == 200
    reviews = resp.json()["reviews"]
    assert reviews
    # At least one review has an unavailable source URL in the sample set.
    assert any(r["source_url_available"] is False for r in reviews)


def test_unknown_property_is_404() -> None:
    resp = _client.get("/market-radar/properties/does-not-exist/reviews")
    assert resp.status_code == 404


def test_unmapped_categories_admin_surface() -> None:
    resp = _client.get("/market-radar/admin/unmapped-categories")
    assert resp.status_code == 200
    cats = resp.json()["categories"]
    assert any(c["category"] == "Parking" and c["count"] > 20 for c in cats)


def test_upload_updates_counts() -> None:
    rows = [
        {
            "platform": "Google",
            "platform_review_id": "upload-1",
            "property_id": "mus-pineview",
            "property_name": "Pine View Inn",
            "author_pseudonym": "anon-upload",
            "date": "2024-06-01",
            "native_rating": 5,
            "text": "Fresh upload review, very clean and friendly",
            "source_url": "https://www.google.com/maps/place/pineview-mussoorie",
        }
    ]
    data = json.dumps(rows).encode("utf-8")
    files = {"file": ("reviews.json", io.BytesIO(data), "application/json")}
    resp = _client.post(
        "/market-radar/collection/upload",
        data={"platform": "Google", "property_id": "mus-pineview"},
        files=files,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["new_count"] == 1
    assert body["status"] in ("succeeded", "partially_succeeded")

    jobs = _client.get("/market-radar/collection/jobs").json()["jobs"]
    assert any(j["job_id"] == body["job_id"] for j in jobs)
