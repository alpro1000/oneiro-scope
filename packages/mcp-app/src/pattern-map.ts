/**
 * Chart pattern — an MCP App view shared by `money_contour` and `vocation_map`.
 *
 * One view, two tools, on purpose: both return the same envelope
 * (`pattern_id`, `computed`, `provenance`, `disclaimer`) and the same nested
 * shapes inside it — a house with its cusp sign, rulers and occupants, plus a
 * handful of named points. Writing two near-identical renderers would give two
 * places to fix the same bug.
 *
 * These are the views the owner was right about. A money contour is a list;
 * a reader cannot do anything with "8th house ruler: Jupiter in Cancer,
 * exaltation, 11th" on its own. So every house, every dignified planet and
 * every named point carries "explain", and the question hands the chat the
 * dignity and the house rather than a paraphrase. The table is the input to
 * the reading, not a substitute for it.
 */

import type { ToolResult } from './bridge';
import { ASK_LABEL, askButton, esc, fromResult, mountView, type Lang } from './view';

interface Placement {
  planet?: string;
  sign?: string;
  house?: number;
  dignity?: string | null;
  status?: string;
  retrograde?: boolean;
}

interface House {
  house?: number;
  cusp_sign?: string;
  rulers?: Placement[];
  occupants?: Placement[];
}

interface Point {
  lon?: number;
  sign?: string;
  house?: number;
  /**
   * A full placement, not a planet name — it carries the dispositor's own
   * sign, house and dignity, which is the interesting part. Typing this as a
   * string is what made the view white-screen on `esc()`.
   */
  dispositor?: Placement;
}

interface Linchpin {
  linked?: boolean;
  type?: string;
  ruler_2nd?: string;
  ruler_8th?: string;
  separation_deg?: number;
  same_sign?: boolean;
}

interface Payload {
  pattern_id?: string;
  layer?: string;
  confidence?: number;
  computed?: Record<string, unknown>;
  provenance?: Record<string, unknown>;
  disclaimer?: string;
  meta?: Record<string, unknown>;
  locale?: string;
}

const P_GLYPH: Record<string, string> = {
  sun: '☉', moon: '☽', mercury: '☿', venus: '♀', mars: '♂', jupiter: '♃',
  saturn: '♄', uranus: '♅', neptune: '♆', pluto: '♇',
};
const SIGN_GLYPH: Record<string, string> = {
  aries: '♈', taurus: '♉', gemini: '♊', cancer: '♋', leo: '♌', virgo: '♍',
  libra: '♎', scorpio: '♏', sagittarius: '♐', capricorn: '♑',
  aquarius: '♒', pisces: '♓',
};

interface PatternHead { title: string; eyebrow: string; lede: string }

interface Copy {
  'money-contour': PatternHead;
  'vocation-map': PatternHead;
  house: string; cusp: string; rulers: string; occupants: string;
  mc: string; workHouses: string; dignified: string; angular: string;
  fortune: string; linchpin: string; sect: string; dispositor: string;
  separation: string; linked: string; notLinked: string; sameSign: string;
  conjunct: string; empty: string; engine: string; houses: string;
  askHouse: string; askPlacement: string; askPoint: string;
  askAllMoney: string; askAllVoc: string; askHint: string;
  waiting: string; noData: string; disclaimerLead: string;
}

