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
import { HostBridge, type HostContext, type ToolResult } from './bridge';

type Lang = 'ru' | 'en';

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

const esc = (s: string) =>
  s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]!));

interface Payload {
  chart_core?: ChartCore;
  provenance?: Record<string, unknown>;
  meta?: Record<string, unknown>;
}

function pickPayload(result: ToolResult): Payload | null {
  const sc = result.structuredContent;
  if (sc && typeof sc === 'object') {
    if ((sc as Payload).chart_core) return sc as Payload;
  }
  // Some hosts deliver the JSON as a text content block instead.
  for (const block of result.content ?? []) {
    const b = block as { type?: string; text?: string };
    if (b?.type === 'text' && typeof b.text === 'string') {
      try {
        const parsed = JSON.parse(b.text);
        if (parsed?.chart_core) return parsed as Payload;
      } catch {
        /* not JSON — the next block may be */
      }
    }
  }
  return null;
}

function render(payload: Payload | null, lang: Lang): string {
  const t = COPY[lang];
  if (!payload?.chart_core) {
    return `<p class="note">${t.empty}</p>`;
  }
  const core = payload.chart_core;
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
    return `<tr>
      <td class="glyph" style="color:var(--p-${name.toLowerCase()},var(--muted))">${P_GLYPH[name] ?? '·'}</td>
      <td class="body">${esc(name)}</td>
      <td class="num">${fmtSign(body.ecl_lon)}${flag}</td>
      <td class="num dim">${body.retrograde ? t.retro : ''}</td>
      <td class="num dim">${house ? `${house} ${t.house}` : '—'}</td>
    </tr>`;
  }).join('');

  // Two lines per aspect rather than four columns. In a 300px instrument panel
  // four columns collide — "orb 6.12°separating" ran together — and the orb is
  // the number the whole row exists for, so it gets its own line with the
  // aspect type and the direction instead of being squeezed.
  const asps = kitAspects(core)
    .slice()
    .sort((x, y) => x.orb - y.orb)
    .map((a) => `<div class="asp">
      <div class="asp-pair">${P_GLYPH[a.a] ?? ''} ${esc(a.a)} <span class="dim">—</span> ${P_GLYPH[a.b] ?? ''} ${esc(a.b)}</div>
      <div class="asp-num num">${esc(a.type)} · ${t.orb} ${fmtOrb(a.orb)} · <span class="dim">${a.applying ? t.applying : t.separating}</span></div>
    </div>`).join('');

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
const root = document.getElementById('root')!;
let lang: Lang = 'ru';

function paint(payload: Payload | null): void {
  root.innerHTML = render(payload, lang);
  bridge.reportSize();
}

const bridge = new HostBridge({
  onToolResult: (result) => paint(pickPayload(result)),
  onContext: (ctx) => applyContext(ctx),
});

function applyContext(ctx: HostContext): void {
  if (ctx.theme) document.documentElement.dataset.theme = ctx.theme;
}

root.innerHTML = `<p class="note">${COPY[lang].waiting}</p>`;

bridge.initialize().then((ctx) => {
  if (ctx) applyContext(ctx);
  bridge.reportSize();
});

// Reflow (host resized the container, fonts settled) changes our height.
if (typeof ResizeObserver !== 'undefined') {
  new ResizeObserver(() => bridge.reportSize()).observe(document.documentElement);
}
