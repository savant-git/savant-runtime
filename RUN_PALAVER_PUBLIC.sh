#!/usr/bin/env bash
set -euo pipefail

APP="/root/savant-runtime/webui_ultra"
LOG="/root/savant-runtime/palaver-frontend-live.log"

cd "$APP"

# Kill old vite/node listeners on likely ports.
fuser -k 5173/tcp 2>/dev/null || true
fuser -k 5174/tcp 2>/dev/null || true
fuser -k 3000/tcp 2>/dev/null || true
fuser -k 3001/tcp 2>/dev/null || true

npm install

nohup npx vite --host 0.0.0.0 --port 5173 > "$LOG" 2>&1 &

sleep 2

echo "=== PROCESS ==="
pgrep -af "vite|node" || true

echo
echo "=== LISTENERS ==="
ss -ltnp | grep -E '5173|5174|3000|3001' || true

echo
echo "=== LOCAL TEST ==="
curl -I http://127.0.0.1:5173 || true

echo
echo "=== PUBLIC TEST FROM VPS ==="
curl -I http://108.175.4.80:5173 || true

echo
echo "=== LOG ==="
tail -80 "$LOG"

echo
echo "OPEN:"
echo "http://108.175.4.80:5173/"
