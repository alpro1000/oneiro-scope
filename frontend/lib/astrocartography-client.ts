/**
 * Astrocartography API Client
 *
 * Client for the interactive relocation-astrology map: fetches the ACG
 * line set (GeoJSON) for a birth chart, and inspects a single clicked
 * point for its four angles + a plain-language summary.
 */

import { resolveApiBase } from './api-base';

export interface AstrocartographyBirthInput {
  birth_date: string; // YYYY-MM-DD
  birth_time?: string; // HH:MM
  birth_timezone: string; // IANA name, e.g. 'Europe/Kyiv'
  birth_lat: number;
  birth_lon: number;
  birth_place?: string;
}

export interface AcgLineFeature {
  type: 'Feature';
  properties: { planet: string; angle: 'MC' | 'IC' | 'Asc' | 'Desc' };
  geometry: { type: 'LineString'; coordinates: [number, number][] };
}

export interface AstrocartographyChartResponse {
  layer: string;
  methodology: string;
  chart: {
    gmst: number;
    obliquity: number;
    planets: Record<string, { ecl_lon: number; ra: number; dec: number }>;
    birth: { lat: number; lon: number; name: string };
  };
  lines: {
    type: 'FeatureCollection';
    features: AcgLineFeature[];
  };
  disclaimer: string;
}

export interface AngleContact {
  planet: string;
  angle: 'MC' | 'IC' | 'Asc' | 'Desc';
  orb_deg: number;
  planet_longitude: number;
  angle_longitude: number;
}

export interface RelocationSummary {
  plain: string;
  work: string[];
  home: string[];
  relationships: string[];
  tension: string[];
  clean: boolean;
  luck: string[];
  confidence: number;
  source: string;
}

export interface AstrocartographyPointResponse {
  location: { lat: number; lon: number };
  angles: { asc: number; mc: number; ic: number; desc: number };
  contacts: AngleContact[];
  score: number;
  summary: RelocationSummary;
  disclaimer: string;
}

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

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const base = getAstrologyApiBase();
  const response = await fetch(`${base}/api/v1/astrology${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `API error: ${response.status}`);
  }

  return response.json();
}

/**
 * Fetch the full ACG line set (GeoJSON) + chart geometry for a birth moment.
 */
export async function getAstrocartographyChart(
  birth: AstrocartographyBirthInput
): Promise<AstrocartographyChartResponse> {
  return postJson<AstrocartographyChartResponse>('/astrocartography/chart', birth);
}

/**
 * Relocate the chart to a clicked point and return its angles + summary.
 */
export async function inspectAstrocartographyPoint(
  birth: AstrocartographyBirthInput,
  point: { lat: number; lon: number; locale?: string }
): Promise<AstrocartographyPointResponse> {
  return postJson<AstrocartographyPointResponse>('/astrocartography/point', {
    ...birth,
    ...point,
  });
}
