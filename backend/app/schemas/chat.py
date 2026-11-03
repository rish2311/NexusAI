from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class ChatStreamRequest(BaseModel):
    thread_id: UUID
    message: str = Field(min_length=1, max_length=32_000)
    idempotency_key: str = Field(min_length=8, max_length=128)


class ChatStopRequest(BaseModel):
    run_id: str = Field(min_length=8, max_length=128)
