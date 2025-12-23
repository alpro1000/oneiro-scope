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
  planet1: string;
  planet2: string;
  aspect_type: string;
  angle: number;
  orb: number;
  applying: boolean;
}

export interface NatalChartResponse {
  status: 'success' | 'error';
  birth_data: {
    date: string;
    time?: string;
    place: string;
    coords: { lat: number; lon: number };
    timezone: string;
  };
  planets: PlanetPosition[];
  houses?: Array<{ number: number; sign: string; degree: number }>;
  aspects: Aspect[];
  sun_sign: string;
  moon_sign: string;
  ascendant?: string;
  interpretation?: string;
  calculated_at: string;
}

export interface HoroscopeResponse {
  status: 'success' | 'error';
  period: string;
  period_start: string;
  period_end: string;
  sun_sign?: string;
  moon_sign?: string;
  current_transits: Array<{
    planet: string;
    sign: string;
    degree: number;
    retrograde: boolean;
  }>;
  retrograde_planets: string[];
  lunar_phase: string;
  lunar_day: number;
  summary: string;
  sections?: {
    general?: string;
    personal?: string;
    social?: string;
    warnings?: string;
  };
  recommendations: string[];
  generated_at: string;
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
  status: 'success' | 'error';
  event_date: string;
  event_type: string;
  favorability_score: number;
  level: string;
  positive_factors: string[];
  risk_factors: string[];
  recommendations: string[];
  alternative_dates: string[];
  interpretation: string;
  calculated_at: string;
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
