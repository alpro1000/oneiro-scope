export type BuildMockArgs = {
  locale: string;
  date: string;
  tz: string;
};

// Moon phase translations matching backend
const MOON_PHASE_LABELS: Record<string, Record<string, string>> = {
  new_moon: {ru: 'Новолуние', en: 'New Moon'},
  waxing_crescent: {ru: 'Растущий серп', en: 'Waxing Crescent'},
  first_quarter: {ru: 'Первая четверть', en: 'First Quarter'},
  waxing_gibbous: {ru: 'Растущая луна', en: 'Waxing Gibbous'},
  full_moon: {ru: 'Полнолуние', en: 'Full Moon'},
  waning_gibbous: {ru: 'Убывающая луна', en: 'Waning Gibbous'},
  last_quarter: {ru: 'Последняя четверть', en: 'Last Quarter'},
  waning_crescent: {ru: 'Убывающий серп', en: 'Waning Crescent'}
};

function getPhaseLabel(phaseKey: string, locale: string): string {
  const translations = MOON_PHASE_LABELS[phaseKey];
  return translations?.[locale] || translations?.en || phaseKey;
}

/**
 * Build a deterministic mock lunar day payload for offline/CI use.
 * This mirrors the server-side fallback but lives in a client-safe module
 * so both server and client code can reuse it without pulling in React cache.
 */
export function buildMockLunarDay({locale, date, tz}: BuildMockArgs) {
  const parsed = new Date(date);
  const safeDate = Number.isNaN(parsed.getTime()) ? new Date() : parsed;

  const msPerDay = 1000 * 60 * 60 * 24;
  const epochDays = Math.floor(safeDate.getTime() / msPerDay);
  const lunarDay = ((epochDays % 30) + 30) % 30 + 1;

  const phaseKeys = [
    'new_moon',
    'waxing_crescent',
    'first_quarter',
    'waxing_gibbous',
    'full_moon',
    'waning_gibbous',
    'last_quarter',
    'waning_crescent'
  ];

  const phaseIndex = Math.floor(((lunarDay - 1) / 30) * phaseKeys.length) % phaseKeys.length;
  const phaseKey = phaseKeys[phaseIndex];
  const phaseLabel = getPhaseLabel(phaseKey, locale);

  return {
    date: safeDate.toISOString().slice(0, 10),
    lunar_day: lunarDay,
    phase: phaseLabel,
    phase_key: phaseKey,
    description: 'Mock lunar data (backend unavailable).',
    recommendation: 'Using offline lunar approximation until the backend is reachable.',
    locale,
    source: 'mock',
    timezone: tz
  };
}

