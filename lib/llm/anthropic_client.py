"""LLMClient backed by the Anthropic SDK."""
from __future__ import annotations

from anthropic import Anthropic


class AnthropicClient:
    def __init__(
        self, *, api_key: str, model: str,
        default_max_tokens: int = 4096, default_temperature: float = 0.2,
    ):
        if not api_key:
            raise ValueError("AnthropicClient requires an API key")
        self._client = Anthropic(api_key=api_key)
        self.model = model
        self.default_max_tokens = default_max_tokens
        self.default_temperature = default_temperature

    def complete(
        self, *, system: str, user: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        msg = self._client.messages.create(
            model=self.model,
            system=system,
            max_tokens=max_tokens if max_tokens is not None else self.default_max_tokens,
            temperature=temperature if temperature is not None else self.default_temperature,
            messages=[{"role": "user", "content": user}],
        )
        # join all text blocks
        return "".join(getattr(b, "text", "") for b in msg.content)
