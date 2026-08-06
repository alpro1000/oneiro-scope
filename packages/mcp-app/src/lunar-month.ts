/**
 * Lunar calendar — an MCP App view for `get_lunar_period`.
 *
 * A month of lunar days is a grid, and a grid is exactly what prose cannot
 * carry: the shape of the cycle — where the new moon falls, how illumination
 * climbs — is the information. Each cell shows the lunar day number, the
 * phase as a drawn disc, and illumination as a number, because "почти полная"
 * is an opinion and 92.5% is a measurement.
 */

import type { ToolResult } from './bridge';
import { esc, fromResult, mountView, type Lang } from './view';

interface Day {
  date?: string;
  lunar_day?: number;
  phase?: string;
  moon_sign?: string;
  illumination?: number;
  moon_age_days?: number;
  lunar_day_start_time?: string;
}

interface Payload {
  days?: Day[];
  count?: number;
  timezone?: string;
  meta?: Record<string, unknown>;
  locale?: string;
}

const PHASE_NAME: Record<Lang, Record<string, string>> = {
  ru: {
    new_moon: 'новолуние', waxing_crescent: 'растущий серп',
    first_quarter: 'первая четверть', waxing_gibbous: 'растущая',
    full_moon: 'полнолуние', waning_gibbous: 'убывающая',
    last_quarter: 'последняя четверть', waning_crescent: 'убывающий серп',
  },
  en: {
    new_moon: 'new moon', waxing_crescent: 'waxing crescent',
    first_quarter: 'first quarter', waxing_gibbous: 'waxing gibbous',
    full_moon: 'full moon', waning_gibbous: 'waning gibbous',
    last_quarter: 'last quarter', waning_crescent: 'waning crescent',
  },
};

const SIGN_GLYPH: Record<string, string> = {
  Aries: '♈', Taurus: '♉', Gemini: '♊', Cancer: '♋', Leo: '♌', Virgo: '♍',
  Libra: '♎', Scorpio: '♏', Sagittarius: '♐', Capricorn: '♑',
  Aquarius: '♒', Pisces: '♓',
};

const COPY = {
  ru: {
    title: 'Лунный календарь',
    day: 'лунный день', starts: 'начало',
    illum: 'освещённость', sign: 'Луна в знаке',
    tz: 'часовой пояс', days: 'дней',
    waiting: 'Ожидание календаря…',
    empty: 'Нет данных. Вызовите get_lunar_period.',
    disclaimerLead: 'Фазы и знаки — астрономия, они проверяемы.',
    disclaimer: 'Рекомендации лунного дня — традиция, а не прогноз. '
      + 'Рефлексивно-развлекательный материал, не медицинский, психологический, '
      + 'юридический или финансовый совет.',
  },
  en: {
    title: 'Lunar calendar',
    day: 'lunar day', starts: 'starts',
    illum: 'illumination', sign: 'Moon in',
    tz: 'timezone', days: 'days',
    waiting: 'Waiting for the calendar…',
    empty: 'No data. Call get_lunar_period.',
    disclaimerLead: 'Phases and signs are astronomy — verifiable.',
    disclaimer: 'What a lunar day is good for is a tradition, not a prediction. '
      + 'Reflective / entertainment material, not medical, psychological, legal '
      + 'or financial advice.',
  },
} as const;

/**
 * The lit part of the disc, as an SVG.
 *
 * `illumination` alone cannot say which limb is lit, so the phase name picks
 * the side. Drawn rather than approximated with a glyph: ☽ and ☾ have only two
 * states, and the whole point of the grid is watching the shape change.
 */
function moonDisc(illum: number, phase: string): string {
  const r = 11;
  const waning = phase.startsWith('waning') || phase === 'last_quarter';
  const k = Math.max(0, Math.min(1, illum));
  // Terminator half-width: 0 at quarter, ±r at new/full.
  const rx = Math.abs(r * (1 - 2 * k));
  const outerSweep = waning ? 0 : 1;
  const innerSweep = k < 0.5 ? (waning ? 1 : 0) : (waning ? 0 : 1);
  const lit = k <= 0.01
    ? ''
    : k >= 0.99
      ? `<circle cx="0" cy="0" r="${r}" fill="var(--p-moon)"/>`
      : `<path d="M 0 ${-r} A ${r} ${r} 0 0 ${outerSweep} 0 ${r} `
        + `A ${rx} ${r} 0 0 ${innerSweep} 0 ${-r} Z" fill="var(--p-moon)"/>`;
  return `<svg viewBox="-14 -14 28 28" width="26" height="26" aria-hidden="true">`
    + `<circle cx="0" cy="0" r="${r}" fill="var(--shelf)" stroke="var(--grat-2)" stroke-width="0.8"/>`
    + `${lit}</svg>`;
}

function render(payload: Payload, lang: Lang): string {
  const t = COPY[lang];
  const days = payload.days ?? [];

  const cells = days.map((d) => {
    const illum = typeof d.illumination === 'number' ? d.illumination : 0;
    const phase = d.phase ?? '';
    const pretty = PHASE_NAME[lang][phase] ?? esc(phase);
    const sign = d.moon_sign ? `${SIGN_GLYPH[d.moon_sign] ?? ''} ${esc(d.moon_sign)}` : '';
    return `<div class="lday">
      <div class="lday-top">
        <span class="num lday-date">${esc(d.date ?? '')}</span>
        ${moonDisc(illum, phase)}
      </div>
      <div class="num lday-n">${d.lunar_day ?? '—'}<span class="dim"> ${t.day}</span></div>
      <div class="lday-phase">${pretty}</div>
      <div class="num lday-illum">${(illum * 100).toFixed(1)}%<span class="dim"> ${t.illum}</span></div>
      ${sign ? `<div class="lday-sign">${sign}</div>` : ''}
      ${d.lunar_day_start_time
        ? `<div class="num lday-start dim">${t.starts} ${esc(d.lunar_day_start_time)}</div>` : ''}
    </div>`;
  }).join('');

  const meta = payload.meta ?? {};
  const provBits = [
    payload.timezone ? `<span><b>${t.tz}</b> ${esc(payload.timezone)}</span>` : '',
    `<span><b>${t.days}</b> ${days.length}</span>`,
    meta.request_id ? `<span><b>request</b> ${esc(String(meta.request_id))}</span>` : '',
  ].filter(Boolean).join('');

  return `
    <div class="head">
      <div class="eyebrow">Swiss Ephemeris · SWIEPH</div>
      <h1>${t.title}</h1>
    </div>
    <div class="lgrid">${cells}</div>
    <div class="prov">${provBits}</div>
    <p class="disclaimer"><b>${t.disclaimerLead}</b> ${t.disclaimer}</p>
  `;
}

mountView<Payload>({
  pick: (result: ToolResult) =>
    fromResult<Payload>(result, (c) =>
      Array.isArray((c as Payload).days) ? (c as Payload) : null),
  render,
  strings: {
    ru: { waiting: COPY.ru.waiting, empty: COPY.ru.empty },
    en: { waiting: COPY.en.waiting, empty: COPY.en.empty },
  },
});
