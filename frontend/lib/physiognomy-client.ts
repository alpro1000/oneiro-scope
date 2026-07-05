/**
 * Physiognomy API client — archive/scanner endpoint.
 *
 * Privacy-first: only 468-point landmark coordinates travel to the
 * backend; the camera frames never leave the device.
 */

import { resolveApiBase } from './api-base';

export interface ArchiveReading {
  system: string;
  topic: string;
  text: string;
  source: string;
  confidence: number;
  support?: string; // e.g. "5/5" — share of frames confirming the topic
}

export interface ArchiveResponse {
  frames_used: number;
  skipped: string[];
  metrics: Record<string, number | null>;
  stability: Record<
    string,
    { median: number; spread: number; frames: number; stable: boolean }
  >;
  primary_element: string | null;
  secondary_element: string | null;
  element_consensus: Record<string, number>;
  element_scores: { element: string; score: number }[];
  dominant_court: string | null;
  readings: ArchiveReading[];
  coverage: Record<string, string>;
  provenance: Record<string, string>;
  disclaimer: string;
}

function getPhysiognomyApiBase(): string {
  const isServer = typeof window === 'undefined';
  return resolveApiBase({
    serviceName: 'Physiognomy API',
    isServer,
    serverEnvVars: [process.env.NEXT_PUBLIC_API_URL],
    clientEnvVars: [process.env.NEXT_PUBLIC_API_URL],
    relativeFallback: '/api',
  });
}

export async function analyzeFaceArchive(
  frames: number[][][],
  locale: string
): Promise<ArchiveResponse> {
  const base = getPhysiognomyApiBase();
  const response = await fetch(`${base}/api/v1/physiognomy/analyze-archive`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({ frames, locale }),
  });

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `API error: ${response.status}`);
  }
  return response.json();
}
