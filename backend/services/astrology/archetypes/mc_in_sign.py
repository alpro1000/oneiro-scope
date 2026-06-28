"""MC (Midheaven) in the 12 signs — career-archetype lookup.

MC = Medium Coeli = the point of the ecliptic that culminates at
birth. It marks the **public face and career direction** — NOT
destiny, NOT "calling" in the romantic sense. It is the social role
through which the person is recognised.

Sources:
- Sue Tompkins, "The Contemporary Astrologer's Handbook" (Flare, 2006),
  ch.13 "The Angles".
- Liz Greene & Howard Sasportas, "The Inner Planets" (Weiser, 1993).
- Robert Hand, "Horoscope Symbols" (Para Research, 1981), ch.6.

Confidence: 0.9 (cited modern tradition).
"""

MC_IN_SIGN: dict[str, dict] = {
    "aries": {
        "archetype": "Pioneer / Entrepreneur",
        "themes": ["initiative", "independent enterprise", "competition", "leadership through action"],
        "description": (
            "Карьерная роль связана с инициативой и независимым действием. "
            "Тебя видят как того, кто начинает первым, идёт в новые "
            "территории, конкурирует и побеждает напрямую. Подходит "
            "предпринимательство, военное дело, спорт, экстренные службы."
        ),
        "source": "Sue Tompkins, Contemporary Astrologer's Handbook (2006), p.234",
    },
    "taurus": {
        "archetype": "Builder / Steward of Material Value",
        "themes": ["financial stability", "material craft", "real estate", "long-term assets"],
        "description": (
            "Карьера через построение материального и эстетического — "
            "финансы, недвижимость, ручное ремесло, искусство как продукт. "
            "Тебя видят как надёжного хранителя ценностей. Медленный, но "
            "устойчивый рост репутации."
        ),
        "source": "Robert Hand, Horoscope Symbols (1981), p.176",
    },
    "gemini": {
        "archetype": "Communicator / Connector",
        "themes": ["media", "writing", "teaching", "trade", "networking"],
        "description": (
            "Публичная роль через коммуникацию: журналистика, преподавание, "
            "продажи, переводы, посредничество. Тебя видят как мост между "
            "людьми и идеями. Часто параллельная многозадачность — "
            "несколько проектов сразу."
        ),
        "source": "Sue Tompkins, Contemporary Astrologer's Handbook (2006), p.236",
    },
    "cancer": {
        "archetype": "Caregiver / Custodian",
        "themes": ["family business", "hospitality", "real estate", "psychology", "nutrition"],
        "description": (
            "Карьерная роль через заботу и защиту: семейный бизнес, "
            "гостеприимство, психология, питание, недвижимость как дом. "
            "Тебя видят как того, к кому идут за эмоциональным укрытием "
            "или 'своим местом'."
        ),
        "source": "Liz Greene & Howard Sasportas, The Inner Planets (1993)",
    },
    "leo": {
        "archetype": "Performer / Creative Leader",
        "themes": ["arts", "stage", "entertainment", "luxury", "creative direction"],
        "description": (
            "Публичная роль предполагает видимость и личное присутствие: "
            "сцена, искусство, развлечения, креативное руководство, "
            "люкс-сектор. Тебя признают через личный 'свет', не через "
            "командную незаметность."
        ),
        "source": "Robert Hand, Horoscope Symbols (1981), p.177",
    },
    "virgo": {
        "archetype": "Craftsman / Analyst",
        "themes": ["precision work", "health", "service", "editing", "data analysis"],
        "description": (
            "Карьера через точное ремесло и аналитику: здравоохранение, "
            "редактура, данные, контроль качества, прикладная наука. "
            "Тебя видят как специалиста по деталям, к которому идут "
            "за надёжной экспертизой."
        ),
        "source": "Sue Tompkins, Contemporary Astrologer's Handbook (2006), p.238",
    },
    "libra": {
        "archetype": "Diplomat / Aesthetic Mediator",
        "themes": ["law", "diplomacy", "design", "consulting", "HR", "partnership work"],
        "description": (
            "Карьерная роль через партнёрство, баланс и эстетику: право, "
            "дипломатия, дизайн, консалтинг, HR, всё, где нужно "
            "посредничество между сторонами. Тебя видят как 'честного "
            "арбитра'."
        ),
        "source": "Liz Greene & Howard Sasportas, The Inner Planets (1993)",
    },
    "scorpio": {
        "archetype": "Investigator / Transformer",
        "themes": ["finance (loans/insurance)", "research", "forensics", "depth psychology", "surgery"],
        "description": (
            "Публичная роль через работу с закрытыми, глубокими, "
            "трансформирующими процессами: финансы партнёров и кредиты, "
            "исследование, форензик, глубинная психотерапия, хирургия, "
            "разведка. Тебя признают как того, кто 'видит под капотом'."
        ),
        "source": "Sue Tompkins, Contemporary Astrologer's Handbook (2006), p.240",
    },
    "sagittarius": {
        "archetype": "Teacher / Visionary",
        "themes": ["higher education", "publishing", "law", "travel industry", "philosophy"],
        "description": (
            "Карьера через смысл и расширение: высшее образование, "
            "издательство, право, философия, индустрия путешествий, "
            "межкультурная работа. Тебя видят как 'мудреца' или "
            "идейного лидера, дающего перспективу."
        ),
        "source": "Robert Hand, Horoscope Symbols (1981), p.178",
    },
    "capricorn": {
        "archetype": "Authority / Institutional Builder",
        "themes": ["corporate management", "government", "engineering", "long structures"],
        "description": (
            "Публичная роль через структуру и иерархию: корпоративное "
            "управление, государственная служба, инженерия, всё, что "
            "строится на десятилетия. Тебя признают через стабильность, "
            "ответственность и принадлежность к 'старшим'."
        ),
        "source": "Liz Greene, Saturn: A New Look at an Old Devil (1976), ch.4",
    },
    "aquarius": {
        "archetype": "Innovator / Networker",
        "themes": ["technology", "non-profit", "scientific research", "futurism", "social systems"],
        "description": (
            "Карьера через инновацию и сообщество: технологии, наука, "
            "non-profit, футуризм, проектирование социальных систем. "
            "Тебя видят как 'своего, но не из системы' — независимая "
            "роль, часто общественно полезная."
        ),
        "source": "Sue Tompkins, Contemporary Astrologer's Handbook (2006), p.242",
    },
    "pisces": {
        "archetype": "Healer / Artist / Mystic",
        "themes": ["arts (music, film)", "psychotherapy", "spiritual service", "addiction recovery"],
        "description": (
            "Публичная роль через сострадание и воображение: искусство "
            "(музыка, кино), психотерапия, духовное служение, "
            "работа с зависимостями. Тебя признают как того, кто "
            "видит/чувствует тонкое."
        ),
        "source": "Liz Greene, The Astrology of Fate (1984), ch.7",
    },
}


def mc_archetype(sign: str) -> dict:
    """Return MC archetype dict for a sign (case-insensitive)."""
    key = sign.lower()
    if key not in MC_IN_SIGN:
        raise KeyError(f"Unknown MC sign: {sign}")
    return MC_IN_SIGN[key]
