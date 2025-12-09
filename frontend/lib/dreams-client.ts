/**
 * Dreams API Client
 *
 * Client for interacting with the dream analysis backend service.
 */

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

export interface DreamAnalysisResponse {
  status: 'success' | 'error';
  dream_id: string;
  analyzed_at: string;
  word_count: number;
  primary_emotion: string;
  emotion_intensity: number;
  symbols: DreamSymbol[];
  content_analysis: ContentAnalysis;
  lunar_context?: LunarContext;
  summary: string;
  interpretation: string;
  themes: string[];
  archetypes: string[];
  recommendations: string[];
  methodology: string;
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
  if (typeof window === 'undefined') {
    // Server-side
    return process.env.DREAMS_API_URL
      ?? process.env.NEXT_PUBLIC_API_URL
      ?? 'http://localhost:8000';
  }
  // Client-side
  return process.env.NEXT_PUBLIC_API_URL ?? '';
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
