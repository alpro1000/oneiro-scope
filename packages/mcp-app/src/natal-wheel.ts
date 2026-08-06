/**
 * Natal wheel — an MCP App view for `calculate_natal_chart`.
 *
 * The host hands us the tool result; everything drawn is derived from its
 * `chart_core` by chart-kit, locally. No network call, no ephemeris, no
 * second implementation of any formula — the same package the web screens
 * use, which is what keeps the chat and the site from drifting apart.
 *
 * The mandatory data rules from the design system are the point of this view,
 * not decoration on it: degrees WITH arcminutes, aspects with orb and
 * applying/separating, borderline placements flagged rather than asserted,
 * the timezone and the historical offset that was actually applied, and a
 * provenance strip. A wheel without those is a styling clone of a competitor.
 */

import {
  aspects as kitAspects,
  houseCusps,
  houseOf,
  resolveSystemFor,
  sep180,
  wheelLayout,
  wheelSvg,
  type ChartCore,
} from '@oneiroscope/chart-kit';
import type { ToolResult } from './bridge';
import { ASK_LABEL, askButton, esc, fromResult, mountView, type Lang } from './view';

const SIGN_GLYPH = ['♈', '♉', '♊', '♋', '♌', '♍', '♎', '♏', '♐', '♑', '♒', '♓'];
const P_GLYPH: Record<string, string> = {
  Sun: '☉', Moon: '☽', Mercury: '☿', Venus: '♀', Mars: '♂', Jupiter: '♃',
  Saturn: '♄', Uranus: '♅', Neptune: '♆', Pluto: '♇', TrueNode: '☊', Chiron: '⚷',
};

const COPY = {
  ru: {
    positions: 'Положения',
    aspects: 'Аспекты',
    birth: 'Момент рождения',
    provenance: 'Происхождение',
    house: 'дом',
    retro: 'R',
    borderline: 'на границе дома',
    applying: 'сходящийся',
    separating: 'расходящийся',
    orb: 'орб',
    noTime: 'Время рождения не указано — дома, Асцендент и MC не определены и не показаны. Положения планет посчитаны на полдень.',
    waiting: 'Ожидание карты от сервера…',
    empty: 'Нет данных карты. Вызовите calculate_natal_chart.',
    engine: 'движок',
    houses: 'дома',
    tz: 'пояс',
    utc: 'UTC',
    askPlacement: 'Объясни это положение в натальной карте',
    askAspect: 'Объясни этот аспект в натальной карте',
    askAll: 'Прочитай эту карту целиком: характер, сильные стороны, зоны роста',
    askHint: 'Нажмите «объяснить» у любой строки — вопрос уйдёт в чат вместе с точными числами.',
    disclaimerLead: 'Геометрия проверяема.',
    disclaimer: 'Значения знаков, домов и аспектов — традиция толкования, не прогноз. Рефлексивно-развлекательный материал, не медицинский, психологический, юридический или финансовый совет.',
  },
  en: {
    positions: 'Positions',
    aspects: 'Aspects',
    birth: 'Birth moment',
    provenance: 'Provenance',
    house: 'house',
    retro: 'R',
    borderline: 'on a house cusp',
    applying: 'applying',
    separating: 'separating',
    orb: 'orb',
    noTime: 'No birth time given — houses, Ascendant and MC are undefined and not shown. Planet positions are computed for noon.',
    waiting: 'Waiting for the chart…',
    empty: 'No chart data. Call calculate_natal_chart.',
    engine: 'engine',
    houses: 'houses',
    tz: 'zone',
    utc: 'UTC',
    askPlacement: 'Explain this placement in the natal chart',
    askAspect: 'Explain this aspect in the natal chart',
    askAll: 'Read this chart as a whole: character, strengths, growth areas',
    askHint: 'Press "explain" on any row — the question goes to the chat with the exact figures.',
    disclaimerLead: 'The geometry is verifiable.',
    disclaimer: 'What a sign, house or aspect means is a tradition of interpretation, not a prediction. Reflective / entertainment material, not medical, psychological, legal or financial advice.',
  },
} as const;

