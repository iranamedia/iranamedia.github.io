// Irana service worker: the app shell works offline; news and audio always come fresh from the network.
const SHELL = 'irana-shell-v3';
const FILES = ['./', 'index.html', 'irana.css', 'app.js', 'logo.jpg', 'icon-192.png', 'manifest.webmanifest'];
self.addEventListener('install', e => { e.waitUntil(caches.open(SHELL).then(c => c.addAll(FILES))); self.skipWaiting(); });
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== SHELL).map(k => caches.delete(k)))));
  self.clients.claim();
});
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin) return;
  if (url.pathname.endsWith('.mp3')) return;                       // audio: straight from the network
  if (url.pathname.endsWith('latest.json')) {                      // news: network first, last copy offline
    e.respondWith(fetch(e.request).then(r => { const c = r.clone(); caches.open(SHELL).then(s => s.put('latest.json', c)); return r; })
      .catch(() => caches.match('latest.json')));
    return;
  }
  e.respondWith(caches.match(e.request, { ignoreSearch: true }).then(r => r || fetch(e.request)));
});
