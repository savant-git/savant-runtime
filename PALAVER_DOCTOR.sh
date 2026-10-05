#!/usr/bin/env bash
set -euo pipefail

BACKEND_PORT=8787
FRONTEND_PORT=5173

GREEN='\033[32m'
RED='\033[31m'
YELLOW='\033[33m'
NC='\033[0m'

ok()   { echo -e "${GREEN}[ OK ]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; }

echo
echo "=============================="
echo " PALAVER DOCTOR"
echo "=============================="
echo

#########################
# Backend
#########################

if curl -fs http://127.0.0.1:${BACKEND_PORT}/api/health >/dev/null 2>&1; then
    ok "Backend responding"
else
    fail "Backend offline"

    fuser -k ${BACKEND_PORT}/tcp 2>/dev/null || true

    systemctl restart palaver-voice-backend.service

    sleep 4

    if curl -fs http://127.0.0.1:${BACKEND_PORT}/api/health >/dev/null 2>&1; then
        ok "Backend recovered"
    else
        fail "Backend failed recovery"
    fi
fi

#########################
# Frontend
#########################

if curl -fs http://127.0.0.1:${FRONTEND_PORT} >/dev/null 2>&1; then
    ok "Frontend responding"
else
    fail "Frontend offline"

    fuser -k ${FRONTEND_PORT}/tcp 2>/dev/null || true

    systemctl restart palaver-frontend.service

    sleep 6

    if curl -fs http://127.0.0.1:${FRONTEND_PORT} >/dev/null 2>&1; then
        ok "Frontend recovered"
    else
        fail "Frontend failed recovery"
    fi
fi

#########################
# Tunnel
#########################

URL=$(
journalctl -u palaver-tunnel.service -n 200 --no-pager \
| grep -Eo 'https://[-a-zA-Z0-9.]+\.trycloudflare\.com' \
| tail -1
)

if [ -n "$URL" ]; then
    ok "Tunnel: $URL"
else
    warn "Tunnel missing"

    systemctl restart palaver-tunnel.service

    sleep 10

    URL=$(
    journalctl -u palaver-tunnel.service -n 200 --no-pager \
    | grep -Eo 'https://[-a-zA-Z0-9.]+\.trycloudflare\.com' \
    | tail -1
    )

    if [ -n "$URL" ]; then
        ok "Tunnel restored"
        echo "$URL"
    else
        fail "Tunnel still unavailable"
    fi
fi

#########################
# AI
#########################

RESP=$(
curl -s \
-X POST \
http://127.0.0.1:${BACKEND_PORT}/api/palaver \
-H "Content-Type: application/json" \
-d '{"text":"health check"}' \
)

echo
echo "AI Response:"
echo "$RESP"

echo
echo "=============================="
echo " COMPLETE"
echo "=============================="
