export type BuildMockArgs = {
  locale: string;
  date: string;
  tz: string;
};

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

