"""Review_Collector (Req 1).

Ingests reviews from three sources — an uploaded file (CSV/JSON), the checked-in
sample dataset, and platform adapters — into an in-memory review store (the
demo persists to SQLite elsewhere). Responsibilities:

* Upload guards: reject the whole file (naming which condition failed) if it is
  larger than 20 MB or contains more than 10 000 reviews (Req 1.3).
* Dedupe by ``(platform, platform_review_id)``: insert new records; overwrite
  text/rating/normalised/date keeping the existing id and count as *updated*
  only when a field actually changed (Req 1.5, 1.6).
* Per-record parse failures are skipped + counted and the batch continues
  (Req 1.7).
* Retry schedule 30/60/120/240/480s, capped at 5 attempts, after which the job
  is ``failed`` while prior records are preserved (Req 1.8).
* A concurrent-job guard rejects a second job for the same (property, platform)
  while one is running (Req 1.9).
* Each run produces a :class:`CollectionJob` status record with platform,
  property, start/end, final status and new/updated/failure counts (Req 1.4,
  1.10).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from app.models.review import Platform, ReviewRecord
from app.services.market_radar.parsing import RawReview, ReviewParser

MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB
MAX_UPLOAD_REVIEWS = 10_000
RETRY_SCHEDULE_SECONDS = (30, 60, 120, 240, 480)  # Req 1.8
MAX_ATTEMPTS = 5


class JobStatus(StrEnum):
    """Final status of a collection job (Req 1.4)."""

    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIALLY_SUCCEEDED = "partially_succeeded"
    FAILED = "failed"


class UploadRejectedError(Exception):
    """Raised when an uploaded file violates a size/count limit (Req 1.3)."""


class ConcurrentJobError(Exception):
    """Raised when a job for the same (property, platform) is already running."""


@dataclass
class CollectionJob:
    """Status record for one collection run (Req 1.4)."""

    job_id: str
    platform: str
    property_id: str
    started_at: datetime
    finished_at: datetime | None = None
    status: JobStatus = JobStatus.RUNNING
    new_count: int = 0
    updated_count: int = 0
    failure_count: int = 0
    attempts: int = 0
    errors: list[str] = field(default_factory=list)


_MUTABLE_FIELDS = ("text", "native_rating", "normalised_rating", "date")


def _dedupe_key(record: ReviewRecord) -> tuple[str, str]:
    return (record.platform, record.platform_review_id)


class ReviewStore:
    """In-memory keyed store of Review_Records (demo-grade)."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, str], ReviewRecord] = {}

    def get(self, key: tuple[str, str]) -> ReviewRecord | None:
        return self._records.get(key)

    def put(self, record: ReviewRecord) -> None:
        self._records[_dedupe_key(record)] = record

    def all(self) -> list[ReviewRecord]:
        return list(self._records.values())

    def for_property(self, property_id: str, platform: str | None = None) -> list[ReviewRecord]:
        return [
            r
            for r in self._records.values()
            if r.property_id == property_id and (platform is None or r.platform == platform)
        ]

    def __len__(self) -> int:
        return len(self._records)


def parse_upload(data: bytes, filename: str) -> list[RawReview]:
    """Parse an uploaded CSV/JSON file into raw review dicts (Req 1.3).

    Rejects the WHOLE file (naming the failing condition) if it exceeds the size
    or review-count limits.
    """
    if len(data) > MAX_UPLOAD_BYTES:
        raise UploadRejectedError(
            f"file size {len(data)} bytes exceeds the 20MB limit (max {MAX_UPLOAD_BYTES})"
        )
    text = data.decode("utf-8")
    rows: list[RawReview]
    if filename.lower().endswith(".json"):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise UploadRejectedError(f"invalid JSON file: {exc}") from exc
        rows = parsed if isinstance(parsed, list) else parsed.get("reviews", [])
    elif filename.lower().endswith(".csv"):
        import csv
        import io

        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
    else:
        raise UploadRejectedError(f"unsupported file type for {filename!r}; use .json or .csv")

    if len(rows) > MAX_UPLOAD_REVIEWS:
        raise UploadRejectedError(
            f"review count {len(rows)} exceeds the 10000-review limit"
        )
    return rows


