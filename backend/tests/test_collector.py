"""Tests for the Review_Collector: dedupe, retry, limits, concurrency (Req 1)."""

from __future__ import annotations

import json

import pytest

from app.models.review import Platform
from app.services.market_radar.collector import (
    MAX_UPLOAD_REVIEWS,
    RETRY_SCHEDULE_SECONDS,
    ConcurrentJobError,
    JobStatus,
    ReviewCollector,
    UploadRejectedError,
    parse_upload,
)


def _raw(
    review_id: str,
    text: str = "Nice stay",
    rating: int = 4,
    platform: str = "Google",
    property_id: str = "prop-1",
) -> dict:
    return {
        "platform": platform,
        "platform_review_id": review_id,
        "property_id": property_id,
        "property_name": "Pine View Inn",
        "author_pseudonym": "anon-1",
        "date": "2024-05-01",
        "native_rating": rating,
        "text": text,
        "source_url": "https://example.com/r/" + review_id,
    }


def test_new_and_updated_and_failure_counts() -> None:
    c = ReviewCollector()
    job1 = c.ingest(
        Platform.GOOGLE,
        "prop-1",
        [_raw("a"), _raw("b"), {"platform": "Google", "text": ""}],
    )
    assert job1.new_count == 2
    assert job1.failure_count == 1
    assert job1.status == JobStatus.PARTIALLY_SUCCEEDED

    # Re-ingest: 'a' unchanged (no update), 'b' changed text (update), 'c' new.
    job2 = c.ingest(
        Platform.GOOGLE,
        "prop-1",
        [_raw("a"), _raw("b", text="Changed text"), _raw("c")],
    )
    assert job2.new_count == 1
    assert job2.updated_count == 1
    assert job2.status == JobStatus.SUCCEEDED
    assert len(c.store) == 3


def test_upload_rejects_too_many_reviews() -> None:
    rows = [_raw(str(i)) for i in range(MAX_UPLOAD_REVIEWS + 1)]
    data = json.dumps(rows).encode("utf-8")
    with pytest.raises(UploadRejectedError) as exc:
        parse_upload(data, "reviews.json")
    assert "10000" in str(exc.value)


def test_upload_rejects_oversize_file() -> None:
    big = b"x" * (20 * 1024 * 1024 + 1)
    with pytest.raises(UploadRejectedError) as exc:
        parse_upload(big, "reviews.json")
    assert "20MB" in str(exc.value) or "size" in str(exc.value)


def test_upload_parses_csv() -> None:
    csv_text = (
        "platform,platform_review_id,property_id,property_name,author_pseudonym,date,native_rating,text,source_url\n"
        "Google,x1,prop-1,Pine,anon,2024-05-01,4,Great place,https://e.com/x1\n"
    )
    rows = parse_upload(csv_text.encode("utf-8"), "r.csv")
    assert len(rows) == 1
    assert rows[0]["platform_review_id"] == "x1"


def test_retry_schedule_caps_at_five_then_fails() -> None:
    c = ReviewCollector()
    slept: list[float] = []

    def always_fail() -> list[dict]:
        raise RuntimeError("platform down")

    job = c.ingest_with_retry(
        Platform.AGODA, "prop-2", always_fail, sleeper=slept.append
    )
    assert job.status == JobStatus.FAILED
    assert job.attempts == 5
    assert slept == list(RETRY_SCHEDULE_SECONDS[:4])


def test_retry_preserves_prior_records_and_succeeds_eventually() -> None:
    c = ReviewCollector()
    # Seed one record so prior data exists.
    c.ingest(
        Platform.AGODA,
        "prop-3",
        [_raw("seed", rating=8, platform="Agoda", property_id="prop-3")],
    )
    calls = {"n": 0}

    def flaky() -> list[dict]:
        calls["n"] += 1
        if calls["n"] < 2:
            raise RuntimeError("transient")
        return [_raw("new1", rating=9, platform="Agoda", property_id="prop-3")]

    job = c.ingest_with_retry(Platform.AGODA, "prop-3", flaky, sleeper=lambda _s: None)
    assert job.status == JobStatus.SUCCEEDED
    assert job.new_count == 1
    assert len(c.store.for_property("prop-3")) == 2


def test_concurrent_job_guard() -> None:
    c = ReviewCollector()

    def reentrant() -> list[dict]:
        # Attempt a second job for the same (property, platform) mid-run.
        with pytest.raises(ConcurrentJobError):
            c.ingest(Platform.GOOGLE, "prop-9", [_raw("z")])
        return [_raw("ok")]

    job = c.ingest_with_retry(Platform.GOOGLE, "prop-9", reentrant, sleeper=lambda _s: None)
    assert job.status == JobStatus.SUCCEEDED
