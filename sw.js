// FS PWA — service worker: cache shell situs + data Qur'an, cache jawaban
// API Qur'an/jadwal sholat yang sudah pernah dimuat (offline). Jangan
// sentuh stream audio/video, APK, atau request non-GET.
// FS-TV-CLEAN 20 Nov 2026: fs-v2 -> fs-v3 supaya semua browser pengunjung
// langsung mengambil hiburan.html baru (daftar TV bersih); cache lama dihapus
// otomatis saat aktivasi. FS TV MODE 22 Nov 2026: fs-v3 -> fs-v4 (tv.js baru).
// FS TV MODE v2.1 23 Nov 2026: fs-v5 -> fs-v6 (perbaiki tv.js: kartu
// film/musik yang dibuat lewat `card.onclick = ...` kini bisa difokus remote;
// tanpa bump ini TV tetap pakai tv.js lama dari cache).
// MUSIK #6 28 Nov 2026: fs-v9 -> fs-v10 (Media Session API: musik & film
// tetap jalan saat HP buka aplikasi lain + kontrol layar kunci; tanpa bump
// ini HP bisa tetap memegang hiburan.html lama dari cache).
var FS_CACHE = 'fs-v10';
var FS_SHELL = [
  '/', '/index.html', '/hiburan.html', '/tools.html', '/ibadah.html',
  '/ai.html', '/trading.html', '/lainnya.html', '/garapan.html', '/journal.html',
  '/style.css', '/tv.js', '/manifest.webmanifest', '/icon-192.png', '/icon-512.png'
];
// Muat halaman juga pakai cache:'no-cache' supaya fetch service worker tidak
// memakai salinan HTTP lama (GitHub Pages max-age=600) — update halaman jadi
// langsung tampil, bukan 10 menit kemudian.
// Data Qur'an lokal (Arab + Latin + terjemahan ID, ~3,1 MB / ~0,8 MB gzip).
// Diunduh sekali saat install; kalau gagal (mis. koneksi putus), install
// tetap lanjut dan file dimuat malas oleh tab Qur'an lalu tersimpan di cache.
var FS_QURAN_DATA = '/data/quran.json';
// Host API yang jawabannya boleh disimpan untuk offline (GET saja).
var FS_API_HOSTS = [
  'api.alquran.cloud', 'api.myquran.com', 'api.aladhan.com',
  'fonts.googleapis.com', 'fonts.gstatic.com'
];
self.addEventListener('install', function(e){
  e.waitUntil(
    caches.open(FS_CACHE).then(function(c){ return c.addAll(FS_SHELL); })
      .then(function(){ return caches.open(FS_CACHE).then(function(c){ return c.add(FS_QURAN_DATA).catch(function(){}); }); })
      .then(function(){ return self.skipWaiting(); })
  );
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
  // API Qur'an / jadwal sholat / font: cache dulu, perbarui di belakang
  // layar — yang pernah dimuat sekali tetap tampil saat offline.
  if (url.origin !== self.location.origin) {
    if (FS_API_HOSTS.indexOf(url.hostname) !== -1) {
      e.respondWith(caches.open(FS_CACHE).then(function(c){
        return c.match(req).then(function(cached){
          var net = fetch(req).then(function(res){
            if (res && res.ok) { var copy = res.clone(); c.put(req, copy); }
            return res;
          }).catch(function(){ return cached; });
          return cached || net;
        });
      }));
    }
    return;
  }
  if (url.pathname.endsWith('.apk')) return;
  if (req.headers.get('range')) return;
  var isPage = req.mode === 'navigate' || url.pathname.endsWith('.html') || url.pathname === '/';
  if (isPage) {
    // Halaman: jaringan dulu, cache sebagai cadangan (supaya update langsung tampil).
    // cache:'no-cache' = selalu tanya server (304 kalau belum berubah), jangan
    // pakai salinan HTTP lama — kalau tidak, push halaman baru baru tampil
    // setelah cache browser kedaluwarsa.
    e.respondWith(fetch(req, {cache: 'no-cache'}).then(function(res){
      var copy = res.clone();
      caches.open(FS_CACHE).then(function(c){ c.put(req, copy); });
      return res;
    }).catch(function(){ return caches.match(req).then(function(r){ return r || caches.match('/index.html'); }); }));
  } else {
    // Aset statis (termasuk data/quran.json): cache dulu, perbarui di belakang layar.
    e.respondWith(caches.match(req).then(function(cached){
      var net = fetch(req).then(function(res){
        if (res && res.ok) { var copy = res.clone(); caches.open(FS_CACHE).then(function(c){ c.put(req, copy); }); }
        return res;
      }).catch(function(){ return cached; });
      return cached || net;
    }));
  }
});
