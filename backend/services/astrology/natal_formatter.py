"""Utilities for turning raw natal chart data into readable Markdown.

The :func:`format_natal_chart` helper is designed for lightweight rendering
of Swiss Ephemeris output without requiring the full domain models used
elsewhere in the service. It accepts a simple ``dict`` payload and returns
either Markdown or a JSON string, making it suitable for CLI tools and API
responses alike.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict


PLANET_EMOJI = {
    "sun": "☉",
    "moon": "☽",
    "mercury": "☿",
    "venus": "♀",
    "mars": "♂",
    "jupiter": "♃",
    "saturn": "♄",
    "uranus": "♅",
    "neptune": "♆",
    "pluto": "♇",
    "ascendant": "↑",
}


PLANET_NAMES = {
    "ru": {
        "sun": "Солнце",
        "moon": "Луна",
        "mercury": "Меркурий",
        "venus": "Венера",
        "mars": "Марс",
        "jupiter": "Юпитер",
        "saturn": "Сатурн",
        "uranus": "Уран",
        "neptune": "Нептун",
        "pluto": "Плутон",
        "ascendant": "Асцендент",
    },
    "en": {
        "sun": "Sun",
        "moon": "Moon",
        "mercury": "Mercury",
        "venus": "Venus",
        "mars": "Mars",
        "jupiter": "Jupiter",
        "saturn": "Saturn",
        "uranus": "Uranus",
        "neptune": "Neptune",
        "pluto": "Pluto",
        "ascendant": "Ascendant",
    },
}


SIGN_NAMES = {
    "Sagittarius": {"ru": "Стрелец", "en": "Sagittarius"},
    "Capricorn": {"ru": "Козерог", "en": "Capricorn"},
    "Aquarius": {"ru": "Водолей", "en": "Aquarius"},
    "Pisces": {"ru": "Рыбы", "en": "Pisces"},
    "Aries": {"ru": "Овен", "en": "Aries"},
    "Taurus": {"ru": "Телец", "en": "Taurus"},
    "Gemini": {"ru": "Близнецы", "en": "Gemini"},
    "Cancer": {"ru": "Рак", "en": "Cancer"},
    "Leo": {"ru": "Лев", "en": "Leo"},
    "Virgo": {"ru": "Дева", "en": "Virgo"},
    "Libra": {"ru": "Весы", "en": "Libra"},
    "Scorpio": {"ru": "Скорпион", "en": "Scorpio"},
}


SIGN_TRAITS = {
    "ru": {
        "Sagittarius": "философичность и стремление к росту",
        "Capricorn": "дисциплина и ответственность",
        "Aquarius": "свобода мысли и инновации",
        "Pisces": "интуиция и эмпатия",
        "Aries": "смелость и прямота",
        "Taurus": "устойчивость и чувственность",
        "Gemini": "любознательность и общительность",
        "Cancer": "забота и эмоциональная глубина",
        "Leo": "щедрость и потребность сиять",
        "Virgo": "внимательность к деталям",
        "Libra": "гармония и дипломатия",
        "Scorpio": "интенсивность и трансформация",
    },
    "en": {
        "Sagittarius": "philosophical and growth-oriented",
        "Capricorn": "disciplined and responsible",
        "Aquarius": "free-thinking and innovative",
        "Pisces": "intuitive and empathetic",
        "Aries": "bold and straightforward",
        "Taurus": "steady and sensual",
        "Gemini": "curious and communicative",
        "Cancer": "caring and emotionally deep",
        "Leo": "generous and eager to shine",
        "Virgo": "detail-oriented",
        "Libra": "harmonizing and diplomatic",
        "Scorpio": "intense and transformative",
    },
}


ASPECT_SYMBOLS = {
    "conjunction": "☌",
    "sextile": "⚹",
    "square": "□",
    "trine": "△",
    "opposition": "☍",
}


ASPECT_DESCRIPTIONS = {
    "ru": {
        "conjunction": "слияние энергий",
        "sextile": "лёгкое сотрудничество",
        "square": "напряжение, требующее действия",
        "trine": "гармоничный поток",
        "opposition": "поиск баланса",
    },
    "en": {
        "conjunction": "fusion of energies",
        "sextile": "easy cooperation",
        "square": "tension that needs action",
        "trine": "harmonious flow",
        "opposition": "seeking balance",
    },
}


MONTHS_RU = [
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
]


def _format_date(date_str: str, locale: str) -> str:
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    except (TypeError, ValueError):
        return date_str

    if locale == "ru":
        month = MONTHS_RU[dt.month - 1]
        return f"{dt.day} {month} {dt.year}"
    return dt.strftime("%B %d, %Y")


def _localized(value: str, locale: str, mapping: Dict[str, Dict[str, str]]) -> str:
    return mapping.get(value, {}).get(locale, value)


def _format_position(name: str, position: Dict[str, Any], locale: str) -> str:
    sign = position.get("sign") or ""
    degree = position.get("degree")
    house = position.get("house")
    degree_txt = f"{degree}°" if degree is not None else ""
    sign_local = _localized(sign, locale, SIGN_NAMES)
    planet_name = PLANET_NAMES[locale].get(name, name)
    emoji = PLANET_EMOJI.get(name, "")
    house_txt = f", {('дом' if locale == 'ru' else 'house')} {house}" if house else ""
    trait = SIGN_TRAITS[locale].get(sign, "")

    if locale == "ru":
        return f"{emoji} **{planet_name} в {sign_local} ({degree_txt}{house_txt})** — {trait}."
    return f"{emoji} **{planet_name} in {sign_local} ({degree_txt}{house_txt})** — {trait}."


def _format_aspect_entry(aspect: Dict[str, Any], locale: str) -> str:
    p1 = aspect.get("planet1", "").lower()
    p2 = aspect.get("planet2", "").lower()
    aspect_type = (aspect.get("type") or "").lower()
    orb = aspect.get("orb")
    orb_txt = f"{orb:.1f}°" if isinstance(orb, (int, float)) else ""
    symbol = ASPECT_SYMBOLS.get(aspect_type, "")
    description = ASPECT_DESCRIPTIONS[locale].get(aspect_type, "")

    p1_name = PLANET_NAMES[locale].get(p1, p1.title())
    p2_name = PLANET_NAMES[locale].get(p2, p2.title())

    if locale == "ru":
        return f"{PLANET_EMOJI.get(p1, '')} {p1_name} {symbol} {PLANET_EMOJI.get(p2, '')} {p2_name} (орб {orb_txt}) — {description}."
    return f"{PLANET_EMOJI.get(p1, '')} {p1_name} {symbol} {PLANET_EMOJI.get(p2, '')} {p2_name} (orb {orb_txt}) — {description}."


def format_natal_chart(data: dict) -> str:
    """
    Принимает JSON-данные натальной карты и возвращает человеко-читаемый отчёт.

    Parameters
    ----------
    data: dict
        Сырые данные с позициями планет и аспектами, совместимые с Swiss Ephemeris.

    Returns
    -------
    str
        Markdown или JSON (если ``output_format=json`` в данных).
    """

    locale = data.get("locale", "ru")
    locale = locale if locale in {"ru", "en"} else "ru"
    output_format = data.get("output_format", "markdown")

    name = data.get("name", "—")
    date = _format_date(data.get("date", ""), locale)
    time = data.get("time", "—")
    place = data.get("place", "—")

    positions = data.get("positions", {}) or {}
    aspects = data.get("aspects", []) or []

    # Core placements
    sun_md = _format_position("sun", positions.get("sun", {}), locale)
    moon_md = _format_position("moon", positions.get("moon", {}), locale)
    asc_md = _format_position("ascendant", positions.get("ascendant", {}), locale)

    # Other planets
    other_planets: list[str] = []
    for key, value in positions.items():
        if key in {"sun", "moon", "ascendant"}:
            continue
        other_planets.append(_format_position(key, value, locale))

    aspect_lines = [_format_aspect_entry(item, locale) for item in aspects]

    report = {
        "title": "# 🜚 NATAL CHART" if locale == "en" else "# 🜚 НАТАЛЬНАЯ КАРТА",
        "identity": [
            ("Name" if locale == "en" else "Имя", name),
            ("Date" if locale == "en" else "Дата", date),
            ("Time" if locale == "en" else "Время", time),
            ("Place" if locale == "en" else "Место", place),
        ],
        "core": [sun_md, moon_md, asc_md],
        "planets": other_planets,
        "aspects": aspect_lines,
    }

    if output_format == "json":
        return json.dumps(report, ensure_ascii=False, indent=2)

    lines: list[str] = [report["title"]]
    lines.append("**Имя:** {0}  " if locale == "ru" else "**Name:** {0}  ".format(name))
    lines.append("**Дата:** {0}  " if locale == "ru" else "**Date:** {0}  ".format(date))
    lines.append("**Время:** {0}  " if locale == "ru" else "**Time:** {0}  ".format(time))
    lines.append("**Место:** {0}  " if locale == "ru" else "**Place:** {0}  ".format(place))
    lines.append("\n---\n")

    lines.append("## 🌞 Основные положения" if locale == "ru" else "## 🌞 Core Placements")
    lines.extend([sun_md, moon_md, asc_md, "", "---", ""])

    lines.append("## 🪐 Планеты" if locale == "ru" else "## 🪐 Planets")
    lines.extend(f"- {planet}" for planet in other_planets)
    lines.extend(["", "---", ""])

    lines.append("## 🔭 Аспекты" if locale == "ru" else "## 🔭 Aspects")
    lines.extend(f"- {aspect}" for aspect in aspect_lines)

    return "\n".join(line.rstrip() for line in lines if line is not None)

