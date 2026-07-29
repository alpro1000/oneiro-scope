/**
 * Offline storage for chart cores, shared by every prototype page.
 *
 * Hand-written, not generated — `chart-kit.js` next to it is an esbuild
 * bundle and CI checks it against its source; this file has no source
 * but itself.
 *
 * A `chart_core` is ~1.7 KB and is everything a page needs, so storing
 * one makes the whole app work with no network. IndexedDB rather than
 * localStorage: localStorage is synchronous on the main thread and a
 * list of saved charts will outgrow what it is meant to hold.
 */

const DB_NAME = 'oneiroscope';
const STORE = 'charts';

function openDb() {
  return new Promise((resolve, reject) => {
    const rq = indexedDB.open(DB_NAME, 1);
    rq.onupgradeneeded = () => rq.result.createObjectStore(STORE, { keyPath: 'id' });
    rq.onsuccess = () => resolve(rq.result);
    rq.onerror = () => reject(rq.error);
  });
}

/** Identity is the birth instant and place — the same chart, once. */
export const chartId = (c) => `${c.birth.utc}|${c.birth.lat}|${c.birth.lon}`;

/**
 * Store a core for offline use.
 *
 * Resolves to null on success, or to a human-readable reason when the
 * browser refused. Storage is a convenience, not the computation: a
 * private-mode browser that blocks IndexedDB still gets a working chart,
 * it just will not have it next time. The caller is handed the reason so
 * it can say so — never swallowed (conventions.md §12).
 */
export async function saveChart(core) {
  try {
    const db = await openDb();
    await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, 'readwrite');
      tx.objectStore(STORE).put({
        id: chartId(core), core, saved_at: new Date().toISOString(),
      });
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error);
    });
    return null;
  } catch (err) {
    console.warn('Карта не сохранена для офлайна:', err);
    return String(err && err.message ? err.message : err);
  }
}

/** The most recently saved core, or null if there is none. */
export async function lastChart() {
  try {
    const db = await openDb();
    return await new Promise((resolve, reject) => {
      const rq = db.transaction(STORE, 'readonly').objectStore(STORE).getAll();
      rq.onsuccess = () => {
        const all = rq.result || [];
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
 * Throws with the server's own message on failure rather than returning
 * a blank chart: a natal chart nobody computed must never look like one
 * somebody did.
 */
export async function fetchChart(apiBase, payload) {
  const res = await fetch(`${apiBase.replace(/\/$/, '')}/chart`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json();
}

/** Register the service worker, if the browser has one. */
export function registerServiceWorker() {
  if (!('serviceWorker' in navigator)) return;
  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register('/sw.js')
      .catch((err) => console.warn('SW не зарегистрирован:', err));
  });
}
