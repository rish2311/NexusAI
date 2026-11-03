from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.usage_event import UsageEvent
from app.llm.pricing_estimates import estimate_commercial_cost_usd
from app.llm.providers.base import LLMUsage


async def record_usage(
    db: AsyncSession,
    *,
    user_id: UUID,
    usage: LLMUsage,
    thread_id: UUID | None = None,
    message_id: UUID | None = None,
    latency_ms: int | None = None,
    status: str = "ok",
) -> UsageEvent:
    estimate = estimate_commercial_cost_usd(
        model=usage.model,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
    )
    event = UsageEvent(
        user_id=user_id,
        thread_id=thread_id,
        message_id=message_id,
        provider=usage.provider,
        model=usage.model,
        tier=usage.tier or "free",
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        estimated_commercial_cost_usd=Decimal(estimate),
        latency_ms=latency_ms,
        status=status,
    )
    db.add(event)
    await db.flush()
    return event
