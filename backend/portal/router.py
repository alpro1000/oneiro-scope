"""Portal: the thin public surface of an MCP-first product.

Four jobs and nothing more (see docs/specs/product-architecture/):
explain · how to connect · what it costs · legal pages required for the
connector directories. Everything a user actually *does* happens in their
chat, not here.

Server-rendered from the same FastAPI service as the API and `/mcp`, so there
is no second host, no build step and no CORS. The "what it can compute" table
is generated from `analysis_plan`, so the site cannot drift away from the
tools the connector really exposes.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from backend.core.config import settings
from backend.services.strategic.analysis_plan import STAGES, TRACK_NAMES
from backend.services.strategic.disclaimer import DISCLAIMER_EN, DISCLAIMER_RU

router = APIRouter(tags=["Portal"], include_in_schema=False)

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# Content is inline rather than in a CMS: five pages that change rarely, and
# keeping them next to the code means the connect instructions stay in sync
# with the deployment they describe.
CONTENT: dict[str, dict[str, str]] = {
    "ru": {
        "nav_connect": "Подключить", "nav_pricing": "Тарифы",
        "nav_privacy": "Приватность", "nav_terms": "Условия",
        "hero_title": "Астрология, сны и лица — прямо в вашем чате",
        "hero_lede": "Расчёты по эфемеридам, чтения с указанием источника. "
                     "Подключается как коннектор к Claude, ChatGPT и Gemini — "
                     "отдельное приложение не нужно.",
        "works_in": "Работает внутри:",
        "works_in_note": "по одной ссылке, без установки",
        "cta_connect": "Как подключить",
        "why_title": "Чем это отличается",
        "why_1_h": "Считает, а не выдумывает",
        "why_1_b": "положения планет, дома, аспекты и транзиты вычисляются "
                   "Swiss Ephemeris; языковая модель их только объясняет.",
        "why_2_h": "Каждое утверждение с источником",
        "why_2_b": "видно, где расчёт, где классическое правило с цитатой, "
                   "а где синтез — и с какой достоверностью.",
        "why_3_h": "Без предсказаний",
        "why_3_b": "система не говорит «случится»: только «традиционно "
                   "связывают», «окно благоприятнее». Это правило проверяется кодом.",
        "why_4_h": "Ничего не забывает",
        "why_4_b": "сервис сам перечисляет, что ещё можно посчитать по вашим "
                   "данным, и в каком порядке это читается.",
        "what_title": "Что умеет",
        "what_note": "Список формируется из самого сервиса — он не может "
                     "разойтись с тем, что реально доступно в чате.",
        "ladder_title": "Лестница достоверности",
        "ladder_body": "Каждый пункт ответа помечен слоем: выше в таблице — "
                       "надёжнее. Нижний слой никогда не переписывает верхний.",
        "ladder_col_layer": "Слой", "ladder_col_conf": "Достоверность",
        "ladder_astronomy": "Астрономический расчёт (Swiss Ephemeris)",
        "ladder_classical": "Классическое правило с цитатой источника",
        "ladder_dictionary": "Словарь символов (сны, архетипы)",
        "ladder_llm": "Синтез языковой модели",
        "ladder_physio": "Физиогномика (историческая традиция, наукой не подтверждена)",
        "connect_title": "Подключение за минуту",
        "connect_lede": "Один адрес — три чата. Установка не требуется.",
        "connect_url_label": "Адрес коннектора",
        "claude_1": "Настройки → Коннекторы → «Добавить свой коннектор».",
        "claude_2": "Вставьте адрес выше и подтвердите вход.",
        "claude_3": "Готово — инструменты появятся в списке чата.",
        "claude_note": "Свои коннекторы доступны на платных планах; "
                       "в организациях их может ограничивать администратор.",
        "gpt_1": "Настройки → «Безопасность и вход» → включите режим разработчика.",
        "gpt_2": "Настройки → «Plugins» (или chatgpt.com/plugins) → «+».",
        "gpt_3": "Вставьте адрес выше.",
        "gpt_note": "Нужен план Plus/Pro/Business — на бесплатном свои "
                    "коннекторы не поддерживаются.",
        "gem_1": "Откройте gemini.google.com/apps.",
        "gem_2": "Внизу добавьте ссылку на своё приложение — вставьте адрес выше.",
        "gem_note": "Поддержка MCP в Gemini раскатывается постепенно.",
        "first_ask_title": "Первый вопрос",
        "first_ask_body": "Просто напишите в чате свои данные рождения — "
                          "сервис сам предложит порядок разбора.",
        "first_ask_example": "Посчитай мою карту: 1 июля 1977, 22:30, Запорожье",
        "first_ask_note": "Дальше можно спрашивать свободно: про деньги, "
                          "профессию, десятилетие, города, лучший день для "
                          "разговора — или рассказать сон.",
        "troubleshoot_title": "Если что-то не так",
        "trouble_401": "коннектор требует входа — пройдите авторизацию в окне чата.",
        "trouble_slow_h": "Первый ответ долгий",
        "trouble_slow_b": "сервер просыпается после простоя; повторите запрос.",
        "trouble_free_h": "Не видно кнопки в ChatGPT",
        "trouble_free_b": "включите режим разработчика; на бесплатном плане "
                          "свои коннекторы недоступны.",
        "pricing_title": "Тарифы",
        "pricing_lede": "Оплата за доступ, а не за каждый вопрос.",
        "pricing_col_plan": "План", "pricing_col_included": "Что входит",
        "pricing_col_price": "Цена",
        "pricing_note": "Тарифы будут уточнены к публичному запуску. "
                        "Оплата и управление подпиской — в личном кабинете.",
        "pricing_how_title": "Как это работает",
        "pricing_how_body": "Вы регистрируетесь здесь и оформляете подписку. "
                            "Тот же аккаунт открывает коннектор в чате: "
                            "при подключении вы просто входите в него.",
        "legal_updated": "Обновлено",
        "legal_draft_notice": "Черновик для ознакомления. Перед публичным "
                              "запуском текст должен быть проверен юристом.",
        "privacy_title": "Политика приватности",
        "terms_title": "Условия использования",
    },
    "en": {
        "nav_connect": "Connect", "nav_pricing": "Pricing",
        "nav_privacy": "Privacy", "nav_terms": "Terms",
        "hero_title": "Astrology, dreams and faces — inside your chat",
        "hero_lede": "Ephemeris-grade computation, readings that cite their "
                     "source. Add it as a connector in Claude, ChatGPT or "
                     "Gemini — no separate app to install.",
        "works_in": "Works inside:",
        "works_in_note": "one URL, nothing to install",
        "cta_connect": "How to connect",
        "why_title": "What makes it different",
        "why_1_h": "It computes, it doesn't invent",
        "why_1_b": "planet positions, houses, aspects and transits come from "
                   "Swiss Ephemeris; the language model only explains them.",
        "why_2_h": "Every claim carries its source",
        "why_2_b": "you see what is calculation, what is a cited classical "
                   "rule, and what is synthesis — with its confidence.",
        "why_3_h": "No fortune-telling",
        "why_3_b": "the system never says \"this will happen\" — only "
                   "\"traditionally associated with\", \"a favourable window\". "
                   "That rule is enforced in code.",
        "why_4_h": "It doesn't forget anything",
        "why_4_b": "the service lists what else can be computed from your "
                   "data, and the order a reading is normally built in.",
        "what_title": "What it can do",
        "what_note": "This list is generated from the service itself, so it "
                     "cannot drift from what is actually available in chat.",
        "ladder_title": "Confidence ladder",
        "ladder_body": "Every statement is tagged with its layer — higher in "
                       "the table is more reliable. A lower layer never "
                       "overrides a higher one.",
        "ladder_col_layer": "Layer", "ladder_col_conf": "Confidence",
        "ladder_astronomy": "Astronomical computation (Swiss Ephemeris)",
        "ladder_classical": "Cited classical rule",
        "ladder_dictionary": "Symbol dictionary (dreams, archetypes)",
        "ladder_llm": "Language-model synthesis",
        "ladder_physio": "Physiognomy (historical tradition, not scientifically validated)",
        "connect_title": "Connect in a minute",
        "connect_lede": "One URL, three chats. Nothing to install.",
        "connect_url_label": "Connector URL",
        "claude_1": "Settings → Connectors → \"Add custom connector\".",
        "claude_2": "Paste the URL above and complete the sign-in.",
        "claude_3": "Done — the tools appear in your chat.",
        "claude_note": "Custom connectors are a paid-plan feature; "
                       "organisation admins may restrict them.",
        "gpt_1": "Settings → \"Security and login\" → enable Developer mode.",
        "gpt_2": "Settings → \"Plugins\" (or chatgpt.com/plugins) → \"+\".",
        "gpt_3": "Paste the URL above.",
        "gpt_note": "Requires Plus/Pro/Business — custom connectors are not "
                    "available on the free tier.",
        "gem_1": "Open gemini.google.com/apps.",
        "gem_2": "At the bottom, add a custom app link — paste the URL above.",
        "gem_note": "MCP support in Gemini is rolling out gradually.",
        "first_ask_title": "Your first question",
        "first_ask_body": "Just type your birth data in the chat — the "
                          "service proposes the reading order itself.",
        "first_ask_example": "Compute my chart: 1 July 1977, 22:30, Zaporizhzhia",
        "first_ask_note": "From there ask freely: money, vocation, the decade "
                          "ahead, cities, the best day for a conversation — "
                          "or describe a dream.",
        "troubleshoot_title": "If something goes wrong",
        "trouble_401": "the connector needs sign-in — complete it in the chat window.",
        "trouble_slow_h": "First response is slow",
        "trouble_slow_b": "the server wakes from idle; just ask again.",
        "trouble_free_h": "No button in ChatGPT",
        "trouble_free_b": "enable Developer mode; custom connectors are not "
                          "available on the free plan.",
        "pricing_title": "Pricing",
        "pricing_lede": "You pay for access, not per question.",
        "pricing_col_plan": "Plan", "pricing_col_included": "Included",
        "pricing_col_price": "Price",
        "pricing_note": "Plans will be finalised before public launch. "
                        "Payment and subscription management live in your account.",
        "pricing_how_title": "How it works",
        "pricing_how_body": "You register here and subscribe. The same account "
                            "opens the connector in your chat — connecting is "
                            "just signing in.",
        "legal_updated": "Updated",
        "legal_draft_notice": "Draft for review. This text must be checked by "
                              "a lawyer before public launch.",
        "privacy_title": "Privacy policy",
        "terms_title": "Terms of use",
    },
}

PLANS: dict[str, list[dict[str, str]]] = {
    "ru": [
        {"name": "Знакомство", "price": "бесплатно",
         "included": "Лунный день, натальная карта, анализ сна — с дневным лимитом."},
        {"name": "Полный", "price": "уточняется",
         "included": "Все разборы: деньги, призвание, декада, лента переломов, "
                     "астрокартография, солярар, элективы, отчёты PDF."},
    ],
    "en": [
        {"name": "Starter", "price": "free",
         "included": "Lunar day, natal chart, dream analysis — with a daily cap."},
        {"name": "Full", "price": "TBA",
         "included": "Every analysis: money, vocation, the decade map, life "
                     "pivots, astrocartography, solar return, electional days, "
                     "PDF reports."},
    ],
}


def _locale(request: Request) -> str:
    """Pick a language: ?lang= wins, else the browser's Accept-Language."""
    q = (request.query_params.get("lang") or "").lower()
    if q in CONTENT:
        return q
    header = (request.headers.get("accept-language") or "").lower()
    return "ru" if header.startswith("ru") else "en"


