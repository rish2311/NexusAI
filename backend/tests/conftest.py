from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Force mock LLM + test JWT before app imports settings
os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-nexusai-sprint1")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.db.base import Base
from app.db.session import get_db
from app.llm.gateway import LLMGateway
from app.llm.providers.mock import MockProvider
from app.main import create_app

# Shared in-memory SQLite so all sessions see the same schema/data
TEST_DATABASE_URL = "sqlite+aiosqlite:///file:nexusai_test?mode=memory&cache=shared&uri=true"


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(
        TEST_DATABASE_URL,
        future=True,
        connect_args={"uri": True, "check_same_thread": False},
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(engine) -> AsyncGenerator[AsyncClient, None]:
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    app = create_app()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    def override_gateway() -> LLMGateway:
        return LLMGateway(provider=MockProvider())

    app.dependency_overrides[get_db] = override_get_db
    from app.llm.gateway import get_gateway

    app.dependency_overrides[get_gateway] = override_gateway

    # Point streaming code at the same in-memory DB
    import app.api.v1.chat as chat_module
    import app.db.session as session_module

    session_module.AsyncSessionLocal = session_factory
    chat_module.AsyncSessionLocal = session_factory

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
