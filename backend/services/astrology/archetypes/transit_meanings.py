"""Transit archetypes — transiting planet × aspect × natal body lookup.

A transit is a *current* planet forming an aspect to a *natal* planet —
a window of time when a developmental theme is active. This table answers
"what is this transit traditionally about?" as deterministic, cited data
(confidence 0.9), NOT as LLM narrative. The exact dates come from the
ASTRONOMY layer (`compute_transits`, confidence 1.0); this module adds
the symbolic meaning on top.

Design — composition + named canonicals, not fabrication:

  - TRANSIT_AGENDA — what each transiting planet *does* when it contacts
    a natal point (tempo + process), cited to Robert Hand "Planets in
    Transit" (1976) and Liz Greene "The Outer Planets and Their Cycles"
    (1983).
  - natal drive — reused from PLANET_DRIVES (planet_in_house module),
    already cited to Tompkins / Hand.
  - aspect nature — reused from ASPECTS, cited to Tompkins "Aspects in
    Astrology" (1989).
  - NAMED_TRANSITS — the handful of canonical life-cycle transits
    (Saturn Return, Saturn hard-aspect to Sun = midlife reappraisal,
    outer-planet identity transits) get an explicit archetype label and
    an extra specific citation. Everything else is composed.

We deliberately do NOT invent a distinct page reference for each of the
~210 (6×5×7) cells — every claim traces to a real source, and the
citations are returned joined.

Confidence: 0.9 (cited modern tradition). Below ephemeris dates (1.0),
above LLM synthesis (0.7).

Lookup returns: archetype, themes, description, tempo, named (optional),
source.
"""

from __future__ import annotations

from backend.services.astrology.archetypes.aspects import ASPECTS
from backend.services.astrology.archetypes.planet_in_house import PLANET_DRIVES

# Transiting planets the transit engine scans (slow planets dominate).
TRANSITING_PLANETS: tuple[str, ...] = (
    "mars", "jupiter", "saturn", "uranus", "neptune", "pluto",
)

# Natal bodies the transit engine contacts. Limited to Sun..Saturn to
# match `transits_engine._NATAL_BODIES` — the astronomy layer does not
# emit transits to natal outer planets (and the Moon needs an exact birth
# time). Drive text for these is reused from PLANET_DRIVES.
NATAL_BODIES: tuple[str, ...] = (
    "sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn",
)

# What each transiting planet's passage is *about*: its process + tempo.
TRANSIT_AGENDA: dict[str, dict] = {
    "mars": {
        "process_ru": "толчок к действию, всплеск энергии и инициативы, иногда раздражение или спешка",
        "tempo": "дни (быстрый транзит)",
        "source": "Robert Hand, Planets in Transit (1976), Mars chapter",
    },
    "jupiter": {
        "process_ru": "расширение, рост возможностей, оптимизм и тяга к большему смыслу",
        "tempo": "недели–месяцы (около года в знаке)",
        "source": "Robert Hand, Planets in Transit (1976), Jupiter chapter",
    },
    "saturn": {
        "process_ru": "проверка на прочность, требование зрелости и ответственности, структурирование и встреча с ограничениями",
        "tempo": "2–3 года в зоне аспекта (с ретро-возвратами)",
        "source": "Liz Greene, Saturn (1976), ch.1; Robert Hand, Planets in Transit (1976), Saturn chapter",
    },
    "uranus": {
        "process_ru": "внезапное пробуждение, разрыв привычного шаблона и потребность в свободе и переменах",
        "tempo": "1–2 года (медленный, с ретро-возвратами)",
        "source": "Liz Greene, The Outer Planets and Their Cycles (1983), Uranus",
    },
    "neptune": {
        "process_ru": "растворение границ, идеализация и обострённая чувствительность, риск иллюзий и потери опоры",
        "tempo": "2–3 года (очень медленный)",
        "source": "Liz Greene, The Outer Planets and Their Cycles (1983), Neptune",
    },
    "pluto": {
        "process_ru": "глубинная трансформация, кризис власти и контроля, проживание смерти-возрождения",
        "tempo": "несколько лет (самый медленный)",
        "source": "Liz Greene, The Outer Planets and Their Cycles (1983), Pluto",
    },
}

# Per-aspect framing of a transit (challenge vs flow), in Russian.
_ASPECT_MODE_RU: dict[str, str] = {
    "conjunction": "слияния и старта нового цикла",
    "opposition": "кульминации и осознания через противостояние",
    "square": "напряжения, требующего действия и роста через кризис",
    "trine": "гармоничного, поддерживающего раскрытия",
    "sextile": "возможности, которую нужно взять сознательным усилием",
}

