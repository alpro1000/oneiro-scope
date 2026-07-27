"""User-scoped endpoints — Phase 6.E + 6.I.

- POST   /users/me/llm-keys              — save BYOK key (encrypted).
- GET    /users/me/llm-keys              — list saved providers + hints.
- DELETE /users/me/llm-keys/{provider}   — revoke a key.
- GET    /users/me/data-export           — GDPR data export (JSON).
- DELETE /users/me                       — request account deletion (soft).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from backend.api.v1.auth import get_current_user_db
from backend.core.database import get_db
from backend.models.user import User
from backend.models.user_llm_key import UserLLMKey
from backend.services.byok import encrypt, hint as make_hint

router = APIRouter(prefix="/users", tags=["users"])

_VALID_PROVIDERS = {"groq", "gemini", "vertex", "together", "openai", "anthropic", "bedrock"}


# ---------- Schemas -------------------------------------------------------


class SaveKeyRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=20)
    api_key: str = Field(min_length=8, max_length=512)


class KeyEntry(BaseModel):
    provider: str
    hint: Optional[str]
    created_at: datetime
    last_used_at: Optional[datetime]


class KeyListResponse(BaseModel):
    keys: list[KeyEntry]


class GdprUser(BaseModel):
    id: str
    email: Optional[str]
    name: Optional[str]
    language: Optional[str]
    timezone: Optional[str]
    created_at: Optional[str]
    is_verified: bool


class GdprSubscription(BaseModel):
    id: str
    tier: Optional[str]
    status: Optional[str]
    provider: Optional[str]
    current_period_end: Optional[str]


class GdprDreamSeriesEntry(BaseModel):
    id: str
    dream_date: str
    locale: str
    coder_version: str
    hvdc: dict
    symbols: Optional[list] = None
    primary_emotion: Optional[str] = None
    created_at: Optional[str] = None


class GdprExportResponse(BaseModel):
    """GDPR Article 20 payload — the full account data contract."""

    user: GdprUser
    subscriptions: list[GdprSubscription]
    byok_providers: list[str]
    dream_count: int
    dream_series: list[GdprDreamSeriesEntry]


# ---------- Routes --------------------------------------------------------


@router.post(
    "/me/llm-keys",
    response_model=KeyEntry,
    status_code=status.HTTP_201_CREATED,
)
async def save_llm_key(
    req: SaveKeyRequest,
    user: User = Depends(get_current_user_db),
    db: AsyncSession = Depends(get_db),
):
    """Save (encrypted) a BYOK LLM key for the given provider."""
    provider = req.provider.lower().strip()
    if provider not in _VALID_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown provider. Allowed: {sorted(_VALID_PROVIDERS)}",
        )

    # Upsert: revoke any existing key for this provider first.
    existing = await db.execute(
        select(UserLLMKey).where(
            UserLLMKey.user_id == user.id, UserLLMKey.provider == provider
        )
    )
    old = existing.scalar_one_or_none()
    if old is not None:
        await db.delete(old)
        await db.flush()

    entry = UserLLMKey(
        user_id=user.id,
        provider=provider,
        encrypted_key=encrypt(req.api_key),
        hint=make_hint(req.api_key),
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    return KeyEntry(
        provider=entry.provider,
        hint=entry.hint,
        created_at=entry.created_at,
        last_used_at=entry.last_used_at,
    )


@router.get("/me/llm-keys", response_model=KeyListResponse)
async def list_llm_keys(
    user: User = Depends(get_current_user_db),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserLLMKey).where(UserLLMKey.user_id == user.id)
    )
    rows = result.scalars().all()
    return KeyListResponse(
        keys=[
            KeyEntry(
                provider=r.provider,
                hint=r.hint,
                created_at=r.created_at,
                last_used_at=r.last_used_at,
            )
            for r in rows
        ]
    )


@router.delete(
    "/me/llm-keys/{provider}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_llm_key(
    provider: str,
    user: User = Depends(get_current_user_db),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserLLMKey).where(
            UserLLMKey.user_id == user.id, UserLLMKey.provider == provider.lower()
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Key not found"
        )
    await db.delete(row)
    await db.commit()


@router.get("/me/data-export", response_model=GdprExportResponse)
async def gdpr_export(
    user: User = Depends(get_current_user_db),
    db: AsyncSession = Depends(get_db),
):
    """GDPR Article 20 — return all user data as JSON."""
    # `user.subscriptions` and `user.llm_keys` are eager-loaded by
    # `get_current_user_db`; dreams aren't (they can be huge), so fetch
    # just the count separately.
    from sqlalchemy import func as sa_func

    from backend.models.dream import Dream
    from backend.services.dreams.series import export_entries

    dream_count_q = await db.execute(
        select(sa_func.count(Dream.id)).where(Dream.user_id == user.id)
    )
    dream_count = dream_count_q.scalar() or 0

    # Coded dream series (HVdC features, no texts) — small rows, export whole.
    dream_series = await export_entries(db, user.id)

    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "language": user.language,
            "timezone": user.timezone,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "is_verified": user.is_verified,
        },
        "subscriptions": [
            {
                "id": str(s.id),
                "tier": s.tier,
                "status": s.status,
                "provider": s.provider,
                "current_period_end": s.current_period_end.isoformat()
                if s.current_period_end
                else None,
            }
            for s in (user.subscriptions or [])
        ],
        "byok_providers": [k.provider for k in (user.llm_keys or [])],
        "dream_count": dream_count,
        "dream_series": dream_series,
    }


@router.delete("/me", status_code=status.HTTP_200_OK)
async def request_account_deletion(
    user: User = Depends(get_current_user_db),
    db: AsyncSession = Depends(get_db),
):
    """GDPR Article 17 — request soft-delete. Cron job hard-purges in 30 days."""
    user.pending_deletion_at = datetime.now(timezone.utc) + timedelta(days=30)
    user.is_active = False
    await db.commit()
    return {
        "status": "pending_deletion",
        "purge_at": user.pending_deletion_at.isoformat(),
        "cancel_until": user.pending_deletion_at.isoformat(),
    }
