"""Disclaimer enforcement (scaffold §1 + domain.md).

Every interpretive response — astrology reading, dream analysis,
strategic synthesis — MUST carry a disclaimer that it is reflective /
entertainment content, not medical / psychological / legal / financial
advice, and that no absolute predictions are offered.

This module gives:
- the canonical disclaimer text (RU/EN/DE/ES/FR)
- `has_disclaimer(text, locale)` — fast check
- `ensure_disclaimer(text, locale)` — append if missing
- `DisclaimerError` raised by hard validators (Pydantic or API layer)
"""

from __future__ import annotations

DISCLAIMER_RU = (
    "Это рефлексивно-развлекательный контент, не медицинский, "
    "психологический, юридический или финансовый совет. Никаких "
    "абсолютных предсказаний."
)

DISCLAIMER_EN = (
    "This is reflective / entertainment content — not medical, "
    "psychological, legal or financial advice. No absolute predictions "
    "are offered."
)

DISCLAIMER_DE = (
    "Dies ist reflektierender / unterhaltender Inhalt — keine "
    "medizinische, psychologische, rechtliche oder finanzielle Beratung. "
    "Keine absoluten Vorhersagen."
)

DISCLAIMER_ES = (
    "Este es contenido reflexivo / de entretenimiento — no es consejo "
    "médico, psicológico, legal ni financiero. Sin predicciones absolutas."
)

DISCLAIMER_FR = (
    "Ce contenu est réflexif / divertissant — ce n'est pas un conseil "
    "médical, psychologique, juridique ou financier. Aucune prédiction "
    "absolue."
)

DISCLAIMERS: dict[str, str] = {
    "ru": DISCLAIMER_RU,
    "en": DISCLAIMER_EN,
    "de": DISCLAIMER_DE,
    "es": DISCLAIMER_ES,
    "fr": DISCLAIMER_FR,
}

# Sentinel phrases — if ANY of these is present, the disclaimer is
# considered satisfied. This lets the LLM phrase its own version as
# long as the meaning is there.
_SENTINELS_RU = (
    "рефлексивно-развлекательный",
    "не медицинский совет",
    "не является советом",
    "это не диагноз",
)
_SENTINELS_EN = (
    "reflective",
    "entertainment content",
    "not medical advice",
    "not legal advice",
    "no absolute prediction",
    "for reflection only",
)


class DisclaimerError(ValueError):
    """Raised when a response that should carry a disclaimer doesn't."""


def has_disclaimer(text: str, locale: str = "ru") -> bool:
    """Return True if the text contains any of the sentinel phrases for
    the given locale (falling back to broader checks)."""
    lower = text.lower()
    if locale == "ru":
        return any(s in lower for s in _SENTINELS_RU)
    # English check works for de/es/fr too if the LLM defaulted there.
    return any(s in lower for s in _SENTINELS_EN)


def ensure_disclaimer(text: str, locale: str = "ru") -> str:
    """If the text already carries a disclaimer, return it unchanged.
    Otherwise append the canonical one for the locale (RU default)."""
    if has_disclaimer(text, locale):
        return text
    disclaimer = DISCLAIMERS.get(locale, DISCLAIMER_RU)
    separator = "\n\n---\n\n" if text.strip() else ""
    return f"{text}{separator}_{disclaimer}_"
