"""Tests for the Destination Lens (Req 14)."""

from __future__ import annotations

import time
from datetime import date

from app.services.destination_lens.entities import extract_place_entities
from app.services.destination_lens.evidence_packet import MIN_QUOTES, EvidencePacketGenerator
from app.services.destination_lens.service import DestinationLensService


def test_extracts_place_entities_english_hinglish_devanagari() -> None:
    en = extract_place_entities("Terrible traffic jam near Mall Road")
    assert any(e.canonical == "mall road" and "traffic" in e.themes for e in en)

    hinglish = extract_place_entities("Kempty Falls ke paas bahut kooda tha")
    assert any(e.canonical == "kempty falls" and "garbage" in e.themes for e in hinglish)

    deva = extract_place_entities("माल रोड पर पार्किंग की समस्या है")
    assert any(e.canonical == "mall road" and "parking" in e.themes for e in deva)


def test_hotspots_are_geocoded_and_sorted() -> None:
    svc = DestinationLensService()
    hotspots = svc.hotspots()
    assert hotspots, "seed should produce hotspots"
    # gazetteer-first geocoding gives coordinates + confidence.
    for h in hotspots:
        assert h.latitude is not None and h.longitude is not None
    # sorted by negative count desc
    counts = [h.negative_count for h in hotspots]
    assert counts == sorted(counts, reverse=True)


def test_heatmap_filters_by_theme_and_date() -> None:
    svc = DestinationLensService()
    all_view = svc.heatmap_view()
    traffic_view = svc.heatmap_view(theme="traffic")
    assert traffic_view["total_negative_mentions"] <= all_view["total_negative_mentions"]
    # a tight date range reduces mentions
    narrow = svc.heatmap_view(start=date(2024, 5, 1), end=date(2024, 5, 31))
    assert narrow["total_negative_mentions"] <= all_view["total_negative_mentions"]


def test_evidence_packet_has_required_sections_and_quotes() -> None:
    svc = DestinationLensService()
    gen = EvidencePacketGenerator(svc)
    start = time.monotonic()
    result = gen.generate("mall road", None, None, None, language="en")
    elapsed = time.monotonic() - start
    assert elapsed < 30.0  # Req 14.4 (well under budget)
    assert result.pdf_bytes.startswith(b"%PDF-")
    assert result.quote_count >= MIN_QUOTES
    assert result.distinct_properties >= 1


def test_evidence_packet_hindi_mode_and_issues_surfaced_metric() -> None:
    svc = DestinationLensService()
    gen = EvidencePacketGenerator(svc)
    before = svc.issues_surfaced
    result = gen.generate("mall road", None, None, None, language="hi")
    assert result.language == "hi"
    assert result.pdf_bytes.startswith(b"%PDF-")
    # Each generated packet increments the issues-surfaced metric (Req 14.8).
    assert svc.issues_surfaced == before + 1


def test_evidence_packet_excludes_pseudonyms_and_pii() -> None:
    svc = DestinationLensService()
    gen = EvidencePacketGenerator(svc)
    result = gen.generate("mall road", None, None, None, language="en")
    text = result.pdf_bytes.decode("latin-1", errors="ignore")
    # Pseudonyms (anon-*/guest-*) must never appear in the packet.
    assert "anon-" not in text
    assert "guest-" not in text
