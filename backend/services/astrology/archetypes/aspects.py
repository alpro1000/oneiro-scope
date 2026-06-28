"""The 5 major aspects — angular-relationship archetype lookup.

Aspects describe **how two planets interact**: harmoniously (trine,
sextile), with tension (square, opposition), or fused (conjunction).

Sources:
- Sue Tompkins, "Aspects in Astrology" (Element, 1989) —
  the modern definitive reference on aspect interpretation.
- Charles Carter, "The Astrological Aspects" (Theosophical, 1930).
- Bil Tierney, "Dynamics of Aspect Analysis" (CRCS, 1980).

Confidence: 0.9 (cited modern tradition).

NOTE: aspect orbs are domain-configurable in domain.md; the
archetype table here is qualitative.
"""

ASPECTS: dict[str, dict] = {
    "conjunction": {
        "angle_deg": 0,
        "default_orb": 8.0,
        "nature": "neutral / fusing",
        "archetype": "Fusion",
        "description": (
            "Соединение (0°) — две планеты сливаются в единый импульс. "
            "Энергия концентрированная, нерасщеплённая. Качество зависит "
            "от характера планет: соединение с Юпитером — расширение; "
            "с Сатурном — сужение и структурирование. Не 'хороший' и не "
            "'плохой' — фундаментальный."
        ),
        "source": "Sue Tompkins, Aspects in Astrology (1989), ch.4",
    },
    "opposition": {
        "angle_deg": 180,
        "default_orb": 8.0,
        "nature": "tense / polarising",
        "archetype": "Polarity",
        "description": (
            "Оппозиция (180°) — две планеты лицом к лицу. Создаёт "
            "осознанность через противоположность, проекцию на другого. "
            "Классически 'трудный' аспект, но именно он даёт зрелость "
            "через интеграцию двух полюсов."
        ),
        "source": "Sue Tompkins, Aspects in Astrology (1989), ch.5",
    },
    "trine": {
        "angle_deg": 120,
        "default_orb": 7.0,
        "nature": "harmonious / flowing",
        "archetype": "Flow",
        "description": (
            "Трин (120°) — гармоничный поток энергии между двумя планетами. "
            "Лёгкий, но иногда настолько лёгкий, что становится привычным "
            "и не развивается. Дары без сопротивления — нужно сознательно "
            "ими пользоваться."
        ),
        "source": "Sue Tompkins, Aspects in Astrology (1989), ch.6",
    },
    "square": {
        "angle_deg": 90,
        "default_orb": 7.0,
        "nature": "tense / activating",
        "archetype": "Tension and Action",
        "description": (
            "Квадрат (90°) — напряжение, требующее действия. Два принципа "
            "конфликтуют и заставляют что-то делать. Классически "
            "'трудный', но самый продуктивный аспект — он двигает. "
            "Без квадратов жизнь стоит."
        ),
        "source": "Sue Tompkins, Aspects in Astrology (1989), ch.7",
    },
    "sextile": {
        "angle_deg": 60,
        "default_orb": 5.0,
        "nature": "harmonious / opportunity",
        "archetype": "Open Door",
        "description": (
            "Секстиль (60°) — благоприятная возможность, но в отличие от "
            "трина, требует усилия, чтобы её взять. Открытая дверь — "
            "надо войти. Часто работает через интеллект и коммуникацию."
        ),
        "source": "Bil Tierney, Dynamics of Aspect Analysis (1980)",
    },
}


def aspect_archetype(name: str) -> dict:
    """Return aspect archetype dict for an aspect name (case-insensitive)."""
    key = name.lower()
    if key not in ASPECTS:
        raise KeyError(f"Unknown aspect: {name}")
    return ASPECTS[key]
