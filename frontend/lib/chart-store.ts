/**
 * Chart-core fetch + offline storage for the Next app.
 *
 * A `chart_core` is ~1.7 KB and is everything a screen needs: from it
 * `@oneiroscope/chart-kit` derives angles, cusps, aspects, dignities and
 * astrocartography for any point on Earth with no further network. So one
 * stored core makes the whole natal screen work with the radio off.
 *
 * This is the typed, in-bundle sibling of `public/vendor/chart-store.js`
 * (which serves the static prototype pages). The prototypes reach it over
 * a `<script type=module>`; the routes import it here. The one call that
 * needs the server — `fetchChart` — is the single paid door, so it carries
 * the account bearer and surfaces the gate's structured 401/402 rather
 * than inventing a chart nobody computed.
 */

import type { ChartCore } from '@oneiroscope/chart-kit';

import { resolveApiBase } from './api-base';
import { authHeaders } from './auth-client';

/** ±HH:MM engine + citations the server stamps onto a computed chart. */
export interface ChartProvenance {
  ephemeris_engine: string;
  ephemeris_version: string;
  accuracy: string;
  sidereal_time: string;
}

/** Both transports return this; see `backend/.../chart_contract.py`. */
export interface ChartResponse {
  chart_core: ChartCore;
  provenance: ChartProvenance;
  how_to_read: string;
  disclaimer: string;
}

/** The structured refusal body the gate returns on 401/402. */
export interface GateDetail {
  error: string;
  reason?: string;
  message?: string;
  reset_at?: string | null;
  account_url?: string;
  tier_required?: string;
  allowance?: { kind: string; free: number; period: string };
}

/** A fetch failure that carries the HTTP status and the gate's detail. */
export class ChartFetchError extends Error {
  status: number;
  detail: GateDetail | null;
  constructor(message: string, status: number, detail: GateDetail | null) {
    super(message);
    this.name = 'ChartFetchError';
    this.status = status;
    this.detail = detail;
  }
}

export interface ChartRequestPayload {
  birth_date: string;
  birth_time?: string | null;
  birth_place?: string;
  latitude?: number | null;
  longitude?: number | null;
  timezone_name?: string | null;
  house_system?: string;
  locale?: string;
}

const DB_NAME = 'oneiroscope';
const STORE = 'charts';

/** Identity is the birth instant and place — the same chart, once. */
export const chartId = (c: ChartCore): string =>
  `${c.birth.utc}|${c.birth.lat}|${c.birth.lon}`;

function chartApiBase(): string {
  const isServer = typeof window === 'undefined';
  return resolveApiBase({
    serviceName: 'Chart API',
    isServer,
    serverEnvVars: [process.env.CHART_API_URL, process.env.NEXT_PUBLIC_API_URL],
    clientEnvVars: [process.env.NEXT_PUBLIC_API_URL],
    relativeFallback: '/api',
  });
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const rq = indexedDB.open(DB_NAME, 1);
    rq.onupgradeneeded = () =>
      rq.result.createObjectStore(STORE, { keyPath: 'id' });
    rq.onsuccess = () => resolve(rq.result);
    rq.onerror = () => reject(rq.error);
  });
}

/**
 * Store a core for offline use.
 *
 * Resolves to null on success, or to a human-readable reason when the
 * browser refused. Storage is a convenience, not the computation: a
 * private-mode browser that blocks IndexedDB still gets a working chart,
 * it just will not have it next time. The reason is handed back so the
 * caller can say so — never swallowed (conventions.md §12).
 */
export async function saveChart(core: ChartCore): Promise<string | null> {
  try {
    const db = await openDb();
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE, 'readwrite');
      tx.objectStore(STORE).put({
        id: chartId(core),
        core,
        saved_at: new Date().toISOString(),
      });
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
    return null;
  } catch (err) {
    const reason = err instanceof Error ? err.message : String(err);
    console.warn('Карта не сохранена для офлайна:', reason);
    return reason;
  }
}

/** The most recently saved core, or null if there is none. */
export async function lastChart(): Promise<ChartCore | null> {
  try {
    const db = await openDb();
    return await new Promise<ChartCore | null>((resolve, reject) => {
      const rq = db.transaction(STORE, 'readonly').objectStore(STORE).getAll();
      rq.onsuccess = () => {
        const all = (rq.result || []) as Array<{ core: ChartCore; saved_at: string }>;
        all.sort((a, b) => (a.saved_at < b.saved_at ? 1 : -1));
        resolve(all.length ? all[0].core : null);
      };
      rq.onerror = () => reject(rq.error);
    });
  } catch {
    return null;
  }
}

/**
 * Ask the server for a chart. The one call that needs the network.
 *
 * Throws {@link ChartFetchError} with the server's own message on failure
 * rather than returning a blank chart: a natal chart nobody computed must
 * never look like one somebody did. On a gate refusal (401 account_required
 * / 402 entitlement_required) the error carries `.status` and the server's
 * structured `.detail`, so the screen shows the factual limit and the
 * account link — not a raw HTTP string.
 *
 * The account bearer, when present, rides along: the chart endpoint
 * requires an account, since "one chart forever" is a promise about one.
 */
export async function fetchChart(
  payload: ChartRequestPayload,
): Promise<ChartResponse> {
  const res = await fetch(`${chartApiBase()}/api/v1/chart`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...authHeaders(),
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    let detail: GateDetail | null = null;
    try {
      detail = ((await res.json()) as { detail?: GateDetail }).detail ?? null;
    } catch {
      /* non-JSON error body — leave detail null, status still speaks */
    }
    throw new ChartFetchError(
      detail?.message || `Не удалось получить карту (${res.status})`,
      res.status,
      detail,
    );
  }
  return res.json();
}
