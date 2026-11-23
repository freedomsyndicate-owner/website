// FS TV MODE — navigasi remote (D-pad) + tampilan 10-foot untuk Android TV.
// Dipakai di semua halaman (index, hiburan, dst). Aktif otomatis kalau
// user-agent TV terdeteksi, atau kalau member menekan tombol "📺 TV".
// Pilihan tersimpan di localStorage 'fsTVMode' ('1'/'0'); ?tv=1 / ?tv=0
// memaksa sekali jalan. Di luar Mode TV, file ini tidak mengubah apa pun.
(function () {
  'use strict';

  var KEY = 'fsTVMode';
  var root = document.documentElement;

  function ua() { try { return navigator.userAgent || ''; } catch (e) { return ''; } }

  function isTVUA() {
    return /(android tv|google tv|smart[- ]?tv|aft[A-Z0-9]*|bravia|hbbtv|netcast|webos|tizen|viera|aquos|roku|fire tv|droidlogic|amlogic|opera tv|mibox|mi box|shield|b860h|s905|rk33|h96|tx3|mecool|ugoos|beelink|tanix|x96|hk1|\batv[0-9])/i.test(ua());
  }

  // Heuristik box Android TV generik: user-agent-nya sering polos tanpa kata
  // "TV" (mis. "Linux; Android 11; B860H ... wv"). Yang membedakan TV dari
  // HP/tablet Android: layar lebar + tidak ada sentuhan + tidak ada hover.
  // HP/tablet selalu punya sentuhan -> tidak kena. Laptop bukan Android.
  function isLikelyTV() {
    if (!/android/i.test(ua())) return false;
    var w = 0;
    try {
      w = Math.max(window.screen ? window.screen.width : 0, window.innerWidth || 0);
    } catch (e) {}
    if (w < 1280) return false;
    var touch = false;
    try { touch = (navigator.maxTouchPoints || 0) > 0 || 'ontouchstart' in window; } catch (e) {}
    if (touch) return false;
    try {
      if (window.matchMedia) {
        return window.matchMedia('(hover: none)').matches || window.matchMedia('(pointer: none)').matches;
      }
    } catch (e) {}
    return true;
  }

  function param(name) {
    try {
      var m = new RegExp('[?&]' + name + '=([^&]*)').exec(location.search || '');
      return m ? decodeURIComponent(m[1]) : null;
    } catch (e) { return null; }
  }

  function stored() {
    try { return localStorage.getItem(KEY); } catch (e) { return null; }
  }

  function shouldBeTV() {
    var p = param('tv');
    if (p === '1') return true;
    if (p === '0') return false;
    var s = stored();
    if (s === '1') return true;
    if (s === '0') return false;
    return isTVUA() || isLikelyTV();
  }

  // --- tombol toggle "📺 TV" (selalu ada, di semua halaman) ---
  function ensureToggle() {
    var b = document.getElementById('fsTvToggle');
    if (b) return b;
    b = document.createElement('button');
    b.id = 'fsTvToggle';
    b.type = 'button';
    b.setAttribute('aria-label', 'Mode TV untuk remote Android TV');
    b.addEventListener('click', function () { setTV(!root.classList.contains('tv-mode'), true); });
    document.body.appendChild(b);
    syncToggle();
    return b;
  }

  function syncToggle() {
    var b = document.getElementById('fsTvToggle');
    if (!b) return;
    var on = root.classList.contains('tv-mode');
    b.textContent = on ? '📺 TV: ON' : '📺 TV';
    b.setAttribute('aria-pressed', on ? 'true' : 'false');
  }

  // --- kursor ala Netflix: highlight mengambang yang meluncur halus ---
  // Bukan outline bawaan (yang loncat instan), tapi satu kotak emas yang
  // mengikuti elemen terfokus dengan transisi CSS + kartu ikut membesar.
  var cursorEl = null;
  var cursorTarget = null;
  var cursorRecheck = null;

  function ensureCursor() {
    var c = document.getElementById('fsTvCursor');
    if (c) { cursorEl = c; return c; }
    c = document.createElement('div');
    c.id = 'fsTvCursor';
    c.setAttribute('aria-hidden', 'true');
    document.body.appendChild(c);
    cursorEl = c;
    return c;
  }

  function positionCursor() {
    if (!root.classList.contains('tv-mode')) return;
    var c = ensureCursor();
    var el = document.activeElement;
    if (!el || el === document.body || !el.getBoundingClientRect) { c.style.display = 'none'; return; }
    var r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) { c.style.display = 'none'; return; }
    var pad = 7;
    c.style.display = 'block';
    c.style.left = (r.left - pad) + 'px';
    c.style.top = (r.top - pad) + 'px';
    c.style.width = (r.width + pad * 2) + 'px';
    c.style.height = (r.height + pad * 2) + 'px';
    if (cursorTarget && cursorTarget !== el) cursorTarget.classList.remove('fs-tv-focus');
    var isNew = cursorTarget !== el;
    cursorTarget = el;
    var tag = (el.tagName || '').toUpperCase();
    if (tag !== 'INPUT' && tag !== 'TEXTAREA' && tag !== 'SELECT' && !el.isContentEditable) {
      el.classList.add('fs-tv-focus');
    }
    // Kartu membesar pakai transisi 0.18s; baca ulang rect sekali setelah
    // selesai supaya kursor membungkus ukuran akhirnya, bukan sebelum scale.
    // Hanya dijadwalkan saat target baru (bukan tiap pemanggilan) supaya
    // tidak jadi timer berulang.
    if (isNew) {
      if (cursorRecheck) clearTimeout(cursorRecheck);
      cursorRecheck = setTimeout(function () { cursorRecheck = null; if (document.activeElement === el) positionCursor(); }, 200);
    }
  }

  function hideCursor() {
    if (cursorTarget) { cursorTarget.classList.remove('fs-tv-focus'); cursorTarget = null; }
    if (cursorEl) cursorEl.style.display = 'none';
  }

  // --- kartu <div onclick> dijadikan bisa difokus remote ---
  function enhance(el) {
    if (!el || el.nodeType !== 1) return;
    if (el.hasAttribute('onclick') && !el.hasAttribute('tabindex')) {
      el.setAttribute('tabindex', '0');
      el.setAttribute('role', 'button');
    }
    if (el.querySelectorAll) {
      var list = el.querySelectorAll('div[onclick]:not([tabindex])');
      for (var i = 0; i < list.length; i++) {
        list[i].setAttribute('tabindex', '0');
        list[i].setAttribute('role', 'button');
      }
    }
  }

  var observer = null;
  function watchCards() {
    if (observer || !window.MutationObserver) return;
    observer = new MutationObserver(function (muts) {
      for (var i = 0; i < muts.length; i++) {
        var added = muts[i].addedNodes;
        for (var j = 0; j < added.length; j++) enhance(added[j]);
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  // --- daftar elemen yang bisa difokus ---
  function focusables() {
    var sel = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
    var all = document.querySelectorAll(sel);
    var out = [];
    for (var i = 0; i < all.length; i++) {
      var el = all[i];
      if (el.closest('[hidden]')) continue;
      var r = el.getBoundingClientRect();
      // display:none = rect nol. Jangan pakai offsetParent: elemen di dalam
      // ancestor position:fixed (sidebar, modal detail) offsetParent-nya null
      // padahal terlihat dan harus bisa difokus remote.
      if (r.width === 0 && r.height === 0) continue;
      var vis = null;
      try { vis = getComputedStyle(el).visibility; } catch (e) {}
      if (vis === 'hidden') continue;
      out.push(el);
    }
    return out;
  }

  // --- navigasi spasial: panah pindah ke elemen terdekat di arah itu ---
  function move(dir) {
    var cur = document.activeElement;
    var els = focusables();
    if (!els.length) return;
    if (!cur || cur === document.body || els.indexOf(cur) === -1) {
      els[0].focus();
      try { els[0].scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'smooth' }); } catch (e) {}
      positionCursor();
      return;
    }
    var r = cur.getBoundingClientRect();
    var cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    var best = null, bestScore = Infinity;
    for (var i = 0; i < els.length; i++) {
      var el = els[i];
      if (el === cur) continue;
      var b = el.getBoundingClientRect();
      var ex = b.left + b.width / 2, ey = b.top + b.height / 2;
      var dx = ex - cx, dy = ey - cy;
      var primary, secondary;
      if (dir === 'left') { if (dx > -4) continue; primary = -dx; secondary = Math.abs(dy); }
      else if (dir === 'right') { if (dx < 4) continue; primary = dx; secondary = Math.abs(dy); }
      else if (dir === 'up') { if (dy > -4) continue; primary = -dy; secondary = Math.abs(dx); }
      else { if (dy < 4) continue; primary = dy; secondary = Math.abs(dx); }
      // Kerucut arah: jangan lompat ke elemen yang jauh menyamping.
      if (secondary > primary * 1.5 + 80) continue;
      var score = primary + secondary * 2.5;
      if (score < bestScore) { bestScore = score; best = el; }
    }
    if (best) {
      best.focus();
      try { best.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'smooth' }); } catch (e) {}
      positionCursor();
    }
  }

  function isTyping(el) {
    if (!el) return false;
    var t = (el.tagName || '').toUpperCase();
    return t === 'INPUT' || t === 'TEXTAREA' || t === 'SELECT' || el.isContentEditable;
  }

  function closeTopModal() {
    // Jangan pakai offsetParent: overlay position:fixed offsetParent-nya null
    // padahal terlihat. Cek display + rect saja.
    var det = document.getElementById('fsADetail');
    if (det && det.style.display !== 'none' && det.getBoundingClientRect().width > 0) {
      det.style.display = 'none';
      return true;
    }
    var cin = document.getElementById('fsCinemaDetail');
    if (cin && cin.style.display !== 'none' && cin.getBoundingClientRect().width > 0) {
      try {
        if (typeof window.fsCinemaCloseDetail === 'function') window.fsCinemaCloseDetail();
        else cin.style.display = 'none';
      } catch (e) { cin.style.display = 'none'; }
      return true;
    }
    var side = document.getElementById('sidebar');
    if (side && side.classList.contains('active')) {
      side.classList.remove('active');
      return true;
    }
    return false;
  }

  function onKey(e) {
    if (!root.classList.contains('tv-mode')) return;
    var k = e.key;
    var t = e.target;
    if (k === 'Escape' || k === 'BrowserBack') {
      if (isTyping(t)) { try { t.blur(); } catch (err) {} return; }
      if (closeTopModal()) { e.preventDefault(); e.stopPropagation(); }
      return;
    }
    if (isTyping(t)) return; // Panah di kolom teks = gerak kursor, jangan dibajak.
    if (k === 'ArrowLeft' || k === 'ArrowRight' || k === 'ArrowUp' || k === 'ArrowDown') {
      e.preventDefault(); e.stopPropagation();
      move(k === 'ArrowLeft' ? 'left' : k === 'ArrowRight' ? 'right' : k === 'ArrowUp' ? 'up' : 'down');
      return;
    }
    if (k === 'Enter' || k === ' ') {
      var el = document.activeElement;
      if (!el || el === document.body) return;
      var tag = (el.tagName || '').toUpperCase();
      // Tombol/link/input sudah ditangani browser; kartu div perlu klik manual.
      if (tag === 'DIV' || el.getAttribute('role') === 'button') {
        e.preventDefault(); e.stopPropagation();
        el.click();
      }
    }
  }

  function focusFirst() {
    var els = focusables();
    var strip = document.querySelector('.fs-tabstrip button');
    var target = strip || els[0];
    if (target) {
      try { target.focus(); target.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'smooth' }); } catch (e) {}
      positionCursor();
    }
  }

  function setTV(on, save) {
    if (on) {
      root.classList.add('tv-mode');
      enhance(document.body);
      watchCards();
      if (save) { try { localStorage.setItem(KEY, '1'); } catch (e) {} }
      syncToggle();
      setTimeout(focusFirst, 350);
      setTimeout(positionCursor, 500);
    } else {
      root.classList.remove('tv-mode');
      hideCursor();
      if (save) { try { localStorage.setItem(KEY, '0'); } catch (e) {} }
      syncToggle();
    }
  }

  function init() {
    ensureToggle();
    if (shouldBeTV()) setTV(true, false);
    document.addEventListener('keydown', onKey, true);
    // Kursor ikut setiap perpindahan fokus (termasuk fokus native WebView).
    document.addEventListener('focusin', function () { positionCursor(); });
    // Saat halaman bergeser (scroll halus), kursor ikut bergeser.
    var scrollT = null;
    window.addEventListener('scroll', function () {
      if (!root.classList.contains('tv-mode')) return;
      if (scrollT) return;
      scrollT = setTimeout(function () { scrollT = null; positionCursor(); }, 60);
    }, true);
    window.addEventListener('resize', function () { positionCursor(); });
    window.FS_TV = { setTV: setTV, isTV: function () { return root.classList.contains('tv-mode'); } };
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
