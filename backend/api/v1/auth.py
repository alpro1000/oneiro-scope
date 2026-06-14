"""Auth endpoints — Phase 6.A.

Email + password registration / login, JWT-based session, /me.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.core.config import settings
from backend.core.database import get_db
from backend.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    security,
    verify_password,
)
from backend.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------- Schemas -------------------------------------------------------


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: Optional[str] = Field(default=None, max_length=255)
    language: str = Field(default="en", pattern="^(ru|en|de|es|fr)$")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    email: str
    language: str


class UserMe(BaseModel):
    id: str
    email: Optional[str]
    name: Optional[str]
    language: str
    timezone: str
    tier: str = "free"
    is_verified: bool


# ---------- Helpers -------------------------------------------------------


async def _user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_current_user_db(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the JWT subject into a real User ORM row.

    Raises 401 on missing/invalid token; 404 if the user was deleted
    after token issuance.
    """
    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
        )
    try:
        uid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token sub"
        )
    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive"
        )
    return user


# ---------- Routes --------------------------------------------------------


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new email+password user. Returns an access token immediately."""
    existing = await _user_by_email(db, req.email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=req.email,
        password_hash=get_password_hash(req.password),
        name=req.name,
        language=req.language,
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id), "email": user.email})
    return TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=str(user.id),
        email=user.email,
        language=user.language,
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Email + password login. Returns 401 on either bad email or bad password
    (don't leak which one to slow down enumeration)."""
    user = await _user_by_email(db, req.email)
    if user is None or not user.password_hash:
        # Constant-time-ish: still run the verify with a dummy hash to
        # avoid timing-leaking whether the email exists.
        verify_password(req.password, "$2b$12$" + "x" * 53)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive"
        )

    user.last_login_at = datetime.utcnow()
    await db.commit()

    token = create_access_token({"sub": str(user.id), "email": user.email})
    return TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=str(user.id),
        email=user.email,
        language=user.language,
    )


@router.get("/me", response_model=UserMe)
async def me(user: User = Depends(get_current_user_db)):
    """Current authenticated user + computed tier."""
    from backend.services.billing.quotas import current_tier

    return UserMe(
        id=str(user.id),
        email=user.email,
        name=user.name,
        language=user.language,
        timezone=user.timezone,
        tier=current_tier(user).value,
        is_verified=user.is_verified,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(user: User = Depends(get_current_user_db)):
    """Issue a fresh token for the currently-authenticated user.

    There's no separate refresh token: any valid access token can be
    swapped for a new one with extended expiry. Adequate for v1.
    """
    token = create_access_token(
        {"sub": str(user.id), "email": user.email},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=str(user.id),
        email=user.email,
        language=user.language,
    )
