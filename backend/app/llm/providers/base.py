from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field


@dataclass
class LLMMessage:
    role: str  # user | assistant | system
    content: str


@dataclass
class LLMUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    provider: str = ""
    model: str = ""
    tier: str = "free"


@dataclass
class StreamChunk:
    text: str = ""
    done: bool = False
    usage: LLMUsage | None = None
    error: str | None = None


@dataclass
class LLMResult:
    text: str
    usage: LLMUsage
    metadata: dict = field(default_factory=dict)


class LLMProvider(ABC):
    name: str
    model: str

    @abstractmethod
    async def generate(self, messages: list[LLMMessage]) -> LLMResult:
        raise NotImplementedError

    @abstractmethod
    async def stream(self, messages: list[LLMMessage]) -> AsyncIterator[StreamChunk]:
        raise NotImplementedError
        yield  # pragma: no cover — makes this an async generator for type checkers
