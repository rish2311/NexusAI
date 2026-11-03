from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.usage_event import UsageEvent
from app.db.models.user import User


class QuotaExceededError(Exception):
    def __init__(self, message: str = "Daily quota exceeded") -> None:
        self.code = "quota_exceeded"
        super().__init__(message)


@dataclass
class QuotaStatus:
    requests_used: int
    tokens_used: int
    request_limit: int
    token_limit: int

    @property
    def requests_remaining(self) -> int:
        return max(0, self.request_limit - self.requests_used)

    @property
    def tokens_remaining(self) -> int:
        return max(0, self.token_limit - self.tokens_used)


def _start_of_utc_day() -> datetime:
    now = datetime.now(UTC)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


async def get_quota_status(db: AsyncSession, user: User) -> QuotaStatus:
    start = _start_of_utc_day()
    result = await db.execute(
        select(
            func.count(UsageEvent.id),
            func.coalesce(func.sum(UsageEvent.input_tokens + UsageEvent.output_tokens), 0),
        ).where(
            UsageEvent.user_id == user.id,
            UsageEvent.created_at >= start,
            UsageEvent.status.in_(["ok", "partial"]),
        )
    )
    row = result.one()
    return QuotaStatus(
        requests_used=int(row[0] or 0),
        tokens_used=int(row[1] or 0),
        request_limit=user.daily_request_quota,
        token_limit=user.daily_token_quota,
    )


async def assert_quota_available(db: AsyncSession, user: User, estimated_tokens: int = 0) -> QuotaStatus:
    status = await get_quota_status(db, user)
    if status.requests_used >= status.request_limit:
        raise QuotaExceededError(
            f"Daily request quota exceeded ({status.request_limit} requests/day)"
        )
    if status.tokens_used + estimated_tokens > status.token_limit:
        raise QuotaExceededError(
            f"Daily token quota exceeded ({status.token_limit} tokens/day)"
        )
    return status


async def get_user_quota_status(db: AsyncSession, user_id: UUID) -> QuotaStatus | None:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        return None
    return await get_quota_status(db, user)
