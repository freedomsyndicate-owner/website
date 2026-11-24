// FS AI Worker — proxy Chat Ai FREEDOM SYNDICATE ke SinarCloud.
//
// Cara kerja: tab Chat Ai di website memanggil Worker ini (POST JSON
// {model, messages}), Worker meneruskan ke SinarCloud dengan API key yang
// disimpan sebagai secret Worker (SINARCLOUD_API_KEY). Key TIDAK PERNAH
// keluar ke browser atau ke kode website (repo publik).
//
// Deploy: Cloudflare Dashboard > Workers & Pages > Create Worker > paste
// file ini > Deploy. Lalu Settings > Variables > Add secret:
//   Name: SINARCLOUD_API_KEY, Value: key SinarCloud (dari console.sinarcloud.com)
//   Name: APISHORT_KEY, Value: key gratis APIShort (dari apishort.com, login Google)
// Atau via wrangler: wrangler secret put SINARCLOUD_API_KEY / APISHORT_KEY
//
// DIAGNOSIS /stream (23 Nov 2026, dites langsung):
//   - GET /stream/movie/:id JALAN (kualitas segar dari VidLink via enc-dec).
//   - Byte video MATI di semua jalur kecuali Box: Worker /stream/proxy kena
//     HTTP 427 dari bcdn (bcdn memblokir egress Cloudflare — berbasis IP,
//     BUKAN header; dites dari VM: UA yang sama dapat 206, dari Worker 427).
//     Surge 403 (mati), cacdn 403. Browser langsung kena 428 (UA browser).
//   - Satu-satunya jalur video yang terbukti jalan: proxy Node di Box 'main'
//     (fs-stream-proxy.js :3002 via Tailscale Funnel) — tapi Box sedang tidur.
//   - Jadi: FS Player tidak bisa diperbaiki dari kode Worker ini. Perbaikan
//     yang benar: bangunkan Box 'main', atau pindahkan proxy video ke VPS
//     Altare (IP publik non-Cloudflare, internet keluar terbukti) lalu ubah
//     FS_BOX_STREAM di hiburan.html. Sampai itu terjadi, film jalan lewat
//     server iframe (VidSrc pertama) — sudah jadi default situs.
//
// Endpoint:
//   GET  /            -> {ok:true} (cek Worker hidup)
//   POST /            -> {model, messages, max_tokens?} diteruskan ke
//                        https://ai.sinarcloud.com/v1/chat/completions
//                        dan responsnya dikembalikan apa adanya (JSON).

const SINAR_BASE = 'https://ai.sinarcloud.com/v1';
const ALLOWED_ORIGINS = [
  'https://freedomsyndicate.my.id',
  'https://www.freedomsyndicate.my.id',
  // Situs yang sama di GitHub Pages (tanpa custom domain).
  'https://freedomsyndicate-owner.github.io',
];

// Proxy MangaDex untuk tab Komik di website (repo open-source: Adolla,
// pola yang sama seperti roadmap kessoku-moe — API MangaDex tidak mengizinkan
// fetch langsung dari browser (tanpa Access-Control-Allow-Origin), jadi
// semua panggilan harus lewat server. Worker ini yang jadi servernya.
//   GET /mdx/<path>?<query>  -> https://api.mangadex.org/<path>?<query>
//   GET /mdx-img?u=<url>      -> gambar MangaDex (cover + halaman chapter)
//   GET /drama/<path>?<query> -> https://apishort.com/v1/<path>?<query>
//     (tab Drama Pendek: ShortMax/DramaBox/ReelShort; key APIShort disimpan
//     sebagai secret Worker APISHORT_KEY, dipasang via header X-API-Key
//     di server — TIDAK PERNAH keluar ke browser. Kalau secret belum
//     diset, request diteruskan tanpa key (APIShort masih mengizinkan
//     tanpa key saat ini, tapi dokumentasinya bilang key wajib dan
//     gratis 100 req/hari — key bisa ditegakkan sewaktu-waktu).
//     Cache: katalog/search/popular 1 jam, detail 30 menit; episode
//     (alleps/chapters/play) TIDAK PERNAH di-cache — URL video
//     bertanda tangan & kedaluwarsa ±8 jam, selalu fresh.
//     hanya host uploads.mangadex.org / *.mangadex.network (bukan open proxy).
const MDX_API = 'https://api.mangadex.org';

