"""Assert the checked-in dataset matches the datasheet and schema (Req 2.8)."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import jsonschema

from app.seed.sample_reviews import PROPERTIES, build_review_records
from app.services.market_radar.parsing import load_schema

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DATASET = _REPO_ROOT / "data" / "sample_reviews" / "mussoorie_reviews.json"
_DATASHEET = _REPO_ROOT / "data" / "datasheet.md"


def _load_dataset() -> list[dict]:
    return json.loads(_DATASET.read_text(encoding="utf-8"))


def test_dataset_matches_seed_source_of_truth() -> None:
    on_disk = _load_dataset()
    from_code = [json.loads(r.model_dump_json()) for r in build_review_records()]
    assert on_disk == from_code, (
        "data/sample_reviews is stale; run scripts/build_dataset.py"
    )


def test_dataset_covers_cluster_of_at_least_5_properties_all_platforms() -> None:
    recs = _load_dataset()
    properties = {r["property_id"] for r in recs}
    platforms = {r["platform"] for r in recs}
    assert len(properties) >= 5
    assert platforms == {"Google", "MakeMyTrip", "Booking.com", "TripAdvisor", "Agoda"}
    # Language mix present.
    langs = {r["detected_language"] for r in recs}
    assert {"en", "hi", "hi-Latn"} <= langs


def test_dataset_validates_against_schema() -> None:
    schema = load_schema()
    for rec in _load_dataset():
        jsonschema.validate(rec, schema)


def test_datasheet_counts_match_dataset() -> None:
    recs = _load_dataset()
    text = _DATASHEET.read_text(encoding="utf-8")

    # Total.
    assert f"**Total records:** {len(recs)}" in text

    # Per-platform rows.
    per_platform = Counter(r["platform"] for r in recs)
    for platform, count in per_platform.items():
        assert f"| {platform} | {count} |" in text

    # Per-property rows.
    per_property = Counter(r["property_name"] for r in recs)
    for name, count in per_property.items():
        assert f"| {name} | {count} |" in text

    # Property count claim.
    assert f"**Properties:** {len(PROPERTIES)}" in text


def test_no_raw_display_names_leak_into_dataset() -> None:
    # Pseudonyms only; the raw display names from the seed must not appear.
    text = _DATASET.read_text(encoding="utf-8")
    for leaked in ("Riya Sharma", "Aarav Mehta", "Daniel O'Brien", "Wei Chen"):
        assert leaked not in text
