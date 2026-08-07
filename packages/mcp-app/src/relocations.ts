/**
 * Relocation comparison — an MCP App view for `compare_relocations`.
 *
 * A table, and the owner's point about tables is the whole reason it exists:
 * a row reading `Asc 134.94°, Uranus 6.0° orb, score 0.0` is exactly what a
 * reader cannot interpret unaided, so every row carries "explain" and hands
 * the chat its own figures. The drawing is the least of it.
 *
 * Two things are shown that a summary would swallow. A score of 0.0 is
 * printed as 0.0 with its own explanation rather than hidden — a quiet zone
 * is a finding, not a gap. And `clean` (no hard contacts) is marked, because
 * "nothing difficult here" is a different statement from "nothing here".
 */

import type { ToolResult } from './bridge';
import { ASK_LABEL, askButton, esc, fromResult, mountView, type Lang } from './view';

interface Hit {
  planet?: string;
  angle?: string;
  orb?: number;
  kind?: string;
}

interface Summary {
  plain?: string;
  work?: string[];
  home?: string[];
  relationships?: string[];
  tension?: string[];
  luck?: string[];
  clean?: boolean;
  confidence?: number;
  source?: string;
}

interface Location {
  name?: string;
  latitude?: number;
  longitude?: number;
  angles?: Record<string, number>;
  angle_hits?: Hit[];
  score?: number;
  summary?: Summary;
  score_explanation?: { plain?: string };
}

interface Payload {
  locations?: Location[];
  methodology?: string;
  meta?: Record<string, unknown>;
  locale?: string;
}

const P_GLYPH: Record<string, string> = {
  Sun: '☉', Moon: '☽', Mercury: '☿', Venus: '♀', Mars: '♂', Jupiter: '♃',
  Saturn: '♄', Uranus: '♅', Neptune: '♆', Pluto: '♇',
  sun: '☉', moon: '☽', mercury: '☿', venus: '♀', mars: '♂', jupiter: '♃',
  saturn: '♄', uranus: '♅', neptune: '♆', pluto: '♇',
};

const COPY = {
  ru: {
    title: 'Сравнение городов',
    eyebrow: 'релокация · углы Placidus',
    lede: 'Углы карты, пересчитанные для каждого места, и планеты рядом с ними.',
    score: 'вес', angles: 'углы', hits: 'планеты на углах', quiet: 'тихая зона',
    clean: 'без жёстких контактов', orb: 'орб', method: 'метод',
    coords: 'координаты', none: 'ни одной планеты в орбе',
    askOne: 'Объясни этот город по релокации',
    askAll: 'Сравни эти города между собой: где и для чего лучше',
    askHint: 'Нажмите «объяснить» у города — в чат уйдут его углы и контакты.',
    waiting: 'Ожидание сравнения…',
    empty: 'Нет данных. Вызовите compare_relocations.',
    disclaimerLead: 'Углы и орбы — геометрия, она проверяема.',
    disclaimer: 'Что «значит» планета на угле в конкретном городе — традиция '
      + 'толкования, а не прогноз и не совет о переезде. Рефлексивно-'
      + 'развлекательный материал, не медицинский, психологический, юридический '
      + 'или финансовый совет.',
  },
  en: {
    title: 'Comparing places',
    eyebrow: 'relocation · Placidus angles',
    lede: 'The chart angles recomputed for each place, and the planets near them.',
    score: 'weight', angles: 'angles', hits: 'planets on angles', quiet: 'quiet zone',
    clean: 'no hard contacts', orb: 'orb', method: 'method',
    coords: 'coordinates', none: 'no planet within orb',
    askOne: 'Explain this place under relocation',
    askAll: 'Compare these places: which suits what',
    askHint: 'Press "explain" on a place — its angles and contacts go to the chat.',
    waiting: 'Waiting for the comparison…',
    empty: 'No data. Call compare_relocations.',
    disclaimerLead: 'Angles and orbs are geometry — verifiable.',
    disclaimer: 'What a planet on an angle "means" in a given city is a tradition '
      + 'of interpretation, not a prediction and not relocation advice. '
      + 'Reflective / entertainment material, not medical, psychological, legal '
      + 'or financial advice.',
  },
} as const;

const ANGLE_LABEL: Record<string, string> = {
  asc: 'Asc', mc: 'MC', ic: 'IC', desc: 'Desc',
};

