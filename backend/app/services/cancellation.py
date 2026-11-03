from __future__ import annotations

import time
from threading import Lock

import redis.asyncio as redis

from app.core.config import get_settings

# In-memory fallback when Redis is unavailable (local/tests)
_memory_stops: dict[str, float] = {}
_memory_lock = Lock()
_TTL_SECONDS = 60 * 30


class CancellationStore:
    def __init__(self) -> None:
        self._redis: redis.Redis | None = None

    async def connect(self) -> None:
        settings = get_settings()
        try:
            client = redis.from_url(settings.redis_url, decode_responses=True)
            await client.ping()
            self._redis = client
        except Exception:  # noqa: BLE001 — fall back to memory
            self._redis = None

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    def _key(self, run_id: str) -> str:
        return f"nexusai:stop:{run_id}"

    async def request_stop(self, run_id: str) -> None:
        if self._redis is not None:
            await self._redis.setex(self._key(run_id), _TTL_SECONDS, "1")
            return
        with _memory_lock:
            _memory_stops[run_id] = time.time() + _TTL_SECONDS

    async def should_stop(self, run_id: str) -> bool:
        if self._redis is not None:
            val = await self._redis.get(self._key(run_id))
            return val == "1"
        with _memory_lock:
            expires = _memory_stops.get(run_id)
            if expires is None:
                return False
            if expires < time.time():
                _memory_stops.pop(run_id, None)
                return False
            return True

    async def clear(self, run_id: str) -> None:
        if self._redis is not None:
            await self._redis.delete(self._key(run_id))
            return
        with _memory_lock:
            _memory_stops.pop(run_id, None)


cancellation_store = CancellationStore()
