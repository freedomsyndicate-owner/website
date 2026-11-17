// SuperAgent Phone — mini-agent server for the Box.
// Serves a mobile chat page and runs a small agent loop:
//   phone --HTTP/SSE--> this server --WS (Muse protocol)--> SuperAgent watch
//   reasoning LLM: FreeLLMAPI Gemini on the Box (primary), LLM7 gpt-oss:20b (fallback)
//   tool execution: task_batch run_command on the Box via the watcher.
// The WS bearer token is NEVER in this file: it is read from disk at runtime
// (~/.superagent-r/remote-agent.json, or a local .ws-token file) and never logged.

import { createHash, randomUUID } from "crypto";

const PORT = Number(process.env.PORT || 8090);
const WS_URL = process.env.WS_URL || "ws://127.0.0.1:7928/muse";
const WORKSPACE = process.env.WORKSPACE || "/workspace";
const TOKEN_FILE = process.env.TOKEN_FILE || ".ws-token";
const LLM_BASE = "https://api.llm7.io/v1";
const LLM_MODEL = "gpt-oss:20b";
const LLM_DEFAULT_MODEL = "default"; // LLM7 default (Codestral): plain content, own quota
const MAX_STEPS = 12;

const SYSTEM_PROMPT = `You are SuperAgent, a coding agent running on a Linux box. The user talks to you from their phone in Indonesian. Reply in Indonesian.

You have exactly ONE tool: run_command (bash shell). Workspace directory: ${WORKSPACE}. All commands run there. Files: read with cat/sed/grep, write with heredoc (cat > file <<'EOF' ... EOF), edit with sed/python3. Check what exists first (ls, cat) before changing anything.

RULES:
- Stay inside ${WORKSPACE}. Never touch ~/.superagent-r/model-config.json, any .env file, or anything outside the workspace.
- Never run rm -rf, mkfs, dd, or any destructive/forkbomb command. Never ask for passwords, seeds, or API keys.
- Prefer small, safe commands. If a command fails, try ONE different approach, then report honestly.
- Keep answers short and plain, like a chat message. No markdown headers.
- Reason briefly: short plan, then act. Do not write long analysis.

RESPONSE FORMAT — reply with ONLY one JSON object, no other text:
- To run a command: {"tool":"run_command","args":{"command":"<shell command>"}}
- To answer the user: {"answer":"<your reply in Indonesian>"}`;

type SseWriter = (event: any) => void;

// ---------- token handling (never logged, never sent to the phone) ----------
async function readTokenFromJson(path: string): Promise<string | null> {
  try {
    const f = Bun.file(path);
    if (!(await f.exists())) return null;
    const j = await f.json();
    const t = j?.wsToken || j?.ws_token || j?.token;
    return typeof t === "string" && t.length >= 16 ? t : null;
  } catch { return null; }
}

async function readTokenFromLog(path: string): Promise<string | null> {
  try {
    const f = Bun.file(path);
    if (!(await f.exists())) return null;
    const text = await f.text();
    // Look for a long token on a line mentioning "token" (the watch prints it at startup).
    const lines = text.split("\n").filter((l) => /token/i.test(l));
    for (const line of lines.reverse()) {
      const m = line.match(/([A-Za-z0-9_-]{32,})/g);
      if (m) {
        const best = m.sort((a, b) => b.length - a.length)[0];
        if (best && !/^(Bearer|token|wsToken)$/i.test(best)) return best;
      }
    }
    return null;
  } catch { return null; }
}

async function loadToken(): Promise<string | null> {
  if (process.env.WS_TOKEN && process.env.WS_TOKEN.length >= 16) return process.env.WS_TOKEN;
  const home = process.env.HOME || "/home/user";
  return (
    (await readTokenFromJson(TOKEN_FILE)) ||
    (await readTokenFromJson(`${home}/.superagent-r/remote-agent.json`)) ||
    (await readTokenFromLog("/workspace/superagent-watch.log")) ||
    (await readTokenFromLog(`${home}/.superagent-r/superagent.log`))
  );
}

