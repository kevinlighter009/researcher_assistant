"""The single LLM interface used by every higher-level module."""
from __future__ import annotations

from typing import Protocol


class LLMClient(Protocol):
    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> str: ...
