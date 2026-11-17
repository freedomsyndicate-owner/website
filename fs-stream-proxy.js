// fs-stream-proxy.js — proxy video untuk FS Player di website FREEDOM SYNDICATE.
// Berjalan di Simular Box 'main' (Node v24, tanpa dependensi).
// Kenapa perlu: host video bcdn.hakunaymatata.com menolak User-Agent browser
// (428) dan menolak egress Cloudflare Workers (427) — tapi IP Box ini lolos
// (206, terbukti 17 Nov 2026). Proxy ini mengambil video dari Box dengan
// UA non-browser, lalu mengalirkannya ke penonton lewat Tailscale Funnel.
//   GET /v?u=<URL bcdn/cacdn yang di-encode>  -> byte video, Range diteruskan
//   GET /health -> ok
// Jalankan:  node fs-stream-proxy.js   (port 3002, hanya 127.0.0.1)
// Funnel:    tailscale serve --bg /stream http://127.0.0.1:3002
const http = require('http');
const https = require('https');
const PORT = process.env.FS_STREAM_PORT || 3002;
const ALLOW = ['bcdn.hakunaymatata.com', 'cacdn.hakunaymatata.com'];
const UA = 'FS-Stream-Proxy/1.0';
const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'Range',
  'Access-Control-Expose-Headers': 'Content-Range, Accept-Ranges, Content-Length',
};

const server = http.createServer((req, res) => {
  let u;
  try { u = new URL(req.url, 'http://x'); } catch (e) { res.writeHead(400); res.end('bad url'); return; }
  if (u.pathname === '/health') { res.writeHead(200, { 'Content-Type': 'text/plain' }); res.end('ok'); return; }
  if (u.pathname !== '/v') { res.writeHead(404); res.end('not found'); return; }
  let target;
  try { target = new URL(u.searchParams.get('u') || ''); } catch (e) { res.writeHead(400); res.end('bad u'); return; }
  if (target.protocol !== 'https:' || !ALLOW.includes(target.hostname)) { res.writeHead(403); res.end('forbidden host'); return; }

  const headers = { 'User-Agent': UA };
  if (req.headers.range) headers.Range = req.headers.range;
  const up = https.get(target.toString(), { headers }, (upRes) => {
    const h = { ...CORS, 'Accept-Ranges': 'bytes' };
    ['content-type', 'content-length', 'content-range'].forEach((k) => {
      if (upRes.headers[k]) h[k] = upRes.headers[k];
    });
    res.writeHead(upRes.statusCode, h);
    upRes.pipe(res);
  });
  up.setTimeout(15000, () => up.destroy(new Error('upstream timeout')));
  up.on('error', () => { if (!res.headersSent) res.writeHead(502, CORS); res.end('upstream error'); });
});

server.listen(PORT, '127.0.0.1', () => console.log('fs-stream-proxy on 127.0.0.1:' + PORT));
