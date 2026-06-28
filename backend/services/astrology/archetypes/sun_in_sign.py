"""Sun in the 12 signs — identity-archetype lookup.

Sun = solar identity, "I am", how the person experiences themselves
as a self. NOT the same as MC (social role). Sun is the inner light;
MC is the public face.

Sources:
- Stephen Arroyo, "Astrology, Karma & Transformation" (CRCS, 1978).
- Liz Greene, "Relating: An Astrological Guide to Living with Others
  on a Small Planet" (Weiser, 1977).
- Sue Tompkins, "The Contemporary Astrologer's Handbook" (2006), ch.5.

Confidence: 0.9 (cited modern tradition).
"""

SUN_IN_SIGN: dict[str, dict] = {
    "aries": {
        "core_identity": "The one who initiates",
        "themes": ["self as pioneer", "courage", "directness", "leadership through example"],
        "growth_edge": "Learning patience and inclusion of others' input.",
        "description": (
            "Идентичность строится через инициативу и прямое действие. "
            "Ты узнаёшь себя в момент, когда первым делаешь шаг. "
            "Точка роста — терпение и способность дать другим время."
        ),
        "source": "Stephen Arroyo, Astrology, Karma & Transformation (1978), ch.4",
    },
    "taurus": {
        "core_identity": "The one who builds and savors",
        "themes": ["self as steward of value", "sensuality", "patience", "reliability"],
        "growth_edge": "Learning to let go of what no longer serves.",
        "description": (
            "Идентичность через создание и сохранение материального и "
            "эстетического. Ты узнаёшь себя в надёжности и качестве. "
            "Точка роста — отпускать то, что устарело."
        ),
        "source": "Liz Greene, Relating (1977), p.62",
    },
    "gemini": {
        "core_identity": "The one who connects ideas",
        "themes": ["self as bridge", "curiosity", "multiplicity", "wit"],
        "growth_edge": "Learning to go deep in one area, not only wide.",
        "description": (
            "Идентичность через любопытство и связывание разных миров. "
            "Ты узнаёшь себя в моменте понимания и передачи. "
            "Точка роста — углубление, а не только расширение."
        ),
        "source": "Sue Tompkins, Contemporary Astrologer's Handbook (2006), p.94",
    },
    "cancer": {
        "core_identity": "The one who nurtures and remembers",
        "themes": ["self as caretaker", "emotional depth", "memory", "rootedness"],
        "growth_edge": "Learning to set boundaries without withdrawal.",
        "description": (
            "Идентичность через заботу, эмоциональную глубину и память. "
            "Ты узнаёшь себя в моменте защиты своих. Точка роста — "
            "ставить границы, не уходя в раковину."
        ),
        "source": "Stephen Arroyo, Astrology, Karma & Transformation (1978), ch.4",
    },
    "leo": {
        "core_identity": "The one who creates and radiates",
        "themes": ["self as creative source", "warmth", "generosity", "presence"],
        "growth_edge": "Learning to share the spotlight.",
        "description": (
            "Идентичность через творческое самовыражение и тепло. "
            "Ты узнаёшь себя в моменте созидания и щедрости. "
            "Точка роста — делиться вниманием, не только получать его."
        ),
        "source": "Liz Greene, Relating (1977), p.85",
    },
    "virgo": {
        "core_identity": "The one who refines and serves",
        "themes": ["self as craftsman", "precision", "service", "improvement"],
        "growth_edge": "Learning self-acceptance amidst the drive to improve.",
        "description": (
            "Идентичность через точность, ремесло и служение. Ты "
            "узнаёшь себя в моменте, когда что-то улучшено и работает "
            "лучше. Точка роста — принять себя несовершенным."
        ),
        "source": "Sue Tompkins, Contemporary Astrologer's Handbook (2006), p.100",
    },
    "libra": {
        "core_identity": "The one who creates harmony",
        "themes": ["self in relation", "diplomacy", "aesthetics", "fairness"],
        "growth_edge": "Learning to hold your own preference, not only mediate.",
        "description": (
            "Идентичность формируется в отношениях и через гармонию. "
            "Ты узнаёшь себя в зеркале другого. Точка роста — иметь "
            "собственное мнение, не только сглаживать."
        ),
        "source": "Liz Greene, Relating (1977), Part III",
    },
    "scorpio": {
        "core_identity": "The one who transforms through depth",
        "themes": ["self as catalyst", "intensity", "honesty", "regeneration"],
        "growth_edge": "Learning to trust and let go of control.",
        "description": (
            "Идентичность через глубину, трансформацию, честность с "
            "темными сторонами. Ты узнаёшь себя в моменте, когда "
            "пережил кризис и переродился. Точка роста — доверять."
        ),
        "source": "Liz Greene, The Astrology of Fate (1984), ch.5",
    },
    "sagittarius": {
        "core_identity": "The one who seeks meaning",
        "themes": ["self as seeker", "vision", "freedom", "philosophy"],
        "growth_edge": "Learning to ground vision in concrete commitment.",
        "description": (
            "Идентичность через поиск смысла, расширение горизонта, "
            "веру в большее. Ты узнаёшь себя в моменте открытия. "
            "Точка роста — превращать видение в конкретные обязательства."
        ),
        "source": "Stephen Arroyo, Astrology, Karma & Transformation (1978), ch.4",
    },
    "capricorn": {
        "core_identity": "The one who builds enduring structure",
        "themes": ["self as authority", "discipline", "responsibility", "achievement"],
        "growth_edge": "Learning to receive support and to rest.",
        "description": (
            "Идентичность через достижение, дисциплину, построение "
            "долгосрочного. Ты узнаёшь себя в моменте, когда что-то "
            "сделано надёжно. Точка роста — позволять помощь и отдых."
        ),
        "source": "Liz Greene, Saturn (1976), ch.3",
    },
    "aquarius": {
        "core_identity": "The one who envisions the future",
        "themes": ["self as innovator", "independence", "community", "originality"],
        "growth_edge": "Learning to stay in body and in personal closeness.",
        "description": (
            "Идентичность через инновацию, оригинальность мышления, "
            "независимость. Ты узнаёшь себя в моменте, когда видишь "
            "то, что другие пока не видят. Точка роста — телесность "
            "и личная близость."
        ),
        "source": "Sue Tompkins, Contemporary Astrologer's Handbook (2006), p.108",
    },
    "pisces": {
        "core_identity": "The one who merges and feels universally",
        "themes": ["self as empath", "compassion", "imagination", "surrender"],
        "growth_edge": "Learning to keep a personal boundary in service.",
        "description": (
            "Идентичность через сострадание, воображение, "
            "способность чувствовать тонкое. Ты узнаёшь себя в "
            "моменте слияния и отдачи. Точка роста — сохранять "
            "свою отдельность, помогая."
        ),
        "source": "Liz Greene, The Astrology of Fate (1984), ch.7",
    },
}


def sun_archetype(sign: str) -> dict:
    """Return Sun identity archetype dict for a sign (case-insensitive)."""
    key = sign.lower()
    if key not in SUN_IN_SIGN:
        raise KeyError(f"Unknown Sun sign: {sign}")
    return SUN_IN_SIGN[key]
