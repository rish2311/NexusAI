from __future__ import annotations

from collections.abc import AsyncIterator

from app.llm.providers.base import LLMMessage, LLMProvider, LLMResult, LLMUsage, StreamChunk


class MockProvider(LLMProvider):
    """Deterministic provider for tests — never calls an external API."""

    name = "mock"
    model = "mock-1"

    def __init__(self, reply: str | None = None) -> None:
        self._reply = reply or (
            "This is a mocked assistant reply for NexusAI Sprint 1 tests."
        )

    def _usage(self, messages: list[LLMMessage], text: str) -> LLMUsage:
        input_tokens = sum(max(1, len(m.content) // 4) for m in messages)
        output_tokens = max(1, len(text) // 4)
        return LLMUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            provider=self.name,
            model=self.model,
            tier="free",
        )

    async def generate(self, messages: list[LLMMessage]) -> LLMResult:
        text = self._reply
        return LLMResult(text=text, usage=self._usage(messages, text))

    async def stream(self, messages: list[LLMMessage]) -> AsyncIterator[StreamChunk]:
        text = self._reply
        # Emit word-by-word to simulate SSE tokens
        words = text.split(" ")
        for i, word in enumerate(words):
            chunk = word if i == 0 else f" {word}"
            yield StreamChunk(text=chunk)
        yield StreamChunk(text="", done=True, usage=self._usage(messages, text))
