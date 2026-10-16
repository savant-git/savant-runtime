#!/usr/bin/env bash
set -euo pipefail

echo "=== STOP SYSTEMD LOOP ==="
systemctl stop palaver-voice-backend.service 2>/dev/null || true
systemctl reset-failed palaver-voice-backend.service 2>/dev/null || true

echo
echo "=== KILL OLD MANUAL BACKEND ON 8787 ==="
ss -ltnp | grep 8787 || true
fuser -k 8787/tcp 2>/dev/null || true
sleep 2
ss -ltnp | grep 8787 || true

echo
echo "=== SANITIZE ENV FOR SYSTEMD ==="
SAN="/root/savant-runtime/runtime/services/palaver-systemd.env"
mkdir -p /root/savant-runtime/runtime/services

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
            lines.append(f'{k}={v}')

dst.write_text("\n".join(lines) + "\n")
print(dst)
PY

echo
echo "=== REWRITE BACKEND SERVICE ==="
cat > /etc/systemd/system/palaver-voice-backend.service <<'SERVICE'
[Unit]
Description=Palaver Voice Backend
After=network.target

[Service]
Type=simple
WorkingDirectory=/root/savant-runtime
EnvironmentFile=-/root/savant-runtime/runtime/services/palaver-systemd.env
ExecStart=/root/savant-runtime/.venv_voice/bin/python /root/savant-runtime/palaver_voice_backend.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable palaver-voice-backend.service
systemctl restart palaver-voice-backend.service

sleep 3

echo
echo "=== BACKEND STATUS ==="
systemctl --no-pager --full status palaver-voice-backend.service | sed -n '1,24p'

echo
echo "=== HEALTH ==="
curl -s http://127.0.0.1:8787/api/health || true
echo

echo
echo "=== TEST ==="
curl -s -X POST http://127.0.0.1:8787/api/palaver \
  -H 'Content-Type: application/json' \
  -d '{"text":"hey palaver what is mobius"}' || true
echo
