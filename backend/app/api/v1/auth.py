from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    refresh_token_expiry,
    validate_password_strength,
    verify_password,
)
from app.db.models.refresh_token import RefreshToken
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.rate_limit import check_login_rate_limit

router = APIRouter()


def _token_response(user: User, refresh_raw: str) -> TokenResponse:
    settings = get_settings()
    access = create_access_token(user_id=user.id, email=user.email)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh_raw,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


async def _issue_refresh_token(
    db: AsyncSession, user: User, family_id: uuid.UUID | None = None
) -> str:
    raw = generate_refresh_token()
    record = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(raw),
        family_id=family_id or uuid.uuid4(),
        expires_at=refresh_token_expiry(),
    )
    db.add(record)
    await db.flush()
    return raw


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    try:
        validate_password_strength(body.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    existing = await db.execute(select(User).where(User.email == body.email.lower()))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    settings = get_settings()
    user = User(
        email=body.email.lower(),
        password_hash=hash_password(body.password),
        daily_request_quota=settings.default_daily_request_quota,
        daily_token_quota=settings.default_daily_token_quota,
    )
    db.add(user)
    await db.flush()
    refresh_raw = await _issue_refresh_token(db, user)
    return _token_response(user, refresh_raw)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    client = request.client.host if request.client else "unknown"
    check_login_rate_limit(f"login:{client}:{body.email.lower()}")

    result = await db.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    refresh_raw = await _issue_refresh_token(db, user)
    return _token_response(user, refresh_raw)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    token_hash = hash_token(body.refresh_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    record = result.scalar_one_or_none()
    now = datetime.now(UTC)

    if record is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    if record.revoked_at is not None:
        # Reuse detected — revoke entire family
        family = await db.execute(
            select(RefreshToken).where(RefreshToken.family_id == record.family_id)
        )
        for sibling in family.scalars().all():
            if sibling.revoked_at is None:
                sibling.revoked_at = now
        await db.flush()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token reuse detected"
        )
    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at < now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

    user_result = await db.execute(select(User).where(User.id == record.user_id))
    user = user_result.scalar_one()

    new_raw = await _issue_refresh_token(db, user, family_id=record.family_id)
    new_hash = hash_token(new_raw)
    new_result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == new_hash))
    new_record = new_result.scalar_one()

    record.revoked_at = now
    record.replaced_by = new_record.id
    await db.flush()
    return _token_response(user, new_raw)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: LogoutRequest, db: AsyncSession = Depends(get_db)) -> None:
    token_hash = hash_token(body.refresh_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    record = result.scalar_one_or_none()
    if record is not None and record.revoked_at is None:
        record.revoked_at = datetime.now(UTC)
        await db.flush()


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)) -> User:
    return user
