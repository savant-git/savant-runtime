#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
APP="$ROOT/webui_ultra"
BACKEND="$ROOT/palaver_voice_backend.py"

if [ ! -d "$APP" ]; then
  echo "[ERROR] Missing frontend app: $APP"
  exit 1
fi

if [ ! -f "$BACKEND" ]; then
  echo "[ERROR] Missing backend: $BACKEND"
  exit 1
fi

cat > /etc/systemd/system/palaver-voice-backend.service <<SERVICE
[Unit]
Description=Palaver Voice Backend
After=network.target

[Service]
Type=simple
WorkingDirectory=$ROOT
EnvironmentFile=-/root/.env
ExecStart=$ROOT/.venv_voice/bin/python $BACKEND
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
SERVICE

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

cat > /etc/systemd/system/palaver-tunnel.service <<SERVICE
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

systemctl enable palaver-voice-backend.service
systemctl enable palaver-frontend.service
systemctl enable palaver-tunnel.service

systemctl restart palaver-voice-backend.service
systemctl restart palaver-frontend.service

sleep 5

if ! curl -fsS http://127.0.0.1:5173 >/dev/null; then
  echo "[ERROR] frontend did not start"
  journalctl -u palaver-frontend.service -n 80 --no-pager
  exit 1
fi

systemctl restart palaver-tunnel.service

sleep 10

echo "=== SERVICES ==="
systemctl --no-pager --full status palaver-voice-backend.service | sed -n '1,14p'
echo
systemctl --no-pager --full status palaver-frontend.service | sed -n '1,14p'
echo
systemctl --no-pager --full status palaver-tunnel.service | sed -n '1,18p'

echo
echo "=== HEALTH ==="
curl -s http://127.0.0.1:8787/api/health || true
echo

echo
echo "=== FRONTEND ==="
curl -I http://127.0.0.1:5173 || true

echo
echo "=== TUNNEL URL ==="
journalctl -u palaver-tunnel.service -n 120 --no-pager \
  | grep -Eo 'https://[-a-zA-Z0-9.]+\.trycloudflare\.com' \
  | tail -1
