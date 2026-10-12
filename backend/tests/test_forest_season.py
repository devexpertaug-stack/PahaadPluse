"""The Forest Season Resort Home_Property tests (FEAT-001).

Covers the generated resort dataset, its ingestion through the REAL pipeline,
the re-centering of the whole dashboard on the resort, and the live
upload-collection path.
"""

from __future__ import annotations

import io
import json

from fastapi.testclient import TestClient

from app.main import app, create_app
from app.seed import sentinel_seed
from app.seed.forest_season_reviews import (
    FOREST_SEASON_ID,
    FOREST_SEASON_NAME,
    generate_forest_season_seed,
)
from app.seed.sample_reviews import PROPERTIES, build_review_records
from app.services.market_radar.analytics_dataset import HOME_PROPERTY_ID

_client = TestClient(create_app())

_ALL_PLATFORMS = {"Google", "MakeMyTrip", "Booking.com", "TripAdvisor", "Agoda"}


# --------------------------------------------------------------------------
# (d) The generator is deterministic (same seed -> same records).
# --------------------------------------------------------------------------
def test_generator_is_deterministic() -> None:
    first = generate_forest_season_seed()
    second = generate_forest_season_seed()
    assert first == second
    # A different seed yields a different dataset (sanity that the seed matters).
    other = generate_forest_season_seed(seed=1)
    assert other != first


def test_generated_dataset_spans_all_platforms_and_languages() -> None:
    seed = generate_forest_season_seed()
    assert 40 <= len(seed) <= 80
    assert {s.platform.value for s in seed} == _ALL_PLATFORMS
    # Some records deliberately omit the source URL (Req 2.9).
    assert any(not s.has_source_url for s in seed)
    assert all(s.property_id == FOREST_SEASON_ID for s in seed)

    # After the real parse+enrich pipeline the resort records mix en/hi/hi-Latn.
    resort = [r for r in build_review_records() if r.property_id == FOREST_SEASON_ID]
    langs = {r.detected_language for r in resort}
    assert {"en", "hi", "hi-Latn"} <= langs


# --------------------------------------------------------------------------
# (a) The resort appears in review-counts on all 5 platforms.
# --------------------------------------------------------------------------
def test_resort_in_review_counts_on_all_platforms() -> None:
    resp = _client.get("/market-radar/review-counts")
    assert resp.status_code == 200
    props = {p["property_id"]: p for p in resp.json()["properties"]}
    assert FOREST_SEASON_ID in props
    home = props[FOREST_SEASON_ID]
    assert home["property_name"] == FOREST_SEASON_NAME
    assert set(home["per_platform"]) == _ALL_PLATFORMS
    assert all(count > 0 for count in home["per_platform"].values())
    assert home["total"] >= 40


def test_resort_reviews_endpoint_populated() -> None:
    resp = _client.get(f"/market-radar/properties/{FOREST_SEASON_ID}/reviews")
    assert resp.status_code == 200
    reviews = resp.json()["reviews"]
    assert len(reviews) >= 40
    # The 'source URL unavailable' path is exercised.
    assert any(r["source_url_available"] is False for r in reviews)


# --------------------------------------------------------------------------
# (b) HOME_PROPERTY_ID is the resort and analytics return it as home.
# --------------------------------------------------------------------------
def test_home_property_id_is_resort() -> None:
    assert HOME_PROPERTY_ID == FOREST_SEASON_ID
    assert PROPERTIES[0].property_id == FOREST_SEASON_ID


def test_analytics_endpoints_centre_on_resort() -> None:
    playbook = _client.get("/market-radar/analytics/playbook")
    assert playbook.status_code == 200
    body = playbook.json()
    assert body["home_property_id"] == FOREST_SEASON_ID
    assert body["home_property_name"] == FOREST_SEASON_NAME

    whatif = _client.get("/market-radar/analytics/what-if/Google")
    assert whatif.status_code == 200
    assert whatif.json()["driver_weights"]

    cps = _client.get("/market-radar/analytics/changepoints")
    assert cps.status_code == 200
    assert "changepoints" in cps.json()

    decomp = _client.get("/market-radar/analytics/decomposition")
    assert decomp.status_code == 200

    tm = _client.get(
        "/market-radar/analytics/time-machine",
        params={"property_id": FOREST_SEASON_ID, "at": "2024-01-15", "aspect": "Food"},
    )
    assert tm.status_code == 200
    assert tm.json()["changepoint"] is not None


