"""Validate the Hinglish_Test_Set (Req 16.1-16.2, 16.6)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.adapters.sentiment import _NEGATIVE_LEXICON, _POSITIVE_LEXICON

_DIR = Path(__file__).resolve().parents[2] / "data" / "hinglish_test_set"
_LABELS = {"positive", "negative", "neutral"}
_ASPECTS = {
    "Food",
    "Room",
    "Housekeeping",
    "Staff",
    "Location",
    "Service",
    "Value_for_Money",
    "Cleanliness",
    "Booking_Experience",
}


def _load() -> list[dict]:
    return json.loads((_DIR / "hinglish_test_set.json").read_text(encoding="utf-8"))


def test_size_within_300_to_500() -> None:
    recs = _load()
    assert 300 <= len(recs) <= 500


def test_every_review_has_overall_and_aspect_labels() -> None:
    for rec in _load():
        assert rec["overall_label"] in _LABELS
        assert rec["aspect_labels"]
        for aspect, label in rec["aspect_labels"].items():
            assert aspect in _ASPECTS
            assert label in _LABELS


def test_double_labelled_subset_at_least_50() -> None:
    double = json.loads((_DIR / "double_labelled_subset.json").read_text(encoding="utf-8"))
    assert len(double) >= 50
    for row in double:
        assert row["annotator_1"] in _LABELS
        assert row["annotator_2"] in _LABELS


def test_guidelines_report_kappa_and_annotators() -> None:
    text = (_DIR / "labelling_guidelines.md").read_text(encoding="utf-8")
    assert "Cohen's kappa" in text
    assert re.search(r"Annotators:\*\*\s*2", text)
    assert re.search(r"kappa, overall label\):\*\*\s*0\.\d+", text)


def test_test_set_vocabulary_disjoint_from_fallback_lexicon() -> None:
    """Req 16.6: no Sentiment_Engine tuning overlap.

    The fallback lexicon tokens must not appear as whole words in the test-set
    text, so the evaluation set is genuinely held out from the lexicon.
    """
    lexicon = {t.lower() for t in (_POSITIVE_LEXICON | _NEGATIVE_LEXICON)}
    tokens: set[str] = set()
    for rec in _load():
        tokens.update(re.findall(r"[^\W_]+", rec["text"].lower()))
    overlap = lexicon & tokens
    assert overlap == set(), f"test set overlaps fallback lexicon: {sorted(overlap)}"
