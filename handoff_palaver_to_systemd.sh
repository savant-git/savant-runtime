#!/usr/bin/env bash
set -euo pipefail

PORT="8787"
SERVICE="palaver.service"
CANONICAL_FRAGMENT="/exiles/palaver/runtime/server.py"

current_pid() {
  ss -ltnp "sport = :${PORT}" 2>/dev/null \
    | grep -oE 'pid=[0-9]+' \
    | cut -d= -f2 \
    | head -n1 \
    || true
}

printf '\n=== CURRENT LISTENER ===\n'

PID="$(current_pid)"

if [ -z "$PID" ]; then
  echo "No listener currently owns port ${PORT}."
else
  CMDLINE="$(
    tr '\0' ' ' <"/proc/$PID/cmdline" 2>/dev/null \
      || true
  )"

  printf 'pid=%s\n' "$PID"
  printf 'cmdline=%s\n' "$CMDLINE"

  if [[ "$CMDLINE" != *"$CANONICAL_FRAGMENT"* ]]; then
    echo "Refusing handoff: current listener is not canonical Palaver." >&2
    exit 1
  fi

  printf '\n=== STOP MANUAL CANONICAL PALAVER ===\n'
  kill -TERM "$PID"

  for _ in {1..40}; do
    if ! kill -0 "$PID" 2>/dev/null; then
      break
    fi
    sleep 0.25
  done

  if kill -0 "$PID" 2>/dev/null; then
    echo "Manual Palaver process did not terminate." >&2
    exit 1
  fi
fi

if ss -ltnp "sport = :${PORT}" | grep -q LISTEN; then
  echo "Port ${PORT} is still occupied after manual-process stop." >&2
  ss -ltnp "sport = :${PORT}"
  exit 1
fi

printf '\n=== START CANONICAL SYSTEMD SERVICE ===\n'

systemctl start "$SERVICE"

for _ in {1..40}; do
  if systemctl is-active --quiet "$SERVICE" \
    && ss -ltnp "sport = :${PORT}" | grep -q LISTEN; then
    break
  fi
  sleep 0.25
done

if ! systemctl is-active --quiet "$SERVICE"; then
  echo "palaver.service failed to become active." >&2
  systemctl --no-pager --full status "$SERVICE" || true
  journalctl -u "$SERVICE" -n 80 --no-pager || true
  exit 1
fi

NEW_PID="$(current_pid)"

if [ -z "$NEW_PID" ]; then
  echo "palaver.service is active but port ${PORT} has no listener." >&2
  exit 1
fi

NEW_CMDLINE="$(
  tr '\0' ' ' <"/proc/$NEW_PID/cmdline" 2>/dev/null \
    || true
)"

if [[ "$NEW_CMDLINE" != *"$CANONICAL_FRAGMENT"* ]]; then
  echo "Port ${PORT} is not owned by canonical Palaver after handoff." >&2
  printf 'pid=%s\ncmdline=%s\n' "$NEW_PID" "$NEW_CMDLINE"
  exit 1
fi

printf '\n=== SYSTEMD OWNERSHIP ===\n'

printf 'pid=%s\n' "$NEW_PID"
printf 'cmdline=%s\n' "$NEW_CMDLINE"

cat "/proc/$NEW_PID/cgroup"

printf '\n=== SERVICE STATUS ===\n'

systemctl --no-pager --full status "$SERVICE"

printf '\n=== HISTORICAL VOICE BACKEND ===\n'

systemctl is-active palaver-voice-backend.service || true
systemctl is-enabled palaver-voice-backend.service || true

printf '\n=== LIVE CHAT CHECK ===\n'

RESPONSE="$(
  curl -fsS \
    -H 'Content-Type: application/json' \
    -d '{"message":"Identify your active persona in one sentence."}' \
    "http://127.0.0.1:${PORT}/api/chat"
)"

printf '%s\n' "$RESPONSE" | python3 -m json.tool

RESPONSE_JSON="$RESPONSE" python3 -c '
import json
import os

data = json.loads(os.environ["RESPONSE_JSON"])

required = {
    "ok": True,
    "persona_id": "orobouros",
    "persona_owner": "envoy",
    "provider_owner": "opus",
    "conversation_owner": "palaver",
}

bad = {
    key: {
        "actual": data.get(key),
        "expected": expected,
    }
    for key, expected in required.items()
    if data.get(key) != expected
}

if bad:
    raise SystemExit(
        "LIVE CHAT VALIDATION FAILED: "
        + repr(bad)
    )

receipt = data.get("context_receipt")

if not isinstance(receipt, dict):
    raise SystemExit(
        "missing Scrybe context receipt"
    )

receipt_required = {
    "owner": "scrybe",
    "canonical_memory_store": "fluid-canon",
    "authoritative": False,
    "rebuildable": True,
}

receipt_bad = {
    key: {
        "actual": receipt.get(key),
        "expected": expected,
    }
    for key, expected in receipt_required.items()
    if receipt.get(key) != expected
}

if receipt_bad:
    raise SystemExit(
        "CONTEXT RECEIPT VALIDATION FAILED: "
        + repr(receipt_bad)
    )

trace = str(data.get("trace") or "")

for required_trace in (
    "openai ok",
    "scrybe context digest=",
):
    if required_trace not in trace:
        raise SystemExit(
            "missing trace evidence: "
            + required_trace
        )

print("PALAVER SYSTEMD LIVE CHAT: valid")
'

printf '\n=== RESULT ===\n'

echo "PALAVER SYSTEMD HANDOFF: valid"
echo "service=palaver.service"
echo "port=${PORT}"
echo "pid=${NEW_PID}"
echo "conversation_owner=palaver"
echo "persona_owner=envoy"
echo "provider_owner=opus"
echo "memory_context_owner=scrybe"
echo "canonical_memory_store=fluid-canon"
