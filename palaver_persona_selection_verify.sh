#!/usr/bin/env bash
set -euo pipefail

PALAVER_ROOT="/root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/palaver"
SERVER="${PALAVER_ROOT}/runtime/server.py"
LAUNCHER="${PALAVER_ROOT}/commands/palaver_ultra"
PORT="8787"
LOG="/tmp/palaver-runtime.log"

echo "=== SYNTAX ==="

python3 -m py_compile "${SERVER}"

echo "PALAVER SERVER SYNTAX: valid"

echo
echo "=== BOOTSTRAP ==="

BOOTSTRAP="$(
    PALAVER_BOOTSTRAP_INSPECT=1 \
    "${LAUNCHER}"
)"

printf '%s\n' "${BOOTSTRAP}"

BOOTSTRAP_JSON="${BOOTSTRAP}" python3 -c '
import json
import os

data = json.loads(
    os.environ["BOOTSTRAP_JSON"]
)

required = {
    "canonical_main_installed": True,
    "canonical_handler_installed": True,
    "persona_http_surface_installed": True,
    "chat_persona_selection_installed": True,
    "opus_inference_installed": True,
    "orobouros_default_persona": True,
    "orobouros_projection_ready": True,
    "persona_owner": "envoy",
    "provider_owner": "opus",
    "default_persona": "orobouros",
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
        "BOOTSTRAP VALIDATION FAILED: "
        + repr(bad)
    )

print("PALAVER PERSONA BOOTSTRAP: valid")
'

echo
echo "=== RESTART ==="

mapfile -t PIDS < <(
    ss -ltnp "sport = :${PORT}" \
    | grep -oE 'pid=[0-9]+' \
    | cut -d= -f2 \
    | sort -u
)

for pid in "${PIDS[@]:-}"; do
    [[ -z "${pid}" ]] && continue

    cmdline="$(
        tr '\0' ' ' <"/proc/${pid}/cmdline" \
        2>/dev/null \
        || true
    )"

    if [[ "${cmdline}" != *"/exiles/palaver/"* ]]; then
        echo "REFUSING TO KILL NON-PALAVER PID ${pid}"
        echo "${cmdline}"
        exit 1
    fi

    kill -TERM "${pid}" 2>/dev/null || true
done

for _ in {1..40}; do
    if ! ss -ltnp "sport = :${PORT}" | grep -q LISTEN; then
        break
    fi

    sleep 0.25
done

if ss -ltnp "sport = :${PORT}" | grep -q LISTEN; then
    echo "PORT ${PORT} STILL OCCUPIED"
    ss -ltnp "sport = :${PORT}"
    exit 1
fi

: >"${LOG}"

nohup "${LAUNCHER}" \
    >"${LOG}" \
    2>&1 &

NEW_PID="$!"

for _ in {1..40}; do
    if ! kill -0 "${NEW_PID}" 2>/dev/null; then
        echo "PALAVER STARTUP FAILED"
        cat "${LOG}"
        exit 1
    fi

    if ss -ltnp "sport = :${PORT}" \
        | grep -q "pid=${NEW_PID}"; then
        break
    fi

    sleep 0.25
done

if ! ss -ltnp "sport = :${PORT}" \
    | grep -q "pid=${NEW_PID}"; then
    echo "PALAVER DID NOT ACQUIRE PORT ${PORT}"
    cat "${LOG}"
    exit 1
fi

echo "PALAVER LISTENER: valid"
echo "pid=${NEW_PID}"

echo
echo "=== PERSONA DISCOVERY ==="

PERSONAS="$(
    curl -fsS \
        "http://127.0.0.1:${PORT}/api/personas"
)"

printf '%s\n' "${PERSONAS}"

PERSONAS_JSON="${PERSONAS}" python3 -c '
import json
import os

data = json.loads(
    os.environ["PERSONAS_JSON"]
)

if data.get("ok") is not True:
    raise SystemExit(
        "persona discovery did not return ok=true"
    )

if data.get("owner") != "envoy":
    raise SystemExit(
        "persona discovery owner is not Envoy"
    )

if data.get("default_persona") != "orobouros":
    raise SystemExit(
        "default persona is not Orobouros"
    )

rows = data.get("personas") or []

ids = {
    row.get("persona_id")
    for row in rows
    if isinstance(row, dict)
}

required = {
    "orobouros",
    "palaver_default",
    "historical_research_mode",
}

missing = sorted(
    required - ids
)

if missing:
    raise SystemExit(
        "persona discovery missing: "
        + repr(missing)
    )

print("PALAVER PERSONA DISCOVERY: valid")
'

echo
echo "=== DEFAULT CHAT ==="

DEFAULT_CHAT="$(
    curl -fsS \
        -H 'Content-Type: application/json' \
        -d '{"message":"Identify your active persona. Be concise."}' \
        "http://127.0.0.1:${PORT}/api/chat"
)"

printf '%s\n' "${DEFAULT_CHAT}"

DEFAULT_CHAT_JSON="${DEFAULT_CHAT}" python3 -c '
import json
import os

data = json.loads(
    os.environ["DEFAULT_CHAT_JSON"]
)

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
        "DEFAULT CHAT VALIDATION FAILED: "
        + repr(bad)
    )

print("PALAVER DEFAULT PERSONA CHAT: valid")
'

echo
echo "=== NON-DEFAULT CHAT ==="

NONDEFAULT_CHAT="$(
    curl -fsS \
        -H 'Content-Type: application/json' \
        -d '{"message":"Identify your active persona. Be concise.","persona_id":"historical_research_mode"}' \
        "http://127.0.0.1:${PORT}/api/chat"
)"

printf '%s\n' "${NONDEFAULT_CHAT}"

NONDEFAULT_CHAT_JSON="${NONDEFAULT_CHAT}" python3 -c '
import json
import os

data = json.loads(
    os.environ["NONDEFAULT_CHAT_JSON"]
)

required = {
    "ok": True,
    "persona_id": "historical_research_mode",
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
        "NON-DEFAULT CHAT VALIDATION FAILED: "
        + repr(bad)
    )

print("PALAVER NON-DEFAULT PERSONA CHAT: valid")
'

echo
echo "=== DEFAULT RESTORATION ==="

RESTORED="$(
    curl -fsS \
        -H 'Content-Type: application/json' \
        -d '{"message":"Identify your active persona. Be concise."}' \
        "http://127.0.0.1:${PORT}/api/chat"
)"

printf '%s\n' "${RESTORED}"

RESTORED_JSON="${RESTORED}" python3 -c '
import json
import os

data = json.loads(
    os.environ["RESTORED_JSON"]
)

if data.get("persona_id") != "orobouros":
    raise SystemExit(
        "request-scoped persona leaked into later request"
    )

print("PALAVER PERSONA REQUEST ISOLATION: valid")
'

echo
echo "=== RESULT ==="

echo "PALAVER PERSONA SELECTION: valid"
echo "default_persona=orobouros"
echo "persona_owner=envoy"
echo "provider_owner=opus"
echo "conversation_owner=palaver"
