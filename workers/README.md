# Workers FREEDOM SYNDICATE

Kode Cloudflare Worker untuk situs freedomsyndicate.my.id. TIDAK ADA
kunci/API key di file-file ini — semua key hidup sebagai Worker secret
di dashboard Cloudflare (Settings > Variables).

- `fs-ai/` — proxy Chat Ai (SinarCloud), MangaDex, FS Player, Drama
  Pendek (APIShort). Secret: `SINARCLOUD_API_KEY`, `APISHORT_KEY`.
  URL: https://fs-ai.sanlana1903.workers.dev
- `fs-cinema-search/` — proxy pencarian film TMDB (ganti OMDb).
  Secret: `TMDB_API_KEY`.
  URL: https://fs-cinema-search.sanlana1903.workers.dev
