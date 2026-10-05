#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"

if [ ! -f "$ROOT/PALAVER_DOCTOR.sh" ]; then
  echo "[ERROR] Missing $ROOT/PALAVER_DOCTOR.sh"
  exit 1
fi

chmod +x "$ROOT/PALAVER_DOCTOR.sh"

cat > /etc/systemd/system/palaver-doctor.service <<SERVICE
[Unit]
Description=Palaver Self-Healing Doctor

[Service]
Type=oneshot
ExecStart=$ROOT/PALAVER_DOCTOR.sh
SERVICE

cat > /etc/systemd/system/palaver-doctor.timer <<'TIMER'
[Unit]
Description=Run Palaver Doctor Every 5 Minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min
Persistent=true

[Install]
WantedBy=timers.target
TIMER

systemctl daemon-reload
systemctl enable palaver-doctor.timer
systemctl restart palaver-doctor.timer

echo "=== TIMER STATUS ==="
systemctl --no-pager --full status palaver-doctor.timer | sed -n '1,22p'

echo
echo "=== RUN DOCTOR NOW ==="
systemctl start palaver-doctor.service

echo
echo "=== DOCTOR LOG ==="
journalctl -u palaver-doctor.service -n 120 --no-pager
