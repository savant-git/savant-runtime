#!/usr/bin/env bash
set -euo pipefail

echo "=== SERVICES ==="
systemctl --no-pager --full status palaver-voice-backend.service | sed -n '1,18p' || true
echo
systemctl --no-pager --full status palaver-frontend.service | sed -n '1,18p' || true
echo
systemctl --no-pager --full status palaver-tunnel.service | sed -n '1,22p' || true

echo
echo "=== PORTS ==="
ss -ltnp | grep -E '8787|5173' || true

echo
echo "=== BACKEND HEALTH ==="
curl -s http://127.0.0.1:8787/api/health || true
echo

echo
echo "=== BACKEND TEST ==="
curl -s -X POST http://127.0.0.1:8787/api/palaver \
  -H 'Content-Type: application/json' \
  -d '{"text":"hey palaver what is the current runtime status"}' || true
echo

echo
echo "=== FRONTEND TEST ==="
curl -I http://127.0.0.1:5173 || true

echo
echo "=== TUNNEL URL ==="
journalctl -u palaver-tunnel.service -n 180 --no-pager \
  | grep -Eo 'https://[-a-zA-Z0-9.]+\.trycloudflare\.com' \
  | tail -1 || true

echo
echo "=== RECENT ERRORS ==="
journalctl -u palaver-voice-backend.service -n 40 --no-pager || true
journalctl -u palaver-frontend.service -n 40 --no-pager || true
journalctl -u palaver-tunnel.service -n 40 --no-pager || true