const COPY: Record<Lang, Copy> = {
  ru: {
    'money-contour': {
      title: 'Денежный контур',
      eyebrow: 'дома 2 · 8 · 11 · управители · Колесо Фортуны',
      lede: 'Свои деньги, чужие деньги и то, что их связывает.',
    },
    'vocation-map': {
      title: 'Карта призвания',
      eyebrow: 'MC · дома 2 · 6 · 10 · достоинства · угловые',
      lede: 'Куда карта разворачивает работу — и чем она за это платит.',
    },
    house: 'дом', cusp: 'куспид', rulers: 'управители', occupants: 'в доме',
    mc: 'MC (вершина карьеры)', workHouses: 'Дома работы',
    dignified: 'Планеты в достоинстве', angular: 'Угловые планеты',
    fortune: 'Колесо Фортуны', linchpin: 'Линчпин: связка своих и чужих денег',
    sect: 'секта', dispositor: 'диспозитор', separation: 'расхождение',
    linked: 'связаны', notLinked: 'не связаны', sameSign: 'в одном знаке',
    conjunct: 'в соединении', empty: 'пусто', engine: 'движок', houses: 'дома',
    askHouse: 'Объясни этот дом в моей карте',
    askPlacement: 'Объясни это положение',
    askPoint: 'Объясни эту точку в моей карте',
    askAllMoney: 'Разбери мой денежный контур целиком: где потолок и где рычаг',
    askAllVoc: 'Разбери мою карту призвания целиком: какие занятия ложатся на неё',
    askHint: 'Нажмите «объяснить» у любого блока — в чат уйдут его знаки, дома и достоинства.',
    waiting: 'Ожидание расчёта…',
    noData: 'Нет данных. Вызовите money_contour или vocation_map.',
    disclaimerLead: 'Дома, управители и достоинства — расчёт, он проверяем.',
  },
  en: {
    'money-contour': {
      title: 'Money contour',
      eyebrow: 'houses 2 · 8 · 11 · rulers · Part of Fortune',
      lede: "Your own money, other people's money, and what links them.",
    },
    'vocation-map': {
      title: 'Vocation map',
      eyebrow: 'MC · houses 2 · 6 · 10 · dignities · angular',
      lede: 'Where the chart turns work — and what it pays for it.',
    },
    house: 'house', cusp: 'cusp', rulers: 'rulers', occupants: 'in the house',
    mc: 'MC (career apex)', workHouses: 'Houses of work',
    dignified: 'Planets in dignity', angular: 'Angular planets',
    fortune: 'Part of Fortune', linchpin: 'Linchpin: own money tied to other people\'s',
    sect: 'sect', dispositor: 'dispositor', separation: 'separation',
    linked: 'linked', notLinked: 'not linked', sameSign: 'same sign',
    conjunct: 'conjunct', empty: 'empty', engine: 'engine', houses: 'houses',
    askHouse: 'Explain this house in my chart',
    askPlacement: 'Explain this placement',
    askPoint: 'Explain this point in my chart',
    askAllMoney: 'Read my money contour as a whole: where the ceiling and the lever are',
    askAllVoc: 'Read my vocation map as a whole: what work fits it',
    askHint: 'Press "explain" on any block — its signs, houses and dignities go to the chat.',
    waiting: 'Waiting for the computation…',
    noData: 'No data. Call money_contour or vocation_map.',
    disclaimerLead: 'Houses, rulers and dignities are computed — verifiable.',
  },
};

const sign = (s?: string) => (s ? `${SIGN_GLYPH[s] ?? ''} ${esc(s)}` : '—');
const planet = (p?: string) => (p ? `${P_GLYPH[p] ?? ''} ${esc(p)}` : '—');

/** A planet with everything that qualifies it — dignity is the point. */
function placementLine(p: Placement, t: Copy): string {
  const bits = [
    sign(p.sign),
    p.house ? `<span class="num">${p.house}</span> ${t.house}` : '',
    p.dignity ? `<span class="dig">${esc(p.dignity)}</span>` : '',
    p.status ? `<span class="dig">${esc(p.status)}</span>` : '',
    p.retrograde ? '<span class="dim">R</span>' : '',
  ].filter(Boolean).join(' · ');
  return `${planet(p.planet)} <span class="dim">—</span> ${bits}`;
}

const placementText = (p: Placement) =>
  `${p.planet ?? ''} ${p.sign ?? ''}${p.house ? `, ${p.house} house` : ''}`
  + `${p.dignity ? `, ${p.dignity}` : ''}${p.status ? `, ${p.status}` : ''}`
  + `${p.retrograde ? ', R' : ''}`;