# --------------------------------------------------------------------------
# (c) Sentinel board/metrics populated for the resort.
# --------------------------------------------------------------------------
def test_sentinel_centres_on_resort() -> None:
    assert sentinel_seed.HOME_PROPERTY_ID == FOREST_SEASON_ID
    assert sentinel_seed.HOME_PROPERTY_NAME == FOREST_SEASON_NAME
    stays = sentinel_seed.build_stays()
    assert stays
    assert all(s.property_id == FOREST_SEASON_ID for s in stays)
    assert all(s.property_name == FOREST_SEASON_NAME for s in stays)

    board = _client.get("/sentinel/board")
    assert board.status_code == 200
    assert board.json()["rows"]

    metrics = _client.get("/sentinel/metrics")
    assert metrics.status_code == 200
    assert metrics.json()["total_complaints"] > 0


def test_concierge_facts_are_resort_topical() -> None:
    resp = _client.get("/concierge/facts")
    assert resp.status_code == 200
    facts = resp.json()["facts"]
    topics = {f["topic"] for f in facts}
    # Resort-topical facts (check-in/out, wifi, breakfast, parking, pets).
    assert {"breakfast", "checkout", "wifi", "parking", "pets"} <= topics


# --------------------------------------------------------------------------
# Live collection path: posting the generated resort file through the real
# upload endpoint ingests it through the collector (the honest "scraping").
# --------------------------------------------------------------------------
def _resort_upload_rows(platform: str, id_suffix: str = "") -> list[dict]:
    """Build upload rows for one platform from the generated resort dataset.

    ``id_suffix`` makes the ``platform_review_id`` distinct from the already
    seeded records so the collector counts them as genuinely new ingests
    (proving the file flows through the live collection path, not a no-op).
    """
    rows: list[dict] = []
    for r in build_review_records():
        if r.property_id != FOREST_SEASON_ID or r.platform != platform:
            continue
        rows.append(
            {
                "platform": r.platform,
                "platform_review_id": f"{r.platform_review_id}{id_suffix}",
                "property_id": r.property_id,
                "property_name": r.property_name,
                "author_pseudonym": r.author_pseudonym,
                "date": r.date.isoformat(),
                "native_rating": r.native_rating,
                "text": r.text,
                "source_url": r.source_url,
            }
        )
    return rows


def test_generated_resort_file_ingests_via_upload_endpoint() -> None:
    client = TestClient(create_app())
    rows = _resort_upload_rows("TripAdvisor", id_suffix="-upload")
    assert rows, "expected generated TripAdvisor resort reviews"

    data = json.dumps(rows).encode("utf-8")
    files = {"file": ("forest_season_tripadvisor.json", io.BytesIO(data), "application/json")}
    resp = client.post(
        "/market-radar/collection/upload",
        data={"platform": "TripAdvisor", "property_id": FOREST_SEASON_ID},
        files=files,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["property_id"] == FOREST_SEASON_ID
    assert body["platform"] == "TripAdvisor"
    assert body["status"] in ("succeeded", "partially_succeeded")
    assert body["failure_count"] == 0
    # The parsed/deduped records flow through the live collector as new ingests.
    assert body["new_count"] == len(rows)

    # Re-posting the identical file is a safe no-op (dedupe), proving the real
    # collector keyed/deduped the records rather than blindly appending.
    files2 = {"file": ("forest_season_tripadvisor.json", io.BytesIO(data), "application/json")}
    resp2 = client.post(
        "/market-radar/collection/upload",
        data={"platform": "TripAdvisor", "property_id": FOREST_SEASON_ID},
        files=files2,
    )
    assert resp2.status_code == 200
    assert resp2.json()["new_count"] == 0


def test_lifespan_resort_endpoints_populated() -> None:
    with TestClient(app) as client:
        counts = client.get("/market-radar/review-counts").json()
        ids = {p["property_id"] for p in counts["properties"]}
        assert FOREST_SEASON_ID in ids
        assert client.get("/sentinel/board").json()["rows"]
        assert client.get("/destination/heatmap").json()["hotspots"]