def _mcp_url(request: Request) -> str:
    """Public MCP endpoint shown for copy-paste.

    A configured value always wins, and outside development it is the *only*
    source: `request.base_url` comes from the Host header, so deriving a
    copy-paste connector URL from it would let a forged header decide which
    server a visitor is told to connect to. In development the derived form is
    kept — it makes the page useful with no config — and forced to https,
    because behind a TLS-terminating proxy the app sees plain http and an http
    connector URL is silently rejected by the chat clients.
    """
    if settings.MCP_PUBLIC_URL:
        return settings.MCP_PUBLIC_URL.rstrip("/")

    if settings.ENVIRONMENT != "development":
        # Nothing trustworthy to build an absolute URL from.
        return settings.MCP_PATH

    return str(request.base_url).rstrip("/") + settings.MCP_PATH


def _ctx(request: Request, **extra: Any) -> dict[str, Any]:
    loc = _locale(request)
    t = CONTENT[loc]
    return {
        "request": request,
        "locale": loc,
        "t": t,
        "app_name": settings.APP_NAME,
        "tagline": t["hero_lede"],
        "disclaimer": DISCLAIMER_RU if loc == "ru" else DISCLAIMER_EN,
        **extra,
    }


def _tracks(locale: str) -> list[dict[str, Any]]:
    """Group the orchestrator's stages for display, preserving reading order."""
    grouped: dict[str, list[dict[str, str]]] = {}
    for stage in sorted(STAGES, key=lambda s: s.order):
        grouped.setdefault(stage.track, []).append({
            "name": stage.name_ru if locale == "ru" else stage.name_en,
            "answers": stage.answers_ru if locale == "ru" else stage.answers_en,
        })
    return [
        {"name": TRACK_NAMES[track][locale], "stages": stages}
        for track, stages in grouped.items()
    ]


