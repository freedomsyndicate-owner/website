// FS Cinema — Cloudflare Worker proxy for TMDB (free tier).
// Purpose: keep the TMDB API key OFF the public GitHub repo.
// The site (hiburan.html) calls this Worker instead of api.themoviedb.org
// directly. The key lives only as a Worker secret:
//   npx wrangler secret put TMDB_API_KEY
// Deploy: npx wrangler deploy  (or: wrangler deploy --name fs-cinema-search)
// Routes (23 Nov 2026 — OMDb dihapus dari situs, semua lewat sini):
//   GET /search?q=...&type=movie|tv&page=... -> TMDB search
//   GET /external?id=<tmdbId>&type=movie|tv  -> TMDB external_ids (imdb_id)
//   GET /tv?id=<tmdbId>                      -> TMDB tv details (number_of_seasons)
//   GET /season?id=<tmdbId>&season=<n>       -> TMDB tv season (episodes[])
//
// Allowed origins: the live site + localhost for testing. Everything
// else gets no CORS headers (the proxy still answers, browsers just
// can't read it cross-origin).

const ALLOWED_ORIGINS = [
  'https://freedomsyndicate.my.id',
  'https://www.freedomsyndicate.my.id',
  'https://freedomsyndicate-owner.github.io',
  'http://localhost:8000',
];

// Rate limit sederhana per isolate (lihat fs-ai-worker): 60 req/menit/IP.
// Bukan pembatas keras — pembatas keras pakai Cloudflare Rate Limiting rules.
const _rlBuckets = new Map();
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

function corsHeaders(origin) {
  const headers = { 'Vary': 'Origin' };
  if (ALLOWED_ORIGINS.includes(origin)) {
    headers['Access-Control-Allow-Origin'] = origin;
  }
  return headers;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const origin = request.headers.get('Origin') || '';
    const headers = corsHeaders(origin);

    if (request.method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: {
          ...headers,
          'Access-Control-Allow-Methods': 'GET, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type',
          'Access-Control-Max-Age': '86400',
        },
      });
    }

    if (request.method !== 'GET') {
      return new Response('Method not allowed', { status: 405, headers });
    }

    // Tolak browser dari origin asing (Origin kosong tetap diizinkan: curl,
    // health check, dan pemutar yang tidak mengirim Origin).
    if (origin && !ALLOWED_ORIGINS.includes(origin)) {
      return new Response(JSON.stringify({ error: 'origin tidak diizinkan' }), {
        status: 403,
        headers: { ...headers, 'Content-Type': 'application/json' },
      });
    }

    const _ip = request.headers.get('CF-Connecting-IP') || 'unknown';
    if (!_rateLimitOk('cinema:' + _ip, 60, 60000)) {
      return new Response(JSON.stringify({ error: 'terlalu banyak permintaan' }), {
        status: 429,
        headers: { ...headers, 'Content-Type': 'application/json' },
      });
    }

    if (!env.TMDB_API_KEY) {
      return new Response(JSON.stringify({ error: 'TMDB_API_KEY not configured' }), {
        status: 500,
        headers: { ...headers, 'Content-Type': 'application/json' },
      });
    }

    const _tmdb = async function(path, cacheSecs) {
      const res = await fetch(
        'https://api.themoviedb.org/3' + path +
        (path.includes('?') ? '&' : '?') + 'api_key=' + encodeURIComponent(env.TMDB_API_KEY),
        { headers: { Accept: 'application/json' } }
      );
      const body = await res.text();
      return new Response(body, {
        status: res.status,
        headers: {
          ...headers,
          'Content-Type': 'application/json',
          'Cache-Control': 'public, max-age=' + cacheSecs,
        },
      });
    };
    const _num = function(v, min, max, def) {
      const n = parseInt(v || '', 10);
      return isNaN(n) ? def : Math.min(Math.max(n, min), max);
    };

    // -- /external?id=<tmdbId>&type=movie|tv -> {imdb_id, ...} --
    if (url.pathname === '/external') {
      const id = url.searchParams.get('id') || '';
      const type = url.searchParams.get('type') === 'tv' ? 'tv' : 'movie';
      if (!/^\d+$/.test(id)) {
        return new Response(JSON.stringify({ error: 'id harus angka' }), {
          status: 400, headers: { ...headers, 'Content-Type': 'application/json' },
        });
      }
      return _tmdb('/' + type + '/' + id + '/external_ids', 3600);
    }

    // -- /tv?id=<tmdbId> -> detail series (number_of_seasons) --
    if (url.pathname === '/tv') {
      const id = url.searchParams.get('id') || '';
      if (!/^\d+$/.test(id)) {
        return new Response(JSON.stringify({ error: 'id harus angka' }), {
          status: 400, headers: { ...headers, 'Content-Type': 'application/json' },
        });
      }
      return _tmdb('/tv/' + id + '?language=en-US', 3600);
    }

    // -- /season?id=<tmdbId>&season=<n> -> {episodes: [...]} --
    if (url.pathname === '/season') {
      const id = url.searchParams.get('id') || '';
      const season = _num(url.searchParams.get('season'), 0, 50, 1);
      if (!/^\d+$/.test(id)) {
        return new Response(JSON.stringify({ error: 'id harus angka' }), {
          status: 400, headers: { ...headers, 'Content-Type': 'application/json' },
        });
      }
      return _tmdb('/tv/' + id + '/season/' + season + '?language=en-US', 3600);
    }

    if (url.pathname !== '/search') {
      return new Response('Not found', { status: 404, headers });
    }

    const q = (url.searchParams.get('q') || '').trim();
    const type = url.searchParams.get('type') === 'tv' ? 'tv' : 'movie';
    const page = Math.min(Math.max(parseInt(url.searchParams.get('page') || '1', 10) || 1, 1), 10);
    if (!q || q.length > 100) {
      return new Response(JSON.stringify({ error: 'q required' }), {
        status: 400,
        headers: { ...headers, 'Content-Type': 'application/json' },
      });
    }
    if (!env.TMDB_API_KEY) {
      return new Response(JSON.stringify({ error: 'TMDB_API_KEY not configured' }), {
        status: 500,
        headers: { ...headers, 'Content-Type': 'application/json' },
      });
    }

    const tmdbUrl =
      'https://api.themoviedb.org/3/search/' + type +
      '?api_key=' + encodeURIComponent(env.TMDB_API_KEY) +
      '&query=' + encodeURIComponent(q) +
      '&language=en-US&page=' + page +
      '&include_adult=false';

    const res = await fetch(tmdbUrl, { headers: { Accept: 'application/json' } });
    const body = await res.text();
    return new Response(body, {
      status: res.status,
      headers: {
        ...headers,
        'Content-Type': 'application/json',
        // Cache identical searches briefly at the edge.
        'Cache-Control': 'public, max-age=300',
      },
    });
  },
};
