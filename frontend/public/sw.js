/**
 * Service worker: the app shell offline, the ephemeris never faked.
 *
 * What can be cached is a product decision, not a caching detail:
 *
 * - The shell and chart-kit are cached aggressively. Once a chart_core
 *   is in IndexedDB, every angle, cusp, aspect and astrocartography
 *   line is recomputed locally, so the whole exploration works with the
 *   radio off.
 * - `POST /api/v1/chart` is NEVER served from cache and never faked. A
 *   new chart needs a real ephemeris computation; answering offline
 *   with a stale or invented one would be the silent degradation the
 *   project bans (conventions.md §12). Offline, the request fails and
 *   the page says so.
 */

const VERSION = 'v1';
const SHELL_CACHE = `oneiro-shell-${VERSION}`;

// Kept deliberately small: the shell plus the kit is all that is needed
// to render a stored chart. Map tiles are third-party and stay
// runtime-cached only, so a first offline visit degrades to no basemap
// rather than to a wrong chart.
const SHELL = [
  '/',
  '/astrocartography.html',
  '/vendor/chart-kit.js',
  // Leaflet is vendored precisely so it can live here: a CDN copy could
  // not be cached (cross-origin responses are opaque) and the map would
  // silently fail to render offline while everything else worked.
  '/vendor/leaflet/leaflet.js',
  '/vendor/leaflet/leaflet.css',
  '/manifest.json',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(SHELL_CACHE)
      // addAll is all-or-nothing; a single 404 would leave no cache at
      // all, so each entry is added independently and best-effort.
      .then((cache) => Promise.allSettled(SHELL.map((url) => cache.add(url))))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((k) => k.startsWith('oneiro-shell-') && k !== SHELL_CACHE)
            .map((k) => caches.delete(k)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Chart computation: network only. There is no honest offline answer.
  if (request.method !== 'GET' || url.pathname.startsWith('/api/')) {
    return;
  }

  // Shell and kit: cache first, refreshed in the background so a new
  // chart-kit build reaches users without a hard reload.
  event.respondWith(
    caches.match(request).then((cached) => {
      const network = fetch(request)
        .then((response) => {
          if (response.ok && url.origin === self.location.origin) {
            const copy = response.clone();
            caches.open(SHELL_CACHE).then((cache) => cache.put(request, copy));
          }
          return response;
        })
        .catch(() => cached);
      return cached || network;
    }),
  );
});
