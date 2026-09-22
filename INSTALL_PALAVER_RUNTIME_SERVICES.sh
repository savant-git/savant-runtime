#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
APP="$ROOT/webui_ultra"
BACKEND="$ROOT/palaver_voice_backend.py"

mkdir -p "$ROOT/runtime/maps" "$ROOT/runtime/services" "$ROOT/canon/palaver"

# Persist latest runtime map if available.
LATEST_MAP="$(find "$ROOT/imports/source-dumps" -type f -name runtime_map.md | sort | tail -1 || true)"
if [ -n "$LATEST_MAP" ] && [ -f "$LATEST_MAP" ]; then
  cp "$LATEST_MAP" "$ROOT/runtime/maps/palaver_runtime_map.md"
fi

cat > "$ROOT/canon/palaver/palaver_voice_interface.md" <<'CANON'
# PALAVER VOICE INTERFACE
# STATUS: ACTIVE
# AUTHORITY: CURRENT RUNTIME PATCH
# DOMAIN: PALAVER
# DEPENDS:
# - webui_ultra frontend
# - palaver_voice_backend.py
# - /root/.env credentials
# - browser SpeechRecognition
# - browser SpeechSynthesis
# - HTTPS tunnel or localhost for microphone access

Palaver voice interface allows spoken activation, transcript normalization,
intent submission, audible response, and backend routing.

Wake phrases:

- wake up palaver
- hey palaver
- palaver awaken
- palaver online

Backend endpoint:

- POST /api/palaver

Backend port:

- 127.0.0.1:8787

Frontend port:

- 127.0.0.1:5173

Cloudflare tunnel is recommended for mobile microphone access because
browser speech APIs generally require HTTPS or localhost.
CANON

cat > "$ROOT/runtime/services/palaver.env" <<ENV
ROOT=$ROOT
APP=$APP
BACKEND=$BACKEND
FRONTEND_PORT=5173
BACKEND_PORT=8787
ENV_FILE=/root/.env
ENV

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
Description=Palaver Vite Frontend
After=network.target palaver-voice-backend.service

[Service]
Type=simple
WorkingDirectory=$APP
Environment=HOST=0.0.0.0
ExecStart=/usr/bin/env npx vite --host 0.0.0.0 --port 5173
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable palaver-voice-backend.service palaver-frontend.service
systemctl restart palaver-voice-backend.service palaver-frontend.service

sleep 3

echo "=== BACKEND ==="
systemctl --no-pager --full status palaver-voice-backend.service | sed -n '1,18p'

echo
echo "=== FRONTEND ==="
systemctl --no-pager --full status palaver-frontend.service | sed -n '1,18p'

echo
echo "=== HEALTH ==="
curl -s http://127.0.0.1:8787/api/health || true
echo

echo
echo "=== FRONTEND TEST ==="
curl -I http://127.0.0.1:5173 || true