// ---------- Muse WS client ----------
function sha256Hex(s: string): string {
  return createHash("sha256").update(s).digest("hex");
}

class MuseClient {
  private ws: WebSocket | null = null;
  private token: string;
  private ready: Promise<void> | null = null;
  private pendingResult = new Map<string, (env: any) => void>();
  private ackWaiter: ((text: string) => void) | null = null;
  private connecting = false;
  connected = false;

  constructor(token: string) { this.token = token; }

  connect(): Promise<void> {
    if (this.ready) return this.ready;
    this.ready = new Promise<void>((resolve, reject) => {
      if (this.connecting) return;
      this.connecting = true;
      const url = `${WS_URL}?token=${encodeURIComponent(this.token)}`;
      console.log(`[phone] connecting to ${WS_URL} ...`);
      const ws = new WebSocket(url);
      this.ws = ws;
      const timeout = setTimeout(() => {
        if (!this.connected) { try { ws.close(); } catch {} this.ready = null; reject(new Error("WS connect timeout")); }
      }, 10000);
      ws.onopen = () => {
        clearTimeout(timeout);
        console.log("[phone] WS open, sending hello");
        this.send({ v: 1, kind: "hello", id: `hello_${randomUUID()}`, ts: Date.now(), nonce: randomUUID() });
      };
      ws.onmessage = (ev) => {
        try {
          const env = JSON.parse(String(ev.data));
          if (env.kind === "welcome") {
            this.connected = true;
            this.connecting = false;
            console.log("[phone] WS welcome, connected");
            resolve();
          } else if (env.kind === "task_result") {
            const fn = this.pendingResult.get(env.id);
            if (fn) { this.pendingResult.delete(env.id); fn(env); }
          } else if (env.kind === "chat" && this.ackWaiter && /accepted/i.test(env.text || "")) {
            const w = this.ackWaiter; this.ackWaiter = null; w(env.text);
          } else if (env.kind === "token_refresh") {
            this.handleTokenRefresh(env);
          } else if (env.kind === "auth_ok") {
            // ok
          }
          // other chat notices are ignored (they are TUI notes)
        } catch (e) { console.log("[phone] bad WS frame", String(e).slice(0, 120)); }
      };
      ws.onerror = () => { /* close follows */ };
      ws.onclose = (ev) => {
        this.connected = false;
        this.connecting = false;
        this.ready = null;
        console.log(`[phone] WS closed ${ev.code} ${String(ev.reason || "").slice(0, 80)}`);
        for (const fn of this.pendingResult.values()) fn({ __closed: true });
        this.pendingResult.clear();
        if (this.ackWaiter) { const w = this.ackWaiter; this.ackWaiter = null; w(""); }
        // reject if never connected
        reject(new Error(`WS closed ${ev.code}`));
      };
    });
    return this.ready;
  }

  private async handleTokenRefresh(env: any) {
    if (typeof env.token === "string" && env.token.length >= 16) {
      this.token = env.token;
      try { await Bun.write(TOKEN_FILE, env.token); console.log("[phone] refreshed token saved"); } catch {}
      this.send({ v: 1, kind: "token_ack", id: `ack_${randomUUID()}`, refresh_id: env.id, status: "ok", ts: Date.now(), nonce: randomUUID() });
    }
  }

