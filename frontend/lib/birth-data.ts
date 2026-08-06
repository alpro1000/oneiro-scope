/**
 * The user's own birth data — one source of truth for every screen.
 *
 * Before this, /natal and /astrocartography each carried their own six
 * `useState` fields pre-filled with a specific person's birth date and city.
 * Every visitor opened the instrument already loaded with someone else's
 * chart, and entering their own meant retyping it on each screen.
 *
 * So: the form starts EMPTY, and what the user enters is kept here and shared.
 * Storage is localStorage — this is the user's own data on the user's own
 * device, it never needs to reach us to render a chart they already fetched,
 * and the account page is where a server-side copy would belong instead.
 *
 * The timezone is deliberately NOT part of what we ask for. `POST /api/v1/chart`
 * derives it from the coordinates via tzdata, historical rules included, which
 * is more reliable than a dropdown of six zones and a user guessing which one
 * applied in their birth year. The zone the server actually used comes back in
 * `chart_core.birth.tz_used` / `utc_offset_used` and is displayed there.
 */

export interface BirthData {
  /** YYYY-MM-DD */
  date: string;
  /** HH:MM. Empty string when the time is not known. */
  time: string;
  /**
   * Explicit, because an empty time field is ambiguous — "not filled in yet"
   * and "genuinely unknown" need different behaviour, and guessing noon
   * silently is the kind of fallback conventions.md §12 forbids. Without a
   * time, angles and houses are undefined and screens must refuse to draw
   * them rather than draw something arbitrary.
   */
  timeKnown: boolean;
  /** Decimal degrees as typed; parsed at submit. Empty until a city resolves. */
  lat: string;
  lon: string;
  /** Human label; also the geocoding query when coordinates are absent. */
  place: string;
}

export const EMPTY_BIRTH: BirthData = {
  date: '',
  time: '',
  timeKnown: true,
  lat: '',
  lon: '',
  place: '',
};

const KEY = 'oneiro.birth.v1';

export function loadBirth(): BirthData | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return null;
    const p = JSON.parse(raw) as Partial<BirthData>;
    if (typeof p !== 'object' || p === null) return null;
    return {
      date: typeof p.date === 'string' ? p.date : '',
      time: typeof p.time === 'string' ? p.time : '',
      timeKnown: p.timeKnown !== false,
      lat: typeof p.lat === 'string' ? p.lat : '',
      lon: typeof p.lon === 'string' ? p.lon : '',
      place: typeof p.place === 'string' ? p.place : '',
    };
  } catch {
    // Corrupt or unreadable (private mode, quota, hand-edited): treat as absent
    // rather than throwing on a page that would otherwise render fine.
    return null;
  }
}

export function saveBirth(b: BirthData): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(KEY, JSON.stringify(b));
  } catch {
    /* storage full or blocked — the chart still works, it just won't persist */
  }
}

export function clearBirth(): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.removeItem(KEY);
  } catch {
    /* nothing to do — see saveBirth */
  }
}

export function hasBirth(b: BirthData): boolean {
  return Boolean(b.date && b.lat && b.lon);
}

/**
 * What is still missing or wrong, in the user's language.
 *
 * Returned as a list rather than a boolean so the form can name the specific
 * problem instead of greying out the button and leaving the user to guess.
 */
export function birthIssues(b: BirthData, lang: 'ru' | 'en'): string[] {
  const ru = lang === 'ru';
  const out: string[] = [];

  if (!b.date) {
    out.push(ru ? 'нужна дата рождения' : 'birth date is required');
  } else if (!/^\d{4}-\d{2}-\d{2}$/.test(b.date)) {
    out.push(ru ? 'дата в формате ГГГГ-ММ-ДД' : 'date must be YYYY-MM-DD');
  } else {
    const year = Number(b.date.slice(0, 4));
    // The shipped .se1 files cover this span; outside it the server would
    // refuse, so say so here rather than after a round trip.
    if (year < 1800 || year > 2399) {
      out.push(ru
        ? 'эфемериды покрывают 1800–2399 годы'
        : 'the ephemeris covers 1800–2399');
    }
  }

  if (b.timeKnown && !b.time) {
    out.push(ru
      ? 'укажите время или отметьте, что оно неизвестно'
      : 'give a time, or mark it as unknown');
  }

  if (!b.lat || !b.lon) {
    out.push(ru ? 'выберите город рождения' : 'choose a birth city');
  } else {
    const la = Number(b.lat);
    const lo = Number(b.lon);
    if (!Number.isFinite(la) || la < -90 || la > 90) {
      out.push(ru ? 'широта вне диапазона −90…90' : 'latitude out of −90…90');
    }
    if (!Number.isFinite(lo) || lo < -180 || lo > 180) {
      out.push(ru ? 'долгота вне диапазона −180…180' : 'longitude out of −180…180');
    }
  }

  return out;
}

/** The shape `fetchChart` wants. Call only when `birthIssues` is empty. */
export function toChartRequest(b: BirthData, locale: 'ru' | 'en') {
  return {
    birth_date: b.date,
    // null, not "12:00" — the server records time_known=false and every screen
    // downstream then knows the angles are not to be drawn.
    birth_time: b.timeKnown && b.time ? `${b.time}:00` : null,
    birth_place: b.place || (locale === 'ru' ? 'место рождения' : 'birthplace'),
    latitude: Number(b.lat),
    longitude: Number(b.lon),
    // Omitted on purpose — see the module note. The server derives it.
    timezone_name: null as string | null,
    locale,
  };
}