// ── formatting: every number in the data face, arcminutes always shown ───────
const norm = (a: number) => ((a % 360) + 360) % 360;

function fmtSign(lon: number): string {
  const l = norm(lon);
  const sign = Math.floor(l / 30) % 12;
  const deg = l - Math.floor(l / 30) * 30;
  const d = Math.floor(deg);
  const m = Math.round((deg - d) * 60);
  // 59.7' rounds to 60 — carry it rather than printing 12°60′.
  const [dd, mm] = m === 60 ? [d + 1, 0] : [d, m];
  return `${SIGN_GLYPH[sign]} ${dd}°${String(mm).padStart(2, '0')}′`;
}

/** Orb to hundredths — never rounded in a flattering direction. */
const fmtOrb = (orb: number) => `${orb.toFixed(2)}°`;

interface Payload {
  chart_core?: ChartCore;
  provenance?: Record<string, unknown>;
  meta?: Record<string, unknown>;
}

function pickPayload(result: ToolResult): Payload | null {
  return fromResult<Payload>(result, (c) =>
    (c as Payload).chart_core ? (c as Payload) : null);
}

function render(payload: Payload, lang: Lang): string {
  const t = COPY[lang];
  const core = payload.chart_core!;
  const b = core.birth;
  const timed = b.time_known;

  // Houses only exist with a birth time. Without one the contract forbids
  // drawing angles, so the wheel is still drawn but nothing is placed in a
  // house and the reason is stated rather than silently omitted.
  let cusps: number[] | null = null;
  let system: string | null = null;
  let substituted = false;
  if (timed) {
    try {
      // Placidus and Koch are undefined near the poles; chart-kit substitutes
      // Porphyry and says so, and the provenance strip names what was used —
      // silently drawing a different system is exactly the kind of quiet swap
      // the confidence ladder forbids.
      const resolved = resolveSystemFor(core, b.lat, b.lon);
      system = resolved.system;
      substituted = resolved.substituted;
      cusps = houseCusps(core, b.lat, b.lon, resolved.system);
    } catch {
      cusps = null;
      system = null;
    }
  }

  const borderline = new Set<string>();
  if (cusps) {
    for (const [name, body] of Object.entries(core.bodies)) {
      for (const cusp of cusps) {
        if (Math.abs(sep180(body.ecl_lon, cusp)) < 1) { borderline.add(name); break; }
      }
    }
  }

  // wheelLayout(core, lat, lon, opts) — and it THROWS without a birth time,
  // on purpose: a wheel drawn from noon-derived angles looks exactly as
  // authoritative as a real one. Respect the refusal instead of catching it
  // into an empty box.
  let svg = '';
  if (timed) {
    try {
      svg = wheelSvg(wheelLayout(core, b.lat, b.lon, { size: 620 }));
    } catch {
      svg = '';
    }
  }

  const rows = Object.entries(core.bodies).map(([name, body]) => {
    const house = cusps ? houseOf(body.ecl_lon, cusps) : null;
    const flag = borderline.has(name)
      ? `<span class="flag" title="${t.borderline}">△</span>` : '';
    // The question carries the placement verbatim — sign, exact degree,
    // house, retrograde — so the model reads what the user is pointing at.
    const q = `${t.askPlacement}: ${name} ${fmtSign(body.ecl_lon)}`
      + `${house ? `, ${house} ${t.house}` : ''}${body.retrograde ? ', R' : ''}`
      + `${borderline.has(name) ? `, ${t.borderline}` : ''}.`;
    return `<tr>
      <td class="glyph" style="color:var(--p-${name.toLowerCase()},var(--muted))">${P_GLYPH[name] ?? '·'}</td>
      <td class="body">${esc(name)}</td>
      <td class="num">${fmtSign(body.ecl_lon)}${flag}</td>
      <td class="num dim">${body.retrograde ? t.retro : ''}</td>
      <td class="num dim">${house ? `${house} ${t.house}` : '—'}</td>
      <td class="ask-cell">${askButton(q, ASK_LABEL[lang])}</td>
    </tr>`;
  }).join('');

  // Two lines per aspect rather than four columns. In a 300px instrument panel
  // four columns collide — "orb 6.12°separating" ran together — and the orb is
  // the number the whole row exists for, so it gets its own line with the
  // aspect type and the direction instead of being squeezed.
  const asps = kitAspects(core)
    .slice()
    .sort((x, y) => x.orb - y.orb)
    .map((a) => {
      const q = `${t.askAspect}: ${a.a} ${a.type} ${a.b}, ${t.orb} ${fmtOrb(a.orb)}, `
        + `${a.applying ? t.applying : t.separating}.`;
      return `<div class="asp">
      <div class="asp-pair">${P_GLYPH[a.a] ?? ''} ${esc(a.a)} <span class="dim">—</span> ${P_GLYPH[a.b] ?? ''} ${esc(a.b)}</div>
      <div class="asp-num num">${esc(a.type)} · ${t.orb} ${fmtOrb(a.orb)} · <span class="dim">${a.applying ? t.applying : t.separating}</span></div>
      ${askButton(q, ASK_LABEL[lang])}
    </div>`;
    }).join('');

  const prov = payload.provenance ?? {};
  const meta = payload.meta ?? {};
  const provBits = [
    `<span><b>${t.engine}</b> ${esc(String(prov.ephemeris_engine ?? 'Swiss Ephemeris'))} ${esc(String(prov.ephemeris_version ?? ''))}</span>`,
    system ? `<span><b>${t.houses}</b> ${esc(system)}${substituted ? ' *' : ''}</span>` : '',
    `<span><b>JD_UT</b> ${core.jd_ut}</span>`,
    meta.request_id ? `<span><b>request</b> ${esc(String(meta.request_id))}</span>` : '',
  ].filter(Boolean).join('');

  return `
    <div class="wrap">
      <div class="wheel">${svg}</div>
      <div class="panels">
        <section>
          <div class="eyebrow">${t.birth}</div>
          <div class="kv"><span>${t.utc}</span><b class="num">${esc(b.utc)}</b></div>
          <div class="kv"><span>${t.tz}</span><b class="num">${esc(b.tz_used)} ${esc(b.utc_offset_used)}</b></div>
          <div class="kv"><span>lat / lon</span><b class="num">${b.lat.toFixed(4)}° / ${b.lon.toFixed(4)}°</b></div>
          ${b.place_label ? `<div class="kv"><span>place</span><b>${esc(b.place_label)}</b></div>` : ''}
          ${askButton(
            `${t.askAll}. ${b.place_label || ''} ${esc(b.utc)} (${esc(b.tz_used)} ${esc(b.utc_offset_used)}).`,
            t.askAll, true,
          )}
          <p class="ask-hint">${t.askHint}</p>
        </section>
        ${timed ? '' : `<p class="note">${t.noTime}</p>`}
        <section>
          <div class="eyebrow">${t.positions}</div>
          <table>${rows}</table>
        </section>
        <section>
          <div class="eyebrow">${t.aspects}</div>
          ${asps}
        </section>
      </div>
    </div>
    <div class="prov">${provBits}</div>
    <p class="disclaimer"><b>${t.disclaimerLead}</b> ${t.disclaimer}</p>
  `;
}

// ── boot ─────────────────────────────────────────────────────────────────────
mountView<Payload>({
  pick: pickPayload,
  render,
  strings: {
    ru: { waiting: COPY.ru.waiting, empty: COPY.ru.empty },
    en: { waiting: COPY.en.waiting, empty: COPY.en.empty },
  },
});
