import {cache} from 'react';
import {buildLunarUrl, resolveLunarApiBase} from './lunar-endpoint';

export type LunarDayPayload = {
  date: string;
  lunar_day: number;
  phase: string;
  phase_key?: string;
  description: string;
  recommendation: string;
  locale: string;
  source: string;
  timezone: string;
  // Optional fields returned by backend but not always used
  phase_angle?: number;
  illumination?: number;
  age?: number;
  moon_sign?: string;
  provenance?: string;
};

type FetchArgs = {
  locale: string;
  date: string;
  tz?: string;
};

async function fetchLunarDay({locale, date, tz}: FetchArgs): Promise<LunarDayPayload> {
  const base = resolveLunarApiBase(true);
  const timezone = tz ?? process.env.LUNAR_DEFAULT_TZ ?? 'UTC';
  const url = buildLunarUrl(base, {date, locale, tz: timezone});
  try {
    const res = await fetch(url, {
      headers: {Accept: 'application/json'},
      next: {revalidate: 60 * 60}
    });

    if (!res.ok) {
      throw new Error(`Failed to fetch lunar day: ${res.status}`);
    }

    const payload = await res.json();
    return {...payload, source: payload.source ?? 'backend'};
  } catch (error) {
    console.warn('Lunar API unreachable, falling back to mock data.', error);
    return buildMockLunarDay({locale, date, tz: timezone});
  }
}

export const getLunarDay = cache(fetchLunarDay);

function buildMockLunarDay({
  locale,
  date,
  tz
}: FetchArgs & {tz: string}): LunarDayPayload {
  const parsed = new Date(date);
  const safeDate = Number.isNaN(parsed.getTime()) ? new Date() : parsed;

  const msPerDay = 1000 * 60 * 60 * 24;
  const epochDays = Math.floor(safeDate.getTime() / msPerDay);
  const lunarDay = ((epochDays % 30) + 30) % 30 + 1;

  const phases = [
    {key: 'new_moon', label: 'New Moon'},
    {key: 'waxing_crescent', label: 'Waxing Crescent'},
    {key: 'first_quarter', label: 'First Quarter'},
    {key: 'waxing_gibbous', label: 'Waxing Gibbous'},
    {key: 'full_moon', label: 'Full Moon'},
    {key: 'waning_gibbous', label: 'Waning Gibbous'},
    {key: 'last_quarter', label: 'Last Quarter'},
    {key: 'waning_crescent', label: 'Waning Crescent'}
  ];

  const phaseIndex = Math.floor(((lunarDay - 1) / 30) * phases.length) % phases.length;
  const phase = phases[phaseIndex];

  return {
    date: safeDate.toISOString().slice(0, 10),
    lunar_day: lunarDay,
    phase: phase.label,
    phase_key: phase.key,
    description: 'Mock lunar data (backend unavailable).',
    recommendation: 'Using offline lunar approximation until the backend is reachable.',
    locale,
    source: 'mock',
    timezone: tz
  };
}
