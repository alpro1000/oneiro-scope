"""Planet in house — 10 planets × 12 houses drive-area lookup.

A planet IN a house tells you WHERE the planet's psychological drive is
invested (the house = life-area). This table is built by **composition**
of two independently-cited layers, not by inventing 120 page references:

  - PLANET_DRIVES — the core drive of each of the 10 planets, cited to
    Sue Tompkins "The Contemporary Astrologer's Handbook" (2006) ch.4
    "The Planets" and Robert Hand "Horoscope Symbols" (1981).
  - HOUSES (sibling module) — the life-area of each house, cited to
    Howard Sasportas "The Twelve Houses" (1985).

This mirrors how Sasportas himself reads a planet-in-house: planet drive
expressed through the house's field of experience. Keeping the citation
honest (two real sources composed) respects the provenance principle —
we do NOT fabricate a distinct page number for each of the 120 cells.

Confidence: 0.9 (cited modern tradition). One tier below ephemeris (1.0),
above LLM synthesis (0.7).

Each lookup returns a dict with:
  - `archetype`   — short label ("<planet drive> in <house field>")
  - `themes`      — planet keyword(s) + house themes
  - `description` — composed Russian text (drive × area)
  - `source`      — both citations, joined
"""

from __future__ import annotations

from backend.services.astrology.archetypes.houses import HOUSES

# Canonical 10 planets used in modern natal interpretation.
PLANETS: tuple[str, ...] = (
    "sun", "moon", "mercury", "venus", "mars",
    "jupiter", "saturn", "uranus", "neptune", "pluto",
)

# Russian short label for each house's field of experience, so composed
# descriptions read naturally. Derived from the cited HOUSES table.
_HOUSE_FIELD_RU: dict[int, str] = {
    1: "самопроявления и того, как ты входишь в жизнь",
    2: "личных ресурсов, денег и самоценности",
    3: "повседневной коммуникации, обучения и ближнего окружения",
    4: "дома, корней и психологического фундамента",
    5: "творчества, игры, романтики и самовыражения",
    6: "ежедневной работы, рутины, здоровья и ремесла",
    7: "партнёрства, брака и значимого Другого",
    8: "общих ресурсов, кризисов и глубинной трансформации",
    9: "смысла, высшего знания, дальних горизонтов и веры",
    10: "карьеры, публичной роли и социального статуса",
    11: "друзей, сообществ и долгосрочных надежд",
    12: "бессознательного, уединения и того, что за кулисами",
}