function isMdxImgHost(h) {
  return h === 'uploads.mangadex.org' || h.endsWith('.mangadex.network');
}

function corsHeaders(origin) {
  return {
    'Access-Control-Allow-Origin': ALLOWED_ORIGINS.includes(origin)
      ? origin
      : ALLOWED_ORIGINS[0],
    'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  };
}

// --- Keamanan (23 Nov 2026): tolak origin asing + rate limit ---
// Aturan origin: tolak HANYA kalau header Origin ADA tapi tidak ada di
// ALLOWED_ORIGINS. Origin kosong tetap diizinkan — <video> (FS Player)
// dan curl tidak mengirim Origin, dan memblokirnya akan mematikan video.
// Ini memblokir penyalahgunaan dari situs orang lain (browser selalu
// mengirim Origin), bukan dari curl — itu batas wajar tanpa Durable Object.
// Rate limit: token bucket di memori per isolate (reset kalau isolate
// didaur ulang — bukan pembatas keras; pembatas keras pakai Cloudflare
// Rate Limiting rules di dashboard). Chat: 30 req/menit/IP, metadata
// /stream: 30 req/menit/IP. Byte video (/stream/proxy) TIDAK dibatasi —
// satu video = puluhan request chunk, membatasinya mematikan playback.
const _rlBuckets = new Map(); // key -> {count, resetAt}
function _rateLimitOk(key, limit, windowMs) {
  const now = Date.now();
  let b = _rlBuckets.get(key);
  if (!b || now >= b.resetAt) {
    b = { count: 0, resetAt: now + windowMs };
    _rlBuckets.set(key, b);
  }
  b.count += 1;
  return b.count <= limit;
}
function isDisallowedOrigin(origin) {
  return !!origin && !ALLOWED_ORIGINS.includes(origin);
}

function jsonResponse(obj, status, origin) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { ...corsHeaders(origin), 'Content-Type': 'application/json' },
  });
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get('Origin') || '';
    const url = new URL(request.url);

    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders(origin) });
    }

    // Tolak browser dari origin asing (situs orang lain yang menembak Worker
    // ini). GET / (health) tetap terbuka.
    if (url.pathname !== '/' && isDisallowedOrigin(origin)) {
      return jsonResponse({ error: 'origin tidak diizinkan' }, 403, origin);
    }
    const _clientIp = request.headers.get('CF-Connecting-IP') || 'unknown';

    // --- Proxy MangaDex (tab Komik) — GET saja, tanpa menyentuh rute chat. ---
    if (request.method === 'GET' && url.pathname === '/mdx-img') {
      let target;
      try {
        target = new URL(url.searchParams.get('u') || '');
      } catch (e) {
        return jsonResponse({ error: 'parameter u tidak valid' }, 400, origin);
      }
      if (target.protocol !== 'https:' || !isMdxImgHost(target.hostname)) {
        return jsonResponse({ error: 'host gambar tidak diizinkan' }, 403, origin);
      }
      const up = await fetch(target.toString(), {
        headers: { 'User-Agent': 'FS-MangaDex-Proxy/1.0' },
      });
      const imgHeaders = {
        ...corsHeaders(origin),
        'Cache-Control': 'public, max-age=86400',
      };
      const ct = up.headers.get('Content-Type');
      if (ct) imgHeaders['Content-Type'] = ct;
      return new Response(up.body, { status: up.status, headers: imgHeaders });
    }

    if (request.method === 'GET' && url.pathname.startsWith('/mdx/')) {
      const upstream = MDX_API + url.pathname.slice(4) + url.search;
      const up = await fetch(upstream, {
        headers: {
          'User-Agent': 'FS-MangaDex-Proxy/1.0',
          Accept: 'application/json',
        },
      });
      const text = await up.text();
      return new Response(text, {
        status: up.status,
        headers: {
          ...corsHeaders(origin),
          'Content-Type': 'application/json',
          'Cache-Control': 'public, max-age=60',
        },
      });
    }

    // --- Drama Pendek (tab Drama Cina) — GET /drama/* ---
    // APIShort (https://apishort.com/v1): katalog + cari + detail + episode
    // ShortMax / DramaBox / ReelShort. Key gratis dipasang server-side via
    // header X-API-Key (atau api_key query) — APIShort sendiri yang
    // mendokumentasikannya. Secret Worker: APISHORT_KEY (Settings >
    // Variables > Add secret, atau: wrangler secret put APISHORT_KEY).
    // Bukan open proxy: host upstream tetap apishort.com, path ditempel
    // ke /v1/ — tidak ada parameter URL dari pengunjung yang bisa
    // mengarahkan request ke host lain.
    if (request.method === 'GET' && url.pathname.startsWith('/drama/')) {
      if (!_rateLimitOk('drama:' + _clientIp, 30, 60000)) {
        return jsonResponse({ error: 'terlalu banyak permintaan, coba lagi sebentar' }, 429, origin);
      }
      const rest = url.pathname.slice('/drama/'.length);
      if (!rest) return jsonResponse({ error: 'path drama tidak lengkap' }, 400, origin);
      const upstream = 'https://apishort.com/v1/' + rest + url.search;
      const upHeaders = { 'User-Agent': 'FS-Drama-Proxy/1.0', Accept: 'application/json' };
      if (env.APISHORT_KEY) upHeaders['X-API-Key'] = env.APISHORT_KEY;
      // Cache: katalog/search/popular 1 jam, detail 30 menit. Episode
      // (alleps/chapters/play/video) TIDAK PERNAH di-cache.
      const _lower = rest.toLowerCase();
      const _isEpisode = _lower.includes('alleps') || _lower.includes('episode') || _lower.includes('chapter') || _lower.includes('/play') || _lower.includes('m3u8');
      const _cacheSecs = _isEpisode ? 0
        : _lower.includes('detail') ? 1800
        : 3600;
      const _cacheKey = new Request(url.toString(), { method: 'GET' });
      const _cache = caches.default;
      if (_cacheSecs > 0) {
        const _hit = await _cache.match(_cacheKey);
        if (_hit) {
          const _h = new Headers(_hit.headers);
          _h.set('Access-Control-Allow-Origin', corsHeaders(origin)['Access-Control-Allow-Origin']);
          return new Response(_hit.body, { status: _hit.status, headers: _h });
        }
      }
      const up = await fetch(upstream, { headers: upHeaders });
      const text = await up.text();
      const respHeaders = {
        ...corsHeaders(origin),
        'Content-Type': 'application/json',
        'Cache-Control': _cacheSecs > 0 ? 'public, max-age=' + _cacheSecs : 'private, no-store',
      };
      const resp = new Response(text, { status: up.status, headers: respHeaders });
      if (_cacheSecs > 0 && up.ok) {
        try { await _cache.put(_cacheKey, resp.clone()); } catch (e) {}
      }
      return resp;
    }

    // --- FS Player tanpa iklan (tab Film) — GET /stream/* ---
    // Pola movie-web (arsitektur referensi): ambil URL stream LANGSUNG lalu
    // putar di <video> sendiri, tanpa iframe provider — jadi tidak ada iklan
    // dan tidak ada tab baru. Logika VidLink diporting dari
    // Inside4ndroid/TMDB-Embed-API (MIT), providers/vidlink.js.
    //   GET /stream/movie/:tmdbId       -> {ok, source, qualities, captions}
    //   GET /stream/tv/:tmdbId/:s/:e    -> sama, untuk series
    //   GET /stream/proxy?u=<url>       -> teruskan byte MP4/SRT (Range ok),
    //       HANYA host bcdn/cacdn.hakunaymatata.com (bukan open proxy).
    //   GET /stream/sub?u=<url .srt>    -> SRT diubah jadi WebVTT.
    // URL video bertanda tangan & berumur pendek — Worker mengambilnya SEGAR
    // tiap kali play, tidak disimpan.
    const ENCDEC = 'https://enc-dec.app';
    const VIDLINK = 'https://vidlink.pro';
    function isStreamHost(h) {
      return h === 'bcdn.hakunaymatata.com' || h === 'cacdn.hakunaymatata.com';
    }
    function srtToVtt(srt) {
      const out = ['WEBVTT', ''];
      srt.replace(/\r\n/g, '\n').split(/\n\n+/).forEach(function(block) {
        const lines = block.split('\n').filter(function(l) { return l.trim() !== ''; });
        if (!lines.length) return;
        if (/^\d+$/.test(lines[0].trim())) lines.shift(); // nomor urut SRT
        if (!lines.length) return;
        lines[0] = lines[0].replace(/,/g, '.'); // 00:00:01,000 -> 00:00:01.000
        if (!lines[0].includes('-->')) return;
        out.push(lines.join('\n'), '');
      });
      return out.join('\n');
    }
    if (request.method === 'GET' && url.pathname.startsWith('/stream/')) {
      const parts = url.pathname.split('/').filter(Boolean); // ['stream','movie','299534']
      // -- /stream/proxy?u=... --
      if (parts[1] === 'proxy') {
        let target;
        try { target = new URL(url.searchParams.get('u') || ''); } catch (e) {
          return jsonResponse({ error: 'parameter u tidak valid' }, 400, origin);
        }
        if (target.protocol !== 'https:' || !isStreamHost(target.hostname)) {
          return jsonResponse({ error: 'host tidak diizinkan' }, 403, origin);
        }
        // PENTING (dites 17 Nov 2026): bcdn MENOLAK User-Agent browser
        // (428) dan Referer vidlink (429) — hanya UA non-browser yang lolos
        // (curl 206). Jadi proxy TIDAK mengirim UA browser / Referer.
        const upHeaders = { 'User-Agent': 'FS-Stream-Proxy/1.0' };
        const range = request.headers.get('Range');
        if (range) upHeaders['Range'] = range;
        const up = await fetch(target.toString(), { headers: upHeaders });
        const pHeaders = { ...corsHeaders(origin), 'Cache-Control': 'private, no-store' };
        ['Content-Type', 'Content-Length', 'Content-Range', 'Accept-Ranges'].forEach(function(h) {
          const v = up.headers.get(h);
          if (v) pHeaders[h] = v;
        });
        return new Response(up.body, { status: up.status, headers: pHeaders });
      }
      // -- /stream/sub?u=... (SRT -> VTT) --
      if (parts[1] === 'sub') {
        let target;
        try { target = new URL(url.searchParams.get('u') || ''); } catch (e) {
          return jsonResponse({ error: 'parameter u tidak valid' }, 400, origin);
        }
        if (target.protocol !== 'https:' || !isStreamHost(target.hostname)) {
          return jsonResponse({ error: 'host tidak diizinkan' }, 403, origin);
        }
        const up = await fetch(target.toString(), { headers: { 'User-Agent': 'FS-Stream-Proxy/1.0' } });
        if (!up.ok) return jsonResponse({ error: 'subtitle gagal diambil' }, up.status, origin);
        const srt = await up.text();
        return new Response(srtToVtt(srt), {
          status: 200,
          headers: { ...corsHeaders(origin), 'Content-Type': 'text/vtt; charset=utf-8', 'Cache-Control': 'private, max-age=300' },
        });
      }
      // -- /stream/movie/:id  dan  /stream/tv/:id/:s/:e --
      if ((parts[1] === 'movie' && parts[2]) || (parts[1] === 'tv' && parts[2] && parts[3] && parts[4])) {
        if (!_rateLimitOk('stream:' + _clientIp, 30, 60000)) {
          return jsonResponse({ error: 'terlalu banyak permintaan, coba lagi sebentar' }, 429, origin);
        }
        const tmdbId = parts[2];
        if (!/^\d+$/.test(tmdbId)) return jsonResponse({ error: 'tmdb id harus angka' }, 400, origin);
        const encRes = await fetch(ENCDEC + '/api/enc-vidlink?text=' + encodeURIComponent(tmdbId), {
          headers: { 'User-Agent': 'FS-Stream-Proxy/1.0', Origin: VIDLINK + '/', Referer: VIDLINK + '/' },
        });
        let encJson;
        try { encJson = await encRes.json(); } catch (e) { encJson = null; }
        if (!encRes.ok || !encJson || !encJson.result) {
          return jsonResponse({ error: 'vidlink tidak tersedia untuk film ini', source: 'vidlink' }, 502, origin);
        }
        const apiPath = parts[1] === 'movie'
          ? '/api/b/movie/' + encJson.result
          : '/api/b/tv/' + encJson.result + '/' + parts[3] + '/' + parts[4];
        const vlRes = await fetch(VIDLINK + apiPath, {
          headers: {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Mobile Safari/537.36',
            Origin: VIDLINK + '/',
            Referer: VIDLINK + '/',
            Accept: 'application/json',
          },
        });
        let vl;
        try { vl = await vlRes.json(); } catch (e) { vl = null; }
        if (!vlRes.ok || !vl || !vl.stream || !vl.stream.qualities) {
          return jsonResponse({ error: 'stream tidak ditemukan', source: 'vidlink' }, 502, origin);
        }
        const proxy = function(u) { return url.origin + '/stream/proxy?u=' + encodeURIComponent(u); };
        const qualities = Object.keys(vl.stream.qualities).map(function(q) {
          const qq = vl.stream.qualities[q];
          return { quality: q, codec: qq.codecName || '', type: qq.type || 'mp4', url: proxy(qq.url) };
        }).sort(function(a, b) { return parseInt(b.quality, 10) - parseInt(a.quality, 10); });
        const captions = (vl.stream.captions || []).map(function(c, i) {
          return { label: c.language || ('Subtitle ' + (i + 1)), url: url.origin + '/stream/sub?u=' + encodeURIComponent(c.url) };
        });
        return jsonResponse({ ok: true, source: 'vidlink', qualities: qualities, captions: captions }, 200, origin);
      }
      return jsonResponse({ error: 'route stream tidak dikenal' }, 404, origin);
    }

    if (request.method === 'GET') {
      return jsonResponse(
        { ok: true, service: 'fs-ai', hint: 'POST {model, messages} untuk chat' },
        200,
        origin
      );
    }

    if (request.method !== 'POST') {
      return jsonResponse({ error: 'method not allowed' }, 405, origin);
    }

    if (!_rateLimitOk('chat:' + _clientIp, 30, 60000)) {
      return jsonResponse({ error: 'terlalu banyak permintaan, coba lagi sebentar' }, 429, origin);
    }
    const _clen = parseInt(request.headers.get('Content-Length') || '0', 10);
    if (_clen > 65536) {
      return jsonResponse({ error: 'body terlalu besar' }, 413, origin);
    }

    if (!env.SINARCLOUD_API_KEY) {
      return jsonResponse(
        { error: 'server belum dikonfigurasi (secret SINARCLOUD_API_KEY belum diset)' },
        500,
        origin
      );
    }

    let body;
    try {
      body = await request.json();
    } catch (e) {
      return jsonResponse({ error: 'body harus JSON' }, 400, origin);
    }

    const model = typeof body.model === 'string' ? body.model.trim() : '';
    const messages = Array.isArray(body.messages) ? body.messages.slice(0, 20) : [];
    if (!model || messages.length === 0) {
      return jsonResponse({ error: 'model dan messages wajib diisi' }, 400, origin);
    }
    const maxTokens = Math.min(
      Math.max(parseInt(body.max_tokens, 10) || 800, 1),
      1000
    );

    const upstream = await fetch(SINAR_BASE + '/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer ' + env.SINARCLOUD_API_KEY,
      },
      body: JSON.stringify({
        model,
        messages,
        max_tokens: maxTokens,
        temperature: 0.7,
      }),
    });

    const text = await upstream.text();
    return new Response(text, {
      status: upstream.status,
      headers: { ...corsHeaders(origin), 'Content-Type': 'application/json' },
    });
  },
};