# Canonical life-cycle transits get an explicit archetype + extra citation.
# Keys are lowercase (transiting, aspect, natal). Natal bodies are limited
# to those the transit engine scans (Sun..Saturn).
NAMED_TRANSITS: dict[tuple[str, str, str], dict] = {
    ("saturn", "conjunction", "saturn"): {
        "named": "Saturn Return",
        "archetype": "Threshold of maturity",
        "extra_ru": (
            "Возвращение Сатурна (~29.5 и ~58.8 лет) — классический рубеж "
            "взросления: подведение итогов, отбрасывание чужого, принятие "
            "ответственности за собственную структуру жизни."
        ),
        "source": "Liz Greene, Saturn (1976), ch.1",
    },
    ("saturn", "square", "sun"): {
        "named": "Midlife reappraisal",
        "archetype": "Test of identity structure",
        "extra_ru": (
            "Сатурн в квадрате к Солнцу традиционно связывают с переоценкой "
            "себя: где жизнь построена на чужих ожиданиях, а где — на твоей "
            "подлинной воле. Часть «среднего возраста» как пересборки."
        ),
        "source": "Liz Greene, The Outer Planets and Their Cycles (1983); Robert Hand, Planets in Transit (1976)",
    },
    ("saturn", "opposition", "sun"): {
        "named": "Midlife reappraisal (culmination)",
        "archetype": "Reckoning with what was built",
        "extra_ru": (
            "Сатурн в оппозиции к Солнцу — точка осознания результатов "
            "прежних усилий, момент честной оценки достигнутого и цены."
        ),
        "source": "Liz Greene, Saturn (1976); Robert Hand, Planets in Transit (1976)",
    },
    ("saturn", "conjunction", "sun"): {
        "named": "Consolidation of self",
        "archetype": "Authority threshold",
        "extra_ru": (
            "Сатурн в соединении с Солнцем — начало нового 29-летнего цикла "
            "ответственности: сужение, концентрация, серьёзность задач."
        ),
        "source": "Robert Hand, Planets in Transit (1976), Saturn chapter",
    },
    ("pluto", "square", "sun"): {
        "named": "Empowerment crisis",
        "archetype": "Profound transformation of identity",
        "extra_ru": (
            "Плутон в квадрате к Солнцу — глубокая перестройка ощущения "
            "себя через кризис власти/контроля; то, что отжило, вынуждено "
            "умереть, чтобы освободить место подлинному."
        ),
        "source": "Liz Greene, The Outer Planets and Their Cycles (1983), Pluto",
    },
    ("neptune", "square", "sun"): {
        "named": "Dissolution of identity",
        "archetype": "Spiritual reorientation",
        "extra_ru": (
            "Нептун в квадрате к Солнцу — размывание прежней опоры на эго, "
            "период тумана и поиска большего смысла; риск иллюзий и "
            "разочарований, дар — чувствительность и сострадание."
        ),
        "source": "Liz Greene, The Outer Planets and Their Cycles (1983), Neptune",
    },
    ("uranus", "square", "sun"): {
        "named": "Awakening crisis",
        "archetype": "Breakout from the old self",
        "extra_ru": (
            "Уран в квадрате к Солнцу — внезапная потребность сбросить "
            "ограничивающую идентичность, рывок к свободе и переменам."
        ),
        "source": "Liz Greene, The Outer Planets and Their Cycles (1983), Uranus",
    },
}


def transit_archetype(transiting: str, aspect: str, natal: str) -> dict:
    """Return the archetype of a transit (transiting planet × aspect × natal body).

    Args:
        transiting: transiting planet (mars/jupiter/saturn/uranus/neptune/pluto).
        aspect: conjunction/opposition/square/trine/sextile.
        natal: natal body being contacted (sun/moon/mercury/venus/mars/
            jupiter/saturn — the bodies the transit engine scans).

    Returns dict with archetype, themes, description, tempo, named, source.
    Raises KeyError on unknown transiting planet / aspect / natal body.
    """
    t = transiting.lower()
    a = aspect.lower()
    n = natal.lower()

    if t not in TRANSIT_AGENDA:
        raise KeyError(f"Unknown / non-scanned transiting planet: {transiting}")
    if a not in ASPECTS:
        raise KeyError(f"Unknown aspect: {aspect}")
    if n not in NATAL_BODIES:
        raise KeyError(f"Unknown / non-scanned natal body: {natal}")

    agenda = TRANSIT_AGENDA[t]
    drive = PLANET_DRIVES[n]
    asp = ASPECTS[a]
    mode_ru = _ASPECT_MODE_RU[a]
    named = NAMED_TRANSITS.get((t, a, n))

    description = (
        f"Транзитный {transiting.capitalize()} в аспекте «{a}» к натальному "
        f"{natal.capitalize()}: {agenda['process_ru']} активирует "
        f"{drive['drive_ru']}. Это период {mode_ru}. "
        f"Темп: {agenda['tempo']}."
    )
    if named:
        description = f"{named['extra_ru']} {description}"

    archetype = (
        named["archetype"]
        if named
        else f"{transiting.capitalize()} {a} natal {natal.capitalize()}"
    )

    source = f"{agenda['source']}; {asp['source']}"
    if named:
        source = f"{named['source']}; {source}"

    result = {
        "archetype": archetype,
        "themes": list(drive["themes"]) + [agenda["tempo"], asp["nature"]],
        "description": description,
        "tempo": agenda["tempo"],
        "named": named["named"] if named else None,
        "source": source,
    }
    return result
