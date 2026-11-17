// Find the FreeLLMAPI client key and save it (mode 600).
// Sources, in order:
//   1. The FreeLLMAPI SQLite DB: settings.unified_api_key
//      (/workspace/freellmapi/server/data/freeapi.db) — tested against /v1/models.
//   2. Key-like vars in /workspace/freellmapi/.env — each tested against /v1/models.
// Usage: bun extract-key.mjs <output-file>
// Prints only key NAMES and pass/fail — never any value.
import fs from "fs";

const out = process.argv[2];
if (!out) { console.error("usage: bun extract-key.mjs <output-file>"); process.exit(1); }

const BASE = process.env.FREELLMAPI_BASE || "http://127.0.0.1:3001/v1";

function clean(v) {
  return v.trim().replace(/^["']+|["']+$/g, "");
}

function save(name, value) {
  fs.writeFileSync(out, value, { mode: 0o600 });
  try { fs.chmodSync(out, 0o600); } catch {}
  console.log(`saved working key (name ${name}, len ${value.length})`);
}

async function testKey(value) {
  try {
    const proc = Bun.spawn(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "8",
      `${BASE}/models`, "-H", `Authorization: Bearer ${value}`], { stdout: "pipe", stderr: "pipe" });
    const code = (await new Response(proc.stdout).text()).trim();
    await proc.exited;
    return code === "200";
  } catch { return false; }
}

// 1. SQLite DB (unified_api_key).
try {
  const { Database } = await import("bun:sqlite");
  const db = new Database("/workspace/freellmapi/server/data/freeapi.db", { readonly: true });
  const row = db.query("SELECT value FROM settings WHERE key = 'unified_api_key'").get();
  db.close();
  const v = row?.value ? clean(String(row.value)) : "";
  if (v.length >= 8) {
    const ok = await testKey(v);
    console.log(`  unified_api_key (DB): ${ok ? "OK" : "fail"}`);
    if (ok) { save("unified_api_key", v); process.exit(0); }
  } else {
    console.log("  unified_api_key (DB): not found");
  }
} catch (e) {
  console.log("  DB lookup failed: " + String(e).slice(0, 100));
}

// 2. .env candidates.
const preferred = ["API_KEY", "FREELLMAPI_KEY", "UNIFIED_API_KEY", "CLIENT_API_KEY"];
const files = ["/workspace/freellmapi/.env", "/workspace/freellmapi/.env.local"];
const candidates = [];
function addCandidate(name, value) {
  const v = clean(value);
  if (v.length >= 8 && !candidates.some((c) => c.value === v)) candidates.push({ name, value: v });
}
for (const p of files) {
  let text = "";
  try { text = fs.readFileSync(p, "utf8"); } catch { continue; }
  const lines = text.split("\n");
  for (const want of preferred) {
    for (const line of lines) {
      const m = line.match(new RegExp("^\\s*" + want + "\\s*=\\s*(.+?)\\s*$"));
      if (m) addCandidate(want, m[1]);
    }
  }
  for (const line of lines) {
    const m = line.match(/^\s*([A-Z_]*KEY[A-Z_]*)\s*=\s*(.+?)\s*$/);
    if (m) addCandidate(m[1], m[2]);
  }
}

if (candidates.length === 0) {
  console.log("no key candidates in freellmapi .env — server will try without key (LLM7 fallback)");
  process.exit(0);
}

console.log(`testing ${candidates.length} key candidate(s) against ${BASE}/models ...`);
for (const c of candidates) {
  const ok = await testKey(c.value);
  console.log(`  ${c.name}: ${ok ? "OK" : "fail"}`);
  if (ok) { save(c.name, c.value); process.exit(0); }
}
console.log("no working freellmapi key found — server will try without key (LLM7 fallback)");
process.exit(0);
