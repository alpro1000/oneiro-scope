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
POINT = "point_of_interest"  # one lat/lon the caller wants examined
PARTNER_BIRTH = "partner_birth_data"
DREAM_TEXT = "dream_text"
FACE_PHOTOS = "face_photos"
TRAITS = "character_traits"
USER_ID = "user_id"

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
    POINT: {
        "ru": "Координаты точки (широта/долгота), которую разбираем?",
        "en": "Coordinates (lat/lon) of the point to examine?",
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
    USER_ID: {
        "ru": "ID пользователя (UUID из аккаунта) — чья серия снов?",
        "en": "User ID (account UUID) — whose dream series?",
    },
}


class Stage:
    """One offerable analysis step.

    `order` is the canonical position in a full reading — the sequence a human
    analyst would follow (identity first, then money/vocation, then timing,
    then validation against the past, then place, then single dates).
    `track` groups stages so the connector can present them as sections.
    `domain` is the coarser split a caller is offered: "astro" covers the
    chart and the face — both read one standing person from static data —
    while "dreams" is per-episode and shares no inputs with them.
    """

    __slots__ = (
        "id", "order", "track", "domain", "tool", "requires", "improves_with",
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
        domain: str = "astro",
    ) -> None:
        self.id = id
        self.order = order
        self.track = track
        self.domain = domain
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
        "solar-return", 60, "timing", "solar_return_chart",
        (BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE),
        name_ru="Солярная карта года", name_en="Solar return",
        answers_ru="Карта на год от дня рождения — темы предстоящего года.",
        answers_en="The birthday-return chart — themes of the year ahead.",
    ),
    Stage(
        "astrocartography", 80, "place", "astrocartography_scan",
        (BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE), improves_with=(CITIES,),
        name_ru="Астрокартография (города)", name_en="Astrocartography (cities)",
        answers_ru="Какие планеты встают на углы в конкретных городах.",
        answers_en="Which planets land on the angles in given cities.",
    ),
    Stage(
        "astrocartography-lines", 81, "place", "astrocartography_lines",
        (BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE),
        name_ru="Линии астрокартографии (карта)",
        name_en="Astrocartography lines (map)",
        answers_ru="Полный набор линий MC/IC/Asc/Desc для интерактивной карты.",
        answers_en="The full MC/IC/Asc/Desc line set for an interactive map.",
    ),
    Stage(
        "astrocartography-point", 83, "place", "astrocartography_point",
        (BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE, POINT),
        name_ru="Разбор одной точки на карте",
        name_en="One map point, explained",
        answers_ru="Релокационные углы и контакты планет для одной точки.",
        answers_en="Relocated angles and planet contacts for one clicked point.",
    ),
    # Independent tracks — no birth data needed.
    # --- Added so the offered menu matches the registry, not a subset of it.
    # These were computable all along but never appeared in the plan, so a
    # connector following `analysis_plan` could not discover them.
    Stage(
        "event-forecast", 95, "timing", "forecast_event",
        (TARGET_DATE,), improves_with=(BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE),
        name_ru="Прогноз по событию", name_en="Event forecast",
        answers_ru="Насколько дата располагает к конкретному действию.",
        answers_en="How favourable a date is for a specific action.",
    ),
    Stage(
        "compare-cities", 82, "place", "compare_relocations",
        (BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE, CITIES),
        name_ru="Сравнение городов", name_en="Compare cities",
        answers_ru="Города рядом: все четыре угла, ось дом/работа, честная сводка.",
        answers_en="Cities side by side: all four angles, home/work axis, honest summary.",
    ),
    Stage(
        "solar-return-where", 65, "timing", "solar_return_suggest",
        (BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE, CITIES),
        depends_on=("solar-return",),
        name_ru="Где встречать день рождения", name_en="Where to spend the birthday",
        answers_ru="Рейтинг городов на момент солнечного возврата.",
        answers_en="City ranking for the moment of solar return.",
    ),
    Stage(
        "lunar-period", 205, "standalone", "get_lunar_period",
        (TARGET_DATE,),
        name_ru="Лунный период", name_en="Lunar period",
        answers_ru="Лунные дни на диапазон дат, а не на один день.",
        answers_en="Lunar days across a date range, not just one day.",
    ),
    Stage(
        "lunar-day", 200, "standalone", "get_lunar_day",
        (), improves_with=(TARGET_DATE,),
        name_ru="Лунный день", name_en="Lunar day",
        answers_ru="Лунный день, фаза, знак Луны, освещённость на дату.",
        answers_en="Lunar day, phase, Moon sign, illumination for a date.",
    ),
    Stage(
        "dream", 210, "dreams", "analyze_dream",
        (DREAM_TEXT,),
        name_ru="Анализ сна", name_en="Dream analysis",
        answers_ru="Hall/Van de Castle + архетипы + сравнение с нормами DreamBank.",
        answers_en="Hall/Van de Castle + archetypes + DreamBank norm comparison.",
        domain="dreams",
    ),
    Stage(
        "dream-series", 211, "dreams", "dream_series_stats",
        (USER_ID,),
        name_ru="Личная серия снов", name_en="Personal dream series",
        answers_ru="Динамика показателей по вашей серии и отклонение последнего "
                   "сна от личной базовой линии (минимум 15 снов).",
        answers_en="Indicator trends over your own series and the latest dream's "
                   "deviation from your personal baseline (15+ dreams).",
        domain="dreams",
    ),
)

