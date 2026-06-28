"""The 12 astrological houses — life-area lookup.

Houses describe **areas of experience**, not personality traits.
A planet in a house tells you WHERE its energy is invested.

Sources:
- Howard Sasportas, "The Twelve Houses" (Aquarian Press, 1985) —
  the modern reference for psychological house interpretation.
- Sue Tompkins, "The Contemporary Astrologer's Handbook" (Flare, 2006), ch.7.
- Robert Hand, "Horoscope Symbols" (Para Research, 1981), ch.7.

Confidence: 0.9 (cited modern tradition).
"""

HOUSES: dict[int, dict] = {
    1: {
        "name": "House of Self",
        "themes": ["personal identity", "appearance", "first impression", "approach to life"],
        "natural_sign": "aries",
        "ruler": "mars",
        "description": (
            "Первый дом — как ты себя проявляешь, твоя 'обложка', "
            "первое впечатление, физическое присутствие, манера "
            "входить в комнату. Не вся идентичность (это Солнце), "
            "а её внешняя оболочка."
        ),
        "source": "Howard Sasportas, The Twelve Houses (1985), ch.6",
    },
    2: {
        "name": "House of Resources",
        "themes": ["personal finances", "values", "self-worth", "possessions"],
        "natural_sign": "taurus",
        "ruler": "venus",
        "description": (
            "Второй дом — твои собственные ресурсы: деньги, ценности, "
            "вещи, которыми ты владеешь. Также самоценность — то, что "
            "ты считаешь достойным внутри себя."
        ),
        "source": "Howard Sasportas, The Twelve Houses (1985), ch.7",
    },
    3: {
        "name": "House of Communication",
        "themes": ["siblings", "local environment", "early learning", "short trips", "writing"],
        "natural_sign": "gemini",
        "ruler": "mercury",
        "description": (
            "Третий дом — ближайшее окружение, братья и сёстры, школа, "
            "повседневная коммуникация, локальные поездки, письмо. "
            "Сфера 'как ты учишься на бытовом уровне'."
        ),
        "source": "Howard Sasportas, The Twelve Houses (1985), ch.8",
    },
    4: {
        "name": "House of Home and Roots",
        "themes": ["family of origin", "home", "private life", "psychological roots", "real estate"],
        "natural_sign": "cancer",
        "ruler": "moon",
        "description": (
            "Четвёртый дом — корни, дом, семья происхождения, "
            "приватная жизнь, психологический фундамент, недвижимость. "
            "Глубинная база, на которой стоит всё остальное."
        ),
        "source": "Sue Tompkins, Contemporary Astrologer's Handbook (2006), p.142",
    },
    5: {
        "name": "House of Creativity and Play",
        "themes": ["creative self-expression", "children", "romance", "hobbies", "speculation"],
        "natural_sign": "leo",
        "ruler": "sun",
        "description": (
            "Пятый дом — творчество, игра, дети, романтика, хобби, "
            "то, что ты делаешь ради радости. Сфера 'детского' "
            "самовыражения у взрослого."
        ),
        "source": "Howard Sasportas, The Twelve Houses (1985), ch.10",
    },
    6: {
        "name": "House of Work and Health",
        "themes": ["daily work", "service", "routines", "health", "skill mastery"],
        "natural_sign": "virgo",
        "ruler": "mercury",
        "description": (
            "Шестой дом — ежедневная работа (НЕ карьера-как-статус, это 10-й), "
            "рутина, служение, здоровье, ремесло. Сфера 'как ты "
            "функционируешь день за днём'."
        ),
        "source": "Robert Hand, Horoscope Symbols (1981), ch.7",
    },
    7: {
        "name": "House of Partnership",
        "themes": ["marriage", "business partners", "open enemies", "contracts", "the 'other'"],
        "natural_sign": "libra",
        "ruler": "venus",
        "description": (
            "Седьмой дом — значимый Другой: брак, деловое партнёрство, "
            "открытые противники, контракты. Зеркало, в котором ты "
            "видишь то, что не видишь в себе."
        ),
        "source": "Howard Sasportas, The Twelve Houses (1985), ch.12",
    },
    8: {
        "name": "House of Shared Resources and Transformation",
        "themes": ["joint finances", "inheritance", "investments", "deep psychology", "death/rebirth"],
        "natural_sign": "scorpio",
        "ruler": "pluto",
        "description": (
            "Восьмой дом — чужие/общие ресурсы: совместные финансы, "
            "наследство, инвестиции, кредиты, страхование. Также "
            "глубинная психология, кризисы и трансформации, всё "
            "табуированное."
        ),
        "source": "Liz Greene, The Astrology of Fate (1984), ch.6",
    },
    9: {
        "name": "House of Higher Learning",
        "themes": ["higher education", "foreign cultures", "philosophy", "long journeys", "publishing"],
        "natural_sign": "sagittarius",
        "ruler": "jupiter",
        "description": (
            "Девятый дом — высшее образование, иностранные культуры, "
            "философия, длинные путешествия, издательство, право. "
            "Сфера 'расширения горизонта смысла'."
        ),
        "source": "Howard Sasportas, The Twelve Houses (1985), ch.14",
    },
    10: {
        "name": "House of Career and Public Role",
        "themes": ["career", "public reputation", "authority", "achievement", "social status"],
        "natural_sign": "capricorn",
        "ruler": "saturn",
        "description": (
            "Десятый дом — карьера в публичном смысле, репутация, "
            "социальный статус, авторитет, то, как тебя видит общество. "
            "MC — вершина этого дома. НЕ 'призвание', а социальная роль."
        ),
        "source": "Sue Tompkins, Contemporary Astrologer's Handbook (2006), p.154",
    },
    11: {
        "name": "House of Community and Hopes",
        "themes": ["friends", "groups", "long-term goals", "social ideals", "the 'tribe'"],
        "natural_sign": "aquarius",
        "ruler": "uranus",
        "description": (
            "Одиннадцатый дом — друзья, группы, единомышленники, "
            "долгосрочные надежды и социальные идеалы, твоё 'племя'. "
            "Сфера 'кто рядом, когда ты строишь будущее'."
        ),
        "source": "Howard Sasportas, The Twelve Houses (1985), ch.16",
    },
    12: {
        "name": "House of the Unconscious",
        "themes": ["unconscious", "solitude", "spiritual retreat", "hidden enemies", "transcendence"],
        "natural_sign": "pisces",
        "ruler": "neptune",
        "description": (
            "Двенадцатый дом — бессознательное, скрытое, уединение, "
            "духовное отступление, всё, что 'за кулисами' жизни. "
            "Сфера 'где ты встречаешься с собой настоящим, без зрителей'."
        ),
        "source": "Liz Greene, The Astrology of Fate (1984), ch.8",
    },
}


def house_archetype(house_number: int) -> dict:
    """Return house archetype dict for a house number 1-12."""
    if house_number not in HOUSES:
        raise KeyError(f"Invalid house number: {house_number} (must be 1-12)")
    return HOUSES[house_number]
