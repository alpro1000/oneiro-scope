"""Analysis orchestrator: what can be computed, in what order, with what inputs.

The problem this solves. A connector exposes 40+ tools; the chat model sees
their names but has no idea which sequence makes a coherent reading, and the
user does not know what to ask for. Both end up improvising, and the good
stuff (astrocartography, decade map, life-pivot validation) never gets used.

So the server answers that itself: given whatever inputs are known so far,
`build_plan` returns an ORDERED plan — stages that can run now, stages blocked
on a missing input, the exact questions to ask, and the canonical sequence in
which a reading is normally assembled. The model reads the plan and offers the
next step; the user can still jump anywhere.

This is data + dependency resolution only — no interpretation, no LLM. Stage
descriptions are bilingual so the connector can speak the user's language.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

# Input keys a stage can require. Kept as plain strings so the plan is
# JSON-serialisable and the model can echo them back as questions.
BIRTH_DATE = "birth_date"
BIRTH_TIME = "birth_time"
BIRTH_PLACE = "birth_place"  # resolved to lat/lon/tz via the geo tools
TARGET_DATE = "target_date"
START_YEAR = "start_year"
SCAN_YEARS = "scan_years"
CITIES = "cities"
PARTNER_BIRTH = "partner_birth_data"
DREAM_TEXT = "dream_text"
FACE_PHOTOS = "face_photos"
TRAITS = "character_traits"

# Human-readable prompts for the inputs a plan is missing. The connector asks
# these verbatim rather than inventing its own phrasing.
INPUT_QUESTIONS: dict[str, dict[str, str]] = {
    BIRTH_DATE: {
        "ru": "Дата рождения (ГГГГ-ММ-ДД)?",
        "en": "Date of birth (YYYY-MM-DD)?",
    },
    BIRTH_TIME: {
        "ru": "Время рождения (ЧЧ:ММ)? Без него дома и Асцендент не считаются.",
        "en": "Time of birth (HH:MM)? Without it houses and the Ascendant are omitted.",
    },
    BIRTH_PLACE: {
        "ru": "Город рождения?",
        "en": "City of birth?",
    },
    TARGET_DATE: {
        "ru": "Какая дата вас интересует (ГГГГ-ММ-ДД)?",
        "en": "Which date are you asking about (YYYY-MM-DD)?",
    },
    START_YEAR: {
        "ru": "С какого года смотреть десятилетие?",
        "en": "Which year should the decade map start from?",
    },
    SCAN_YEARS: {
        "ru": "Какой период прошлого сверяем (например 1995–2026)?",
        "en": "Which past window should we validate (e.g. 1995-2026)?",
    },
    CITIES: {
        "ru": "Какие города сравниваем?",
        "en": "Which cities should we compare?",
    },
    PARTNER_BIRTH: {
        "ru": "Данные рождения второго человека (дата, время, город)?",
        "en": "Second person's birth data (date, time, city)?",
    },
    DREAM_TEXT: {
        "ru": "Расскажите сон своими словами.",
        "en": "Describe the dream in your own words.",
    },
    FACE_PHOTOS: {
        "ru": "Пришлите свои фото (анфас/три четверти, ровный свет).",
        "en": "Upload your own photos (front / three-quarter, even light).",
    },
    TRAITS: {
        "ru": "Перечислите черты характера персонажа.",
        "en": "List the character's traits.",
    },
}


class Stage:
    """One offerable analysis step.

    `order` is the canonical position in a full reading — the sequence a human
    analyst would follow (identity first, then money/vocation, then timing,
    then validation against the past, then place, then single dates).
    `track` groups stages so the connector can present them as sections.
    """

    __slots__ = (
        "id", "order", "track", "tool", "requires", "improves_with",
        "depends_on", "name_ru", "name_en", "answers_ru", "answers_en",
    )

    def __init__(
        self,
        id: str,
        order: int,
        track: str,
        tool: str,
        requires: tuple[str, ...],
        name_ru: str,
        name_en: str,
        answers_ru: str,
        answers_en: str,
        improves_with: tuple[str, ...] = (),
        depends_on: tuple[str, ...] = (),
    ) -> None:
        self.id = id
        self.order = order
        self.track = track
        self.tool = tool
        self.requires = requires
        self.improves_with = improves_with
        self.depends_on = depends_on
        self.name_ru = name_ru
        self.name_en = name_en
        self.answers_ru = answers_ru
        self.answers_en = answers_en


# Canonical reading order. Tool names match the MCP registry in
# backend/mcp/server.py — keep them in sync when tools are added.
STAGES: tuple[Stage, ...] = (
    Stage(
        "natal-chart", 10, "foundation", "calculate_natal_chart",
        (BIRTH_DATE, BIRTH_PLACE), improves_with=(BIRTH_TIME,),
        name_ru="Натальная карта", name_en="Natal chart",
        answers_ru="Основа: положения планет, дома, аспекты, достоинства.",
        answers_en="The foundation: planet positions, houses, aspects, dignities.",
    ),
    Stage(
        "money-contour", 20, "self", "money_contour",
        (BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE), depends_on=("natal-chart",),
        name_ru="Денежный контур", name_en="Money contour",
        answers_ru="Как устроены деньги: 2-й и 8-й дома, управители, где потолок.",
        answers_en="How money works: 2nd and 8th houses, rulers, where the ceiling is.",
    ),
    Stage(
        "vocation-map", 30, "self", "vocation_map",
        (BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE), depends_on=("natal-chart",),
        name_ru="Карта призвания", name_en="Vocation map",
        answers_ru="Кластеры профессий: MC и его управитель, дома работы, достоинства.",
        answers_en="Profession clusters: MC and its ruler, work houses, dignities.",
    ),
    Stage(
        "transits", 40, "timing", "compute_transits",
        (BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE),
        name_ru="Транзиты на период", name_en="Transits for a window",
        answers_ru="Точные даты аспектов транзитных планет к натальным.",
        answers_en="Exact dates of transiting-to-natal aspects.",
    ),
    Stage(
        "decade-map", 50, "timing", "decade_map",
        (BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE), improves_with=(START_YEAR,),
        depends_on=("natal-chart",),
        name_ru="Декада по годам", name_en="Decade map",
        answers_ru="Десятилетие: фазы, возвраты Сатурна, окна старта и урожая.",
        answers_en="The decade: phases, Saturn returns, launch and harvest windows.",
    ),
    Stage(
        "solar-return", 60, "timing", "solar_return_chart",
        (BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE),
        name_ru="Солярная карта года", name_en="Solar return",
        answers_ru="Карта на год от дня рождения — темы предстоящего года.",
        answers_en="The birthday-return chart — themes of the year ahead.",
    ),
    Stage(
        "life-pivots", 70, "validation", "life_pivots",
        (BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE), improves_with=(SCAN_YEARS,),
        depends_on=("natal-chart",),
        name_ru="Лента переломов (сверка с жизнью)",
        name_en="Life-pivot timeline (validation)",
        answers_ru="Датированные окна прошлого — проверяем карту по фактам, "
                   "подтверждённые окна повышают достоверность прогноза.",
        answers_en="Dated past windows — validate the chart against real events; "
                   "confirmed windows raise the confidence of forecasts.",
    ),
    Stage(
        "astrocartography", 80, "place", "astrocartography_scan",
        (BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE), improves_with=(CITIES,),
        name_ru="Астрокартография (города)", name_en="Astrocartography (cities)",
        answers_ru="Какие планеты встают на углы в конкретных городах.",
        answers_en="Which planets land on the angles in given cities.",
    ),
    Stage(
        "electional-day", 90, "timing", "electional_day",
        (BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE, TARGET_DATE),
        name_ru="Электив дня (лучшие часы)", name_en="Electional day (best hours)",
        answers_ru="Часы конкретной даты: Луна, пустой ход, фаза, ретро-Меркурий.",
        answers_en="Hours of a given date: Moon, void-of-course, phase, Mercury retrograde.",
    ),
    Stage(
        "horoscope", 100, "timing", "generate_horoscope",
        (BIRTH_DATE,), improves_with=(BIRTH_TIME, BIRTH_PLACE),
        name_ru="Гороскоп на период", name_en="Horoscope for a period",
        answers_ru="День / неделя / месяц / год с опорой на карту.",
        answers_en="Day / week / month / year, grounded in the chart.",
    ),
    Stage(
        "synastry", 110, "relations", "synastry",
        (BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE, PARTNER_BIRTH),
        name_ru="Синастрия (совместимость)", name_en="Synastry",
        answers_ru="Взаимные аспекты двух карт.",
        answers_en="Cross-aspects between two charts.",
    ),
    # Independent tracks — no birth data needed.
    Stage(
        "lunar-day", 200, "standalone", "get_lunar_day",
        (), improves_with=(TARGET_DATE,),
        name_ru="Лунный день", name_en="Lunar day",
        answers_ru="Лунный день, фаза, знак Луны, освещённость на дату.",
        answers_en="Lunar day, phase, Moon sign, illumination for a date.",
    ),
    Stage(
        "dream", 210, "standalone", "analyze_dream",
        (DREAM_TEXT,),
        name_ru="Анализ сна", name_en="Dream analysis",
        answers_ru="Hall/Van de Castle + архетипы + сравнение с нормами DreamBank.",
        answers_en="Hall/Van de Castle + archetypes + DreamBank norm comparison.",
    ),
    Stage(
        "physiognomy", 220, "standalone", "analyze_face_archive",
        (FACE_PHOTOS,),
        name_ru="Портрет по лицу (только свой)",
        name_en="Face portrait (self only)",
        answers_ru="Метрики по фото + чтения из KB. Только свои фото — "
                   "чтение третьих лиц запрещено этикой системы.",
        answers_en="Photo metrics + KB readings. Own photos only — reading third "
                   "parties is forbidden by the system's ethics rule.",
    ),
    Stage(
        "character-face", 230, "standalone", "reverse_physiognomy_prompt",
        (TRAITS,),
        name_ru="Персонаж → лицо (промпт портрета)",
        name_en="Character → face (portrait prompt)",
        answers_ru="Обратная физиогномика для вымышленного персонажа или себя.",
        answers_en="Reverse physiognomy for a fictional character or yourself.",
    ),
)

_TRACK_NAMES: dict[str, dict[str, str]] = {
    "foundation": {"ru": "Основа", "en": "Foundation"},
    "self": {"ru": "Личность и ресурсы", "en": "Self and resources"},
    "timing": {"ru": "Время и окна", "en": "Timing and windows"},
    "validation": {"ru": "Сверка с жизнью", "en": "Validation against life"},
    "place": {"ru": "Место", "en": "Place"},
    "relations": {"ru": "Отношения", "en": "Relationships"},
    "standalone": {"ru": "Отдельные инструменты", "en": "Standalone tools"},
}


def _known(available: Iterable[str]) -> set[str]:
    return {k for k in available if k}


def build_plan(
    available_inputs: Optional[Iterable[str]] = None,
    completed: Optional[Iterable[str]] = None,
    locale: str = "ru",
) -> dict[str, Any]:
    """Return the ordered analysis plan for the inputs known so far.

    Args:
        available_inputs: input keys the caller already has (see the module
            constants, e.g. `["birth_date", "birth_place"]`).
        completed: stage ids already run in this conversation — they move to
            `completed` and stop being offered as the next step.
        locale: "ru" or "en" for the human-readable text.

    Returns a dict with `ready`, `blocked`, `completed`, `next_step`,
    `questions_to_ask` and `tracks`, all JSON-serialisable.
    """
    loc = "ru" if locale == "ru" else "en"
    have = _known(available_inputs or ())
    done = set(completed or ())

    ready: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    completed_out: list[dict[str, Any]] = []
    missing_all: list[str] = []

    for st in sorted(STAGES, key=lambda s: s.order):
        entry: dict[str, Any] = {
            "id": st.id,
            "order": st.order,
            "track": st.track,
            "track_name": _TRACK_NAMES[st.track][loc],
            "name": st.name_ru if loc == "ru" else st.name_en,
            "answers": st.answers_ru if loc == "ru" else st.answers_en,
            "tool": st.tool,
            "requires": list(st.requires),
        }
        missing = [k for k in st.requires if k not in have]
        degraded = [k for k in st.improves_with if k not in have]
        unmet_deps = [d for d in st.depends_on if d not in done]

        if st.id in done:
            completed_out.append(entry)
            continue

        if missing:
            entry["missing_inputs"] = missing
            entry["questions"] = [
                INPUT_QUESTIONS[k][loc] for k in missing if k in INPUT_QUESTIONS
            ]
            blocked.append(entry)
            missing_all.extend(missing)
            continue

        if degraded:
            entry["degraded_without"] = degraded
            entry["note"] = (
                "Посчитается, но точность ниже без: " if loc == "ru"
                else "Runs, but less precise without: "
            ) + ", ".join(degraded)
        if unmet_deps:
            # A soft dependency: the stage still runs (each tool recomputes the
            # chart itself), but reading it before its prerequisite is confusing.
            entry["better_after"] = unmet_deps
        ready.append(entry)

    # Deduplicate questions while keeping first-seen order.
    seen: set[str] = set()
    questions: list[dict[str, str]] = []
    for key in missing_all:
        if key in seen or key not in INPUT_QUESTIONS:
            continue
        seen.add(key)
        questions.append({"input": key, "question": INPUT_QUESTIONS[key][loc]})

    return {
        "locale": loc,
        "known_inputs": sorted(have),
        "next_step": ready[0] if ready else None,
        "ready": ready,
        "blocked": blocked,
        "completed": completed_out,
        "questions_to_ask": questions,
        "tracks": [
            {"track": t, "name": names[loc]} for t, names in _TRACK_NAMES.items()
        ],
        "total_stages": len(STAGES),
    }
