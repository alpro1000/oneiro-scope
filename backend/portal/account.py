"""Portal: the account page (личный кабинет).

Everything a user *does* happens in their chat — this page exists for the
handful of things a chat connector cannot do: see which plan you are on, add
your own LLM key, take your data out, and delete the account. It is
server-rendered HTML over the API that already exists
(`backend/api/v1/auth.py`, `billing.py`, `users.py`), so there is one
implementation of each rule rather than two.

Session handling: the same JWT the API issues, parked in an httpOnly cookie.
`SameSite=Lax` means the browser withholds it on cross-site POSTs, which is
what stands in for CSRF tokens here — every mutating route is a POST.

The database is touched lazily, inside the handlers, not through a
`Depends(get_db)` parameter: a signed-out visitor should get the sign-in page
from a deployment with no database configured, rather than a 500 from
dependency resolution.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from backend.core.config import settings

# Same package: reuse the portal's chrome, locale pick and content dict so the
# account page cannot drift from the rest of the site.
from backend.portal.router import _ctx as page_context, templates

logger = logging.getLogger("oneiro.portal.account")

router = APIRouter(tags=["Portal"], include_in_schema=False)

SESSION_COOKIE = "oneiro_session"

# Wording lives here rather than in router.CONTENT — it is only ever used by
# these three templates, and keeping it adjacent makes the page editable in
# one place.
TEXT: dict[str, dict[str, str]] = {
    "ru": {
        "title": "Кабинет",
        "signin_h": "Вход в кабинет",
        "signin_lede": "Кабинет нужен только для тарифа, своих ключей и "
                       "выгрузки данных. Сами расчёты живут в чате.",
        "email": "Почта",
        "password": "Пароль",
        "signin_btn": "Войти",
        "register_btn": "Создать аккаунт",
        "register_h": "Впервые здесь?",
        "signout": "Выйти",
        "plan": "Тариф",
        "plan_free": "Бесплатный",
        "status": "Статус подписки",
        "until": "Оплачено до",
        "cancels": "Отменяется в конце периода",
        "no_sub": "Активной подписки нет.",
        "pricing_link": "Посмотреть тарифы",
        "connector_h": "Ваш коннектор",
        "connector_b": "Добавьте этот адрес в Claude, ChatGPT или Gemini:",
        "keys_h": "Свои ключи к моделям",
        "keys_b": "Если добавить свой ключ, запросы идут через него и не "
                  "расходуют лимит тарифа.",
        "keys_none": "Своих ключей не добавлено.",
        "keys_added": "добавлен",
        "keys_manage": "Ключи добавляются и отзываются через API "
                       "(/api/v1/users/me/llm-keys).",
        "data_h": "Ваши данные",
        "data_export": "Выгрузить всё, что о вас хранится (JSON)",
        "delete_h": "Удаление аккаунта",
        "delete_b": "Данные стираются сразу и безвозвратно: почта, имя, хеш "
                    "пароля, привязка коннектора, ключ выданной натальной "
                    "карты, подписки и закодированная серия снов. Отменить "
                    "нельзя — сначала выгрузите данные, если они нужны.",
        "delete_confirm": "Я понимаю последствия",
        "delete_btn": "Удалить аккаунт",
        "deleted_h": "Аккаунт удалён",
        "deleted_b": "Данные стёрты",
        "err_credentials": "Неверная почта или пароль.",
        "err_exists": "Такая почта уже зарегистрирована — войдите.",
        "err_weak": "Пароль должен быть не короче 8 символов.",
        "err_unavailable": "Кабинет временно недоступен. Коннектор при этом "
                           "работает — он не зависит от этой страницы.",
        "err_confirm": "Отметьте галочку подтверждения.",
    },
    "en": {
        "title": "Account",
        "signin_h": "Sign in",
        "signin_lede": "The account page is only for your plan, your own API "
                       "keys and data export. The readings themselves live in "
                       "your chat.",
        "email": "Email",
        "password": "Password",
        "signin_btn": "Sign in",
        "register_btn": "Create account",
        "register_h": "First time here?",
        "signout": "Sign out",
        "plan": "Plan",
        "plan_free": "Free",
        "status": "Subscription status",
        "until": "Paid until",
        "cancels": "Cancels at period end",
        "no_sub": "No active subscription.",
        "pricing_link": "See plans",
        "connector_h": "Your connector",
        "connector_b": "Add this URL in Claude, ChatGPT or Gemini:",
        "keys_h": "Your own model keys",
        "keys_b": "With your own key, requests go through it and don't count "
                  "against the plan's quota.",
        "keys_none": "No keys of your own added.",
        "keys_added": "added",
        "keys_manage": "Keys are added and revoked through the API "
                       "(/api/v1/users/me/llm-keys).",
        "data_h": "Your data",
        "data_export": "Export everything held about you (JSON)",
        "delete_h": "Delete account",
        "delete_b": "The data is erased immediately and irreversibly: "
                    "email, name, password hash, connector identity, the "
                    "issued chart grant key, subscriptions and the coded "
                    "dream series. This cannot be undone — export first if "
                    "you want a copy.",
        "delete_confirm": "I understand the consequences",
        "delete_btn": "Delete account",
        "deleted_h": "Account deleted",
        "deleted_b": "Data erased",
        "err_credentials": "Wrong email or password.",
        "err_exists": "That email is already registered — sign in instead.",
        "err_weak": "Password must be at least 8 characters.",
        "err_unavailable": "The account page is temporarily unavailable. The "
                           "connector is unaffected — it does not depend on "
                           "this page.",
        "err_confirm": "Please tick the confirmation box.",
    },
}


@asynccontextmanager
async def _session():
    """One database session, opened only when a handler truly needs one."""
    from backend.core.database import get_db

    agen = get_db()
    session = await agen.__anext__()
    try:
        yield session
    finally:
        await agen.aclose()


def _cookie_kwargs() -> dict[str, Any]:
    return {
        "httponly": True,
        # Lax withholds the cookie on cross-site POSTs, which is the CSRF
        # defence for the forms on this page.
        "samesite": "lax",
        "secure": settings.ENVIRONMENT != "development",
        "path": "/",
    }


def _sign_in(response: Any, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **_cookie_kwargs(),
    )


def _sign_out(response: Any) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")


async def _user_from_cookie(request: Request, db: Any) -> Optional[Any]:
    """Resolve the session cookie to a User, or None.

    Reuses the API's own resolver so the token rules (subject, expiry, active
    flag, eager loading) have exactly one definition.
    """
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None

    from fastapi.security import HTTPAuthorizationCredentials

    from backend.api.v1.auth import get_current_user_db

    try:
        return await get_current_user_db(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=token), db
        )
    except Exception:
        # Expired, revoked, deleted user — all of it means "signed out".
        return None


def _ctx(request: Request, **extra: Any) -> dict[str, Any]:
    ctx = page_context(request)
    ctx["a"] = TEXT[ctx["locale"]]
    ctx.update(extra)
    return ctx


def _signin_page(request: Request, error: str = "", status_code: int = 200):
    return templates.TemplateResponse(
        request, "account_signin.html", _ctx(request, error=error),
        status_code=status_code,
    )


# --- pages -------------------------------------------------------------------

@router.get("/account", response_class=HTMLResponse)
async def account(request: Request):
    """Dashboard when signed in, sign-in form otherwise."""
    if not request.cookies.get(SESSION_COOKIE):
        return _signin_page(request)

    try:
        async with _session() as db:
            user = await _user_from_cookie(request, db)
            if user is None:
                response = _signin_page(request)
                _sign_out(response)  # stale cookie: don't ask twice
                return response
            return await _dashboard(request, user, db)
    except Exception as exc:
        logger.warning("Account page unavailable: %s", exc)
        return _signin_page(
            request, error=TEXT[_ctx(request)["locale"]]["err_unavailable"],
            status_code=503,
        )


async def _dashboard(request: Request, user: Any, db: Any):
    from backend.api.v1.billing import my_subscription

    from backend.portal.router import _mcp_url

    try:
        sub = await my_subscription(user, db)
        subscription = sub.model_dump()
    except Exception as exc:  # billing is not load-bearing for this page
        logger.warning("Subscription lookup failed for the account page: %s", exc)
        subscription = {"tier": "free", "status": None}

    return templates.TemplateResponse(
        request,
        "account.html",
        _ctx(
            request,
            email=user.email,
            name=user.name,
            subscription=subscription,
            keys=[
                {"provider": k.provider, "hint": k.hint}
                for k in (user.llm_keys or [])
            ],
            mcp_url=_mcp_url(request),
        ),
    )


# --- actions -----------------------------------------------------------------

@router.post("/account/signin")
async def signin(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    action: str = Form("signin"),
):
    """Sign in or register, then land on the dashboard.

    Delegates to the API's own handlers rather than re-implementing password
    checks — including the deliberate constant-time behaviour on unknown
    emails.
    """
    locale = _ctx(request)["locale"]
    text = TEXT[locale]

    from fastapi import HTTPException

    from backend.api.v1.auth import (
        LoginRequest,
        RegisterRequest,
        login as api_login,
        register as api_register,
    )

    try:
        async with _session() as db:
            if action == "register":
                if len(password) < 8:
                    return _signin_page(request, error=text["err_weak"], status_code=400)
                token_response = await api_register(
                    RegisterRequest(
                        email=email,
                        password=password,
                        language=locale,
                    ),
                    db,
                )
            else:
                token_response = await api_login(
                    LoginRequest(email=email, password=password), db
                )
    except HTTPException as exc:
        error = {
            409: text["err_exists"],
            401: text["err_credentials"],
            403: text["err_credentials"],
        }.get(exc.status_code, text["err_credentials"])
        return _signin_page(request, error=error, status_code=exc.status_code)
    except Exception as exc:
        logger.warning("Sign-in unavailable: %s", exc)
        return _signin_page(request, error=text["err_unavailable"], status_code=503)

    response = RedirectResponse("/account", status_code=303)
    _sign_in(response, token_response.access_token)
    return response


@router.post("/account/signout")
async def signout():
    response = RedirectResponse("/account", status_code=303)
    _sign_out(response)
    return response


@router.get("/account/export")
async def export_data(request: Request):
    """GDPR export, straight to the browser as a download."""
    from backend.api.v1.users import gdpr_export

    try:
        async with _session() as db:
            user = await _user_from_cookie(request, db)
            if user is None:
                return RedirectResponse("/account", status_code=303)
            payload = await gdpr_export(user, db)
    except Exception as exc:
        logger.warning("Data export failed: %s", exc)
        return RedirectResponse("/account", status_code=303)

    return JSONResponse(
        payload,
        headers={
            "content-disposition": 'attachment; filename="oneiroscope-data.json"'
        },
    )


@router.post("/account/delete")
async def delete_account(request: Request, confirm: str = Form("")):
    """Erase the account, gated on an explicit tick. Irreversible."""
    locale = _ctx(request)["locale"]
    text = TEXT[locale]

    if confirm != "yes":
        return _signin_page(request, error=text["err_confirm"], status_code=400)

    from backend.api.v1.users import delete_account as erase_account

    try:
        async with _session() as db:
            user = await _user_from_cookie(request, db)
            if user is None:
                return RedirectResponse("/account", status_code=303)
            await erase_account(user, db)
    except Exception as exc:
        logger.warning("Account deletion failed: %s", exc)
        return _signin_page(request, error=text["err_unavailable"], status_code=503)

    response = templates.TemplateResponse(
        request,
        "account_deleted.html",
        _ctx(request),
    )
    _sign_out(response)
    return response
