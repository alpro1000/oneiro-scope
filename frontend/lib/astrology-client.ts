/**
 * Astrology API Client
 *
 * Client for interacting with the astrology backend service.
 */

import { resolveApiBase } from './api-base';

// Types for API requests/responses
export interface NatalChartRequest {
  birth_date: string;  // YYYY-MM-DD
  birth_time?: string; // HH:MM (optional)
  birth_place: string;
  locale?: string;     // 'en' | 'ru'
}

export interface PlanetPosition {
  // Backend returns 'planet' field with lowercase enum values like "sun", "moon"
  planet: string;
  // Sign is also lowercase enum value like "aries", "taurus"
  sign: string;
  // Absolute degree (0-359.99)
  degree: number;
  // Degree within sign (0-29.99)
  sign_degree: number;
  // House number (1-12), null if birth time not provided
  house?: number;
  // Whether planet is in retrograde motion
  retrograde: boolean;
}

export interface Aspect {
  // Backend returns planet enums as lowercase strings
  planet1: string;
  planet2: string;
  aspect_type: string;  // conjunction, sextile, square, trine, opposition, quincunx
  orb: number;          // Orb in degrees (0-10)
  applying: boolean;    // True if aspect is forming
  // Note: No "angle" field in backend - aspect_type determines the angle
}

export interface House {
  number: number;        // 1-12
  sign: string;          // lowercase zodiac sign
  degree: number;        // 0-29.99
  planets: string[];     // planets in this house
}

export interface NatalChartResponse {
  // Backend returns flat structure, not nested birth_data
  id: string;
  user_id?: string;
  birth_date: string;      // YYYY-MM-DD
  birth_time?: string;     // HH:MM:SS or null
  birth_place: string;
  latitude: number;        // Decimal
  longitude: number;       // Decimal
  timezone: string;
  // Zodiac signs (lowercase enum values)
  sun_sign: string;
  moon_sign: string;
  ascendant?: string;      // Requires birth_time
  midheaven?: string;      // Requires birth_time
  // Chart data
  planets: PlanetPosition[];
  houses?: House[];        // Requires birth_time
  aspects: Aspect[];
  // LLM interpretation
  interpretation?: string;
  // Metadata
  created_at: string;      // Backend field name (not "calculated_at")
  calculation_method: string;
}

export interface TransitInfo {
  transiting_planet: string;
  natal_planet: string;
  aspect: string;           // AspectType enum value
  exact_date: string;
  orb: number;
  description: string;
}

export interface HoroscopeResponse {
  id: string;
  user_id?: string;
  natal_chart_id?: string;
  period: string;           // daily, weekly, monthly, yearly
  period_start: string;
  period_end: string;
  // Transits (backend field name is "transits", not "current_transits")
  transits: TransitInfo[];
  retrograde_planets: string[];  // Planet enum values as strings
  lunar_phase: string;
  lunar_day: number;
  // LLM interpretation - backend has separate fields, not nested "sections"
  summary: string;
  love_and_relationships?: string;
  career_and_finance?: string;
  health_and_wellness?: string;
  recommendations: string[];
  created_at: string;       // Backend field name (not "generated_at")
}

export interface EventForecastRequest {
  event_date: string;       // YYYY-MM-DD
  event_type: string;
  event_location?: string;
  event_description?: string;
  natal_chart_id?: string;
  locale?: string;
}

export interface EventForecastResponse {
  id: string;
  user_id?: string;
  natal_chart_id?: string;
  event_date: string;
  event_type: string;
  event_location?: string;
  // Favorability
  favorability_score: number;      // 0-100
  favorability_level: string;      // Backend field name (not "level")
  // Transits and planetary info
  transits: TransitInfo[];
  retrograde_planets: string[];
  lunar_phase: string;
  lunar_day: number;
  // Analysis
  positive_factors: string[];
  risk_factors: string[];
  recommendations: string[];
  alternative_dates?: string[];    // Only when score < 50
  created_at: string;              // Backend field name (not "calculated_at")
  // Note: Backend doesn't have "interpretation" field
}

// API base URL resolution
function getAstrologyApiBase(): string {
  const isServer = typeof window === 'undefined';

  return resolveApiBase({
    serviceName: 'Astrology API',
    isServer,
    serverEnvVars: [process.env.ASTROLOGY_API_URL, process.env.NEXT_PUBLIC_API_URL],
    clientEnvVars: [process.env.NEXT_PUBLIC_API_URL],
    relativeFallback: '/api',
  });
}

/**
 * Calculate natal chart
 */
export async function calculateNatalChart(
  request: NatalChartRequest
): Promise<NatalChartResponse> {
  const base = getAstrologyApiBase();
  const url = `${base}/api/v1/astrology/natal-chart`;

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `API error: ${response.status}`);
  }

  return response.json();
}

/**
 * Get horoscope
 */
export async function getHoroscope(params: {
  period?: 'daily' | 'weekly' | 'monthly' | 'yearly';
  date?: string;
  natal_chart_id?: string;
  locale?: string;
}): Promise<HoroscopeResponse> {
  const base = getAstrologyApiBase();
  const searchParams = new URLSearchParams();

  if (params.period) searchParams.set('period', params.period);
  if (params.date) searchParams.set('date', params.date);
  if (params.natal_chart_id) searchParams.set('natal_chart_id', params.natal_chart_id);
  if (params.locale) searchParams.set('locale', params.locale);

  const url = `${base}/api/v1/astrology/horoscope?${searchParams.toString()}`;

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `API error: ${response.status}`);
  }

  return response.json();
}

/**
 * Forecast event favorability
 */
export async function forecastEvent(
  request: EventForecastRequest
): Promise<EventForecastResponse> {
  const base = getAstrologyApiBase();
  const url = `${base}/api/v1/astrology/event-forecast`;

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `API error: ${response.status}`);
  }

  return response.json();
}

/**
 * Get list of event types
 */
export async function getEventTypes(): Promise<{
  event_types: Array<{
    value: string;
    label_en: string;
    label_ru: string;
  }>;
}> {
  const base = getAstrologyApiBase();
  const url = `${base}/api/v1/astrology/event-types`;

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}

/**
 * Get retrograde planets
 */
export async function getRetrogradePlanets(date?: string): Promise<{
  date: string;
  retrograde_planets: Array<{
    planet: string;
    description_ru: string;
    description_en: string;
  }>;
}> {
  const base = getAstrologyApiBase();
  const searchParams = new URLSearchParams();
  if (date) searchParams.set('date', date);

  const url = `${base}/api/v1/astrology/retrograde?${searchParams.toString()}`;

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}
