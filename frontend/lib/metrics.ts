/**
 * Anonymous funnel counters — first-party, no identifiers, no cookies.
 *
 * The whole privacy claim of this product's analytics rests on what this file
 * does NOT do, so read it as a list of absences:
 *
 * - it never generates or reads a user id, session id, device id or cookie;
 * - it sends exactly two fields — an event name from a closed list, and one
 *   boolean the browser worked out for itself;
 * - it talks only to this service's own API, so no third party ever learns a
 *   visitor exists;
 * - it fails silently and never blocks, because a counter must not be able to
 *   break the page it is counting.
 *
 * The one thing kept on the device is a date string: the day this browser was
 * last seen. It is what makes "came back on another day" countable without
 * anybody being identified — the comparison happens here, and the server
 * receives a yes/no that cannot be traced to a visitor. It is also why the
 * privacy policy mentions device storage explicitly.
 */

import { resolveApiBase } from '@/lib/api-base';

/** The closed list, mirrored from `backend/services/metrics/funnel.py`. */
export type FunnelEvent =
  | 'face_result_shown'
  | 'birth_date_entered'
  | 'natal_computed'
  | 'share_clicked'
  | 'dream_analyzed';

const SEEN_KEY = 'oneiro.lastSeenDay';

const today = (): string => new Date().toISOString().slice(0, 10);

/**
 * Has this browser been here on an EARLIER day?
 *
 * Stamps today's date as a side effect, so the first visit answers false and
 * a visit on any later day answers true. Only the date is kept — not a count,
 * not a history, nothing that describes a person's pattern of use.
 */
export function isReturningVisitor(now: string = today()): boolean {
  try {
    const last = window.localStorage.getItem(SEEN_KEY);
    if (last !== now) window.localStorage.setItem(SEEN_KEY, now);
    return Boolean(last) && last !== now;
  } catch {
    // Private mode, storage disabled, embedded webview. A visitor we cannot
    // recognise counts as new — undercounting returns is the honest failure
    // direction; the alternative would be inventing an identifier.
    return false;
  }
}

/**
 * Record one event. Fire-and-forget: never awaited, never throws, never
 * delays a render. A failed counter is a lost number, not a broken page.
 */
export function track(event: FunnelEvent): void {
  if (typeof window === 'undefined') return;
  const body = JSON.stringify({ event, returning: isReturningVisitor() });
  try {
    // `resolveApiBase` throws when the deployment has no API URL configured.
    // That is correct for a feature the user is waiting on and wrong here, so
    // it is inside the same try that swallows a failed request.
    const base = resolveApiBase({
      serviceName: 'Metrics API',
      isServer: false,
      serverEnvVars: [process.env.NEXT_PUBLIC_API_URL],
      clientEnvVars: [process.env.NEXT_PUBLIC_API_URL],
      relativeFallback: '/api',
    });
    void fetch(`${base}/api/v1/metrics/event`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body,
      // No credentials: this request must not carry a session cookie, which
      // would attach an identity to a measurement that has none.
      credentials: 'omit',
      keepalive: true,
    }).catch(() => undefined);
  } catch {
    /* counting must never surface to the person being counted */
  }
}
