from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.models.user import User
from app.llm.gateway import LLMGateway
from app.llm.providers.base import LLMMessage
from app.llm.providers.mock import MockProvider
from app.llm.quotas import QuotaExceededError, assert_quota_available
from app.llm.metering import record_usage
from app.llm.providers.base import LLMUsage


@pytest.mark.asyncio
async def test_mock_generate_and_stream() -> None:
    gateway = LLMGateway(provider=MockProvider(reply="Hello from mock"))
    result = await gateway.generate([LLMMessage(role="user", content="Hi")])
    assert "mock" in result.text.lower() or result.text == "Hello from mock"
    assert result.usage.provider == "mock"
    assert result.usage.tier == "free"

    parts: list[str] = []
    usage = None
    async for chunk in gateway.stream([LLMMessage(role="user", content="Hi")]):
        if chunk.text:
            parts.append(chunk.text)
        if chunk.done:
            usage = chunk.usage
    assert "".join(parts) == "Hello from mock"
    assert usage is not None
    assert usage.output_tokens > 0


@pytest.mark.asyncio
async def test_quota_exceeded(db_session: AsyncSession) -> None:
    user = User(
        email="quota@example.com",
        password_hash=hash_password("securepass1"),
        daily_request_quota=1,
        daily_token_quota=10_000,
    )
    db_session.add(user)
    await db_session.flush()

    usage = LLMUsage(
        input_tokens=10,
        output_tokens=10,
        provider="mock",
        model="mock-1",
        tier="free",
    )
    await record_usage(db_session, user_id=user.id, usage=usage)
    await db_session.commit()

    with pytest.raises(QuotaExceededError):
        await assert_quota_available(db_session, user)
