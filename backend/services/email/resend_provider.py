"""Resend transactional email provider.

Quiet no-op when `RESEND_API_KEY` is missing — dev environments do not
need email to run, and the call path remains the same for production.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

RESEND_URL = "https://api.resend.com/emails"

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

_SUPPORTED_LOCALES = ("en", "ru", "de", "es", "fr")


def _from_email() -> str:
    return os.getenv("RESEND_FROM_EMAIL", "OneiroScope <noreply@oneiroscope.app>")


def render(template_name: str, locale: str, **vars: str) -> tuple[str, str]:
    """Load a template and substitute {variables}. Returns (subject, html).

    Falls back to English when the requested locale isn't translated yet.
    Templates live under `templates/<locale>/<template_name>.{subject,html}`.
    """
    locale = locale if locale in _SUPPORTED_LOCALES else "en"
    base = _TEMPLATES_DIR / locale / template_name
    fallback = _TEMPLATES_DIR / "en" / template_name

    subject_path = base.with_suffix(".subject")
    html_path = base.with_suffix(".html")
    if not subject_path.exists():
        subject_path = fallback.with_suffix(".subject")
    if not html_path.exists():
        html_path = fallback.with_suffix(".html")

    subject = subject_path.read_text(encoding="utf-8").strip()
    html = html_path.read_text(encoding="utf-8")
    for k, v in vars.items():
        subject = subject.replace(f"{{{k}}}", str(v))
        html = html.replace(f"{{{k}}}", str(v))
    return subject, html


async def send_email(
    *,
    to: str,
    template_name: str,
    locale: str = "en",
    vars: Optional[dict] = None,
) -> bool:
    """Send a transactional email via Resend. Returns True on success.

    No-op (returns False, logs) when `RESEND_API_KEY` is unset — dev and
    test environments stay green.
    """
    api_key = os.getenv("RESEND_API_KEY", "")
    if not api_key:
        logger.info("RESEND_API_KEY unset — skipping email '%s' to %s", template_name, to)
        return False

    subject, html = render(template_name, locale, **(vars or {}))

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            RESEND_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": _from_email(),
                "to": [to],
                "subject": subject,
                "html": html,
            },
        )
        if resp.status_code >= 400:
            logger.error(
                "Resend send failed: %s %s", resp.status_code, resp.text[:300]
            )
            return False
    return True
