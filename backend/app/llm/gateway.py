from __future__ import annotations

import asyncio
import random
from collections.abc import AsyncIterator
from time import perf_counter

from app.core.config import get_settings
from app.llm.providers.base import LLMMessage, LLMProvider, LLMResult, StreamChunk
from app.llm.providers.gemini import GeminiProvider
from app.llm.providers.mock import MockProvider


class ProviderUnavailableError(Exception):
    def __init__(self, message: str = "LLM provider unavailable") -> None:
        self.code = "provider_unavailable"
        super().__init__(message)


class LLMGateway:
    """Provider-independent gateway with retries, timeouts, and metering hooks."""

    def __init__(self, provider: LLMProvider | None = None) -> None:
        settings = get_settings()
        self._provider = provider or self._build_provider(settings.llm_provider)
        self._timeout = settings.llm_timeout_seconds
        self._max_retries = settings.llm_max_retries

    @staticmethod
    def _build_provider(name: str) -> LLMProvider:
        if name == "mock":
            return MockProvider()
        if name == "gemini":
            return GeminiProvider()
        raise ValueError(f"Unknown LLM provider: {name}")

    @property
    def provider_name(self) -> str:
        return self._provider.name

    @property
    def model(self) -> str:
        return self._provider.model

    async def generate(self, messages: list[LLMMessage]) -> LLMResult:
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                return await asyncio.wait_for(
                    self._provider.generate(messages),
                    timeout=self._timeout,
                )
            except Exception as exc:  # noqa: BLE001 — normalize provider errors
                last_error = exc
                if attempt >= self._max_retries:
                    break
                delay = (2**attempt) * 0.25 + random.uniform(0, 0.25)
                await asyncio.sleep(delay)
        raise ProviderUnavailableError(str(last_error) if last_error else "Unknown provider error")

    async def stream(self, messages: list[LLMMessage]) -> AsyncIterator[StreamChunk]:
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                async with asyncio.timeout(self._timeout):
                    async for chunk in self._provider.stream(messages):
                        yield chunk
                return
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt >= self._max_retries:
                    break
                delay = (2**attempt) * 0.25 + random.uniform(0, 0.25)
                await asyncio.sleep(delay)
        yield StreamChunk(
            error=str(last_error) if last_error else "Unknown provider error",
            done=True,
        )

    def get_usage_meta(self) -> dict[str, str]:
        return {
            "provider": self._provider.name,
            "model": self._provider.model,
            "tier": "free",
        }


def timed_ms(start: float) -> int:
    return int((perf_counter() - start) * 1000)


def get_gateway() -> LLMGateway:
    return LLMGateway()
