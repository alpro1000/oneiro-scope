'use client';

/**
 * Lunar calendar — the instrument reading of the Moon.
 *
 * The hero shows one lunar day (today, or a day picked from the grid): its
 * number, the phase and illumination, the Moon's sign, when the lunar day
 * began. The grid is a real month, each cell carrying its lunar-day number.
 *
 * Every value is the backend's Swiss-Ephemeris computation — the phase name,
 * description, recommendation and sign come localized from the server, and the
 * numbers (lunar day, illumination, JD_UT) are shown in mono because they are
 * the calculation, not an opinion. Nothing here is faked: a day that fails to
 * load says so (conventions.md §12), it never shows an invented phase.
 */

import {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import {fetchLunarDayClient} from '../lib/lunar-client';
import type {LunarDayPayload} from '../lib/lunar-server';
// Only the pure storage helpers — the TimezoneSelector component itself pulls
// in next-intl; the instrument screens use a plain inline select instead.
import {getStoredTimezone, setStoredTimezone} from './TimezoneSelector';

type Lang = 'ru' | 'en';

// IANA zone names, shown verbatim — technical, language-neutral, mono.
const ZONES = ['Europe/Moscow', 'Europe/Kyiv', 'Europe/Prague', 'Europe/Bratislava',
  'Europe/Madrid', 'Europe/Rome', 'Europe/Athens', 'Asia/Tokyo', 'America/New_York', 'UTC'];

const WAXING = new Set(['new_moon', 'waxing_crescent', 'first_quarter', 'waxing_gibbous']);

function ui(lang: Lang) {
  const ru = {
    eyebrow: 'лунный календарь · Swiss Ephemeris', titleA: 'Фаза, ', titleEm: 'день', titleB: ' и знак',
    lunarDay: 'лунный день', phase: 'фаза', illum: 'освещённость', moonSign: 'Луна в знаке',
    dayStarted: 'день начался', focus: 'Энергия дня', recommendation: 'Рекомендации',
    month: 'Лунный месяц', tz: 'Часовой пояс', today: 'сегодня',
    loading: 'Считаем месяц…', retry: 'Повторить',
    error: 'Лунные данные недоступны: сервер не ответил. Расчёт делается на сервере — офлайн его не подменяем выдумкой.',
    waxing: 'растущая', waning: 'убывающая',
    engine: 'движок', tzLbl: 'пояс', src: 'источник',
    disclaimerLead: 'Фаза и день — астрономия, они проверяемы.',
    disclaimer: 'Значение лунного дня — традиция толкования, а не предсказание, и не '
      + 'медицинский, психологический, юридический или финансовый совет.',
    weekdays: ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'],
    months: ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля',
      'августа', 'сентября', 'октября', 'ноября', 'декабря'],
    monthsNom: ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль',
      'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'],
  };
  const en = {
    eyebrow: 'lunar calendar · Swiss Ephemeris', titleA: 'Phase, ', titleEm: 'day', titleB: ' and sign',
    lunarDay: 'lunar day', phase: 'phase', illum: 'illumination', moonSign: 'Moon in sign',
    dayStarted: 'day began', focus: "Day's energy", recommendation: 'Guidance',
    month: 'Lunar month', tz: 'Timezone', today: 'today',
    loading: 'Computing the month…', retry: 'Retry',
    error: 'Lunar data unavailable: the server did not answer. The computation is server-side — offline we do not substitute an invented one.',
    waxing: 'waxing', waning: 'waning',
    engine: 'engine', tzLbl: 'zone', src: 'source',
    disclaimerLead: 'The phase and the day are astronomy — verifiable.',
    disclaimer: 'The meaning of a lunar day is a tradition of interpretation, not a prediction, and not '
      + 'medical, psychological, legal or financial advice.',
    weekdays: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
    months: ['January', 'February', 'March', 'April', 'May', 'June', 'July',
      'August', 'September', 'October', 'November', 'December'],
    monthsNom: ['January', 'February', 'March', 'April', 'May', 'June', 'July',
      'August', 'September', 'October', 'November', 'December'],
  };
  return lang === 'ru' ? ru : en;
}

const iso = (d: Date) => d.toISOString().slice(0, 10);
const todayIso = (payloadDate: string) => payloadDate;

