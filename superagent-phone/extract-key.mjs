// Extract the FreeLLMAPI client key from its .env (if any) into a mode-600 file.
// Usage: bun extract-key.mjs <output-file>
// Prints only the key NAME and LENGTH — never the value.
import fs from "fs";

const out = process.argv[2];
if (!out) { console.error("usage: bun extract-key.mjs <output-file>"); process.exit(1); }

const preferred = ["API_KEY", "FREELLMAPI_KEY", "UNIFIED_API_KEY"];
const files = ["/workspace/freellmapi/.env", "/workspace/freellmapi/.env.local"];

function clean(v) {
  return v.trim().replace(/^["']+|["']+$/g, "");
}

let found = null;
for (const p of files) {
  let text = "";
  try { text = fs.readFileSync(p, "utf8"); } catch { continue; }
  const lines = text.split("\n");
  for (const want of preferred) {
    for (const line of lines) {
      const m = line.match(new RegExp("^\\s*" + want + "\\s*=\\s*(.+?)\\s*$"));
      if (m && clean(m[1]).length >= 8) { found = { name: want, value: clean(m[1]) }; break; }
    }
    if (found) break;
  }
  if (found) break;
  for (const line of lines) {
    const m = line.match(/^\s*([A-Z_]*KEY[A-Z_]*)\s*=\s*(.+?)\s*$/);
    if (m && clean(m[2]).length >= 8) { found = { name: m[1], value: clean(m[2]) }; break; }
  }
  if (found) break;
}

if (!found) {
  console.log("no freellmapi key found in .env — server will try without key (LLM7 fallback)");
  process.exit(0);
}
fs.writeFileSync(out, found.value, { mode: 0o600 });
try { fs.chmodSync(out, 0o600); } catch {}
console.log("freellmapi key saved (name " + found.name + ", len " + found.value.length + ")");
