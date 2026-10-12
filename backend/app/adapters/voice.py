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
    """Result of a transcription."""

    text: str
    language: str
    engine: str


class VoicePipeline(ABC):
    """Interface for audio transcription."""

    @abstractmethod
    def transcribe(self, audio: bytes, *, language: str | None = None) -> Transcription:
        """Transcribe ``audio`` bytes into text."""


class StubVoicePipeline(VoicePipeline):
    """Stub transcriber used offline. Returns an explicit placeholder."""

    def transcribe(self, audio: bytes, *, language: str | None = None) -> Transcription:
        return Transcription(
            text="[voice-stub] transcription unavailable in local/demo mode",
            language=language or "unknown",
            engine="stub",
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
