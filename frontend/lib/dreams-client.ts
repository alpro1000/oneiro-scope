/**
 * Dreams API Client
 *
 * Client for interacting with the dream analysis backend service.
 */

import { resolveApiBase } from './api-base';

// Types for API requests/responses
export interface DreamAnalysisRequest {
  dream_text: string;
  dream_date?: string;  // YYYY-MM-DD
  dreamer_gender?: 'male' | 'female' | 'other';
  dreamer_age_group?: 'child' | 'teen' | 'adult' | 'senior';
  locale?: string;
}

export interface DreamSymbol {
  symbol: string;
  category: string;
  frequency: number;
  significance: number;
  interpretation_ru: string;
  interpretation_en: string;
  archetype?: string;
}

export interface ContentAnalysis {
  male_characters: number;
  female_characters: number;
  animal_characters: number;
  friendly_interactions: number;
  aggressive_interactions: number;
  sexual_interactions: number;
  successes: number;
  failures: number;
  misfortunes: number;
  good_fortunes: number;
  positive_emotions: number;
  negative_emotions: number;
  male_female_ratio?: number;
  aggression_friendliness_ratio?: number;
  success_failure_ratio?: number;
}

export interface LunarContext {
  lunar_day: number;
  lunar_phase: string;
  moon_sign?: string;
  interpretation_ru: string;
  interpretation_en: string;
}

/** One structurally coded HVdC event with the clause it was coded from.
 *  This is the provenance behind every ContentAnalysis count — confidence is
 *  always 1.0 because the coding is deterministic, not inferred. */
export interface HvdcEvent {
  category: string;
  subtype: string;
  actor: string;
  target?: string | null;
  evidence: string;
  source: string;
  confidence: number;
}

export interface NormDeviation {
  indicator: string;
  user_value: number;
  norm_value: number;
  deviation: number;
  /** percentage_points | ratio — never assume one; the units differ per indicator. */
  deviation_unit: string;
  significance: string;
  description_ru: string;
  description_en: string;
  events_observed: number;
  min_events_required?: number;
}

export interface NormComparisonResult {
  gender_used: string;
  method_note_ru?: string | null;
  method_note_en?: string | null;
  /** null when no indicator passed the data threshold — an uncomputed score
   *  is NOT a perfect 100, and must not be rendered as one. */
  overall_typicality?: number | null;
  typicality_warning_ru?: string | null;
  typicality_warning_en?: string | null;
  deviations: NormDeviation[];
}

export interface DreamAnalysisResponse {
  status: 'success' | 'error';
  dream_id: string;
  analyzed_at: string;
  word_count: number;
  primary_emotion: string;
  emotion_intensity: number;
  symbols: DreamSymbol[];
  content_analysis: ContentAnalysis;
  /** Per-event evidence behind the content_analysis counts. The frontend used
   *  to drop this along with norm_comparison/disclaimer/degraded — i.e. it hid
   *  the deterministic layer and showed only the LLM prose. */
  hvdc_evidence?: HvdcEvent[];
  hvdc_coder_version?: string | null;
  norm_comparison?: NormComparisonResult | null;
  lunar_context?: LunarContext;
  summary: string;
  interpretation: string;
  themes: string[];
  archetypes: string[];
  recommendations: string[];
  methodology: string;
  /** Required on every dreams response (reflective/entertainment framing). */
  disclaimer?: string | null;
  /** Explicit degradation ledger ('field: reason'). Empty = full data.
   *  Shown, never swallowed — silent nulls are banned (conventions.md §12). */
  degraded?: string[];
}

export interface DreamCategory {
  value: string;
  description_en: string;
  description_ru: string;
}

export interface DreamArchetype {
  id: string;
  name: string;
  description: string;
}

// API base URL resolution
function getDreamsApiBase(): string {
  const isServer = typeof window === 'undefined';

  return resolveApiBase({
    serviceName: 'Dreams API',
    isServer,
    serverEnvVars: [process.env.DREAMS_API_URL, process.env.NEXT_PUBLIC_API_URL],
    clientEnvVars: [process.env.NEXT_PUBLIC_API_URL],
    relativeFallback: '/api',
  });
}

/**
 * Analyze a dream
 */
export async function analyzeDream(
  request: DreamAnalysisRequest
): Promise<DreamAnalysisResponse> {
  const base = getDreamsApiBase();
  const url = `${base}/api/v1/dreams/analyze`;

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
 * Get list of dream content categories
 */
export async function getDreamCategories(): Promise<{
  categories: DreamCategory[];
  methodology: string;
}> {
  const base = getDreamsApiBase();
  const url = `${base}/api/v1/dreams/categories`;

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
 * Get list of common dream symbols
 */
export async function getDreamSymbols(locale: string = 'ru'): Promise<{
  symbols: Array<{
    id: string;
    category: string;
    interpretation: string;
    archetype?: string;
    significance: number;
  }>;
  count: number;
}> {
  const base = getDreamsApiBase();
  const url = `${base}/api/v1/dreams/symbols?locale=${locale}`;

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
 * Get list of Jungian archetypes
 */
export async function getDreamArchetypes(locale: string = 'ru'): Promise<{
  archetypes: DreamArchetype[];
}> {
  const base = getDreamsApiBase();
  const url = `${base}/api/v1/dreams/archetypes?locale=${locale}`;

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
