from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, status

from app.core.config import get_settings

_buckets: dict[str, deque[float]] = defaultdict(deque)
_lock = Lock()


def check_login_rate_limit(key: str) -> None:
    """Simple in-memory sliding-window rate limit for login attempts."""
    settings = get_settings()
    limit = settings.login_rate_limit_per_minute
    now = time.time()
    window = 60.0
    with _lock:
        q = _buckets[key]
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Try again shortly.",
            )
        q.append(now)
