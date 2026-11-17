# SuperAgent Phone

A mobile web page that lets San talk to SuperAgent on Simular Box `main` from his phone. No app install, just open the link.

## How it works

```
phone --HTTPS (Tailscale Funnel)--> Box:8090 (this server, Bun)
   this server --WS (Muse protocol, ?token=)--> SuperAgent watch (Box:7928)
   this server --HTTPS--> LLM7 gpt-oss:20b (free, reasoning brain)
   watch --task_batch run_command--> executes shell commands on the Box
```

- The page is a simple chat UI (`public/index.html`, Indonesian).
- The server (`server.ts`) runs the agent loop: it asks the brain what to do, sends the shell command to the watcher as a `task_batch`, feeds the result back, and streams the final answer to the phone (SSE). Brains in order: FreeLLMAPI Gemini on the Box (needs its client key — see `extract-key.mjs`), LLM7 `default` (Codestral), LLM7 `gpt-oss:20b`.
- The WS bearer token is **never in this repo**: the server reads it from disk at runtime (`~/.superagent-r/remote-agent.json`, or a local `.ws-token` file, mode 600). Same for the FreeLLMAPI client key, if the gateway needs one: `deploy.sh` extracts it opaquely via `extract-key.mjs` into `.freellmapi-key` (mode 600). Neither is ever printed or logged.
- One task at a time; further messages queue.

## Deploy (on the Box)

```bash
cd /tmp && rm -rf site && git clone --depth 1 https://github.com/freedomsyndicate-owner/website.git site
cp -r site/superagent-phone /workspace/superagent-phone
cd /workspace/superagent-phone && bash deploy.sh
# update later: cd /tmp/site && git pull && cp -r superagent-phone/* /workspace/superagent-phone/ && bash /workspace/superagent-phone/deploy.sh
```

`deploy.sh` finds the WS token (length only is printed), starts the server on 127.0.0.1:8090, wires Tailscale Serve so the public Funnel URL serves the page at `/` and keeps the WS at `/muse`, adds the server to `start-superagent.sh` (reboot-safe), and verifies both endpoints.

## Security

The Funnel URL is the only gate: **anyone who opens the page link can use the agent** (YOLO FULL — it runs shell commands on the Box). Do not share the link. The WS token stays on the Box; the phone browser never sees it.
