"""F7 Owner's weekly Hindi voice briefing tests (Req 22)."""

from __future__ import annotations

from app.adapters.llm import TemplateLLMClient
from app.adapters.voice import MAX_BRIEFING_SECONDS, StubTextToSpeech
from app.adapters.whatsapp import MockWhatsAppGateway
from app.services.market_radar.briefing import BriefingGenerator


def _generator() -> tuple[BriefingGenerator, MockWhatsAppGateway]:
    gateway = MockWhatsAppGateway(signing_secret="test")
    gen = BriefingGenerator(
        llm=TemplateLLMClient(), tts=StubTextToSpeech(), gateway=gateway
    )
    return gen, gateway


def test_briefing_covers_required_content() -> None:
    gen, _ = _generator()
    b = gen.generate(open_p1_p2=2, new_changepoints=1, deliver=False).to_dict()
    script = b["script"]
    assert "रेटिंग" in script  # rating change
    assert "पहलू" in script  # top improving/declining aspect
    assert "बदलाव बिंदु" in script  # changepoints
    assert "शिकायत" in script  # P1/P2 complaints
    assert "सुझाव" in script  # recommended action


def test_numbers_sourced_from_metrics() -> None:
    gen, _ = _generator()
    b = gen.generate(open_p1_p2=3, new_changepoints=2, deliver=False).to_dict()
    assert b["metrics"]["open_p1_p2"] == 3
    assert b["metrics"]["new_changepoints"] == 2
    assert str(b["metrics"]["open_p1_p2"]) in b["script"]


def test_audio_within_sixty_seconds() -> None:
    gen, _ = _generator()
    b = gen.generate(deliver=False).to_dict()
    assert b["estimated_seconds"] <= MAX_BRIEFING_SECONDS
    assert b["within_cap"] is True
    assert b["audio_is_placeholder"] is True
    assert b["audio_note"]


def test_delivered_to_opted_in_owners_via_whatsapp_mock() -> None:
    gen, gateway = _generator()
    owners = ["+919800000900", "+919800000901"]
    b = gen.generate(opted_in_owners=owners, deliver=True).to_dict()
    assert b["delivered_to"] == owners
    assert len(gateway.outbox) == 2
    # Both the audio marker and the script text are delivered.
    assert "audio" in gateway.outbox[0].body


def test_template_fallback_is_labelled() -> None:
    gen, _ = _generator()
    b = gen.generate(deliver=False).to_dict()
    assert b["template_generated"] is True
