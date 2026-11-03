from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1 import api_router
from app.core.config import get_settings
from app.db.session import engine
from app.services.cancellation import cancellation_store


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await cancellation_store.connect()
    yield
    await cancellation_store.close()
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="NexusAI API",
        version="1.0.0",
        description="Sprint 1 — authenticated streaming chatbot (Gemini free tier)",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz() -> dict[str, str]:
        # DB check
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        # Redis check (optional soft — memory fallback is OK)
        await cancellation_store.connect()
        return {"status": "ready"}

    return app


app = create_app()