function houseBlock(h: House, t: Copy, lang: Lang): string {
  const rulers = h.rulers ?? [];
  const occupants = h.occupants ?? [];
  const q = `${t.askHouse}: ${h.house} ${t.house}, ${t.cusp} ${h.cusp_sign ?? ''}. `
    + `${t.rulers}: ${rulers.map(placementText).join('; ') || '—'}. `
    + `${t.occupants}: ${occupants.map(placementText).join('; ') || t.empty}.`;
  return `<section>
    <div class="eyebrow">${h.house} ${t.house} · ${t.cusp} ${sign(h.cusp_sign)}</div>
    <div class="blk">
      <div class="blk-lbl">${t.rulers}</div>
      ${rulers.length
        ? rulers.map((r) => `<div class="pl">${placementLine(r, t)}</div>`).join('')
        : `<div class="pl dim">—</div>`}
    </div>
    <div class="blk">
      <div class="blk-lbl">${t.occupants}</div>
      ${occupants.length
        ? occupants.map((o) => `<div class="pl">${placementLine(o, t)}</div>`).join('')
        : `<div class="pl dim">${t.empty}</div>`}
    </div>
    ${askButton(q, ASK_LABEL[lang])}
  </section>`;
}

function pointBlock(label: string, p: Point, t: Copy, lang: Lang): string {
  const q = `${t.askPoint}: ${label} — ${p.sign ?? ''}`
    + `${p.house ? `, ${p.house} ${t.house}` : ''}`
    + `${p.dispositor ? `, ${t.dispositor} ${placementText(p.dispositor)}` : ''}`
    + `${typeof p.lon === 'number' ? `, ${p.lon.toFixed(2)}°` : ''}.`;
  return `<section>
    <div class="eyebrow">${label}</div>
    <div class="kv"><span>${t.house}</span><b class="num">${p.house ?? '—'}</b></div>
    <div class="kv"><span>sign</span><b>${sign(p.sign)}</b></div>
    ${p.dispositor ? `<div class="blk"><div class="blk-lbl">${t.dispositor}</div>
      <div class="pl">${placementLine(p.dispositor, t)}</div></div>` : ''}
    ${typeof p.lon === 'number' ? `<div class="kv"><span>lon</span><b class="num">${p.lon.toFixed(2)}°</b></div>` : ''}
    ${askButton(q, ASK_LABEL[lang])}
  </section>`;
}

function listBlock(
  label: string, items: Placement[], t: Copy, lang: Lang,
): string {
  if (!items.length) return '';
  return `<section>
    <div class="eyebrow">${label}</div>
    ${items.map((p) => `<div class="pl">${placementLine(p, t)}`
      + askButton(`${t.askPlacement}: ${placementText(p)}.`, ASK_LABEL[lang])
      + `</div>`).join('')}
  </section>`;
}