  private send(env: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify(env));
  }

  private waitAck(timeoutMs = 5000): Promise<string> {
    return new Promise((resolve) => {
      this.ackWaiter = resolve;
      setTimeout(() => { if (this.ackWaiter) { this.ackWaiter = null; resolve(""); } }, timeoutMs);
    });
  }

  async runTask(task: string, onEvent: SseWriter): Promise<string> {
    await this.connect();
    const taskId = `task_${randomUUID()}`;
    const ackPromise = this.waitAck();
    this.send({ v: 1, kind: "task_request", id: taskId, task, workspace: WORKSPACE, tools: ["run_command"], ts: Date.now(), nonce: randomUUID() });
    await ackPromise; // proceed even if the ack chat never arrives
    const messages: any[] = [
      { role: "system", content: SYSTEM_PROMPT },
      { role: "user", content: task },
    ];
    let finalAnswer = "";
    for (let step = 0; step < MAX_STEPS; step++) {
      const llm = await callLlm(messages);
      if (!llm.ok) { finalAnswer = llm.reason; break; }
      const reply = llm.text;
      let parsed: any = null;
      try { parsed = JSON.parse(reply); } catch { /* plain text */ }
      if (parsed && parsed.tool === "run_command" && parsed.args?.command) {
        const cmd = String(parsed.args.command).slice(0, 2000);
        onEvent({ type: "cmd", text: cmd });
        const batchId = `batch_${randomUUID()}`;
        const resultP = new Promise<any>((resolve) => {
          this.pendingResult.set(batchId, resolve);
          setTimeout(() => { if (this.pendingResult.has(batchId)) { this.pendingResult.delete(batchId); resolve({ __timeout: true }); } }, 120000);
        });
        this.send({ v: 1, kind: "task_batch", id: batchId, task_id: taskId, calls: [{ id: "c1", tool: "run_command", args: { command: cmd }, timeout_ms: 120000 }], ts: Date.now(), nonce: randomUUID() });
        const res = await resultP;
        if (res?.__closed) { finalAnswer = "Koneksi ke SuperAgent putus di tengah jalan. Coba lagi."; break; }
        if (res?.__timeout) {
          messages.push({ role: "assistant", content: reply });
          messages.push({ role: "user", content: "TOOL RESULT (timeout 120s): perintah belum selesai dalam 120 detik." });
          onEvent({ type: "out", text: "(perintah kehabisan waktu 120 detik)" });
          continue;
        }
        // ack the result with its digest so the watcher can release it
        try {
          const raw = JSON.stringify({ v: 1, kind: "task_result", id: res.id, task_id: res.task_id, results: res.results });
          this.send({ v: 1, kind: "result_ack", id: res.id, task_id: res.task_id, result_sha256: sha256Hex(raw), ts: Date.now(), nonce: randomUUID() });
        } catch {}
        const call = res.results?.[0];
        const out = call?.ok ? (call.output || "(tidak ada output)") : `ERROR: ${call?.error || "gagal"}`;
        const clipped = String(out).slice(0, 6000);
        onEvent({ type: "out", text: clipped.slice(0, 1200) });
        messages.push({ role: "assistant", content: reply });
        messages.push({ role: "user", content: `TOOL RESULT:\n${clipped}` });
        continue;
      }
      // final answer (parsed.answer or plain text)
      finalAnswer = parsed?.answer ? String(parsed.answer) : reply;
      break;
    }
    if (!finalAnswer) finalAnswer = "Selesai, tapi tidak ada jawaban akhir. Coba ulangi dengan perintah yang lebih spesifik.";
    try {
      this.send({ v: 1, kind: "task_done", id: `done_${randomUUID()}`, task_id: taskId, summary: finalAnswer.slice(0, 2000), ts: Date.now(), nonce: randomUUID() });
    } catch {}
    return finalAnswer;
  }
}

// ---------- Brains ----------
// Primary: FreeLLMAPI on this Box (Gemini flash-lite, no shared daily quota).
// Fallback: LLM7 gpt-oss:20b (keyless, shared quota — can 429 or answer empty).
// Returns {ok:true,text} or {ok:false,reason} so the phone shows the real cause.
const FREELLMAPI_BASE = process.env.FREELLMAPI_BASE || "http://127.0.0.1:3001/v1";
const FREELLMAPI_MODEL = process.env.FREELLMAPI_MODEL || "gemini-flash-lite";

