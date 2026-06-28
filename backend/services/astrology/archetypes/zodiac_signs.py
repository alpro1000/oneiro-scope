"""Zodiac sign archetypes — the 12 elemental keywords table.

Sources:
- Sue Tompkins, "Aspects in Astrology" (Element, 1989), Part I.
- Liz Greene & Stephen Arroyo, "The Astrology of Fate" (Weiser, 1984).
- Stephen Arroyo, "Astrology, Psychology, and the Four Elements" (CRCS, 1975).

Confidence: 0.9 (cited classical/modern tradition).
"""

ZODIAC_SIGNS: dict[str, dict] = {
    "aries": {
        "element": "fire",
        "modality": "cardinal",
        "ruler": "mars",
        "keywords": ["initiative", "courage", "self-assertion", "pioneer", "impulse"],
        "shadow": ["impatience", "aggression", "isolation"],
        "description": (
            "Огненный кардинальный знак Овна классически связывают с "
            "инициативой, прямой волей, способностью начинать. "
            "Под управлением Марса — энергия выражается через действие, "
            "не через рефлексию. В тени: импульсивность, нетерпимость к "
            "медленным процессам, изоляция от командной работы."
        ),
        "source": "Sue Tompkins, Aspects in Astrology (1989), ch.2",
    },
    "taurus": {
        "element": "earth",
        "modality": "fixed",
        "ruler": "venus",
        "keywords": ["stability", "sensuality", "material building", "patience", "loyalty"],
        "shadow": ["stubbornness", "possessiveness", "inertia"],
        "description": (
            "Земной фиксированный знак Тельца — про устойчивое построение "
            "материального и эстетического. Управление Венерой даёт чувство "
            "ценности, ручную работу, любовь к надёжному комфорту. В тени — "
            "упрямство, накопительство, сопротивление переменам."
        ),
        "source": "Sue Tompkins, Aspects in Astrology (1989), ch.2",
    },
    "gemini": {
        "element": "air",
        "modality": "mutable",
        "ruler": "mercury",
        "keywords": ["communication", "curiosity", "multiplicity", "exchange", "wit"],
        "shadow": ["scatter", "superficiality", "restlessness"],
        "description": (
            "Воздушный мутабельный знак Близнецов — про коммуникацию, "
            "обучение, мост между идеями и людьми. Управляется Меркурием. "
            "В тени: рассеянность, поверхностность, неспособность углубиться "
            "в одну тему до конца."
        ),
        "source": "Liz Greene, Relating (1977), Part II",
    },
    "cancer": {
        "element": "water",
        "modality": "cardinal",
        "ruler": "moon",
        "keywords": ["home", "nurturing", "memory", "protection", "emotional depth"],
        "shadow": ["clinging", "moodiness", "withdrawal"],
        "description": (
            "Водный кардинальный знак Рака — про дом, заботу, эмоциональную "
            "память, защиту своих. Лунное управление делает его глубоко "
            "циклическим и интуитивным. В тени: цепляние за прошлое, "
            "перепады настроения, отступление в раковину."
        ),
        "source": "Sue Tompkins, Aspects in Astrology (1989), ch.2",
    },
    "leo": {
        "element": "fire",
        "modality": "fixed",
        "ruler": "sun",
        "keywords": ["creativity", "leadership", "play", "recognition", "warmth"],
        "shadow": ["pride", "drama", "need for approval"],
        "description": (
            "Огненный фиксированный знак Льва — про творческое самовыражение, "
            "лидерство через личное присутствие, способность согреть и "
            "вдохновить. Солнечное управление. В тени: гордыня, "
            "театральность, болезненная нужда в признании."
        ),
        "source": "Robert Hand, Horoscope Symbols (1981), Part II",
    },
    "virgo": {
        "element": "earth",
        "modality": "mutable",
        "ruler": "mercury",
        "keywords": ["precision", "service", "analysis", "craft", "improvement"],
        "shadow": ["criticism", "perfectionism", "anxiety"],
        "description": (
            "Земной мутабельный знак Девы — про точность, ремесло, "
            "служение, систематическое улучшение деталей. Управление "
            "Меркурием — аналитическое. В тени: разрушительная критика, "
            "перфекционизм, тревожность из-за деталей."
        ),
        "source": "Sue Tompkins, Aspects in Astrology (1989), ch.2",
    },
    "libra": {
        "element": "air",
        "modality": "cardinal",
        "ruler": "venus",
        "keywords": ["balance", "partnership", "diplomacy", "aesthetics", "fairness"],
        "shadow": ["indecision", "people-pleasing", "avoidance of conflict"],
        "description": (
            "Воздушный кардинальный знак Весов — про партнёрство, баланс, "
            "дипломатию, эстетику. Венерианское управление в социальном "
            "режиме. В тени: нерешительность, угождение всем, избегание "
            "конфликта ценой собственной позиции."
        ),
        "source": "Liz Greene, Relating (1977), Part III",
    },
    "scorpio": {
        "element": "water",
        "modality": "fixed",
        "ruler": "pluto",
        "keywords": ["transformation", "depth", "investigation", "intensity", "power"],
        "shadow": ["obsession", "control", "vengeance"],
        "description": (
            "Водный фиксированный знак Скорпиона — про трансформацию через "
            "глубину, исследование скрытого, владение силой. Современное "
            "управление Плутоном (классически — Марс). В тени: "
            "одержимость, контроль, мстительность."
        ),
        "source": "Liz Greene, The Astrology of Fate (1984), ch.5",
    },
    "sagittarius": {
        "element": "fire",
        "modality": "mutable",
        "ruler": "jupiter",
        "keywords": ["meaning", "expansion", "philosophy", "foreign cultures", "vision"],
        "shadow": ["dogmatism", "overreach", "restlessness"],
        "description": (
            "Огненный мутабельный знак Стрельца — про поиск смысла, "
            "расширение через знание, путешествия и философию, "
            "большую визию. Под Юпитером. В тени: догматизм, переоценка "
            "себя, неспособность приземлиться."
        ),
        "source": "Sue Tompkins, Aspects in Astrology (1989), ch.2",
    },
    "capricorn": {
        "element": "earth",
        "modality": "cardinal",
        "ruler": "saturn",
        "keywords": ["structure", "achievement", "discipline", "authority", "responsibility"],
        "shadow": ["coldness", "rigidity", "over-control"],
        "description": (
            "Земной кардинальный знак Козерога — про построение долгосрочной "
            "структуры, достижение через дисциплину, ответственность и "
            "иерархию. Под Сатурном. В тени: холодность, ригидность, "
            "избыточный контроль над собой и другими."
        ),
        "source": "Liz Greene, Saturn: A New Look at an Old Devil (1976)",
    },
    "aquarius": {
        "element": "air",
        "modality": "fixed",
        "ruler": "uranus",
        "keywords": ["innovation", "community", "vision", "independence", "originality"],
        "shadow": ["detachment", "contrarianism", "alienation"],
        "description": (
            "Воздушный фиксированный знак Водолея — про инновацию, "
            "сообщество единомышленников, независимость взглядов, "
            "оригинальность. Современное управление Ураном (классически — "
            "Сатурн). В тени: эмоциональная отстранённость, противоречие "
            "ради противоречия, одиночество."
        ),
        "source": "Robert Hand, Horoscope Symbols (1981), Part II",
    },
    "pisces": {
        "element": "water",
        "modality": "mutable",
        "ruler": "neptune",
        "keywords": ["compassion", "imagination", "spirituality", "merging", "intuition"],
        "shadow": ["escapism", "victim role", "boundary loss"],
        "description": (
            "Водный мутабельный знак Рыб — про сострадание, воображение, "
            "духовное слияние, тонкую интуицию. Современное управление "
            "Нептуном (классически — Юпитер). В тени: эскапизм, роль "
            "жертвы, размытие границ."
        ),
        "source": "Liz Greene, The Astrology of Fate (1984), ch.7",
    },
}


def sign_archetype(sign: str) -> dict:
    """Return the archetype dict for a sign name (case-insensitive)."""
    key = sign.lower()
    if key not in ZODIAC_SIGNS:
        raise KeyError(f"Unknown sign: {sign}")
    return ZODIAC_SIGNS[key]
