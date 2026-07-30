import {cache} from 'react';
import {buildLunarUrl, resolveLunarApiBase} from './lunar-endpoint';

export type LunarDayPayload = {
  date: string;
  lunar_day: number;
  lunar_day_start_time?: string; // Time when current lunar day started (HH:MM)
  phase: string;
  phase_key?: string;
  description: string;
  recommendation: string;
  locale: string;
  source: string;
  timezone: string;
  // Optional fields the backend returns
  phase_angle?: number;
  illumination?: number;
  age?: number;
  moon_sign?: string;
  // Provenance: engine + JD are promoted to the top level; the full detail is
  // a dict (ephemeris_engine, jd_ut, …).
  ephemeris_engine?: string;
  jd_ut?: number;
  provenance?: Record<string, unknown>;
};

type FetchArgs = {
  locale: string;
  date: string;
  tz?: string;
};

/**
 * Fetch one lunar day from the backend.
 *
 * No mock fallback: a lunar day nobody computed must never look like one
 * somebody did (conventions.md §12). On failure this throws, and the two
 * callers surface it honestly — the `/api/lunar` route returns a 502 and the
 * calendar page shows an error state — rather than quietly serving an invented
 * phase. The Swiss-Ephemeris computation is the product; a plausible fake is
 * exactly what the project forbids.
 */
async function fetchLunarDay({locale, date, tz}: FetchArgs): Promise<LunarDayPayload> {
  const base = resolveLunarApiBase(true);
  const timezone = tz ?? process.env.LUNAR_DEFAULT_TZ ?? 'UTC';
  const url = buildLunarUrl(base, {date, locale, tz: timezone});
  const res = await fetch(url, {
    headers: {Accept: 'application/json'},
    next: {revalidate: 60 * 60}
  });
  if (!res.ok) {
    throw new Error(`Lunar API responded with ${res.status}`);
  }
  const payload = await res.json();
  return {...payload, source: payload.source ?? 'backend'};
}

export const getLunarDay = cache(fetchLunarDay);
