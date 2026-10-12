"""Review_Parser and Review_Printer (Req 3).

Responsibilities:

* Parse ``Raw_Review`` payloads (per-platform dicts, CSV/JSON upload rows and
  the sample dataset) into :class:`~app.models.review.ReviewRecord` instances.
* Apply the documented per-platform linear native->normalised rating mapping:
  the platform's native minimum maps to ``1.0`` and its maximum to ``5.0``,
  linearly interpolated and rounded to 2 decimal places (Req 3.3).
* Raise a structured, non-fatal :class:`ReviewParseError` (naming the field and
  source id) on missing/empty text, date or rating, an unparseable or future
  date, or an out-of-scale rating — the batch continues (Req 3.1, 3.2).
* Emit canonical UTF-8 JSON that validates against the published schema and
  round-trips byte-identically through the parser (Req 3.4, 3.5, 3.8).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.models.review import (
    PLATFORM_RATING_SCALES,
    Platform,
    ReviewRecord,
)

RawReview = dict[str, Any]

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "review_record.schema.json"


class ReviewParseError(Exception):
    """A per-record parse failure that names the offending field + source id.

    Raised (and caught by batch callers) so one bad record never aborts the
    whole batch (Req 3.1).
    """

    def __init__(self, field: str, source_id: str, reason: str) -> None:
        self.field = field
        self.source_id = source_id
        self.reason = reason
        super().__init__(f"{field} (source_id={source_id!r}): {reason}")


@dataclass
class BatchParseResult:
    """Outcome of parsing a batch of raw reviews."""

    records: list[ReviewRecord]
    errors: list[ReviewParseError]


def normalise_rating(platform: Platform, native_value: float) -> float:
    """Map a native rating onto the canonical ``[1.0, 5.0]`` scale (Req 3.3).

    Linear interpolation with the platform minimum -> 1.0 and maximum -> 5.0,
    rounded to two decimal places. Raises ``ValueError`` if out of scale.
    """
    low, high = PLATFORM_RATING_SCALES[platform]
    if native_value < low or native_value > high:
        raise ValueError(
            f"rating {native_value} outside native scale [{low}, {high}] for {platform}"
        )
    if high == low:
        return 5.0
    normalised = 1.0 + (native_value - low) * (5.0 - 1.0) / (high - low)
    return round(normalised, 2)


def _parse_date(value: Any, source_id: str) -> date:
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ReviewParseError("date", source_id, "missing/empty date")
    if isinstance(value, date) and not isinstance(value, datetime):
        parsed = value
    else:
        text = value.isoformat() if isinstance(value, datetime) else str(value).strip()
        try:
            parsed = date.fromisoformat(text[:10])
        except ValueError as exc:
            raise ReviewParseError("date", source_id, f"unparseable date {value!r}") from exc
    today = datetime.now(UTC).date()
    if parsed > today:
        raise ReviewParseError("date", source_id, f"future date {parsed.isoformat()}")
    return parsed


def _parse_rating(value: Any, source_id: str) -> float:
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ReviewParseError("rating", source_id, "missing/empty rating")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ReviewParseError("rating", source_id, f"non-numeric rating {value!r}") from exc


def _require_text(value: Any, source_id: str) -> str:
    if value is None or not str(value).strip():
        raise ReviewParseError("text", source_id, "missing/empty text")
    return str(value)


class ReviewParser:
    """Parse Raw_Review payloads into Review_Records."""

    def parse_one(self, raw: RawReview) -> ReviewRecord:
        """Parse a single raw review. Raises :class:`ReviewParseError`."""
        source_id = str(raw.get("platform_review_id") or raw.get("id") or "<unknown>")

        platform_value = raw.get("platform")
        try:
            platform = Platform(platform_value)
        except ValueError as exc:
            raise ReviewParseError(
                "platform", source_id, f"unknown platform {platform_value!r}"
            ) from exc

        text = _require_text(raw.get("text"), source_id)
        review_date = _parse_date(raw.get("date"), source_id)
        native_rating = _parse_rating(raw.get("native_rating", raw.get("rating")), source_id)
        try:
            normalised = normalise_rating(platform, native_rating)
        except ValueError as exc:
            raise ReviewParseError("native_rating", source_id, str(exc)) from exc

        source_url = raw.get("source_url")
        if "missing_source_url" in raw:
            missing_url = bool(raw["missing_source_url"])
        else:
            missing_url = not (isinstance(source_url, str) and source_url.strip())

        payload: dict[str, Any] = {
            "id": str(raw.get("id") or f"{platform.value}:{source_id}"),
            "platform": platform.value,
            "platform_review_id": source_id,
            "property_id": str(raw.get("property_id") or "unknown"),
            "property_name": str(raw.get("property_name") or "unknown"),
            "author_pseudonym": str(raw.get("author_pseudonym") or ""),
            "date": review_date,
            "native_rating": native_rating,
            "normalised_rating": normalised,
            "text": text,
            "source_url": None if missing_url else source_url,
            "missing_source_url": missing_url,
        }
        # Carry through already-derived fields when re-parsing printed records.
        for key in (
            "detected_language",
            "script",
            "detection_confidence",
            "transliterated_text",
            "aspect_ratings",
            "overall_sentiment",
            "overall_sentiment_confidence",
            "aspect_mentions",
            "sentiment_model_version",
            "transliteration_failed",
            "sentiment_unsupported",
            "sentiment_text_absent",
            "sentiment_failed",
        ):
            if key in raw:
                payload[key] = raw[key]

        try:
            return ReviewRecord(**payload)
        except ValidationError as exc:
            raise ReviewParseError("record", source_id, str(exc)) from exc

    def parse_batch(self, raws: list[RawReview]) -> BatchParseResult:
        """Parse a list of raw reviews, collecting errors without aborting."""
        records: list[ReviewRecord] = []
        errors: list[ReviewParseError] = []
        for raw in raws:
            try:
                records.append(self.parse_one(raw))
            except ReviewParseError as exc:
                errors.append(exc)
        return BatchParseResult(records=records, errors=errors)


class ReviewPrinter:
    """Serialise Review_Records to canonical UTF-8 JSON (Req 3.4)."""

    def to_dict(self, record: ReviewRecord) -> dict[str, Any]:
        """Return a JSON-ready dict (dates as ISO strings, enums as values)."""
        return json.loads(record.model_dump_json())

    def to_json(self, record: ReviewRecord) -> str:
        """Return canonical UTF-8 JSON: sorted keys, no ASCII escaping."""
        return json.dumps(
            self.to_dict(record),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )


def round_trip(record: ReviewRecord) -> ReviewRecord:
    """``parse(print(record))`` helper used by the property tests (Req 3.5)."""
    printer = ReviewPrinter()
    parser = ReviewParser()
    return parser.parse_one(printer.to_dict(record))


def load_schema() -> dict[str, Any]:
    """Load the published Review_Record JSON schema."""
    with _SCHEMA_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)
