#!/usr/bin/env bash
set -euo pipefail

APP="/root/savant-runtime/webui_ultra"
FRONT_LOG="/root/savant-runtime/palaver-vite.log"
TUNNEL_LOG="/root/savant-runtime/palaver-cloudflare.log"

cd "$APP"

fuser -k 5173/tcp 2>/dev/null || true
pkill -f "cloudflared tunnel --url http://localhost:5173" 2>/dev/null || true

npm install

nohup npx vite --host 0.0.0.0 --port 5173 > "$FRONT_LOG" 2>&1 &

sleep 3

if ! command -v cloudflared >/dev/null 2>&1; then
  cd /tmp
  wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
  dpkg -i cloudflared-linux-amd64.deb
fi

nohup cloudflared tunnel --url http://localhost:5173 > "$TUNNEL_LOG" 2>&1 &

sleep 6

echo "=== VITE ==="
curl -I http://127.0.0.1:5173 || true

echo
echo "=== CLOUDFLARE URL ==="
grep -Eo 'https://[-a-zA-Z0-9.]+\.trycloudflare\.com' "$TUNNEL_LOG" | tail -1 || true

echo
echo "If no URL appeared yet, run:"
echo "tail -f $TUNNEL_LOG"