const deg = (v: number) => `${v.toFixed(2)}°`;
const glyph = (p: string) => P_GLYPH[p] ?? P_GLYPH[p.toLowerCase()] ?? '·';

function render(payload: Payload, lang: Lang): string {
  const t = COPY[lang];
  const locations = payload.locations ?? [];

  // Sorted by weight, strongest first — the whole reason to compare.
  const ordered = [...locations].sort((a, b) => (b.score ?? 0) - (a.score ?? 0));

  const rows = ordered.map((loc) => {
    const hits = loc.angle_hits ?? [];
    const hitText = hits.length
      ? hits.map((h) => `${glyph(h.planet ?? '')} ${esc(h.planet ?? '')} ${esc(h.angle ?? '')}`
        + ` <span class="num">${t.orb} ${deg(h.orb ?? 0)}</span>`).join(' · ')
      : `<span class="dim">${t.none}</span>`;

    const angles = Object.entries(loc.angles ?? {})
      .map(([k, v]) => `${ANGLE_LABEL[k] ?? esc(k)} <span class="num">${deg(v)}</span>`)
      .join(' · ');

    // The question carries the figures, not a description of them.
    const q = `${t.askOne}: ${loc.name ?? ''} `
      + `(${(loc.latitude ?? 0).toFixed(4)}, ${(loc.longitude ?? 0).toFixed(4)}). `
      + `${t.angles}: ${Object.entries(loc.angles ?? {})
        .map(([k, v]) => `${ANGLE_LABEL[k] ?? k} ${deg(v)}`).join(', ')}. `
      + `${t.hits}: ${hits.length
        ? hits.map((h) => `${h.planet} ${h.angle} ${t.orb} ${deg(h.orb ?? 0)}`).join('; ')
        : t.none}. ${t.score} ${(loc.score ?? 0).toFixed(1)}.`;

    return `<section class="loc">
      <div class="loc-head">
        <h2>${esc(loc.name ?? '—')}</h2>
        <span class="num loc-score">${(loc.score ?? 0).toFixed(1)}<span class="dim"> ${t.score}</span></span>
      </div>
      <div class="kv"><span>${t.coords}</span><b class="num">${(loc.latitude ?? 0).toFixed(4)}° / ${(loc.longitude ?? 0).toFixed(4)}°</b></div>
      <div class="loc-line"><span class="lbl">${t.angles}</span> ${angles}</div>
      <div class="loc-line"><span class="lbl">${t.hits}</span> ${hitText}</div>
      ${loc.summary?.clean ? `<div class="loc-flag">${t.clean}</div>` : ''}
      ${loc.summary?.plain ? `<p class="loc-plain">${esc(loc.summary.plain)}</p>` : ''}
      ${!hits.length && loc.score_explanation?.plain
        ? `<p class="loc-plain dim">${esc(loc.score_explanation.plain)}</p>` : ''}
      ${askButton(q, ASK_LABEL[lang])}
    </section>`;
  }).join('');

  const meta = payload.meta ?? {};
  const provBits = [
    payload.methodology ? `<span><b>${t.method}</b> ${esc(payload.methodology)}</span>` : '',
    meta.request_id ? `<span><b>request</b> ${esc(String(meta.request_id))}</span>` : '',
  ].filter(Boolean).join('');

  return `
    <div class="head">
      <div class="eyebrow">${t.eyebrow}</div>
      <h1>${t.title}</h1>
      <p class="lede">${t.lede}</p>
    </div>
    <div class="locs">${rows}</div>
    ${ordered.length ? `<div class="ask-row">${askButton(
      `${t.askAll}: ${ordered.map((l) => `${l.name} (${t.score} ${(l.score ?? 0).toFixed(1)})`).join(', ')}.`,
      t.askAll, true,
    )}<span class="ask-hint">${t.askHint}</span></div>` : ''}
    <div class="prov">${provBits}</div>
    <p class="disclaimer"><b>${t.disclaimerLead}</b> ${t.disclaimer}</p>
  `;
}

mountView<Payload>({
  pick: (result: ToolResult) =>
    fromResult<Payload>(result, (c) =>
      Array.isArray((c as Payload).locations) ? (c as Payload) : null),
  render,
  strings: {
    ru: { waiting: COPY.ru.waiting, empty: COPY.ru.empty },
    en: { waiting: COPY.en.waiting, empty: COPY.en.empty },
  },
});
