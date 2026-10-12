"""Tests that default config selects the local/fallback adapters."""

from __future__ import annotations

from app.adapters.geocoder import GazetteerGeocoder, get_geocoder
from app.adapters.llm import TemplateLLMClient, get_llm_client
from app.adapters.sentiment import FallbackSentimentEngine, get_sentiment_engine
from app.adapters.voice import StubVoicePipeline, get_voice_pipeline
from app.adapters.whatsapp import MockWhatsAppGateway, get_whatsapp_gateway


def test_default_adapters_are_local_fallbacks() -> None:
    assert isinstance(get_sentiment_engine(), FallbackSentimentEngine)
    assert isinstance(get_llm_client(), TemplateLLMClient)
    assert isinstance(get_whatsapp_gateway(), MockWhatsAppGateway)
    assert isinstance(get_voice_pipeline(), StubVoicePipeline)
    assert isinstance(get_geocoder(), GazetteerGeocoder)


def test_sentiment_is_idempotent_and_tags_version() -> None:
    engine = get_sentiment_engine()
    first = engine.classify("The room was clean and the staff friendly")
    second = engine.classify("The room was clean and the staff friendly")
    assert first == second
    assert first.label == "positive"
    assert first.model_version


def test_sentiment_evidence_spans_are_substrings_of_original() -> None:
    engine = get_sentiment_engine()
    text = "Rooms were dirty and service was slow"
    result = engine.classify(text)
    assert result.label == "negative"
    for span in result.evidence:
        assert span in text


def test_sentiment_handles_empty_input() -> None:
    engine = get_sentiment_engine()
    assert engine.classify("").label == "unsupported"


def test_llm_output_is_labelled_template_generated() -> None:
    client = get_llm_client()
    response = client.generate("Draft a reply to a guest complaint")
    assert response.template_generated is True
    assert "template-generated" in response.text


def test_whatsapp_mock_records_outbound_and_verifies_signature() -> None:
    gateway = get_whatsapp_gateway()
    assert isinstance(gateway, MockWhatsAppGateway)
    gateway.send("+911234567890", "Namaste from PahadPulse")
    assert len(gateway.outbox) == 1
    payload = b"hello"
    signature = gateway.sign(payload)
    assert gateway.verify_webhook(payload, signature) is True
    assert gateway.verify_webhook(payload, "sha256=bad") is False


def test_geocoder_resolves_mussoorie() -> None:
    geocoder = get_geocoder()
    point = geocoder.geocode("Mussoorie")
    assert point is not None
    assert point.source == "gazetteer"
    assert geocoder.geocode("Nowhere-ville") is None
