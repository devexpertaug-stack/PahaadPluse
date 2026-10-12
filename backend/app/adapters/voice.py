"""Voice / transcription pipeline adapter.

Defines the :class:`VoicePipeline` interface and a stub implementation. A real
Whisper adapter sits behind the same interface in a later feature.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.core.config import VoiceProvider, get_settings


@dataclass
class Transcription:
    """Result of a transcription (Req 21).

    ``language`` is the detected language tag (at least ``hi``, ``en`` and one
    more Indian language are supported in the demo). ``confidence`` is in
    ``[0, 1]``; a value below 0.5 flags the complaint for staff. For a
    non-English transcript ``translation_en`` carries an English translation.
    """

    text: str
    language: str
    engine: str
    confidence: float = 0.9
    translation_en: str | None = None


class VoicePipeline(ABC):
    """Interface for audio transcription."""

    @abstractmethod
    def transcribe(self, audio: bytes, *, language: str | None = None) -> Transcription:
        """Transcribe ``audio`` bytes into text."""


# Deterministic demo "audio" protocol: in the sandbox there is no live ASR, so
# the demo helper passes the intended transcript as UTF-8 bytes optionally
# prefixed with a header ``lang=<tag>;conf=<float>|<transcript>``. The stub
# parses that header so the whole voice loop is demonstrable offline, covering
# Hindi, English and Garhwali (a third Indian language) in the demo.
_SUPPORTED_VOICE_LANGS = frozenset({"en", "hi", "gbm"})  # gbm = Garhwali

# Tiny glossary for a best-effort English gloss of a non-English transcript.
_VOICE_GLOSSARY = {
    "geyser": "geyser",
    "kaam": "working",
    "nahi": "not",
    "kar": "",
    "raha": "",
    "room": "room",
    "mein": "in",
    "garam": "hot",
    "pani": "water",
    "nahin": "not",
    "aa": "coming",
    "आ": "coming",
    "रहा": "",
    "गरम": "hot",
    "पानी": "water",
    "नहीं": "not",
    "गीजर": "geyser",
}


def _detect_voice_language(text: str) -> str:
    if any("\u0900" <= ch <= "\u097f" for ch in text):
        return "hi"
    lowered = text.lower()
    hinglish_markers = {"nahi", "nahin", "kaam", "raha", "mein", "pani", "garam", "hai"}
    if any(m in lowered.split() for m in hinglish_markers):
        return "hi"
    return "en"


def _gloss_en(text: str) -> str:
    out = []
    for raw in text.split():
        token = raw.strip(".,!?;:").lower()
        gloss = _VOICE_GLOSSARY.get(token)
        if gloss is None:
            out.append(raw)
        elif gloss:
            out.append(gloss)
    return " ".join(out)


class StubVoicePipeline(VoicePipeline):
    """Offline stub transcriber.

    Decodes the demo "audio" bytes into a transcript, detects the language and
    confidence from an optional header, and produces an English translation for
    non-English transcripts. Falls back to an explicit placeholder when the
    bytes are not demo-encoded.
    """

    def transcribe(self, audio: bytes, *, language: str | None = None) -> Transcription:
        header_lang: str | None = None
        confidence = 0.9
        try:
            decoded = audio.decode("utf-8")
        except (UnicodeDecodeError, AttributeError):
            return Transcription(
                text="[voice-stub] transcription unavailable in local/demo mode",
                language=language or "und",
                engine="stub",
                confidence=0.0,
            )
        text = decoded
        if "|" in decoded and decoded.split("|", 1)[0].startswith("lang="):
            header, text = decoded.split("|", 1)
            for part in header.split(";"):
                if part.startswith("lang="):
                    header_lang = part[len("lang=") :].strip()
                elif part.startswith("conf="):
                    try:
                        confidence = float(part[len("conf=") :])
                    except ValueError:
                        pass
        detected = header_lang or language or _detect_voice_language(text)
        if detected not in _SUPPORTED_VOICE_LANGS:
            detected = _detect_voice_language(text)
        translation = None
        if detected != "en":
            translation = _gloss_en(text)
        return Transcription(
            text=text,
            language=detected,
            engine="stub",
            confidence=confidence,
            translation_en=translation,
        )


class WhisperVoicePipeline(VoicePipeline):
    """Stub for a real Whisper adapter (same interface)."""

    def __init__(self, model_path: str) -> None:
        self._model_path = model_path

    def transcribe(self, audio: bytes, *, language: str | None = None) -> Transcription:
        raise NotImplementedError(
            "Whisper adapter is not yet implemented; use the stub pipeline."
        )


def get_voice_pipeline() -> VoicePipeline:
    """Select the voice pipeline based on configuration."""
    settings = get_settings()
    if settings.voice_provider is VoiceProvider.WHISPER and settings.voice_model_path:
        try:
            return WhisperVoicePipeline(model_path=settings.voice_model_path)
        except Exception:  # pragma: no cover - defensive, model unavailable
            pass
    return StubVoicePipeline()


# ---------------------------------------------------------------------------
# Text-to-speech (TTS) adapter for the Owner's weekly Hindi voice briefing
# (Req 22). Interface + a stub that emits a placeholder audio artifact when a
# real TTS engine (e.g. gTTS) is not reachable in the sandbox.
# ---------------------------------------------------------------------------
# Average Hindi narration pace used to estimate audio duration from a script so
# the briefing can be kept within the 60-second cap (Req 22.3).
HINDI_WORDS_PER_SECOND = 2.5
MAX_BRIEFING_SECONDS = 60.0


@dataclass
class SpeechArtifact:
    """Result of a text-to-speech synthesis for the voice briefing."""

    audio: bytes
    engine: str
    is_placeholder: bool
    estimated_seconds: float
    note: str | None = None


class TextToSpeech(ABC):
    """Interface for turning a script into speech audio."""

    @abstractmethod
    def synthesize(self, script: str, *, language: str = "hi") -> SpeechArtifact:
        """Synthesize ``script`` into audio bytes."""


def estimate_speech_seconds(script: str) -> float:
    """Estimate narration seconds for ``script`` at the Hindi pace."""
    words = max(1, len(script.split()))
    return round(words / HINDI_WORDS_PER_SECOND, 1)


class StubTextToSpeech(TextToSpeech):
    """Offline TTS stub.

    In the sandbox gTTS / a cloud TTS is typically unreachable, so this emits a
    deterministic placeholder audio artifact (a tiny WAV-like header plus the
    UTF-8 script bytes) and documents that it is a placeholder. The whole
    briefing loop stays demonstrable offline.
    """

    def synthesize(self, script: str, *, language: str = "hi") -> SpeechArtifact:
        estimated = estimate_speech_seconds(script)
        header = b"RIFF\x00\x00\x00\x00WAVEfmt placeholder;"
        audio = header + script.encode("utf-8")
        return SpeechArtifact(
            audio=audio,
            engine="stub",
            is_placeholder=True,
            estimated_seconds=estimated,
            note=(
                "Placeholder audio artifact: no live TTS engine reachable in "
                "this environment. The script text accompanies the audio."
            ),
        )


def get_tts() -> TextToSpeech:
    """Select the TTS engine (only the offline stub is wired for the demo)."""
    return StubTextToSpeech()
