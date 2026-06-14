"""Email template rendering tests (Phase 6.H)."""

from __future__ import annotations

import pytest

from backend.services.email.resend_provider import _SUPPORTED_LOCALES, render


@pytest.mark.parametrize("locale", _SUPPORTED_LOCALES)
def test_welcome_template_renders_in_each_locale(locale):
    subject, html = render("welcome", locale, name="Alice")
    assert "Alice" in subject
    assert "Alice" in html
    assert html.lstrip().startswith("<!DOCTYPE html>")


def test_unknown_locale_falls_back_to_en():
    subject, html = render("welcome", "zz", name="Bob")
    # English subject contains 'Welcome'.
    assert "Welcome" in subject
    assert "Bob" in subject


def test_variable_substitution_replaces_all():
    subject, html = render("welcome", "en", name="Дмитрий")
    assert "Дмитрий" in subject
    assert "Дмитрий" in html
    assert "{name}" not in subject
    assert "{name}" not in html
