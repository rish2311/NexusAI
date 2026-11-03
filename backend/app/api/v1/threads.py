from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models.message import Message
from app.db.models.thread import Thread
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.threads import (
    MessageListResponse,
    MessageResponse,
    ThreadCreate,
    ThreadResponse,
    ThreadUpdate,
)

router = APIRouter()


async def _get_owned_thread(db: AsyncSession, thread_id: UUID, user: User) -> Thread:
    result = await db.execute(
        select(Thread).where(Thread.id == thread_id, Thread.user_id == user.id)
    )
    thread = result.scalar_one_or_none()
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    return thread


@router.get("", response_model=list[ThreadResponse])
async def list_threads(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Thread]:
    result = await db.execute(
        select(Thread).where(Thread.user_id == user.id).order_by(Thread.updated_at.desc())
    )
    return list(result.scalars().all())


@router.post("", response_model=ThreadResponse, status_code=status.HTTP_201_CREATED)
async def create_thread(
    body: ThreadCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Thread:
    thread = Thread(user_id=user.id, title=body.title)
    db.add(thread)
    await db.flush()
    return thread


@router.get("/{thread_id}", response_model=ThreadResponse)
async def get_thread(
    thread_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Thread:
    return await _get_owned_thread(db, thread_id, user)


@router.patch("/{thread_id}", response_model=ThreadResponse)
async def rename_thread(
    thread_id: UUID,
    body: ThreadUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Thread:
    thread = await _get_owned_thread(db, thread_id, user)
    thread.title = body.title
    thread.updated_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(thread)
    return thread


@router.delete("/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_thread(
    thread_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    thread = await _get_owned_thread(db, thread_id, user)
    await db.delete(thread)
    await db.flush()


@router.get("/{thread_id}/messages", response_model=MessageListResponse)
async def list_messages(
    thread_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageListResponse:
    await _get_owned_thread(db, thread_id, user)

    stmt = (
        select(Message)
        .where(Message.thread_id == thread_id, Message.user_id == user.id)
        .order_by(Message.created_at.asc())
        .limit(limit + 1)
    )
    if cursor:
        try:
            cursor_dt = datetime.fromisoformat(cursor)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid cursor") from exc
        stmt = stmt.where(Message.created_at > cursor_dt)

    result = await db.execute(stmt)
    rows = list(result.scalars().all())
    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        next_cursor = rows[-1].created_at.isoformat()

    items = [
        MessageResponse(
            id=m.id,
            thread_id=m.thread_id,
            role=m.role,
            content=m.content,
            metadata=m.metadata_ or {},
            created_at=m.created_at,
        )
        for m in rows
    ]
    return MessageListResponse(items=items, next_cursor=next_cursor)
