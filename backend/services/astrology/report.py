"""Profile report builder — the artifact users actually share.

Session testing showed the end deliverable is always the same bundle:
natal snapshot → birth city read → current city read → thematic city
shortlist → a year of slow transits by month. This module assembles
that bundle deterministically as JSON and renders a self-contained
HTML document (print-to-PDF ready) with no extra dependencies.

All astronomy comes from the existing engines; interpretation stays at
the labels/buckets level (symbol tier). Every report carries the
project disclaimer.
"""

from __future__ import annotations

from datetime import date as date_cls, timedelta
from html import escape
from typing import Optional

try:
    import swisseph as swe
except ImportError as exc:  # pragma: no cover
    raise ImportError("pyswisseph is required for reports") from exc

from backend.services.astrology.astrocartography import (
    compare_locations,
    theme_scan,
)
from backend.services.astrology.historic_tz import BirthMoment
from backend.services.astrology.transits_engine import find_transits

from backend.core.ephemeris import FLAGS as _FLAGS, EPHEMERIS_VERSION

_BODIES = {
    "Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY,
    "Venus": swe.VENUS, "Mars": swe.MARS, "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN, "Uranus": swe.URANUS, "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO,
}

_SIGNS_RU = [
    "Овен", "Телец", "Близнецы", "Рак", "Лев", "Дева",
    "Весы", "Скорпион", "Стрелец", "Козерог", "Водолей", "Рыбы",
]
_SIGNS_EN = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

DISCLAIMER_RU = (
    "Рефлексивно-развлекательный характер. Астрономия — Swiss Ephemeris "
    "(достоверность 1.0); тематические оценки — правила классической "
    "традиции (0.8). Не предсказание; не медицинский, психологический, "
    "юридический или финансовый совет. Результат зависит от точности "
    "времени рождения."
)
DISCLAIMER_EN = (
    "Reflective / entertainment content. Astronomy — Swiss Ephemeris "
    "(confidence 1.0); thematic labels — classical rule-set (0.8). Not a "
    "prediction; not medical, psychological, legal or financial advice. "
    "Results depend on birth-time accuracy."
)

# Default candidate pool for the thematic shortlist — the cities that
# came up across session tests. Callers can pass their own list.
DEFAULT_CITIES: list[tuple[str, float, float]] = [
    ("London", 51.51, -0.13), ("Dublin", 53.35, -6.26),
    ("Paris", 48.86, 2.35), ("Barcelona", 41.39, 2.17),
    ("Madrid", 40.42, -3.70), ("Lisbon", 38.72, -9.14),
    ("Rome", 41.90, 12.50), ("Milan", 45.46, 9.19),
    ("Vienna", 48.21, 16.37), ("Prague", 50.08, 14.44),
    ("Brno", 49.20, 16.61), ("Warsaw", 52.23, 21.01),
    ("Krakow", 50.06, 19.94), ("Budapest", 47.50, 19.04),
    ("Berlin", 52.52, 13.40), ("Munich", 48.14, 11.58),
    ("Zurich", 47.37, 8.54), ("Belgrade", 44.79, 20.45),
    ("Sofia", 42.70, 23.32), ("Zagreb", 45.81, 15.98),
    ("Athens", 37.98, 23.73), ("Tbilisi", 41.72, 44.79),
    ("Yerevan", 40.18, 44.51), ("Dubai", 25.20, 55.27),
    ("Tel Aviv", 32.08, 34.78), ("Stockholm", 59.33, 18.07),
    ("New York", 40.71, -74.01), ("Miami", 25.76, -80.19),
    ("Los Angeles", 34.05, -118.24), ("Mexico City", 19.43, -99.13),
    ("Buenos Aires", -34.60, -58.38), ("Cape Town", -33.92, 18.42),
    ("Bangkok", 13.76, 100.50), ("Bali", -8.41, 115.19),
    ("Tokyo", 35.68, 139.69), ("Sydney", -33.87, 151.21),
]

_THEMES = ("luck", "career", "relationships", "home")
_THEME_RU = {
    "luck": "Удача", "career": "Карьера",
    "relationships": "Отношения", "home": "Дом и уют",
}