/** Days of the month plus how many weekday blanks precede day 1 (Mon-first). */
function monthGrid(year: number, month: number): {days: string[]; lead: number} {
  const first = new Date(Date.UTC(year, month, 1));
  const total = new Date(Date.UTC(year, month + 1, 0)).getUTCDate();
  const lead = (first.getUTCDay() + 6) % 7; // JS: 0=Sun; we want Mon=0
  const days: string[] = [];
  for (let d = 1; d <= total; d++) days.push(iso(new Date(Date.UTC(year, month, d))));
  return {days, lead};
}

/** A moon disc whose brightness IS the illuminated fraction — no faked
 *  terminator geometry, just the number rendered as light. */
function MoonDisc({illum, size = 46}: {illum: number; size?: number}) {
  const r = size / 2 - 1;
  const c = size / 2;
  const f = Math.max(0, Math.min(1, illum));
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden="true">
      <circle cx={c} cy={c} r={r} fill="var(--panel)" stroke="var(--grat-2)" />
      <circle cx={c} cy={c} r={r} fill="var(--p-moon)" fillOpacity={f} />
      <circle cx={c} cy={c} r={r} fill="none" stroke="var(--grat-2)" strokeOpacity={0.6} />
    </svg>
  );
}

interface Props {
  initial: LunarDayPayload;
  locale: string;
  defaultTz: string;
}

