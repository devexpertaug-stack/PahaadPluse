"""Unit + property tests for Review_Parser / Review_Printer (Req 3)."""

from __future__ import annotations

from datetime import date, timedelta

import jsonschema
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.models.review import Platform, ReviewRecord
from app.services.market_radar.parsing import (
    ReviewParseError,
    ReviewParser,
    ReviewPrinter,
    load_schema,
    normalise_rating,
    round_trip,
)

_PARSER = ReviewParser()
_PRINTER = ReviewPrinter()


def _raw(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "google:abc",
        "platform": "Google",
        "platform_review_id": "abc",
        "property_id": "prop-1",
        "property_name": "Pine View Inn",
        "author_pseudonym": "anon-123",
        "date": "2024-05-01",
        "native_rating": 4,
        "text": "Lovely stay",
        "source_url": "https://maps.google.com/review/abc",
    }
    base.update(overrides)
    return base


def test_parse_valid_record() -> None:
    record = _PARSER.parse_one(_raw())
    assert record.platform == Platform.GOOGLE.value
    assert record.normalised_rating == 4.0


def test_booking_native_scale_maps_to_1_5() -> None:
    assert normalise_rating(Platform.BOOKING, 1.0) == 1.0
    assert normalise_rating(Platform.BOOKING, 10.0) == 5.0
    assert normalise_rating(Platform.BOOKING, 5.5) == 3.0


@pytest.mark.parametrize(
    "overrides,field",
    [
        ({"text": ""}, "text"),
        ({"text": "   "}, "text"),
        ({"date": ""}, "date"),
        ({"date": "not-a-date"}, "date"),
        ({"native_rating": None}, "rating"),
        ({"native_rating": 99}, "native_rating"),
    ],
)
def test_invalid_fields_raise_naming_error(overrides: dict, field: str) -> None:
    with pytest.raises(ReviewParseError) as exc:
        _PARSER.parse_one(_raw(**overrides))
    assert exc.value.field == field
    assert exc.value.source_id  # names the source id


def test_future_date_rejected() -> None:
    future = (date.today() + timedelta(days=5)).isoformat()
    with pytest.raises(ReviewParseError) as exc:
        _PARSER.parse_one(_raw(date=future))
    assert exc.value.field == "date"


def test_batch_continues_past_bad_records() -> None:
    result = _PARSER.parse_batch(
        [
            _raw(platform_review_id="ok1"),
            _raw(text="", platform_review_id="bad"),
            _raw(platform_review_id="ok2"),
        ]
    )
    assert len(result.records) == 2
    assert len(result.errors) == 1
    assert result.errors[0].source_id == "bad"


def test_printed_json_validates_against_published_schema() -> None:
    record = _PARSER.parse_one(_raw())
    payload = _PRINTER.to_dict(record)
    jsonschema.validate(payload, load_schema())


# ---- property tests ----

_DEVANAGARI_TEXT = st.sampled_from(
    [
        "कमरा बहुत अच्छा था",
        "खाना स्वादिष्ट था",
        "साफ़ और शांत जगह",
        "स्टाफ़ बहुत मददगार",
    ]
)
_HINGLISH_TEXT = st.sampled_from(
    [
        "kamra bahut accha tha",
        "khana badhiya staff saaf",
        "jagah shandaar lekin mehenga",
        "sewa achhi thi value for money",
    ]
)


@given(
    platform=st.sampled_from(list(Platform)),
    native=st.floats(min_value=1.0, max_value=10.0),
)
def test_normalised_rating_always_in_range(platform: Platform, native: float) -> None:
    from app.models.review import PLATFORM_RATING_SCALES

    low, high = PLATFORM_RATING_SCALES[platform]
    native = max(low, min(high, native))
    normalised = normalise_rating(platform, native)
    assert 1.0 <= normalised <= 5.0


@given(text=st.one_of(_DEVANAGARI_TEXT, _HINGLISH_TEXT))
def test_round_trip_parse_print_is_byte_identical(text: str) -> None:
    record = _PARSER.parse_one(_raw(text=text, platform_review_id="rt"))
    once = _PRINTER.to_json(record)
    twice = _PRINTER.to_json(round_trip(record))
    assert once == twice
    # And the record itself is unchanged field-for-field.
    assert round_trip(record) == record


def test_round_trip_preserves_model_identity() -> None:
    record = ReviewRecord(
        id="x",
        platform=Platform.AGODA,
        platform_review_id="y",
        property_id="p",
        property_name="n",
        author_pseudonym="anon",
        date=date(2024, 1, 1),
        native_rating=8.0,
        normalised_rating=normalise_rating(Platform.AGODA, 8.0),
        text="कमरा अच्छा",
    )
    assert round_trip(record) == record
