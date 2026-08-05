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
  /** "background" marks a width-family reading the backend itself flags as
   *  lens-sensitive (close phone range inflates face width). Must be shown
   *  de-emphasised — not silently mixed in with the robust ones. */
  scope?: string;
}

/** The backend's own reconciled verdict per dimension — the layer it trusts
 *  most. The frontend used to drop it and render only the raw readings. */
export interface ArchiveTrait {
  dimension: string;
  label: string;
  verdict: string;
  verdict_label: string;
  score: number;
  conflicted: boolean;
  evidence: string[];
  /** What is missing before this dimension can be read at all. */
  needed: string[];
}

/** Lens-ROBUST deviations from neutral: deliberately excludes the width
 *  family, which is why it is the honest headline. */
export interface ArchiveSignatureItem {
  metric: string;
  median: number;
  neutral: number;
  deviation_units: number;
}

export interface ArchiveResponse {
  frames_used: number;
  skipped: string[];
  metrics: Record<string, number | null>;
  traits: ArchiveTrait[];
  signature: ArchiveSignatureItem[];
  /** Why the width-family readings are caveated; empty when not applicable. */
  lens_note: string;
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