@router.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    loc = _locale(request)
    return templates.TemplateResponse(
        request, "index.html", _ctx(request, tracks=_tracks(loc))
    )


@router.get("/connect", response_class=HTMLResponse)
async def connect(request: Request):
    return templates.TemplateResponse(
        request, "connect.html", _ctx(request, mcp_url=_mcp_url(request))
    )


@router.get("/pricing", response_class=HTMLResponse)
async def pricing(request: Request):
    loc = _locale(request)
    return templates.TemplateResponse(
        request, "pricing.html", _ctx(request, plans=PLANS[loc])
    )


# --- Legal ---------------------------------------------------------------
# Required for the connector directories. Written from what the code actually
# does: birth data is passed per call and not persisted by the tools, face
# photos are self-only, interpretations are reflective content.

def _privacy_sections(loc: str) -> list[dict[str, Any]]:
    if loc == "ru":
        return [
            {"h": "Какие данные обрабатываются", "p": [
                "Для расчётов вы передаёте данные рождения (дата, время, место) "
                "и, по желанию, текст сна или свои фотографии. Эти данные "
                "передаются в запросе, используются для ответа и не сохраняются "
                "инструментами расчёта."],
             "list": [
                "Аккаунт: адрес электронной почты и статус подписки.",
                "Технические журналы: факт обращения, время, код ответа.",
                "Содержимое запросов не используется для обучения моделей."]},
            {"h": "Кому передаются данные", "p": [
                "Текстовые интерпретации формируются внешними провайдерами "
                "языковых моделей. Геокодирование городов выполняется внешним "
                "сервисом. Платежи обрабатывает платёжный провайдер; данные "
                "карты к нам не попадают."]},
            {"h": "Фотографии лица", "p": [
                "Анализ лица предназначен только для собственных фотографий "
                "пользователя. Анализ третьих лиц не выполняется. Фотографии "
                "обрабатываются для получения метрик и не публикуются."]},
            {"h": "Ваши права", "p": [
                "Вы можете запросить удаление аккаунта и связанных данных, "
                "а также выгрузку того, что о вас хранится. Для этого напишите "
                "на контактный адрес, указанный в условиях использования."]},
        ]
    return [
        {"h": "What data is processed", "p": [
            "To compute a reading you supply birth data (date, time, place) "
            "and optionally a dream text or your own photos. That data travels "
            "with the request, is used to produce the answer, and is not "
            "persisted by the computation tools."],
         "list": [
            "Account: email address and subscription status.",
            "Technical logs: that a request happened, when, and its status.",
            "Request content is not used to train models."]},
        {"h": "Who data is shared with", "p": [
            "Text interpretations are produced by external language-model "
            "providers. City geocoding uses an external service. Payments are "
            "handled by a payment provider; card details never reach us."]},
        {"h": "Face photographs", "p": [
            "Face analysis is for your own photographs only. Third parties are "
            "not analysed. Photos are processed to derive metrics and are not "
            "published."]},
        {"h": "Your rights", "p": [
            "You may request deletion of your account and associated data, and "
            "an export of what is held about you, via the contact address in "
            "the terms of use."]},
    ]


