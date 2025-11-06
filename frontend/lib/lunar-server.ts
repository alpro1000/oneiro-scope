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
  const res = await fetch(url, {
    headers: {Accept: 'application/json'},
    next: {revalidate: 60 * 60}
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch lunar day: ${res.status}`);
  }

  return res.json();
}

export const getLunarDay = cache(fetchLunarDay);
