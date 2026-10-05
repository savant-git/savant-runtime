#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"

if ! command -v cloudflared >/dev/null 2>&1; then
  cd /tmp
  wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
  dpkg -i cloudflared-linux-amd64.deb
fi

cat > /etc/systemd/system/palaver-tunnel.service <<'SERVICE'
[Unit]
Description=Palaver Cloudflare Quick Tunnel
After=network.target palaver-frontend.service
Requires=palaver-frontend.service

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

sleep 8

echo "=== TUNNEL STATUS ==="
systemctl --no-pager --full status palaver-tunnel.service | sed -n '1,24p'

echo
echo "=== TUNNEL URL ==="
journalctl -u palaver-tunnel.service -n 80 --no-pager \
  | grep -Eo 'https://[-a-zA-Z0-9.]+\.trycloudflare\.com' \
  | tail -1

echo
echo "Open the URL above in Chrome."