TRACK_NAMES: dict[str, dict[str, str]] = {
    "foundation": {"ru": "Основа", "en": "Foundation"},
    "self": {"ru": "Личность и ресурсы", "en": "Self and resources"},
    "timing": {"ru": "Время и окна", "en": "Timing and windows"},
    "place": {"ru": "Место", "en": "Place"},
    "standalone": {"ru": "Отдельные инструменты", "en": "Standalone tools"},
    "dreams": {"ru": "Сны", "en": "Dreams"},
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
            "track_name": TRACK_NAMES[st.track][loc],
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
            {"track": t, "name": names[loc]} for t, names in TRACK_NAMES.items()
        ],
        "total_stages": len(STAGES),
    }


# --- Capability menu (compact since WP-11) ------------------------------------
#
# Why this exists. A caller that lands on one tool has no way to learn the
# rest of the surface. `build_plan` already answers "what can be computed and
# in what order", but nothing surfaced it unless the model thought to ask.
#
# Why it is THIS small. The first version attached the full ready/blocked/
# questions structure to every response; a live audit measured ~90k chars of
# menu across one conversation — the menu had become the payload. What a
# model actually needs in-band is "which tools are one step away"; everything
# else lives one call away in `analysis_plan`. Budget: ≤200 chars, enforced
# by test.

# Reference dictionaries: lookups, not computations over a person. All of
# them live behind the single `lookup` tool since WP-10.
#
# "face" is a domain in this table but not in `capability_menu` — deliberately.
# A face reading is a dictionary lookup keyed by what the reader said about
# their own face; it computes nothing, depends on nothing, and leads nowhere,
# so it is not a stage in a reading and offers no next step. Listing it here is
# what keeps `test_every_registered_computation_is_a_stage_or_reference`
# meaningful: every registered tool is either a step or a declared lookup.
REFERENCE_TOOLS: dict[str, tuple[str, ...]] = {
    "astro": ("lookup", "search_city", "validate_birth_data"),
    "dreams": ("lookup",),
    "face": ("read_face_traits", "physiognomy_methods"),
}


def capability_menu(
    domain: str = "astro",
    known_inputs: Optional[Iterable[str]] = None,
    completed: Optional[Iterable[str]] = None,
    locale: str = "ru",
) -> dict[str, Any]:
    """Compact "what else can I compute" block: up to three ready tools.

    `next` lists only steps whose required inputs the calling tool already
    had — the next call needs nothing further. Stage order is preserved, so
    the first entry is the canonical next step of a full reading. The
    ordered plan, blocked steps and their questions live in `analysis_plan`.

    Args:
        domain: "astro" or "dreams" — a dream response never offers chart
            steps and vice versa.
        known_inputs: input keys the calling tool already had.
        completed: stage ids already run, so they stop being offered.
        locale: kept for call-site compatibility; the compact block carries
            tool names only, which are locale-free.
    """
    have = _known(known_inputs or ())
    done = set(completed or ())

    next_tools: list[str] = []
    for st in sorted(STAGES, key=lambda s: s.order):
        if st.domain != domain or st.id in done:
            continue
        if any(k not in have for k in st.requires):
            continue
        if st.tool not in next_tools:
            next_tools.append(st.tool)
        if len(next_tools) == 3:
            break

    return {"next": next_tools, "full_plan_tool": "analysis_plan"}
