/* Sharingan Draft Board — offline-ready service worker.
   NETWORK-FIRST for the shell + data: every load pulls the latest build (and the freshest
   news/mocks/myguys data) when online; the cache is only the OFFLINE fallback for draft day.
   Versioned cache name — bump CACHE to force a clean purge on deploy. */
const CACHE = 'ffb-sharingan-v2';
const ASSETS = [
  './', './index.html', './sw.js',
  './data/board.json', './data/mocks.json', './data/myguys.json',
  './data/news.json', './data/injury.json', './data/rankings.json',
  './data/players.json', './data/rookies.json', './data/expert_lists.json', './data/context_notes.json'
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});
self.addEventListener('fetch', e => {
  const u = new URL(e.request.url);
  if (e.request.method !== 'GET' || u.origin !== location.origin) return;
  if (u.pathname.includes('test_harness')) return; // never cache the test page
  const navigate = e.request.mode === 'navigate';
  // network-first: fresh build/data when online, cache fallback when offline
  e.respondWith(
    fetch(e.request).then(res => {
      if (res.ok) {
        const copy = res.clone();
        caches.open(CACHE).then(c => c.put(e.request, copy));
      }
      return res;
    }).catch(() =>
      caches.match(e.request).then(hit => hit || (navigate ? caches.match('./index.html') : undefined))
    )
  );
});
