from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models.idempotency import IdempotencyRecord
from app.db.models.message import Message
from app.db.models.thread import Thread
from app.db.models.user import User
from app.db.session import AsyncSessionLocal, get_db
from app.llm.gateway import LLMGateway, get_gateway, timed_ms
from app.llm.metering import record_usage
from app.llm.providers.base import LLMMessage
from app.llm.quotas import QuotaExceededError, assert_quota_available
from app.schemas.chat import ChatStopRequest, ChatStreamRequest
from app.services.cancellation import cancellation_store

router = APIRouter()


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _request_hash(thread_id: uuid.UUID, message: str) -> str:
    raw = f"{thread_id}:{message}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@router.post("/stream")
async def chat_stream(
    body: ChatStreamRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    gateway: LLMGateway = Depends(get_gateway),
) -> StreamingResponse:
    # Ownership check
    thread_result = await db.execute(
        select(Thread).where(Thread.id == body.thread_id, Thread.user_id == user.id)
    )
    thread = thread_result.scalar_one_or_none()
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

    req_hash = _request_hash(body.thread_id, body.message)

    # Idempotency
    existing = await db.execute(
        select(IdempotencyRecord).where(
            IdempotencyRecord.user_id == user.id,
            IdempotencyRecord.idempotency_key == body.idempotency_key,
        )
    )
    idem = existing.scalar_one_or_none()
    if idem is not None:
        if idem.request_hash != req_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency key reused with different payload",
            )
        if idem.status == "completed" and idem.response_payload:

            async def replay() -> AsyncIterator[str]:
                payload = idem.response_payload or {}
                for tok in payload.get("tokens", []):
                    yield _sse("token", {"text": tok})
                yield _sse("done", payload.get("done", {}))

            return StreamingResponse(replay(), media_type="text/event-stream")

    try:
        await assert_quota_available(db, user)
    except QuotaExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc

    if idem is None:
        idem = IdempotencyRecord(
            user_id=user.id,
            idempotency_key=body.idempotency_key,
            request_hash=req_hash,
            status="pending",
        )
        db.add(idem)

    # Persist user message first
    user_msg = Message(
        thread_id=thread.id,
        user_id=user.id,
        role="user",
        content=body.message,
        metadata_={},
    )
    db.add(user_msg)

    # Auto-title from first message
    if thread.title == "New chat":
        thread.title = body.message[:80].strip() or "New chat"
    thread.updated_at = datetime.now(UTC)

    await db.flush()
    await db.commit()

    run_id = str(uuid.uuid4())
    user_id = user.id
    thread_id = thread.id
    user_content = body.message

    async def event_generator() -> AsyncIterator[str]:
        start = perf_counter()
        assistant_parts: list[str] = []
        tokens_for_idem: list[str] = []
        assistant_msg_id: uuid.UUID | None = None

        # Heartbeat immediately so client knows stream is open
        yield f": heartbeat\n\n"
        yield _sse("run", {"run_id": run_id})

        try:
            async with AsyncSessionLocal() as session:
                # Load history
                hist = await session.execute(
                    select(Message)
                    .where(Message.thread_id == thread_id)
                    .order_by(Message.created_at.asc())
                )
                history_msgs = [
                    LLMMessage(role=m.role, content=m.content) for m in hist.scalars().all()
                ]

                stopped = False
                error_code: str | None = None
                error_message: str | None = None
                usage_payload = None

                try:
                    async for chunk in gateway.stream(history_msgs):
                        if await request.is_disconnected():
                            stopped = True
                            break
                        if await cancellation_store.should_stop(run_id):
                            stopped = True
                            break

                        if chunk.error:
                            error_code = "provider_unavailable"
                            error_message = chunk.error
                            break

                        if chunk.text:
                            assistant_parts.append(chunk.text)
                            tokens_for_idem.append(chunk.text)
                            yield _sse("token", {"text": chunk.text})

                        if chunk.done and chunk.usage:
                            usage_payload = chunk.usage

                        # Periodic heartbeat comment
                        if len(assistant_parts) % 20 == 0:
                            yield f": heartbeat\n\n"
                except Exception as exc:  # noqa: BLE001
                    error_code = "provider_unavailable"
                    error_message = str(exc)

                full_text = "".join(assistant_parts)
                usage_meta = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "tier": "free",
                    "provider": gateway.provider_name,
                    "model": gateway.model,
                    "estimated_commercial_cost_usd": 0.0,
                }

                assistant = Message(
                    thread_id=thread_id,
                    user_id=user_id,
                    role="assistant",
                    content=full_text,
                    metadata_={
                        "run_id": run_id,
                        "stopped": stopped,
                        "partial": stopped or bool(error_code),
                    },
                )
                session.add(assistant)
                await session.flush()
                assistant_msg_id = assistant.id

                if usage_payload is not None:
                    event = await record_usage(
                        session,
                        user_id=user_id,
                        usage=usage_payload,
                        thread_id=thread_id,
                        message_id=assistant.id,
                        latency_ms=timed_ms(start),
                        status="partial" if stopped else ("error" if error_code else "ok"),
                    )
                    usage_meta = {
                        "input_tokens": usage_payload.input_tokens,
                        "output_tokens": usage_payload.output_tokens,
                        "tier": usage_payload.tier,
                        "provider": usage_payload.provider,
                        "model": usage_payload.model,
                        "estimated_commercial_cost_usd": float(
                            event.estimated_commercial_cost_usd or 0
                        ),
                    }

                assistant.metadata_ = {
                    **(assistant.metadata_ or {}),
                    "usage": usage_meta,
                }
                done_data = {
                    "message_id": str(assistant.id),
                    "run_id": run_id,
                    "usage": usage_meta,
                }

                # Update idempotency record
                idem_row = await session.execute(
                    select(IdempotencyRecord).where(
                        IdempotencyRecord.user_id == user_id,
                        IdempotencyRecord.idempotency_key == body.idempotency_key,
                    )
                )
                idem_rec = idem_row.scalar_one_or_none()
                if idem_rec is not None and not error_code:
                    idem_rec.status = "completed"
                    idem_rec.completed_at = datetime.now(UTC)
                    idem_rec.response_payload = {
                        "tokens": tokens_for_idem,
                        "done": done_data,
                    }

                thr = await session.get(Thread, thread_id)
                if thr is not None:
                    thr.updated_at = datetime.now(UTC)

                await session.commit()

                if error_code:
                    yield _sse(
                        "error",
                        {"code": error_code, "message": error_message or "Provider error"},
                    )
                else:
                    yield _sse("done", done_data)

        except QuotaExceededError as exc:
            yield _sse("error", {"code": exc.code, "message": str(exc)})
        except Exception as exc:  # noqa: BLE001
            yield _sse("error", {"code": "internal_error", "message": str(exc)})
        finally:
            await cancellation_store.clear(run_id)
            _ = user_content
            _ = assistant_msg_id

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/stop", status_code=status.HTTP_204_NO_CONTENT)
async def chat_stop(
    body: ChatStopRequest,
    user: User = Depends(get_current_user),
) -> None:
    _ = user  # authenticated stop only
    await cancellation_store.request_stop(body.run_id)
