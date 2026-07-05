"""Self-contained HTML report for a physiognomy reading.

Print-to-PDF-ready, no external assets — same delivery pattern as
`astrology/report.py`. Zone-structured: metrics → elements → courts →
readings grouped by system, each with its source, then the disclaimer.
"""

from __future__ import annotations

from html import escape

from backend.services.physiognomy.schemas import PhysiognomyResponse

_SYSTEM_LABELS = {
    "ru": {
        "mianxiang": "Мянсян (китайское чтение лица)",
        "lavater": "Лафатер — три этажа",
        "corman": "Морфопсихология Кормана",
        "kretschmer": "Конституция Кречмера",
        "fwhr": "fWHR (современная литература)",
    },
    "en": {
        "mianxiang": "Mianxiang (Chinese face reading)",
        "lavater": "Lavater — three storeys",
        "corman": "Corman morphopsychology",
        "kretschmer": "Kretschmer constitution",
        "fwhr": "fWHR (modern literature)",
    },
}

_ELEMENT_RU = {"wood": "Дерево", "fire": "Огонь", "earth": "Земля",
               "metal": "Металл", "water": "Вода"}
_COURT_RU = {"upper": "верхний (лоб)", "middle": "средний (глаза-нос)",
             "lower": "нижний (рот-подбородок)"}


def render_html(resp: PhysiognomyResponse, *, locale: str = "ru") -> str:
    ru = locale != "en"
    t = {
        "title": "Физиогномический отчёт" if ru else "Physiognomy report",
        "metrics": "Измерения (геометрия, достоверность 1.0)" if ru
                   else "Measurements (geometry, confidence 1.0)",
        "elements": "Пять элементов" if ru else "Five elements",
        "court": "Доминирующий двор" if ru else "Dominant court",
        "readings": "Чтения традиций (достоверность 0.6)" if ru
                    else "Tradition readings (confidence 0.6)",
        "source": "источник" if ru else "source",
        "primary": "первичный" if ru else "primary",
        "secondary": "вторичный" if ru else "secondary",
    }

    metrics_html = ""
    if resp.metrics:
        rows = "".join(
            f"<tr><td>{escape(k)}</td><td>{v}</td></tr>"
            for k, v in resp.metrics.model_dump().items() if v is not None
        )
        prov = escape(resp.metrics_provenance or "")
        metrics_html = (
            f"<h2>{t['metrics']}</h2><table>{rows}</table>"
            f"<div class='sub'>{prov}</div>"
        )

    elements_html = ""
    if resp.element_scores and resp.primary_element and resp.secondary_element:
        def el(name: str) -> str:
            return _ELEMENT_RU.get(name, name) if ru else name.title()
        bars = "".join(
            f"<tr><td>{el(e.element)}</td><td>{e.score}</td></tr>"
            for e in resp.element_scores
        )
        elements_html = (
            f"<h2>{t['elements']}</h2>"
            f"<div class='pill'><b>{t['primary']}:</b> {el(resp.primary_element)}"
            f" · <b>{t['secondary']}:</b> {el(resp.secondary_element)}</div>"
            f"<table>{bars}</table>"
        )
        if resp.dominant_court:
            court = (_COURT_RU.get(resp.dominant_court, resp.dominant_court)
                     if ru else resp.dominant_court)
            elements_html += f"<div class='pill'><b>{t['court']}:</b> {court}</div>"

    labels = _SYSTEM_LABELS["ru" if ru else "en"]
    by_system: dict[str, list] = {}
    for r in resp.readings:
        by_system.setdefault(r.system, []).append(r)
    readings_html = f"<h2>{t['readings']}</h2>"
    for system, items in by_system.items():
        readings_html += f"<h3>{escape(labels.get(system, system))}</h3>"
        for r in items:
            readings_html += (
                f"<div class='pill'>{escape(r.text)}<br>"
                f"<span class='sub'>{t['source']}: {escape(r.source)}"
                f" · {r.confidence}</span></div>"
            )

    return f"""<!DOCTYPE html><html lang="{'ru' if ru else 'en'}"><head>
<meta charset="utf-8"><title>{t['title']}</title><style>
@page {{ size: A4; margin: 15mm; }}
body {{ font-family: 'DejaVu Sans', Arial, sans-serif; color: #1f2430;
       font-size: 11px; line-height: 1.5; }}
h1 {{ font-size: 20px; color: #3a2f6b; margin: 0 0 4px; }}
h2 {{ font-size: 14px; color: #5b8def; border-bottom: 2px solid #e6e9f5;
     padding-bottom: 3px; margin: 16px 0 8px; }}
h3 {{ font-size: 12px; color: #3a2f6b; margin: 10px 0 3px; }}
table {{ width: 100%; border-collapse: collapse; margin: 6px 0; }}
td {{ border: 1px solid #dfe3f0; padding: 3px 6px; }}
.pill {{ background: #eef0fb; border-radius: 8px; padding: 8px 10px;
        margin: 5px 0; }}
.sub {{ font-size: 9.5px; color: #8a8fa8; }}
.disc {{ font-size: 9px; color: #8a8fa8; border-top: 1px solid #e6e9f5;
        padding-top: 8px; margin-top: 14px; }}
</style></head><body>
<h1>🀄 {t['title']}</h1>
{metrics_html}
{elements_html}
{readings_html}
<div class="disc">{escape(resp.disclaimer)}</div>
</body></html>"""
