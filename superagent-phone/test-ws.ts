// Direct WS protocol test (no LLM): proves task_request -> task_batch ->
// task_result -> result_ack -> task_done works against the local watcher.
// Usage: bun test-ws.ts   (reads token from ~/.superagent-r/remote-agent.json)
import { createHash, randomUUID } from "crypto";

const WS_URL = process.env.WS_URL || "ws://127.0.0.1:9225/muse";
const home = process.env.HOME || "/home/user";
const cfg: any = await Bun.file(`${home}/.superagent-r/remote-agent.json`).json();
const token = cfg.wsToken as string;
console.log("token len:", token.length);

const sha = (s: string) => createHash("sha256").update(s).digest("hex");
const taskId = `task_${randomUUID()}`;
const batchId = `batch_${randomUUID()}`;

const ws = new WebSocket(`${WS_URL}?token=${encodeURIComponent(token)}`);
const send = (o: any) => { ws.send(JSON.stringify(o)); console.log(">>", o.kind, o.id || ""); };
const deadline = setTimeout(() => { console.log("TIMEOUT"); process.exit(1); }, 30000);

ws.onopen = () => {
  console.log("open, sending hello");
  send({ v: 1, kind: "hello", id: `hello_${randomUUID()}`, ts: Date.now(), nonce: randomUUID() });
};
ws.onmessage = (ev) => {
  const env = JSON.parse(String(ev.data));
  console.log("<<", env.kind, JSON.stringify(env).slice(0, 400));
  if (env.kind === "welcome") {
    send({ v: 1, kind: "task_request", id: taskId, task: "test echo", workspace: "/workspace", tools: ["run_command"], ts: Date.now(), nonce: randomUUID() });
  } else if (env.kind === "chat" && /accepted/i.test(env.text || "")) {
    send({ v: 1, kind: "task_batch", id: batchId, task_id: taskId, calls: [{ id: "c1", tool: "run_command", args: { command: "echo halo-hp-123 && pwd" }, timeout_ms: 30000 }], ts: Date.now(), nonce: randomUUID() });
  } else if (env.kind === "task_result") {
    const raw = JSON.stringify({ v: 1, kind: "task_result", id: env.id, task_id: env.task_id, results: env.results });
    console.log("result_sha256 from server:", env.result_sha256);
    console.log("computed digest:           ", sha(raw));
    console.log("digest match:", env.result_sha256 === sha(raw));
    send({ v: 1, kind: "result_ack", id: env.id, task_id: env.task_id, result_sha256: sha(raw), ts: Date.now(), nonce: randomUUID() });
    send({ v: 1, kind: "task_done", id: `done_${randomUUID()}`, task_id: taskId, summary: "test ok", ts: Date.now(), nonce: randomUUID() });
    setTimeout(() => { clearTimeout(deadline); console.log("TEST DONE"); process.exit(0); }, 1000);
  }
};
ws.onerror = (e) => console.log("ws error", e);
ws.onclose = (ev) => console.log("ws closed", ev.code, String(ev.reason || ""));
