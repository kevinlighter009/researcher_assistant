"""Test double for LLMClient. Scripted responses or a callable."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, Union


@dataclass
class _RecordedCall:
    system: str
    user: str
    max_tokens: int
    temperature: float


class FakeLLMClient:
    def __init__(
        self,
        responses: Union[Iterable[str], Callable[..., str]],
    ):
        if callable(responses):
            self._fn = responses
            self._queue = None
        else:
            self._fn = None
            self._queue = list(responses)
        self.calls: list[_RecordedCall] = []

    def complete(
        self, *, system: str, user: str,
        max_tokens: int = 4096, temperature: float = 0.2,
    ) -> str:
        self.calls.append(_RecordedCall(system, user, max_tokens, temperature))
        if self._fn is not None:
            return self._fn(system=system, user=user,
                            max_tokens=max_tokens, temperature=temperature)
        if not self._queue:
            raise IndexError("FakeLLMClient ran out of scripted responses")
        return self._queue.pop(0)
