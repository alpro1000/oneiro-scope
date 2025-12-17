import {buildLunarUrl, resolveLunarApiBase} from './lunar-endpoint';
import type {LunarDayPayload} from './lunar-server';

export async function fetchLunarDayClient(
  date: string,
  locale: string,
  timezone?: string
): Promise<LunarDayPayload> {
  const base = resolveLunarApiBase(false);
  const tz = timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone ?? 'Europe/Moscow';
  const url = buildLunarUrl(base, {date, locale, tz});
  const response = await fetch(url, {
    headers: {Accept: 'application/json'}
  });

  if (!response.ok) {
    throw new Error(`Lunar API responded with ${response.status}`);
  }

  return response.json();
}