export default function LunarInstrument({initial, locale, defaultTz}: Props) {
  const lang: Lang = locale === 'ru' ? 'ru' : 'en';
  const t = ui(lang);

  const [tz, setTz] = useState(initial.timezone || defaultTz);
  const [selected, setSelected] = useState<LunarDayPayload>(initial);
  const [view, setView] = useState(() => {
    const d = new Date(`${initial.date}T00:00:00Z`);
    return {year: d.getUTCFullYear(), month: d.getUTCMonth()};
  });
  const [cells, setCells] = useState<Map<string, LunarDayPayload>>(
    () => new Map([[initial.date, initial]]),
  );
  const [status, setStatus] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle');
  const cacheRef = useRef<Map<string, LunarDayPayload>>(new Map([[`${initial.date}|${initial.timezone}`, initial]]));

  useEffect(() => {
    const stored = getStoredTimezone();
    if (stored && stored !== tz) setTz(stored);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const grid = useMemo(() => monthGrid(view.year, view.month), [view]);

  // Load every day of the viewed month for the chosen zone. No fabrication:
  // a day that will not load leaves the whole grid in an honest error state.
  const loadMonth = useCallback(async () => {
    setStatus('loading');
    try {
      const results = await Promise.all(
        grid.days.map(async (date) => {
          const key = `${date}|${tz}`;
          const cached = cacheRef.current.get(key);
          if (cached) return cached;
          const payload = await fetchLunarDayClient(date, lang, tz, {retries: 2, baseDelay: 400});
          cacheRef.current.set(key, payload);
          return payload;
        }),
      );
      const next = new Map<string, LunarDayPayload>();
      results.forEach((p) => next.set(p.date, p));
      setCells(next);
      setStatus('ready');
      // keep the hero in step with the chosen zone
      const sel = next.get(selected.date);
      if (sel) setSelected(sel);
    } catch {
      setStatus('error');
    }
  }, [grid, tz, lang, selected.date]);

  useEffect(() => {
    loadMonth();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view, tz]);

  const shiftMonth = (delta: number) =>
    setView(({year, month}) => {
      const m = month + delta;
      return {year: year + Math.floor(m / 12), month: ((m % 12) + 12) % 12};
    });

  const s = selected;
  const illum = typeof s.illumination === 'number' ? s.illumination : 0;
  const waxing = s.phase_key ? WAXING.has(s.phase_key)
    : (typeof s.phase_angle === 'number' ? s.phase_angle < 180 : true);
  const engine = s.ephemeris_engine || (s.provenance?.ephemeris_engine as string | undefined) || 'SWIEPH';
  const jd = typeof s.jd_ut === 'number' ? s.jd_ut : (s.provenance?.jd_ut as number | undefined);

  return (
    <main style={{padding: 'clamp(14px,2.2vw,30px)'}}>
      <header style={{
        display: 'flex', flexWrap: 'wrap', alignItems: 'flex-end', gap: '12px 28px',
        paddingBottom: 14, marginBottom: 'clamp(12px,1.6vw,20px)', borderBottom: '1px solid var(--grat-1)',
      }}>
        <div>
          <span className="eyebrow">{t.eyebrow}</span>
          <h1 style={{fontSize: 'clamp(28px,5vw,52px)', margin: 0}}>{t.titleA}<em>{t.titleEm}</em>{t.titleB}</h1>
        </div>
        <div style={{marginLeft: 'auto'}}>
          <label style={{display: 'block', color: 'var(--dim)', fontFamily: 'var(--font-data)', fontSize: 10, letterSpacing: '.04em', textTransform: 'uppercase', margin: '0 0 3px', textAlign: 'right'}}>{t.tz}</label>
          <select
            value={tz}
            onChange={(e) => {setTz(e.target.value); setStoredTimezone(e.target.value);}}
            aria-label={t.tz}
            style={{background: 'var(--abyss)', color: 'var(--parchment)', border: '1px solid var(--grat-2)', fontFamily: 'var(--font-data)', fontSize: 12, padding: '6px 8px', minWidth: 180}}>
            {(ZONES.includes(tz) ? ZONES : [tz, ...ZONES]).map((z) => (
              <option key={z} value={z}>{z}</option>
            ))}
          </select>
        </div>
      </header>

      <div className="stage">
        {/* ── month grid ── */}
        <div className="panel">
          <div className="panel-block" style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between'}}>
            <button type="button" onClick={() => shiftMonth(-1)} style={navBtn} aria-label="prev month">‹</button>
            <span style={{fontFamily: 'var(--font-display)', fontSize: 19}}>
              {t.monthsNom[view.month]} <span className="num" style={{color: 'var(--muted)', fontSize: 15}}>{view.year}</span>
            </span>
            <button type="button" onClick={() => shiftMonth(1)} style={navBtn} aria-label="next month">›</button>
          </div>

          <div className="panel-block">
            <div style={{display: 'grid', gridTemplateColumns: 'repeat(7,1fr)', gap: 4}}>
              {t.weekdays.map((w) => (
                <div key={w} className="num" style={{textAlign: 'center', fontSize: 10, letterSpacing: '.08em', color: 'var(--dim)', paddingBottom: 4}}>{w}</div>
              ))}
              {Array.from({length: grid.lead}).map((_, i) => <div key={`b${i}`} />)}
              {grid.days.map((date) => {
                const cell = cells.get(date);
                const dom = Number(date.slice(8, 10));
                const isSel = date === s.date;
                const isToday = date === todayIso(initial.date);
                return (
                  <button
                    key={date}
                    type="button"
                    onClick={() => cell && setSelected(cell)}
                    disabled={!cell}
                    data-testid={`day-${date}`}
                    aria-current={isToday ? 'date' : undefined}
                    style={{
                      display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1,
                      padding: '5px 0 4px', cursor: cell ? 'pointer' : 'default', background: isSel ? 'var(--shelf)' : 'transparent',
                      border: `1px solid ${isSel ? 'var(--brass)' : isToday ? 'var(--grat-2)' : 'transparent'}`,
                      fontFamily: 'var(--font-data)',
                    }}>
                    <span style={{fontSize: 11, color: isSel ? 'var(--parchment)' : 'var(--muted)'}}>{dom}</span>
                    <span style={{fontSize: 13, color: isSel ? 'var(--brass)' : cell ? 'var(--parchment)' : 'var(--dim)', fontVariantNumeric: 'tabular-nums'}}>
                      {cell ? cell.lunar_day : status === 'loading' ? '·' : '–'}
                    </span>
                  </button>
                );
              })}
            </div>
            {status === 'error' && (
              <div style={{marginTop: 12, border: '1px solid var(--brass-dim)', background: 'var(--notice-bg)', color: 'var(--notice-ink)', padding: '9px 12px', fontSize: 12.5, lineHeight: 1.5}}>
                {t.error}{' '}
                <button type="button" onClick={loadMonth} style={{background: 'none', border: 0, color: 'var(--brass)', cursor: 'pointer', textDecoration: 'underline', padding: 0, font: 'inherit'}}>{t.retry}</button>
              </div>
            )}
            {status === 'loading' && (
              <div className="num" style={{marginTop: 10, fontSize: 11, color: 'var(--dim)', letterSpacing: '.06em'}}>{t.loading}</div>
            )}
          </div>
        </div>

        {/* ── the day (hero) ── */}
        <aside className="panel">
          <div className="panel-block" style={{display: 'flex', gap: 15, alignItems: 'center'}}>
            <MoonDisc illum={illum} />
            <div>
              <div className="eyebrow" style={{marginBottom: 4}}>{t.lunarDay}</div>
              <div className="num" style={{fontSize: 34, lineHeight: 1, color: 'var(--brass)'}}>{s.lunar_day}</div>
              <div className="num" style={{fontSize: 11.5, color: 'var(--muted)', marginTop: 4}}>
                {new Date(`${s.date}T00:00:00Z`).getUTCDate()} {t.months[new Date(`${s.date}T00:00:00Z`).getUTCMonth()]}
                {s.date === initial.date ? ` · ${t.today}` : ''}
              </div>
            </div>
          </div>

          <div className="panel-block">
            <table style={{width: '100%', borderCollapse: 'collapse'}} className="num">
              <tbody>
                <tr><td style={cellL}>{t.phase}</td><td style={cellR}>{s.phase} <span style={{color: 'var(--dim)'}}>· {waxing ? t.waxing : t.waning}</span></td></tr>
                <tr><td style={cellL}>{t.illum}</td><td style={cellR}>{Math.round(illum * 100)}%</td></tr>
                {s.moon_sign && <tr><td style={cellL}>{t.moonSign}</td><td style={cellR}>{s.moon_sign}</td></tr>}
                {s.lunar_day_start_time && <tr><td style={cellL}>{t.dayStarted}</td><td style={cellR}>{s.lunar_day_start_time}</td></tr>}
              </tbody>
            </table>
          </div>

          {s.description && (
            <div className="panel-block">
              <div className="eyebrow" style={{marginBottom: 7}}>{t.focus}</div>
              <p style={{fontSize: 13, lineHeight: 1.55, color: 'var(--parchment)', margin: 0}}>{s.description}</p>
            </div>
          )}
          {s.recommendation && (
            <div className="panel-block">
              <div className="eyebrow" style={{marginBottom: 7}}>{t.recommendation}</div>
              <p style={{fontSize: 13, lineHeight: 1.55, color: 'var(--muted)', margin: 0}}>{s.recommendation}</p>
            </div>
          )}
        </aside>
      </div>

      <div className="provenance" style={{display: 'flex', flexWrap: 'wrap', gap: '4px 22px'}}>
        <span><b style={{color: 'var(--muted)', fontWeight: 400}}>{t.engine}</b> {engine}</span>
        {jd !== undefined && <span><b style={{color: 'var(--muted)', fontWeight: 400}}>JD_UT</b> {jd}</span>}
        <span><b style={{color: 'var(--muted)', fontWeight: 400}}>{t.tzLbl}</b> {s.timezone || tz}</span>
        <span><b style={{color: 'var(--muted)', fontWeight: 400}}>{t.src}</b> {s.source}</span>
      </div>

      <p style={{fontSize: 13, color: 'var(--muted)', maxWidth: '64ch', lineHeight: 1.6, marginTop: 12}}>
        <b style={{color: 'var(--parchment)', fontWeight: 500}}>{t.disclaimerLead}</b> {t.disclaimer}
      </p>
    </main>
  );
}

const navBtn: React.CSSProperties = {
  background: 'transparent', color: 'var(--muted)', border: '1px solid var(--grat-2)',
  fontFamily: 'var(--font-data)', fontSize: 16, lineHeight: 1, padding: '2px 11px', cursor: 'pointer',
};
const cellL: React.CSSProperties = {padding: '3px 0', fontSize: 12, color: 'var(--dim)', letterSpacing: '.06em'};
const cellR: React.CSSProperties = {padding: '3px 0', fontSize: 12.5, color: 'var(--parchment)', textAlign: 'right'};
