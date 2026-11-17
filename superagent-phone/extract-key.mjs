// Find the FreeLLMAPI client key by TESTING candidates against /v1/models.
// Usage: bun extract-key.mjs <output-file>
// Prints only key NAMES and pass/fail — never any value.
// The first candidate that returns HTTP 200 is saved (mode 600).
import fs from "fs";

const out = process.argv[2];
if (!out) { console.error("usage: bun extract-key.mjs <output-file>"); process.exit(1); }

const BASE = process.env.FREELLMAPI_BASE || "http://127.0.0.1:3001/v1";
const preferred = ["API_KEY", "FREELLMAPI_KEY", "UNIFIED_API_KEY", "CLIENT_API_KEY"];
const files = ["/workspace/freellmapi/.env", "/workspace/freellmapi/.env.local"];

function clean(v) {
  return v.trim().replace(/^["']+|["']+$/g, "");
}

// Collect candidates in order: preferred names first, then any *KEY* var.
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

async function testKey(value) {
  try {
    const proc = Bun.spawn(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "8",
      `${BASE}/models`, "-H", `Authorization: Bearer ${value}`], { stdout: "pipe", stderr: "pipe" });
    const code = (await new Response(proc.stdout).text()).trim();
    await proc.exited;
    return code === "200";
  } catch { return false; }
}

console.log(`testing ${candidates.length} key candidate(s) against ${BASE}/models ...`);
for (const c of candidates) {
  const ok = await testKey(c.value);
  console.log(`  ${c.name}: ${ok ? "OK" : "fail"}`);
  if (ok) {
    fs.writeFileSync(out, c.value, { mode: 0o600 });
    try { fs.chmodSync(out, 0o600); } catch {}
    console.log(`saved working key (name ${c.name}, len ${c.value.length})`);
    process.exit(0);
  }
}
console.log("no working freellmapi key found — server will try without key (LLM7 fallback)");
process.exit(0);