def _terms_sections(loc: str) -> list[dict[str, Any]]:
    if loc == "ru":
        return [
            {"h": "Что это за сервис", "p": [
                "Сервис выполняет астрономические расчёты и предлагает "
                "интерпретации в традициях астрологии, анализа сновидений и "
                "физиогномики. Доступ предоставляется через коннектор в "
                "чат-приложениях."]},
            {"h": "Характер материалов", "p": [
                "Все интерпретации носят рефлексивно-развлекательный характер. "
                "Это не медицинская, психологическая, юридическая или "
                "финансовая консультация. Сервис не даёт предсказаний и не "
                "гарантирует наступления событий. Решения вы принимаете сами."],
             "list": [
                "Физиогномика — историческая традиция; научной валидности не имеет.",
                "Анализ лица допустим только для собственных фотографий."]},
            {"h": "Использование", "p": [
                "Не используйте сервис для оценки третьих лиц без их ведома, "
                "для принятия решений о людях (найм, кредит и подобное) и для "
                "любых целей, запрещённых законом."]},
            {"h": "Оплата и отказ", "p": [
                "Подписка оформляется и отменяется в личном кабинете. "
                "Доступность сервиса может прерываться на обслуживание."]},
            {"h": "Контакты", "p": [
                "Контактный адрес будет указан здесь до публичного запуска."]},
        ]
    return [
        {"h": "What this service is", "p": [
            "The service performs astronomical computations and offers "
            "interpretations in the traditions of astrology, dream analysis "
            "and physiognomy. Access is provided through a connector inside "
            "chat applications."]},
        {"h": "Nature of the material", "p": [
            "All interpretations are reflective / entertainment content. They "
            "are not medical, psychological, legal or financial advice. The "
            "service offers no predictions and guarantees no outcomes. "
            "Decisions remain yours."],
         "list": [
            "Physiognomy is a historical tradition with no scientific validity.",
            "Face analysis is permitted for your own photographs only."]},
        {"h": "Acceptable use", "p": [
            "Do not use the service to assess third parties without their "
            "knowledge, to make decisions about people (hiring, credit and the "
            "like), or for any purpose prohibited by law."]},
        {"h": "Payment and cancellation", "p": [
            "Subscriptions are managed in your account. Availability may be "
            "interrupted for maintenance."]},
        {"h": "Contact", "p": [
            "A contact address will be published here before public launch."]},
    ]


@router.get("/privacy", response_class=HTMLResponse)
async def privacy(request: Request):
    loc = _locale(request)
    return templates.TemplateResponse(request, "legal.html", _ctx(
        request,
        page_title=CONTENT[loc]["privacy_title"],
        sections=_privacy_sections(loc),
        updated=date.today().isoformat(),
        draft=True,
    ))


@router.get("/terms", response_class=HTMLResponse)
async def terms(request: Request):
    loc = _locale(request)
    return templates.TemplateResponse(request, "legal.html", _ctx(
        request,
        page_title=CONTENT[loc]["terms_title"],
        sections=_terms_sections(loc),
        updated=date.today().isoformat(),
        draft=True,
    ))
