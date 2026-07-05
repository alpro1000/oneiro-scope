"""Self-contained HTML report for a horoscope.

Two-layer structure per owner feedback (2026-07-05): the FULL narrative
first (summary + per-sphere texts — already long-form from the
interpretation layer), then compact takeaways for memorization, then
the astronomical data (transits, retrogrades, lunar context) with
provenance, then the disclaimer.
"""

from __future__ import annotations

from html import escape

from backend.services.astrology.report import DISCLAIMER_EN, DISCLAIMER_RU
from backend.services.astrology.schemas import HoroscopeResponse

_PERIOD_RU = {"daily": "на день", "weekly": "на неделю",
              "monthly": "на месяц", "yearly": "на год"}


def render_horoscope_html(resp: HoroscopeResponse, *, locale: str = "ru") -> str:
    ru = locale != "en"
    period = resp.period.value if hasattr(resp.period, "value") else str(resp.period)
    t = {
        "title": (f"Гороскоп {_PERIOD_RU.get(period, period)}" if ru
                  else f"{period.title()} horoscope"),
        "narrative": "Полный разбор" if ru else "Full reading",
        "love": "Любовь и отношения" if ru else "Love & relationships",
        "career": "Карьера и финансы" if ru else "Career & finance",
        "health": "Самочувствие" if ru else "Health & wellness",
        "theses": "Тезисы для запоминания" if ru else "Key takeaways",
        "sky": "Астрономический контекст (достоверность 1.0)" if ru
               else "Astronomical context (confidence 1.0)",
        "transits": "Транзиты" if ru else "Transits",
        "retro": "Ретроградные" if ru else "Retrograde",
        "lunar": "Луна" if ru else "Moon",
    }

    def block(title: str, text: str | None) -> str:
        if not text:
            return ""
        paras = "".join(f"<p>{escape(x)}</p>" for x in text.split("\n") if x.strip())
        return f"<h3>{escape(title)}</h3>{paras}"

    narrative = (
        f"<h2>{t['narrative']}</h2>"
        + "".join(f"<p>{escape(x)}</p>" for x in resp.summary.split("\n") if x.strip())
        + block(t["love"], resp.love_and_relationships)
        + block(t["career"], resp.career_and_finance)
        + block(t["health"], resp.health_and_wellness)
    )

    theses = ""
    if resp.recommendations:
        items = "".join(f"<li>{escape(r)}</li>" for r in resp.recommendations)
        theses = f"<h2>{t['theses']}</h2><div class='pill'><ul>{items}</ul></div>"

    def _v(x) -> str:
        return x.value if hasattr(x, "value") else str(x)

    transit_rows = "".join(
        f"<tr><td>{escape(_v(tr.transiting_planet))} {escape(_v(tr.aspect))} "
        f"{escape(_v(tr.natal_planet))}</td>"
        f"<td>{escape(str(tr.exact_date))}</td><td>{tr.orb}°</td></tr>"
        for tr in resp.transits[:12]
    )
    retro = ", ".join(
        p.value if hasattr(p, "value") else str(p) for p in resp.retrograde_planets
    ) or ("нет" if ru else "none")
    lunar = f"{resp.lunar_phase_display or resp.lunar_phase} · {resp.lunar_day}"
    sky = (
        f"<h2>{t['sky']}</h2>"
        f"<div class='pill'><b>{t['lunar']}:</b> {escape(lunar)} · "
        f"<b>{t['retro']}:</b> {escape(retro)}</div>"
        + (f"<h3>{t['transits']}</h3><table>{transit_rows}</table>" if transit_rows else "")
    )

    prov = ""
    if resp.provenance:
        prov = f"<div class='sub'>{escape(str(resp.provenance.model_dump()))}</div>"

    dates = f"{resp.period_start} — {resp.period_end}"
    return f"""<!DOCTYPE html><html lang="{'ru' if ru else 'en'}"><head>
<meta charset="utf-8"><title>{t['title']}</title><style>
@page {{ size: A4; margin: 15mm; }}
body {{ font-family: 'DejaVu Sans', Arial, sans-serif; color: #1f2430;
       font-size: 11px; line-height: 1.55; }}
h1 {{ font-size: 20px; color: #3a2f6b; margin: 0 0 4px; }}
h2 {{ font-size: 14px; color: #5b8def; border-bottom: 2px solid #e6e9f5;
     padding-bottom: 3px; margin: 16px 0 8px; }}
h3 {{ font-size: 12px; color: #3a2f6b; margin: 10px 0 3px; }}
table {{ width: 100%; border-collapse: collapse; margin: 6px 0; }}
td {{ border: 1px solid #dfe3f0; padding: 3px 6px; }}
.pill {{ background: #eef0fb; border-radius: 8px; padding: 8px 10px;
        margin: 5px 0; }}
.sub {{ font-size: 9px; color: #8a8fa8; }}
.disc {{ font-size: 9px; color: #8a8fa8; border-top: 1px solid #e6e9f5;
        padding-top: 8px; margin-top: 14px; }}
ul {{ margin: 4px 0; padding-left: 18px; }}
p {{ margin: 6px 0; }}
</style></head><body>
<h1>✨ {t['title']}</h1>
<div class="sub">{escape(dates)}</div>
{narrative}
{theses}
{sky}
{prov}
<div class="disc">{DISCLAIMER_RU if ru else DISCLAIMER_EN}</div>
</body></html>"""
