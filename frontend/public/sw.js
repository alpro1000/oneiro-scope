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

const VERSION = 'v5';
const SHELL_CACHE = `oneiro-shell-${VERSION}`;

// Kept deliberately small: the shell plus the kit is all that is needed
// to render a stored chart. Map tiles are third-party and stay
// runtime-cached only, so a first offline visit degrades to no basemap
// rather than to a wrong chart.
const SHELL = [
  '/',
  // Both static prototypes (the natal wheel and astrocartography) are now
  // Next routes at /<locale>/natal and /<locale>/astrocartography. They and
  // their chunks — including the bundled chart-kit and its own canvas basemap
  // — are runtime-cached by the fetch handler like any app navigation, not
  // precached here. The vendored kit below is kept for the drift check only.
  '/vendor/chart-kit.js',
  '/vendor/chart-store.js',
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

/** A real Response saying WHY there is nothing to show. A rejected
 *  respondWith would surface the browser's own network error instead, which
 *  tells the user nothing — and the first offline visit, with nothing cached,
 *  is exactly when that happens. */
function offlineResponse() {
  return new Response(
    'Офлайн, и эта страница ещё не сохранена. ' +
      'Откройте приложение один раз с сетью — после этого ' +
      'сохранённая карта работает без неё.',
    {
      status: 503,
      statusText: 'Offline and not cached',
      headers: { 'Content-Type': 'text/plain; charset=utf-8' },
    },
  );
}

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Chart computation: network only. There is no honest offline answer.
  if (request.method !== 'GET' || url.pathname.startsWith('/api/')) {
    return;
  }

  // Navigations (HTML documents): NETWORK FIRST, cache only as the offline
  // fallback.
  //
  // A document is the one thing here that is NOT content-addressed: its URL
  // stays /ru/face across every deploy while the hashed chunk names inside it
  // change. Serving it cache-first pinned a returning visitor to whichever
  // build they last saw and made every deploy invisible for at least one
  // visit — a shipped fix would sit there while the old bundle kept running
  // (exactly how the self-hosted face-model fix stayed unseen behind a page
  // cached one deploy earlier). Network-first keeps the offline promise: the
  // cached copy still answers when the network does not.
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response.ok && url.origin === self.location.origin) {
            const copy = response.clone();
            caches.open(SHELL_CACHE).then((cache) => cache.put(request, copy));
          }
          return response;
        })
        .catch(() =>
          caches.match(request).then((cached) => cached || offlineResponse()),
        ),
    );
    return;
  }

  // Everything else — hashed Next chunks, the vendored kit, the face model and
  // wasm — is content-addressed or version-pinned, so cache-first is both safe
  // and the reason a stored chart still opens with the radio off.
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
        .catch(() => cached || offlineResponse());
      return cached || network;
    }),
  );
});