let freellmapiKey: string | null = null;
async function loadFreellmapiKey(): Promise<string | null> {
  if (freellmapiKey !== null) return freellmapiKey;
  if (process.env.FREELLMAPI_KEY && process.env.FREELLMAPI_KEY.length >= 8) { freellmapiKey = process.env.FREELLMAPI_KEY; return freellmapiKey; }
  try {
    const f = Bun.file(".freellmapi-key");
    if (await f.exists()) {
      const v = (await f.text()).trim();
      if (v.length >= 8) { freellmapiKey = v; return v; }
    }
  } catch {}
  freellmapiKey = null;
  return null;
}

// gpt-oss via LLM7 sometimes puts its whole reply in the `reasoning` field
// and leaves `content` empty. If content is empty, try to recover JSON from reasoning.
function extractFromMessage(msg: any): string | null {
  const content = typeof msg?.content === "string" ? msg.content.trim() : "";
  if (content) return content;
  const reasoning = typeof msg?.reasoning === "string" ? msg.reasoning : "";
  if (!reasoning) return null;
  const m = reasoning.match(/\{[\s\S]*?"(tool|answer)"[\s\S]*?\}/);
  if (m) return m[0];
  return null;
}

async function callChatApi(base: string, model: string, key: string | null, messages: any[]): Promise<{ ok: boolean; text?: string; reason?: string; http?: number; retryAfter?: number }> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (key) headers["Authorization"] = `Bearer ${key}`;
  try {
    const res = await fetch(`${base}/chat/completions`, {
      method: "POST",
      headers,
      body: JSON.stringify({ model, messages, temperature: 0.2, max_tokens: 4000 }),
      signal: AbortSignal.timeout(90000),
    });
    if (!res.ok) {
      const body = await res.text().catch(() => "");
      console.log(`[phone] LLM ${base} HTTP ${res.status}: ${body.slice(0, 200)}`);
      if (res.status === 429) {
        let wait = "";
        let retryAfter = 0;
        try { const e = JSON.parse(body); const s = e?.error?.retry_after; if (typeof s === "number") { retryAfter = s; wait = s >= 3600 ? ` sekitar ${Math.round(s / 3600)} jam lagi` : ` sekitar ${Math.ceil(s / 60)} menit lagi`; } } catch {}
        return { ok: false, http: 429, retryAfter, reason: `Kuota harian LLM7 (otak gratis) sedang habis. Coba lagi${wait}.` };
      }
      return { ok: false, http: res.status, reason: `Otak error HTTP ${res.status}. Coba lagi sebentar lagi.` };
    }
    const j: any = await res.json();
    const msg = j?.choices?.[0]?.message;
    const text = extractFromMessage(msg);
    if (!text) {
      console.log(`[phone] LLM ${base} empty content, finish=${j?.choices?.[0]?.finish_reason}, usage=${JSON.stringify(j?.usage)}`);
      return { ok: false, reason: "Otak menjawab kosong. Coba lagi." };
    }
    return { ok: true, text };
  } catch (e) {
    console.log(`[phone] LLM ${base} fetch failed`, String(e).slice(0, 150));
    return { ok: false, reason: "Tidak bisa menghubungi otak. Coba lagi sebentar lagi." };
  }
}

let freellmapiModel: string | null = null;
async function resolveFreellmapiModel(): Promise<string> {
  if (freellmapiModel) return freellmapiModel;
  if (process.env.FREELLMAPI_MODEL) { freellmapiModel = process.env.FREELLMAPI_MODEL; return freellmapiModel; }
  try {
    const res = await fetch(`${FREELLMAPI_BASE}/models`, { signal: AbortSignal.timeout(10000) });
    const j: any = await res.json();
    const ids: string[] = (j?.data || []).map((m: any) => m?.id).filter(Boolean);
    const pick = ids.find((id) => /gemini/i.test(id)) || ids[0];
    if (pick) { freellmapiModel = pick; console.log(`[phone] FreeLLMAPI model: ${pick}`); return pick; }
  } catch (e) { console.log("[phone] FreeLLMAPI /models failed", String(e).slice(0, 120)); }
  freellmapiModel = FREELLMAPI_MODEL;
  return freellmapiModel;
}

