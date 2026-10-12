"""Application configuration via pydantic-settings.

Reads environment variables (and an optional `.env` file) and exposes typed
settings. Feature-flag/provider enums select real-vs-fallback adapter
implementations. All providers default to local/fallback values so the service
runs with NO third-party credentials.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class SentimentProvider(StrEnum):
    """Which sentiment engine implementation to use."""

    FALLBACK = "fallback"
    MURIL = "muril"


class LLMProvider(StrEnum):
    """Which LLM client implementation to use."""

    FALLBACK = "fallback"
    OPENAI = "openai"
    AZURE = "azure"


class WhatsAppProvider(StrEnum):
    """Which WhatsApp gateway implementation to use."""

    MOCK = "mock"
    TWILIO = "twilio"
    META = "meta"


class VoiceProvider(StrEnum):
    """Which voice pipeline implementation to use."""

    STUB = "stub"
    WHISPER = "whisper"


class GeocoderProvider(StrEnum):
    """Which geocoder implementation to use."""

    GAZETTEER = "gazetteer"
    EXTERNAL = "external"


class Settings(BaseSettings):
    """Typed application settings loaded from the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- Core app ----
    app_env: str = "local"
    frontend_origin: str = "http://localhost:3000"
    database_url: str = "sqlite+aiosqlite:///./data/pahadpulse.sqlite"

    # ---- Security / privacy ----
    pii_encryption_key: str = "dev-only-pii-key-change-me"
    pseudonym_salt: str = "dev-only-pseudonym-salt-change-me"
    session_secret: str = "dev-only-session-secret-change-me"

    # ---- Sentiment engine ----
    sentiment_model_provider: SentimentProvider = SentimentProvider.FALLBACK
    sentiment_model_name: str = "lexicon-fallback-v1"
    sentiment_model_path: str = ""

    # ---- LLM ----
    llm_api_provider: LLMProvider = LLMProvider.FALLBACK
    llm_api_key: str = ""
    llm_api_base_url: str = ""
    llm_api_model: str = "template-fallback-v1"

    # ---- WhatsApp ----
    whatsapp_provider: WhatsAppProvider = WhatsAppProvider.MOCK
    whatsapp_account_sid: str = ""
    whatsapp_auth_token: str = ""
    whatsapp_from_number: str = ""
    whatsapp_signing_secret: str = "dev-only-whatsapp-signing-secret"

    # ---- Voice ----
    voice_provider: VoiceProvider = VoiceProvider.STUB
    voice_model_path: str = ""

    # ---- Geocoder ----
    geocoder_provider: GeocoderProvider = GeocoderProvider.GAZETTEER
    geocoder_api_key: str = ""
    geocoder_api_base_url: str = ""

    @property
    def cors_origins(self) -> list[str]:
        """Allowed CORS origins for the frontend website."""
        return [self.frontend_origin]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
