#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
APP="$ROOT/webui_ultra"
BACKEND="$ROOT/palaver_voice_backend.py"
ENV_SAN="$ROOT/runtime/services/palaver-systemd.env"

mkdir -p "$ROOT/runtime/services"

echo "=== STOP SERVICES ==="
systemctl stop palaver-voice-backend.service 2>/dev/null || true
systemctl stop palaver-frontend.service 2>/dev/null || true
systemctl stop palaver-tunnel.service 2>/dev/null || true
systemctl reset-failed palaver-voice-backend.service 2>/dev/null || true
systemctl reset-failed palaver-frontend.service 2>/dev/null || true
systemctl reset-failed palaver-tunnel.service 2>/dev/null || true

echo
echo "=== KILL MANUAL LISTENERS ==="
fuser -k 8787/tcp 2>/dev/null || true
fuser -k 5173/tcp 2>/dev/null || true
pkill -f "cloudflared tunnel --url http://127.0.0.1:5173" 2>/dev/null || true
pkill -f "cloudflared tunnel --url http://localhost:5173" 2>/dev/null || true

echo
echo "=== SANITIZE /root/.env FOR SYSTEMD ==="
python3 - <<'PY'
from pathlib import Path

src = Path("/root/.env")
dst = Path("/root/savant-runtime/runtime/services/palaver-systemd.env")

lines = []
if src.exists():
    for raw in src.read_text(errors="ignore").splitlines():
        s = raw.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        if s.startswith("export "):
            s = s[len("export "):].strip()
        k, v = s.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k:
            lines.append(f"{k}={v}")

dst.write_text("\n".join(lines) + "\n")
print(dst)
PY

echo
echo "=== WRITE BACKEND SERVICE ==="
cat > /etc/systemd/system/palaver-voice-backend.service <<SERVICE
[Unit]
Description=Palaver Voice Backend
After=network.target

[Service]
Type=simple
WorkingDirectory=$ROOT
EnvironmentFile=-$ENV_SAN
ExecStart=$ROOT/.venv_voice/bin/python $BACKEND
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
SERVICE

echo
echo "=== WRITE FRONTEND SERVICE ==="
cat > /etc/systemd/system/palaver-frontend.service <<SERVICE
[Unit]
Description=Palaver Frontend
After=network.target palaver-voice-backend.service
Wants=palaver-voice-backend.service

[Service]
Type=simple
WorkingDirectory=$APP
ExecStart=/usr/bin/env npx vite --host 0.0.0.0 --port 5173
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
SERVICE

echo
echo "=== WRITE TUNNEL SERVICE ==="
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

echo
echo "=== START STACK ==="
systemctl daemon-reload
systemctl enable palaver-voice-backend.service palaver-frontend.service palaver-tunnel.service
systemctl restart palaver-voice-backend.service
sleep 3
systemctl restart palaver-frontend.service
sleep 5
systemctl restart palaver-tunnel.service
sleep 10

echo
echo "=== STATUS ==="
systemctl --no-pager --full status palaver-voice-backend.service | sed -n '1,14p'
echo
systemctl --no-pager --full status palaver-frontend.service | sed -n '1,14p'
echo
systemctl --no-pager --full status palaver-tunnel.service | sed -n '1,16p'

echo
echo "=== TESTS ==="
curl -s http://127.0.0.1:8787/api/health || true
echo
curl -I http://127.0.0.1:5173 || true

echo
echo "=== TUNNEL URL ==="
journalctl -u palaver-tunnel.service -n 160 --no-pager \
  | grep -Eo 'https://[-a-zA-Z0-9.]+\.trycloudflare\.com' \
  | tail -1 || true
