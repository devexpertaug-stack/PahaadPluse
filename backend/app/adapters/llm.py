"""LLM client adapter.

Defines the :class:`LLMClient` interface and a deterministic template fallback
that labels its output as template-generated (Req 12.9 / 34.3). Real providers
(OpenAI/Azure/etc.) sit behind the same interface and are selected by config.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.core.config import LLMProvider, get_settings


@dataclass
class LLMResponse:
    """Result of an LLM generation."""

    text: str
    model: str
    template_generated: bool


class LLMClient(ABC):
    """Interface for text generation."""

    @abstractmethod
    def generate(self, prompt: str, *, context: dict | None = None) -> LLMResponse:
        """Generate text for ``prompt`` with optional structured ``context``."""


class TemplateLLMClient(LLMClient):
    """Deterministic template fallback. Output is labelled template-generated."""

    def __init__(self, model: str = "template-fallback-v1") -> None:
        self._model = model

    def generate(self, prompt: str, *, context: dict | None = None) -> LLMResponse:
        summary = (prompt or "").strip()
        if len(summary) > 240:
            summary = summary[:237] + "..."
        context = context or {}
        details = ", ".join(f"{k}={v}" for k, v in context.items())
        body = (
            "[template-generated] PahadPulse drafted this response from a "
            "deterministic template because no live LLM is configured.\n"
            f"Request: {summary or '(empty)'}"
        )
        if details:
            body += f"\nContext: {details}"
        return LLMResponse(text=body, model=self._model, template_generated=True)


class RemoteLLMClient(LLMClient):
    """Stub for a real remote LLM provider (same interface)."""

    def __init__(self, provider: LLMProvider, model: str, api_key: str, base_url: str) -> None:
        self._provider = provider
        self._model = model
        self._api_key = api_key
        self._base_url = base_url

    def generate(self, prompt: str, *, context: dict | None = None) -> LLMResponse:
        raise NotImplementedError(
            "Remote LLM adapter is not yet implemented; use the template fallback."
        )


def get_llm_client() -> LLMClient:
    """Select the LLM client based on configuration."""
    settings = get_settings()
    if settings.llm_api_provider is not LLMProvider.FALLBACK and settings.llm_api_key:
        try:
            return RemoteLLMClient(
                provider=settings.llm_api_provider,
                model=settings.llm_api_model,
                api_key=settings.llm_api_key,
                base_url=settings.llm_api_base_url,
            )
        except Exception:  # pragma: no cover - defensive, provider unavailable
            pass
    return TemplateLLMClient(model=settings.llm_api_model)
