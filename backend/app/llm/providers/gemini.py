from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator

import google.generativeai as genai

from app.core.config import get_settings
from app.llm.providers.base import LLMMessage, LLMProvider, LLMResult, LLMUsage, StreamChunk


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        settings = get_settings()
        self.model = model or settings.gemini_model
        key = api_key if api_key is not None else settings.gemini_api_key
        if not key:
            raise ValueError("GEMINI_API_KEY is required when using the Gemini provider")
        genai.configure(api_key=key)
        self._model = genai.GenerativeModel(self.model)

    def _to_gemini_history(self, messages: list[LLMMessage]) -> list[dict]:
        history: list[dict] = []
        for msg in messages:
            if msg.role == "system":
                history.append({"role": "user", "parts": [f"[System]\n{msg.content}"]})
                history.append({"role": "model", "parts": ["Understood."]})
                continue
            role = "user" if msg.role == "user" else "model"
            history.append({"role": role, "parts": [msg.content]})
        return history

    def _usage_from_response(self, response: object, fallback_in: int, fallback_out: int) -> LLMUsage:
        input_tokens = fallback_in
        output_tokens = fallback_out
        meta = getattr(response, "usage_metadata", None)
        if meta is not None:
            input_tokens = int(getattr(meta, "prompt_token_count", None) or input_tokens)
            output_tokens = int(getattr(meta, "candidates_token_count", None) or output_tokens)
        return LLMUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            provider=self.name,
            model=self.model,
            tier="free",
        )

    async def generate(self, messages: list[LLMMessage]) -> LLMResult:
        history = self._to_gemini_history(messages[:-1] if messages else [])
        last = messages[-1].content if messages else ""
        chat = self._model.start_chat(history=history)
        response = await chat.send_message_async(last)
        text = getattr(response, "text", "") or ""
        fallback_in = sum(max(1, len(m.content) // 4) for m in messages)
        fallback_out = max(1, len(text) // 4)
        return LLMResult(text=text, usage=self._usage_from_response(response, fallback_in, fallback_out))

    def _sync_stream(self, messages: list[LLMMessage]) -> Iterator[StreamChunk]:
        history = self._to_gemini_history(messages[:-1] if messages else [])
        last = messages[-1].content if messages else ""
        chat = self._model.start_chat(history=history)
        response = chat.send_message(last, stream=True)
        collected = ""
        final_chunk = None
        for chunk in response:
            final_chunk = chunk
            part = ""
            try:
                part = chunk.text or ""
            except Exception:  # noqa: BLE001 — some chunks have no text parts
                part = ""
            if part:
                collected += part
                yield StreamChunk(text=part)
        fallback_in = sum(max(1, len(m.content) // 4) for m in messages)
        fallback_out = max(1, len(collected) // 4)
        usage = self._usage_from_response(
            final_chunk if final_chunk is not None else object(),
            fallback_in,
            fallback_out,
        )
        yield StreamChunk(text="", done=True, usage=usage)

    async def stream(self, messages: list[LLMMessage]) -> AsyncIterator[StreamChunk]:
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[StreamChunk | None] = asyncio.Queue()

        def worker() -> None:
            try:
                for chunk in self._sync_stream(messages):
                    asyncio.run_coroutine_threadsafe(queue.put(chunk), loop).result()
            except Exception as exc:  # noqa: BLE001
                asyncio.run_coroutine_threadsafe(
                    queue.put(StreamChunk(error=str(exc), done=True)),
                    loop,
                ).result()
            finally:
                asyncio.run_coroutine_threadsafe(queue.put(None), loop).result()

        await asyncio.to_thread(lambda: None)  # ensure loop is ready
        task = loop.run_in_executor(None, worker)
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield item
        finally:
            await task
