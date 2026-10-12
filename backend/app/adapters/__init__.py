"""External-service adapters.

Each module defines an abstract interface plus a working local/fallback
implementation. The factory functions here select the implementation based on
configured providers so the platform runs with no third-party credentials.
"""

from __future__ import annotations

from app.adapters.geocoder import Geocoder, get_geocoder
from app.adapters.llm import LLMClient, get_llm_client
from app.adapters.sentiment import SentimentEngine, get_sentiment_engine
from app.adapters.voice import VoicePipeline, get_voice_pipeline
from app.adapters.whatsapp import WhatsAppGateway, get_whatsapp_gateway

__all__ = [
    "SentimentEngine",
    "get_sentiment_engine",
    "LLMClient",
    "get_llm_client",
    "WhatsAppGateway",
    "get_whatsapp_gateway",
    "VoicePipeline",
    "get_voice_pipeline",
    "Geocoder",
    "get_geocoder",
]
