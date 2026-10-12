"""Market Radar analytics API tests (Req 7-13, 16)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_trends_endpoint_default() -> None:
    r = client.get("/market-radar/analytics/trends")
    assert r.status_code == 200
    body = r.json()
    assert body["granularity"] == "monthly"
    assert len(body["platforms"]) == 5


def test_trends_invalid_range_422() -> None:
    r = client.get(
        "/market-radar/analytics/trends",
        params={"start": "2024-06-01", "end": "2024-01-01"},
    )
    assert r.status_code == 422


def test_decomposition_endpoint() -> None:
    r = client.get("/market-radar/analytics/decomposition")
    assert r.status_code == 200
    assert r.json()["cluster_size"] == 6


def test_changepoints_endpoint() -> None:
    r = client.get("/market-radar/analytics/changepoints")
    assert r.status_code == 200
    assert "changepoints" in r.json()


def test_what_if_model_and_project() -> None:
    r = client.get("/market-radar/analytics/what-if/Google")
    assert r.status_code == 200
    assert r.json()["driver_weights"]
    p = client.post(
        "/market-radar/analytics/what-if/Google/project",
        json={"deltas": {"Food": 0.3}},
    )
    assert p.status_code == 200
    body = p.json()
    assert 1.0 <= body["projected_rating"] <= 5.0
    assert 1 <= body["projected_rank"] <= body["cluster_size"]


def test_time_machine_endpoint() -> None:
    r = client.get(
        "/market-radar/analytics/time-machine",
        params={"property_id": "mus-pineview", "at": "2024-01-15", "aspect": "Food"},
    )
    assert r.status_code == 200
    assert r.json()["changepoint"]["date"] == "2024-01-01"


def test_playbook_endpoint() -> None:
    r = client.get("/market-radar/analytics/playbook")
    assert r.status_code == 200
    assert "lagging" in r.json()


def test_gap_finder_endpoint() -> None:
    r = client.get("/market-radar/analytics/gap-finder")
    assert r.status_code == 200
    assert r.json()["themes"]


def test_benchmark_endpoint() -> None:
    r = client.get("/market-radar/analytics/benchmark")
    assert r.status_code == 200
    assert len(r.json()["systems"]) == 3
