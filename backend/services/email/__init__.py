"""Transactional email (Phase 6.H).

Resend is the chosen provider (see docs/PLAN.md decisions). Stays a
no-op when `RESEND_API_KEY` isn't set so dev environments don't crash.
"""

from backend.services.email.resend_provider import send_email

__all__ = ["send_email"]
