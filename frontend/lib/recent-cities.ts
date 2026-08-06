/**
 * Cities the user has actually looked at on the map.
 *
 * The astrocartography panel used to ship a fixed list of seven cities — the
 * places one particular person had asked about. For anyone else they were
 * seven irrelevant buttons. The list is now built from where THIS user has
 * pointed, most recent first, and starts empty.
 */

export interface RecentCity {
  name: string;
  lat: number;
  lon: number;
}

const KEY = 'oneiro.acg.cities.v1';
const LIMIT = 8;

export function loadRecentCities(): RecentCity[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter((c): c is RecentCity =>
        typeof c === 'object' && c !== null
        && typeof (c as RecentCity).name === 'string'
        && Number.isFinite((c as RecentCity).lat)
        && Number.isFinite((c as RecentCity).lon))
      .slice(0, LIMIT);
  } catch {
    return [];
  }
}

/** Prepend, de-duplicate by name, cap. Returns the new list. */
export function rememberCity(city: RecentCity): RecentCity[] {
  const next = [city, ...loadRecentCities().filter((c) => c.name !== city.name)].slice(0, LIMIT);
  if (typeof window !== 'undefined') {
    try {
      window.localStorage.setItem(KEY, JSON.stringify(next));
    } catch {
      /* storage blocked — the jump still worked, it just won't be remembered */
    }
  }
  return next;
}

export function forgetRecentCities(): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.removeItem(KEY);
  } catch {
    /* nothing to do */
  }
}
