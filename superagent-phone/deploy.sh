#!/bin/bash
# Deploy SuperAgent Phone on Simular Box 'main'.
# Run from the cloned repo dir:  bash deploy.sh
# No secret is ever printed: only the token LENGTH is shown.
set -euo pipefail
cd "$(dirname "$0")"
DIR="$PWD"

echo "== 1. bun =="
command -v bun >/dev/null || { echo "bun not found in PATH"; exit 1; }
bun --version

echo "== 2. WS token (length only) =="
export TOKEN_FILE="$DIR/.ws-token"
if [ ! -s "$TOKEN_FILE" ]; then
  bun -e '
    const fs = require("fs");
    const home = process.env.HOME || "/home/user";
    let tok = null;
    try {
      const j = JSON.parse(fs.readFileSync(home + "/.superagent-r/remote-agent.json", "utf8"));
      tok = j.wsToken || j.token || null;
    } catch {}
    if (!tok) { console.error("TOKEN_NOT_FOUND in remote-agent.json"); process.exit(1); }
    fs.writeFileSync(process.env.TOKEN_FILE, tok, { mode: 0o600 });
    try { fs.chmodSync(process.env.TOKEN_FILE, 0o600); } catch {}
    console.log("token saved, len " + tok.length);
  ' || { echo "could not locate WS token (check ~/.superagent-r/remote-agent.json)"; exit 1; }
else
  echo "token file already exists"
fi

echo "== 2b. FreeLLMAPI brain (otak utama, di Box) =="
echo -n "models: "
curl -s --max-time 5 http://127.0.0.1:3001/v1/models | head -c 200; echo
# If the gateway needs its own client key, save it opaquely (name + length only).
export KEY_FILE="$DIR/.freellmapi-key"
if [ ! -s "$KEY_FILE" ]; then
  bun extract-key.mjs "$KEY_FILE" || echo "key lookup skipped (will try without key)"
else
  echo "freellmapi key file already exists"
fi

echo "== 3. SuperAgent watch alive? =="
if curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://127.0.0.1:7928/muse | grep -q 426; then
  echo "watch WS answers 426 (ok)"
else
  echo "WARNING: watch WS on 127.0.0.1:7928 did not answer 426 — check dev/watch processes"
  ps aux | grep -E "muse watch|cli.tsx" | grep -v grep || true
fi

echo "== 4. start phone server (port 8090) =="
# Always restart so a redeploy picks up the new code.
fuser -k 8090/tcp 2>/dev/null || true
sleep 2
(PORT=8090 WS_URL=ws://127.0.0.1:7928/muse TOKEN_FILE="$TOKEN_FILE" nohup bun server.ts >> /workspace/superagent-phone.log 2>&1 &)
sleep 4
tail -5 /workspace/superagent-phone.log
curl -s --max-time 5 http://127.0.0.1:8090/api/health || { echo "phone server did not come up"; exit 1; }
echo "phone server up"

echo "== 5. tailscale funnel: / -> page, /muse -> WS =="
# NOTE: plain `tailscale serve` turns the funnel OFF; use funnel --set-path (additive per path).
sudo tailscale funnel --bg --https=443 --set-path /muse http://127.0.0.1:7928
sudo tailscale funnel --bg --https=443 --set-path / http://127.0.0.1:8090
sleep 2
tailscale serve status
tailscale funnel status || true

echo "== 6. verify public endpoints (warnings only, never fatal) =="
echo -n "root: "; curl -s -o /dev/null -w "%{http_code}\n" --max-time 10 https://main.tailb5991a.ts.net/ || echo "root curl failed (funnel may still be starting)"
echo -n "muse: "; curl -s -o /dev/null -w "%{http_code}\n" --max-time 10 https://main.tailb5991a.ts.net/muse || echo "muse curl failed"
curl -s --max-time 10 https://main.tailb5991a.ts.net/ | grep -o "<title>[^<]*</title>" || echo "WARN: root did not return the page title (yet)"

echo "== 7. reboot persistence =="
if ! grep -q "superagent-phone" /workspace/start-superagent.sh 2>/dev/null; then
  cat >> /workspace/start-superagent.sh <<'EOF'

# SuperAgent Phone (mobile chat page) — started with dev+watch
if [ -d /workspace/superagent-phone ]; then
  (cd /workspace/superagent-phone && PORT=8090 WS_URL=ws://127.0.0.1:7928/muse nohup bun server.ts >> /workspace/superagent-phone.log 2>&1 &)
fi
EOF
  echo "added to start-superagent.sh"
else
  echo "already in start-superagent.sh"
fi

echo "== DONE =="
echo "Page: https://main.tailb5991a.ts.net/"
echo "WS:   wss://main.tailb5991a.ts.net/muse"