def _fmt_sign(lon: float, locale: str) -> str:
    signs = _SIGNS_RU if locale == "ru" else _SIGNS_EN
    s = int(lon // 30) % 12
    d = lon % 30
    return f"{int(d)}°{int((d - int(d)) * 60):02d}' {signs[s]}"


def build_report(
    moment: BirthMoment,
    *,
    birth_place: tuple[str, float, float],
    current_place: Optional[tuple[str, float, float]] = None,
    year_start: Optional[date_cls] = None,
    cities: Optional[list[tuple[str, float, float]]] = None,
    locale: str = "ru",
) -> dict:
    """Assemble the full profile report as a JSON-ready dict."""
    jd = moment.jd_ut
    pool = cities or DEFAULT_CITIES
    start = year_start or date_cls.today()
    end = start + timedelta(days=365)

    natal = {
        name: {
            "longitude": round(swe.calc_ut(jd, code, _FLAGS)[0][0], 4),
            "position": _fmt_sign(swe.calc_ut(jd, code, _FLAGS)[0][0], locale),
            "retrograde": swe.calc_ut(jd, code, _FLAGS)[0][3] < 0,
        }
        for name, code in _BODIES.items()
    }
    cusps, ascmc = swe.houses(jd, birth_place[1], birth_place[2], b"P")
    natal["ASC"] = {
        "longitude": round(ascmc[0], 4),
        "position": _fmt_sign(ascmc[0], locale),
        "retrograde": False,
    }
    natal["MC"] = {
        "longitude": round(ascmc[1], 4),
        "position": _fmt_sign(ascmc[1], locale),
        "retrograde": False,
    }

    places = [birth_place] + ([current_place] if current_place else [])
    relocations = compare_locations(jd, places, locale=locale)

    themes = {
        theme: theme_scan(jd, pool, theme, top_n=6) for theme in _THEMES
    }

    slow = {"Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"}
    events = [
        {
            "date": e.exact_date,
            "transiting": e.transiting,
            "aspect": e.aspect,
            "natal": e.natal,
            "harmonious": e.aspect in ("conjunction", "trine", "sextile"),
        }
        for e in find_transits(jd, start, end, orb_deg=1.0)
        if e.transiting in slow
    ]

    return {
        "birth": {
            "utc": moment.utc_iso,
            "timezone": moment.timezone_name,
            "utc_offset_hours": moment.utc_offset_hours,
            "tz_source": moment.source,
            "pre_1970": moment.pre_1970,
            "place": birth_place[0],
        },
        "natal": natal,
        "relocations": relocations,
        "themes": themes,
        "year_transits": events,
        "provenance": {
            "astronomy": EPHEMERIS_VERSION,
            "method": "Astro*Carto*Graphy (Lewis 1976); Placidus houses",
            "confidence": {"astronomy": 1.0, "labels": 0.8},
        },
        "disclaimer": DISCLAIMER_RU if locale == "ru" else DISCLAIMER_EN,
    }


def render_html(report: dict, *, locale: str = "ru") -> str:
    """Render the report dict as a self-contained printable HTML page."""
    ru = locale == "ru"
    t = {
        "title": "Астрологический профиль" if ru else "Astrology profile",
        "natal": "Натальная карта" if ru else "Natal chart",
        "reloc": "Города: углы и резюме" if ru else "Places: angles & summary",
        "themes": "Города по темам" if ru else "Cities by theme",
        "year": "Год: медленные транзиты" if ru else "Year: slow transits",
        "clean": "чисто" if ru else "clean",
        "mixed": "с минусом" if ru else "mixed",
        "glossary_title": "Как читать этот отчёт" if ru else "How to read this report",
    }
    b = report["birth"]

    glossary_html = (
        """<div class="pill">
<b>ASC</b> — как ты проявляешься, первое впечатление · <b>MC</b> — карьера, статус ·
<b>DESC</b> — партнёрства, союзы · <b>IC</b> — дом, тыл, семья.<br>
Конъюнкция/трин/секстиль — планета работает мягко и заодно с этой сферой; квадратура/оппозиция —
трение, требующее внимания, не запрет. Чем меньше орб (°), тем точнее и сильнее контакт.<br>
✅ чисто = рядом на углах нет Марса/Сатурна/Плутона; ⚠️ с минусом = есть, вместе с плюсом идёт и трение.<br>
Общий балл считает только Венеру/Юпитер/Солнце/Луну (плюс) и Сатурн/Марс/Плутон (минус) — Меркурий,
Уран и Нептун в него не входят, даже если стоят точно на углу (у них просто нет общепринятого
классического «плюс/минус»). Поэтому рядом всегда показана «загруженность углов» — сумма ВСЕХ
контактов без деления на плюс/минус; город может быть тихим по баллу, но шумным по загруженности —
и у каждого города ниже расписаны ВСЕ найденные контакты, а не только те, что видит балл.</div>"""
        if ru else
        """<div class="pill">
<b>ASC</b> — how you come across · <b>MC</b> — career, status ·
<b>DESC</b> — partnerships · <b>IC</b> — home, roots, family.<br>
Conjunction/trine/sextile = the planet works smoothly with that area; square/opposition = friction
worth noting, not a verdict. Smaller orb (°) = tighter, stronger contact.<br>
✅ clean = no Mars/Saturn/Pluto on any angle nearby; ⚠️ mixed = there is one alongside the plus.<br>
The composite score only counts Venus/Jupiter/Sun/Moon (+) and Saturn/Mars/Pluto (−) — Mercury,
Uranus and Neptune are NOT counted even when exactly on an angle (they have no agreed classical
+/- valence). That's why an "angle load" number is always shown alongside — the unsigned sum of
ALL contacts — so a place can be quiet by score but loud by load; every city below also lists ALL
found contacts, not just the ones the score can see.</div>"""
    )

    def row(cells: list[str], tag: str = "td") -> str:
        return "<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>"

    natal_rows = "".join(
        row([escape(k), escape(v["position"]), "R" if v["retrograde"] else ""])
        for k, v in report["natal"].items()
    )

    _TAG_ICON = {"benefic": "🟢", "challenging": "🔴", "neutral": "⚪"}
    reloc_blocks = ""
    for r in report["relocations"]:
        s = r["summary"]
        full = r.get("full_breakdown", [])
        breakdown_rows = "".join(
            row([
                _TAG_ICON.get(h["tag"], ""),
                f"{h['planet']}→{h['angle']}",
                f"{h['orb_deg']:.2f}°",
                escape(h["description"]),
            ])
            for h in full
        ) or row(["—", "—", "—", "нет контактов в пределах орба" if ru else "no contacts within orb"])
        score_expl = r.get("score_explanation", {})
        score_note = score_expl.get("plain", "")
        sig = score_expl.get("total_significance")
        sig_label = (
            f" · загруженность углов (все планеты) {sig}" if ru else f" · angle load (all planets) {sig}"
        ) if sig is not None else ""
        reloc_blocks += (
            f"<div class='pill'><b>{escape(r['name'])}</b> · score "
            f"{r['score']:+.1f}{sig_label} — <i>{escape(score_note)}</i><br>"
            f"<i>{escape(s['plain'])}</i>"
            f"<table>{breakdown_rows}</table></div>"
        )

    theme_blocks = ""
    for theme, rows_ in report["themes"].items():
        label = _THEME_RU[theme] if ru else theme.title()
        items = "".join(
            row([
                escape(c["name"]),
                f"{c['score']:+.1f}",
                t["clean"] if c["clean"] else t["mixed"],
                ", ".join(
                    f"{m['planet']}→{m['angle']} {m['orb_deg']}°"
                    for m in c["matches"][:3]
                ),
            ])
            for c in rows_
        )
        theme_blocks += (
            f"<h3>{escape(label)}</h3><table>"
            + row(["", "score", "", ""], "th") + items + "</table>"
        )

    year_rows = "".join(
        row([
            e["date"], "🟢" if e["harmonious"] else "🔴",
            f"{e['transiting']} {e['aspect']} {e['natal']}",
        ])
        for e in report["year_transits"]
    )

    return f"""<!DOCTYPE html><html lang="{locale}"><head><meta charset="utf-8">
<title>{t['title']}</title><style>
@page {{ size: A4; margin: 15mm; }}
body {{ font-family: 'DejaVu Sans', Arial, sans-serif; color: #1f2430;
       font-size: 11px; line-height: 1.5; }}
h1 {{ font-size: 20px; color: #3a2f6b; margin: 0 0 4px; }}
h2 {{ font-size: 14px; color: #5b8def; border-bottom: 2px solid #e6e9f5;
     padding-bottom: 3px; margin: 16px 0 8px; }}
h3 {{ font-size: 12px; color: #3a2f6b; margin: 10px 0 3px; }}
table {{ width: 100%; border-collapse: collapse; margin: 6px 0; }}
th, td {{ border: 1px solid #dfe3f0; padding: 3px 6px; text-align: left; }}
th {{ background: #f0f2fb; }}
.pill {{ background: #eef0fb; border-radius: 8px; padding: 8px 10px;
        margin: 5px 0; }}
.disc {{ font-size: 9px; color: #8a8fa8; border-top: 1px solid #e6e9f5;
        padding-top: 8px; margin-top: 14px; }}
</style></head><body>
<h1>🌍 {t['title']}</h1>
<div>{escape(b['place'])} · {escape(b['utc'])} UTC
 · tz {escape(b['timezone'])} ({b['utc_offset_hours']:+.1f}h,
 {escape(b['tz_source'])})</div>
<h2>{t['glossary_title']}</h2>{glossary_html}
<h2>{t['natal']}</h2><table>{natal_rows}</table>
<h2>{t['reloc']}</h2>{reloc_blocks}
<h2>{t['themes']}</h2>{theme_blocks}
<h2>{t['year']}</h2><table>{year_rows}</table>
<div class="disc">{escape(report['disclaimer'])}</div>
</body></html>"""