async function callLlm(messages: any[]): Promise<{ ok: boolean; text?: string; reason?: string }> {
  // 1. FreeLLMAPI on the Box (Gemini, local, no shared quota).
  const key = await loadFreellmapiKey();
  const model = await resolveFreellmapiModel();
  const primary = await callChatApi(FREELLMAPI_BASE, model, key, messages);
  if (primary.ok) return primary;
  // 401/403/404 from FreeLLMAPI means key/model wrong — still try LLM7.
  // 2. LLM7 "default" (Codestral): returns plain content, separate quota.
  const fallback = await callChatApi(LLM_BASE, LLM_DEFAULT_MODEL, "llm7", messages);
  if (fallback.ok) return fallback;
  // 3. LLM7 gpt-oss:20b (may be quota-exhausted or reasoning-only).
  const last = await callChatApi(LLM_BASE, LLM_MODEL, "llm7", messages);
  if (last.ok) return last;
  // Report the LONGEST wait, not the last error (a 60s rate-limit can hide a 25h daily quota).
  const fails = [primary, fallback, last];
  const worst = fails.reduce((a, b) => (b.retryAfter ?? -1) > (a.retryAfter ?? -1) ? b : a, fails[0]);
  return { ok: false, reason: worst.reason || last.reason || fallback.reason || primary.reason || "Otak tidak menjawab. Coba lagi." };
}

// ---------- HTTP server (page + SSE chat) ----------
const token = await loadToken();
if (!token) {
  console.error("[phone] FATAL: WS token not found (checked .ws-token, ~/.superagent-r/remote-agent.json, watch log).");
  process.exit(1);
}
console.log(`[phone] token loaded (len ${token.length}), WS ${WS_URL}`);
const muse = new MuseClient(token);
muse.connect().catch((e) => console.log("[phone] initial WS connect failed, will retry on first chat:", String(e).slice(0, 120)));

let busy = false;
const queue: Array<() => void> = [];

function nextInQueue() {
  busy = false;
  const fn = queue.shift();
  if (fn) { busy = true; fn(); }
}

const server = Bun.serve({
  port: PORT,
  hostname: "127.0.0.1",
  async fetch(req) {
    const url = new URL(req.url);
    if (url.pathname === "/") {
      const html = await Bun.file("public/index.html").text().catch(() => "<h1>index.html hilang</h1>");
      return new Response(html, { headers: { "Content-Type": "text/html; charset=utf-8" } });
    }
    if (url.pathname === "/api/health") {
      return Response.json({ ok: true, ws: muse.connected, busy, queued: queue.length });
    }
    if (url.pathname === "/api/chat" && req.method === "POST") {
      let body: any = {};
      try { body = await req.json(); } catch {}
      const text = typeof body.text === "string" ? body.text.trim().slice(0, 2000) : "";
      if (!text) return Response.json({ error: "teks kosong" }, { status: 400 });
      let resolveStream: any;
      const stream = new ReadableStream({
        start(controller) {
          const send = (event: any) => {
            try { controller.enqueue(new TextEncoder().encode(`data: ${JSON.stringify(event)}\n\n`)); } catch {}
          };
          const run = async () => {
            send({ type: "status", text: "Mengerjakan…" });
            try {
              const answer = await muse.runTask(text, send);
              send({ type: "answer", text: answer });
            } catch (e) {
              send({ type: "error", text: `Gagal: ${String(e).slice(0, 300)}` });
            }
            try { controller.close(); } catch {}
            nextInQueue();
          };
          if (busy) {
            queue.push(run);
            send({ type: "status", text: `Menunggu giliran (antrean ${queue.length})…` });
          } else {
            busy = true;
            run();
          }
        },
      });
      return new Response(stream, { headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache", Connection: "keep-alive" } });
    }
    return new Response("not found", { status: 404 });
  },
});

console.log(`[phone] SuperAgent Phone server on http://127.0.0.1:${server.port}`);
