#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
APP="$ROOT/webui_ultra"

echo "=== VERIFY BACKEND ==="
curl -s http://127.0.0.1:8787/api/health || true
echo

echo
echo "=== VERIFY FRONTEND SERVICE FILE ==="
if [ ! -f /etc/systemd/system/palaver-frontend.service ]; then
  cat > /etc/systemd/system/palaver-frontend.service <<SERVICE
[Unit]
Description=Palaver Frontend
After=network.target palaver-voice-backend.service

[Service]
Type=simple
WorkingDirectory=$APP
ExecStart=/usr/bin/env npx vite --host 0.0.0.0 --port 5173
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
SERVICE
fi

systemctl daemon-reload
systemctl enable palaver-frontend.service
systemctl restart palaver-frontend.service

sleep 5

echo
echo "=== FRONTEND HEALTH ==="
curl -I http://127.0.0.1:5173 || true

echo
echo "=== FIX TUNNEL SERVICE ==="
cat > /etc/systemd/system/palaver-tunnel.service <<'SERVICE'
[Unit]
Description=Palaver Cloudflare Quick Tunnel
After=network.target palaver-frontend.service
Wants=palaver-frontend.service

[Service]
Type=simple
ExecStart=/usr/bin/cloudflared tunnel --url http://127.0.0.1:5173
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable palaver-tunnel.service
systemctl restart palaver-tunnel.service

sleep 10

echo
echo "=== ALL SERVICES ==="
systemctl --no-pager --full status palaver-voice-backend.service | sed -n '1,12p'
echo
systemctl --no-pager --full status palaver-frontend.service | sed -n '1,12p'
echo
systemctl --no-pager --full status palaver-tunnel.service | sed -n '1,16p'

echo
echo "=== TUNNEL URL ==="
journalctl -u palaver-tunnel.service -n 150 --no-pager \
  | grep -Eo 'https://[-a-zA-Z0-9.]+\.trycloudflare\.com' \
  | tail -1

echo
echo "=== PALAVER API TEST ==="
curl -s -X POST http://127.0.0.1:8787/api/palaver \
  -H 'Content-Type: application/json' \
  -d '{"text":"hey palaver summarize the runtime status"}' || true
echo
