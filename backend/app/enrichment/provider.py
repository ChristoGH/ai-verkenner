"""LLM provider abstraction (M4) — cloud by default, injectable for tests.

The pipeline depends only on the `LLMProvider` protocol (one method: `complete`). The real
implementation is the Anthropic cloud SDK, imported **lazily** so the app and tests load without
`anthropic` installed or an API key set. Tests inject a deterministic fake; a missing key or
provider degrades to `None`, and the enricher falls back to the rule-based path.
"""

from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

from app.core.config import settings

logger = logging.getLogger(__name__)


@runtime_checkable
class LLMProvider(Protocol):
    """Minimal completion interface: a system prompt + a user message in, raw text out."""

    name: str

    def complete(self, *, system: str, user: str) -> str:
        ...


class AnthropicProvider:
    """Cloud provider backed by the Anthropic Messages API (Claude).

    Uses `claude-opus-4-8` with adaptive thinking by default (see app/core/config.py). The SDK is
    imported lazily so importing this module never requires `anthropic`.
    """

    def __init__(self, model: str, api_key: str, max_tokens: int) -> None:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - only without the extra installed
            raise RuntimeError(
                'AnthropicProvider requires the "llm" extra: pip install -e ".[llm]"'
            ) from exc

        self._client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.name = f"anthropic:{model}"

    def complete(self, *, system: str, user: str) -> str:
        resp = self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in resp.content if block.type == "text")


def get_provider() -> LLMProvider | None:
    """Build the configured provider, or `None` to enrich via the rule-based fallback.

    `LLM_PROVIDER=none` (or `fake` — tests inject their own) and a missing API key both yield
    `None`; the enricher then degrades to deterministic minimal enrichment rather than failing.
    """
    provider = settings.llm_provider.strip().lower()
    if provider in ("", "none", "fake"):
        return None
    if provider == "anthropic":
        if not settings.llm_api_key:
            logger.warning(
                "LLM_PROVIDER=anthropic but no API key set; enrichment will use the "
                "rule-based fallback"
            )
            return None
        return AnthropicProvider(settings.llm_model, settings.llm_api_key, settings.llm_max_tokens)
    logger.warning("unknown LLM_PROVIDER '%s'; enrichment will use the fallback", provider)
    return None