class ReviewCollector:
    """Collect reviews from uploads, the sample dataset and platform adapters."""

    def __init__(self, store: ReviewStore | None = None) -> None:
        self.store = store or ReviewStore()
        self.parser = ReviewParser()
        self.jobs: dict[str, CollectionJob] = {}
        self._active: set[tuple[str, str]] = set()
        self._job_seq = 0

    # ---- public ingest entrypoints ----
    def ingest(
        self,
        platform: Platform,
        property_id: str,
        raws: list[RawReview],
    ) -> CollectionJob:
        """Ingest an already-parsed batch of raw reviews as one job."""
        guard_key = (platform.value, property_id)
        if guard_key in self._active:
            raise ConcurrentJobError(
                f"a collection job for {property_id}/{platform.value} is already running"
            )
        self._active.add(guard_key)
        self._job_seq += 1
        job = CollectionJob(
            job_id=f"job-{self._job_seq}",
            platform=platform.value,
            property_id=property_id,
            started_at=datetime.now(UTC),
        )
        self.jobs[job.job_id] = job
        try:
            self._apply_batch(job, raws)
            self._finalise(job)
        finally:
            self._active.discard(guard_key)
        return job

    def ingest_with_retry(
        self,
        platform: Platform,
        property_id: str,
        fetch: Callable[[], list[RawReview]],
        sleeper: Callable[[float], None] = lambda _s: None,
    ) -> CollectionJob:
        """Run a fetch+ingest with the 30/60/120/240/480s retry cap (Req 1.8).

        ``fetch`` may raise to simulate a transient platform failure. After
        ``MAX_ATTEMPTS`` failures the job is marked ``failed`` while any records
        collected on earlier successful attempts are preserved.
        """
        guard_key = (platform.value, property_id)
        if guard_key in self._active:
            raise ConcurrentJobError(
                f"a collection job for {property_id}/{platform.value} is already running"
            )
        self._active.add(guard_key)
        self._job_seq += 1
        job = CollectionJob(
            job_id=f"job-{self._job_seq}",
            platform=platform.value,
            property_id=property_id,
            started_at=datetime.now(UTC),
        )
        self.jobs[job.job_id] = job
        try:
            for attempt in range(MAX_ATTEMPTS):
                job.attempts = attempt + 1
                try:
                    raws = fetch()
                except Exception as exc:  # transient failure
                    job.errors.append(f"attempt {attempt + 1} failed: {exc}")
                    # Sleep before the NEXT attempt only (no sleep after the
                    # final attempt): 30/60/120/240s between 5 attempts.
                    if attempt < MAX_ATTEMPTS - 1:
                        sleeper(RETRY_SCHEDULE_SECONDS[attempt])
                    continue
                self._apply_batch(job, raws)
                self._finalise(job)
                return job
            # Exhausted retries: fail but keep prior records (Req 1.8).
            job.status = JobStatus.FAILED
            job.finished_at = datetime.now(UTC)
            return job
        finally:
            self._active.discard(guard_key)

    # ---- internals ----
    def _apply_batch(self, job: CollectionJob, raws: list[RawReview]) -> None:
        result = self.parser.parse_batch(raws)
        for err in result.errors:
            job.failure_count += 1
            job.errors.append(str(err))
        for record in result.records:
            key = _dedupe_key(record)
            existing = self.store.get(key)
            if existing is None:
                self.store.put(record)
                job.new_count += 1
                continue
            # Overwrite mutable fields keeping the existing id; count as updated
            # only if something changed (Req 1.6).
            changed = any(
                getattr(existing, field_name) != getattr(record, field_name)
                for field_name in _MUTABLE_FIELDS
            )
            if changed:
                merged = existing.model_copy(
                    update={fname: getattr(record, fname) for fname in _MUTABLE_FIELDS}
                )
                self.store.put(merged)
                job.updated_count += 1

    def _finalise(self, job: CollectionJob) -> None:
        job.finished_at = datetime.now(UTC)
        processed = job.new_count + job.updated_count
        if job.failure_count and processed:
            job.status = JobStatus.PARTIALLY_SUCCEEDED
        elif job.failure_count and not processed:
            job.status = JobStatus.FAILED
        else:
            job.status = JobStatus.SUCCEEDED

    def is_running(self, platform: Platform, property_id: str) -> bool:
        """Return True if a job for (property, platform) is active."""
        return (platform.value, property_id) in self._active
