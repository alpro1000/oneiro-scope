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
 *
 * Order is the server's order. `compare_relocations` documents itself as
 * "comparison, not ranking" and `score_explanation` spells out why: the
 * scorer weighs only Venus/Jupiter/Sun/Moon and Saturn/Mars/Pluto, so
 * Mercury, Uranus and Neptune contribute exactly 0 however tight their orb.
 * Sorting by that number would present "unscored" as "weakest", which is the
 * one reading the server explicitly warns against — so `total_significance`
 * is shown beside the score and the caveat travels with every place.
 */

import type { ToolResult } from './bridge';
import { ASK_LABEL, askButton, esc, fromResult, mountView, type Lang } from './view';

interface Hit {
  planet?: string;
  angle?: string;
  /** The server's field name. Reading `orb` here printed 0.00° for every
   *  contact — and, worse, sent that fabricated exactness to the chat. */
  orb_deg?: number;
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
  score_explanation?: {
    plain?: string;
    total_significance?: number;
    unweighted?: Hit[];
  };
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
    significance: 'суммарная значимость',
    significanceHint: 'без знака — считает и то, что вес не учитывает',
    scoreCaveat: 'Вес считает только Венеру/Юпитер/Солнце/Луну (плюс) и '
      + 'Сатурн/Марс/Плутон (минус); Меркурий, Уран и Нептун дают ровно 0 при '
      + 'любом орбе. Низкий вес — не «пусто»: сверяйся с суммарной значимостью. '
      + 'Порядок городов — как в запросе, это сравнение, а не рейтинг.',
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
    significance: 'total significance',
    significanceHint: 'unsigned — counts what the weight leaves out',
    scoreCaveat: 'The weight scores only Venus/Jupiter/Sun/Moon (positive) and '
      + 'Saturn/Mars/Pluto (negative); Mercury, Uranus and Neptune contribute '
      + 'exactly 0 at any orb. A low weight is not "nothing here" — read it '
      + 'against total significance. Places are in the order asked for: this is '
      + 'a comparison, not a ranking.',
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

/**
 * A figure, or an em dash — never a substitute number.
 *
 * `(v ?? 0).toFixed(2)` reads as a measurement and is indistinguishable from
 * a real one. When a field is missing the honest output is that it is
 * missing, in the view and in the text sent to the chat alike.
 */
const num = (v: unknown, digits: number): string =>
  typeof v === 'number' && Number.isFinite(v) ? v.toFixed(digits) : '—';
const deg = (v: unknown) => (typeof v === 'number' && Number.isFinite(v) ? `${v.toFixed(2)}°` : '—');
const glyph = (p: string) => P_GLYPH[p] ?? P_GLYPH[p.toLowerCase()] ?? '·';
/** One contact in plain text — used identically on screen and in the ask. */
const hitText = (h: Hit, orbWord: string) =>
  `${h.planet ?? '?'} ${h.angle ?? '?'} ${orbWord} ${deg(h.orb_deg)}`;

function render(payload: Payload, lang: Lang): string {
  const t = COPY[lang];
  // Server order, deliberately: see the note at the top of this file.
  const ordered = payload.locations ?? [];

  const rows = ordered.map((loc) => {
    const hits = loc.angle_hits ?? [];
    const hitsHtml = hits.length
      ? hits.map((h) => `${glyph(h.planet ?? '')} ${esc(h.planet ?? '')} ${esc(h.angle ?? '')}`
        + ` <span class="num">${t.orb} ${deg(h.orb_deg)}</span>`).join(' · ')
      : `<span class="dim">${t.none}</span>`;

    const angles = Object.entries(loc.angles ?? {})
      .map(([k, v]) => `${ANGLE_LABEL[k] ?? esc(k)} <span class="num">${deg(v)}</span>`)
      .join(' · ');

    const sig = loc.score_explanation?.total_significance;

    // The question carries the figures, not a description of them.
    const q = `${t.askOne}: ${loc.name ?? ''} `
      + `(${num(loc.latitude, 4)}, ${num(loc.longitude, 4)}). `
      + `${t.angles}: ${Object.entries(loc.angles ?? {})
        .map(([k, v]) => `${ANGLE_LABEL[k] ?? k} ${deg(v)}`).join(', ')}. `
      + `${t.hits}: ${hits.length
        ? hits.map((h) => hitText(h, t.orb)).join('; ')
        : t.none}. `
      + `${t.score} ${num(loc.score, 1)}`
      + (typeof sig === 'number' ? `, ${t.significance} ${num(sig, 1)}` : '')
      + `. ${t.scoreCaveat}`;

    return `<section class="loc">
      <div class="loc-head">
        <h2>${esc(loc.name ?? '—')}</h2>
        <span class="num loc-score">${num(loc.score, 1)}<span class="dim"> ${t.score}</span></span>
      </div>
      <div class="kv"><span>${t.coords}</span><b class="num">${num(loc.latitude, 4)}° / ${num(loc.longitude, 4)}°</b></div>
      <div class="loc-line"><span class="lbl">${t.angles}</span> ${angles}</div>
      <div class="loc-line"><span class="lbl">${t.hits}</span> ${hitsHtml}</div>
      ${typeof sig === 'number'
        ? `<div class="loc-line"><span class="lbl">${t.significance}</span> <span class="num">${num(sig, 1)}</span> <span class="dim">${t.significanceHint}</span></div>`
        : ''}
      ${loc.summary?.clean ? `<div class="loc-flag">${t.clean}</div>` : ''}
      ${loc.summary?.plain ? `<p class="loc-plain">${esc(loc.summary.plain)}</p>` : ''}
      ${loc.score_explanation?.plain
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
      `${t.askAll}: ${ordered.map((l) => `${l.name} (${t.score} ${num(l.score, 1)}`
        + (typeof l.score_explanation?.total_significance === 'number'
          ? `, ${t.significance} ${num(l.score_explanation.total_significance, 1)}` : '')
        + ')').join(', ')}. ${t.scoreCaveat}`,
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
