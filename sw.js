// FS PWA — service worker: cache shell situs, jangan sentuh API/stream luar.
var FS_CACHE = 'fs-v1';
var FS_SHELL = [
  '/', '/index.html', '/hiburan.html', '/tools.html', '/ibadah.html',
  '/ai.html', '/trading.html', '/lainnya.html', '/garapan.html', '/journal.html',
  '/style.css', '/manifest.webmanifest', '/icon-192.png', '/icon-512.png'
];
self.addEventListener('install', function(e){
  e.waitUntil(caches.open(FS_CACHE).then(function(c){ return c.addAll(FS_SHELL); }).then(function(){ return self.skipWaiting(); }));
});
self.addEventListener('activate', function(e){
  e.waitUntil(caches.keys().then(function(keys){
    return Promise.all(keys.filter(function(k){ return k !== FS_CACHE; }).map(function(k){ return caches.delete(k); }));
  }).then(function(){ return self.clients.claim(); }));
});
self.addEventListener('fetch', function(e){
  var req = e.request;
  if (req.method !== 'GET') return;
  var url = new URL(req.url);
  // Hanya layani asal sendiri; API, stream, audio, dan APK lewat tanpa disentuh.
  if (url.origin !== self.location.origin) return;
  if (url.pathname.endsWith('.apk')) return;
  if (req.headers.get('range')) return;
  var isPage = req.mode === 'navigate' || url.pathname.endsWith('.html') || url.pathname === '/';
  if (isPage) {
    // Halaman: jaringan dulu, cache sebagai cadangan (supaya update langsung tampil).
    e.respondWith(fetch(req).then(function(res){
      var copy = res.clone();
      caches.open(FS_CACHE).then(function(c){ c.put(req, copy); });
      return res;
    }).catch(function(){ return caches.match(req).then(function(r){ return r || caches.match('/index.html'); }); }));
  } else {
    // Aset statis: cache dulu, perbarui di belakang layar.
    e.respondWith(caches.match(req).then(function(cached){
      var net = fetch(req).then(function(res){
        if (res && res.ok) { var copy = res.clone(); caches.open(FS_CACHE).then(function(c){ c.put(req, copy); }); }
        return res;
      }).catch(function(){ return cached; });
      return cached || net;
    }));
  }
});