# Each planet's core drive. `archetype` = short English drive label;
# `drive_ru` = the psychological need in Russian; `focus_ru` = the verb
# of how it acts; `themes` = keywords; `source` = real citation.
PLANET_DRIVES: dict[str, dict] = {
    "sun": {
        "archetype": "The will to shine",
        "drive_ru": "сознательная воля, жизненная сила и потребность быть собой",
        "focus_ru": "ты ищешь признание и вкладываешь жизненную энергию",
        "themes": ["identity", "vitality", "purpose"],
        "source": "Sue Tompkins, Contemporary Astrologer's Handbook (2006), ch.4 (The Sun)",
    },
    "moon": {
        "archetype": "The need to feel safe",
        "drive_ru": "эмоциональные потребности, инстинкт заботы и чувство безопасности",
        "focus_ru": "ты эмоционально привязываешься и ищешь ощущение дома",
        "themes": ["emotion", "security", "nurture"],
        "source": "Sue Tompkins, Contemporary Astrologer's Handbook (2006), ch.4 (The Moon)",
    },
    "mercury": {
        "archetype": "The drive to connect ideas",
        "drive_ru": "мышление, речь, любопытство и обмен информацией",
        "focus_ru": "ты думаешь, учишься и налаживаешь связи",
        "themes": ["thought", "communication", "curiosity"],
        "source": "Robert Hand, Horoscope Symbols (1981), ch.5 (Mercury)",
    },
    "venus": {
        "archetype": "The pull toward harmony",
        "drive_ru": "ценности, влечение, удовольствие и стремление к гармонии",
        "focus_ru": "ты ищешь близость, красоту и то, что тебе дорого",
        "themes": ["values", "attraction", "harmony"],
        "source": "Sue Tompkins, Contemporary Astrologer's Handbook (2006), ch.4 (Venus)",
    },
    "mars": {
        "archetype": "The will to act",
        "drive_ru": "воля к действию, желание, напор и способность отстаивать себя",
        "focus_ru": "ты действуешь, добиваешься и заявляешь о себе",
        "themes": ["action", "desire", "assertion"],
        "source": "Sue Tompkins, Contemporary Astrologer's Handbook (2006), ch.4 (Mars)",
    },
    "jupiter": {
        "archetype": "The search for meaning",
        "drive_ru": "рост, экспансия, вера, смысл и щедрость",
        "focus_ru": "ты расширяешься, ищешь смысл и доверяешь большему",
        "themes": ["expansion", "meaning", "faith"],
        "source": "Robert Hand, Horoscope Symbols (1981), ch.5 (Jupiter)",
    },
    "saturn": {
        "archetype": "The work of mastery",
        "drive_ru": "структура, дисциплина, ответственность и мастерство через усилие",
        "focus_ru": "ты выстраиваешь, берёшь ответственность и взрослеешь через ограничение",
        "themes": ["structure", "discipline", "maturation"],
        "source": "Liz Greene, Saturn (1976), ch.1; Sue Tompkins, Handbook (2006), ch.4",
    },
    "uranus": {
        "archetype": "The urge to break free",
        "drive_ru": "потребность в свободе, новаторство и индивидуация",
        "focus_ru": "ты обновляешь, отделяешься от шаблона и ищешь свободу",
        "themes": ["freedom", "innovation", "individuation"],
        "source": "Sue Tompkins, Contemporary Astrologer's Handbook (2006), ch.4 (Uranus)",
    },
    "neptune": {
        "archetype": "The longing to merge",
        "drive_ru": "растворение границ, идеал, воображение и тоска по единству",
        "focus_ru": "ты идеализируешь, мечтаешь и стремишься к большему, чем ты сам",
        "themes": ["imagination", "ideal", "transcendence"],
        "source": "Sue Tompkins, Contemporary Astrologer's Handbook (2006), ch.4 (Neptune)",
    },
    "pluto": {
        "archetype": "The power to transform",
        "drive_ru": "глубинная трансформация, власть, кризис и возрождение",
        "focus_ru": "ты проживаешь кризис и перерождение, сталкиваясь с глубиной",
        "themes": ["transformation", "power", "regeneration"],
        "source": "Liz Greene, The Astrology of Fate (1984), ch.6; Robert Hand, Horoscope Symbols (1981), ch.5",
    },
}


def planet_in_house_archetype(planet: str, house_number: int) -> dict:
    """Return composed planet-in-house archetype (planet drive × house field).

    Args:
        planet: lowercase planet name (sun/moon/.../pluto).
        house_number: 1-12.

    Returns dict with archetype, themes, description, source.
    Raises KeyError on an unknown planet or invalid house number.
    """
    p = planet.lower()
    if p not in PLANET_DRIVES:
        raise KeyError(f"Unknown planet: {planet}")
    if house_number not in HOUSES:
        raise KeyError(f"Invalid house number: {house_number} (must be 1-12)")

    drive = PLANET_DRIVES[p]
    house = HOUSES[house_number]
    field_ru = _HOUSE_FIELD_RU[house_number]

    description = (
        f"{drive['drive_ru'].capitalize()} находит выражение в сфере "
        f"{field_ru} ({house['name']}, дом {house_number}). "
        f"Традиционно это означает, что {drive['focus_ru']} именно в этой "
        f"области жизни."
    )

    return {
        "archetype": f"{drive['archetype']} in the field of {house['name']}",
        "themes": list(drive["themes"]) + list(house["themes"]),
        "description": description,
        "source": f"{drive['source']}; {house['source']}",
    }