function render(payload: Payload, lang: Lang): string {
  const t = COPY[lang];
  const id = payload.pattern_id === 'vocation-map' ? 'vocation-map' : 'money-contour';
  const head = t[id];
  const c = (payload.computed ?? {}) as Record<string, any>;
  const blocks: string[] = [];

  if (id === 'money-contour') {
    for (const key of ['house_2', 'house_8', 'house_11']) {
      if (c[key]) blocks.push(houseBlock(c[key] as House, t, lang));
    }
    const lp = c.linchpin as Linchpin | undefined;
    if (lp) {
      const q = `${t.linchpin}: ${lp.linked ? t.linked : t.notLinked}`
        + `${lp.type ? `, ${lp.type}` : ''}, ${lp.ruler_2nd ?? ''} / ${lp.ruler_8th ?? ''}`
        + `${typeof lp.separation_deg === 'number' ? `, ${t.separation} ${lp.separation_deg.toFixed(2)}°` : ''}`
        + `${lp.same_sign ? `, ${t.sameSign}` : ''}.`;
      blocks.push(`<section>
        <div class="eyebrow">${t.linchpin}</div>
        <div class="kv"><span>${lp.linked ? t.linked : t.notLinked}</span>
          <b>${planet(lp.ruler_2nd)} <span class="dim">/</span> ${planet(lp.ruler_8th)}</b></div>
        ${typeof lp.separation_deg === 'number'
          ? `<div class="kv"><span>${t.separation}</span><b class="num">${lp.separation_deg.toFixed(2)}°</b></div>` : ''}
        ${lp.same_sign ? `<div class="loc-flag">${t.sameSign}</div>` : ''}
        ${askButton(q, ASK_LABEL[lang])}
      </section>`);
    }
    if (c.sect) {
      blocks.push(`<section><div class="eyebrow">${t.sect}</div>
        <div class="kv"><span>${esc(String(c.sect))}</span></div></section>`);
    }
  } else {
    const mc = c.mc as { sign?: string; rulers?: Placement[]; conjunct?: Placement[] } | undefined;
    if (mc) {
      const q = `${t.mc}: ${mc.sign ?? ''}. ${t.rulers}: `
        + `${(mc.rulers ?? []).map(placementText).join('; ') || '—'}`
        + `${(mc.conjunct ?? []).length ? `. ${t.conjunct}: ${(mc.conjunct ?? []).map(placementText).join('; ')}` : ''}.`;
      blocks.push(`<section>
        <div class="eyebrow">${t.mc}</div>
        <div class="kv"><span>sign</span><b>${sign(mc.sign)}</b></div>
        <div class="blk"><div class="blk-lbl">${t.rulers}</div>
          ${(mc.rulers ?? []).map((r) => `<div class="pl">${placementLine(r, t)}</div>`).join('')
            || `<div class="pl dim">—</div>`}</div>
        ${(mc.conjunct ?? []).length ? `<div class="blk"><div class="blk-lbl">${t.conjunct}</div>
          ${(mc.conjunct ?? []).map((r) => `<div class="pl">${placementLine(r, t)}</div>`).join('')}</div>` : ''}
        ${askButton(q, ASK_LABEL[lang])}
      </section>`);
    }
    const wh = (c.work_houses ?? {}) as Record<string, House>;
    for (const key of Object.keys(wh).sort((a, b) => Number(a) - Number(b))) {
      blocks.push(houseBlock(wh[key], t, lang));
    }
    blocks.push(listBlock(t.dignified, (c.dignified ?? []) as Placement[], t, lang));
    blocks.push(listBlock(t.angular, (c.angular ?? []) as Placement[], t, lang));
  }

  if (c.part_of_fortune) {
    blocks.push(pointBlock(t.fortune, c.part_of_fortune as Point, t, lang));
  }

  const prov = payload.provenance ?? {};
  const meta = payload.meta ?? {};
  const provBits = [
    prov.ephemeris_engine ? `<span><b>${t.engine}</b> ${esc(String(prov.ephemeris_engine))}</span>` : '',
    prov.house_system ? `<span><b>${t.houses}</b> ${esc(String(prov.house_system))}</span>` : '',
    typeof payload.confidence === 'number'
      ? `<span><b>confidence</b> ${payload.confidence.toFixed(1)}</span>` : '',
    meta.request_id ? `<span><b>request</b> ${esc(String(meta.request_id))}</span>` : '',
  ].filter(Boolean).join('');

  const askAll = id === 'vocation-map' ? t.askAllVoc : t.askAllMoney;

  return `
    <div class="head">
      <div class="eyebrow">${head.eyebrow}</div>
      <h1>${head.title}</h1>
      <p class="lede">${head.lede}</p>
    </div>
    <div class="pgrid">${blocks.filter(Boolean).join('')}</div>
    <div class="ask-row">${askButton(askAll, askAll, true)}
      <span class="ask-hint">${t.askHint}</span></div>
    <div class="prov">${provBits}</div>
    <p class="disclaimer"><b>${t.disclaimerLead}</b> ${esc(payload.disclaimer ?? '')}</p>
  `;
}

mountView<Payload>({
  pick: (result: ToolResult) =>
    fromResult<Payload>(result, (c) => {
      const p = c as Payload;
      return p.pattern_id && p.computed ? p : null;
    }),
  render,
  strings: {
    ru: { waiting: COPY.ru.waiting, empty: COPY.ru.noData },
    en: { waiting: COPY.en.waiting, empty: COPY.en.noData },
  },
});
