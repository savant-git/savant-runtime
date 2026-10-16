#!/usr/bin/env bash
set -euo pipefail

PALAVER_ROOT="/root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/palaver"
LAUNCHER="${PALAVER_ROOT}/commands/palaver_ultra"
PORT="8787"
BASE_URL="http://127.0.0.1:${PORT}"
LOG="/tmp/palaver-runtime.log"

listener_pids() {
    ss -ltnp "sport = :${PORT}" \
        | grep -oE 'pid=[0-9]+' \
        | cut -d= -f2 \
        | sort -u
}

echo "=== RESTART CANONICAL PALAVER ==="

mapfile -t PIDS < <(
    listener_pids
)

for pid in "${PIDS[@]:-}"; do
    [[ -z "${pid}" ]] && continue

    cmdline="$(
        tr '\0' ' ' <"/proc/${pid}/cmdline" \
        2>/dev/null \
        || true
    )"

    if [[ "${cmdline}" != *"/exiles/palaver/"* ]]; then
        echo "REFUSING TO TERMINATE NON-PALAVER PID ${pid}"
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
echo "=== SET WORKSPACE PERSONA ==="

SET_PREF="$(
    curl -fsS \
        -H 'Content-Type: application/json' \
        -d '{"persona_id":"historical_research_mode"}' \
        "${BASE_URL}/api/workspace/save"
)"

printf '%s\n' "${SET_PREF}"

SET_PREF_JSON="${SET_PREF}" python3 -c '
import json
import os

data = json.loads(
    os.environ["SET_PREF_JSON"]
)

required = {
    "ok": True,
    "workspace_persona": "historical_research_mode",
    "default_persona": "orobouros",
    "persona_owner": "envoy",
    "workspace_owner": "palaver",
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
        "WORKSPACE PERSONA SAVE FAILED: "
        + repr(bad)
    )

print("WORKSPACE PERSONA SAVE: valid")
'

echo
echo "=== VERIFY PREFERENCE ==="

PREF="$(
    curl -fsS \
        "${BASE_URL}/api/persona/preference"
)"

printf '%s\n' "${PREF}"

PREF_JSON="${PREF}" python3 -c '
import json
import os

data = json.loads(
    os.environ["PREF_JSON"]
)

required = {
    "ok": True,
    "workspace_persona": "historical_research_mode",
    "effective_persona": "historical_research_mode",
    "default_persona": "orobouros",
    "owner": "palaver",
    "persona_authority": "envoy",
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
        "PERSONA PREFERENCE READ FAILED: "
        + repr(bad)
    )

print("WORKSPACE PERSONA PREFERENCE: valid")
'

echo
echo "=== WORKSPACE PERSONA CHAT ==="

WORKSPACE_CHAT="$(
    curl -fsS \
        -H 'Content-Type: application/json' \
        -d '{"message":"Identify your active persona. Be concise."}' \
        "${BASE_URL}/api/chat"
)"

printf '%s\n' "${WORKSPACE_CHAT}"

WORKSPACE_CHAT_JSON="${WORKSPACE_CHAT}" python3 -c '
import json
import os

data = json.loads(
    os.environ["WORKSPACE_CHAT_JSON"]
)

required = {
    "ok": True,
    "persona_id": "historical_research_mode",
    "persona_source": "workspace",
    "workspace_persona": "historical_research_mode",
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
        "WORKSPACE CHAT FAILED: "
        + repr(bad)
    )

print("WORKSPACE PERSONA CHAT: valid")
'

echo
echo "=== REQUEST OVERRIDE ==="

OVERRIDE="$(
    curl -fsS \
        -H 'Content-Type: application/json' \
        -d '{"message":"Identify your active persona. Be concise.","persona_id":"orobouros"}' \
        "${BASE_URL}/api/chat"
)"

printf '%s\n' "${OVERRIDE}"

OVERRIDE_JSON="${OVERRIDE}" python3 -c '
import json
import os

data = json.loads(
    os.environ["OVERRIDE_JSON"]
)

required = {
    "ok": True,
    "persona_id": "orobouros",
    "persona_source": "request",
    "workspace_persona": "historical_research_mode",
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
        "REQUEST OVERRIDE FAILED: "
        + repr(bad)
    )

print("REQUEST PERSONA OVERRIDE: valid")
'

echo
echo "=== WORKSPACE RESTORATION ==="

RESTORED="$(
    curl -fsS \
        -H 'Content-Type: application/json' \
        -d '{"message":"Identify your active persona. Be concise."}' \
        "${BASE_URL}/api/chat"
)"

printf '%s\n' "${RESTORED}"

RESTORED_JSON="${RESTORED}" python3 -c '
import json
import os

data = json.loads(
    os.environ["RESTORED_JSON"]
)

if data.get("persona_id") != "historical_research_mode":
    raise SystemExit(
        "workspace persona did not restore"
    )

if data.get("persona_source") != "workspace":
    raise SystemExit(
        "restored persona source is not workspace"
    )

print("WORKSPACE PERSONA RESTORATION: valid")
'

echo
echo "=== PRESERVE PREFERENCE THROUGH ORDINARY WORKSPACE SAVE ==="

SAVE_OTHER="$(
    curl -fsS \
        -H 'Content-Type: application/json' \
        -d '{"open_file":"README.md","panel":"editor"}' \
        "${BASE_URL}/api/workspace/save"
)"

printf '%s\n' "${SAVE_OTHER}"

PREF_AFTER="$(
    curl -fsS \
        "${BASE_URL}/api/persona/preference"
)"

PREF_AFTER_JSON="${PREF_AFTER}" python3 -c '
import json
import os

data = json.loads(
    os.environ["PREF_AFTER_JSON"]
)

if data.get("workspace_persona") != "historical_research_mode":
    raise SystemExit(
        "ordinary workspace save erased persona preference"
    )

print("WORKSPACE PERSONA CARRY-FORWARD: valid")
'

echo
echo "=== CLEAR WORKSPACE PERSONA ==="

CLEAR="$(
    curl -fsS \
        -H 'Content-Type: application/json' \
        -d '{"persona_id":null}' \
        "${BASE_URL}/api/workspace/save"
)"

printf '%s\n' "${CLEAR}"

CLEAR_JSON="${CLEAR}" python3 -c '
import json
import os

data = json.loads(
    os.environ["CLEAR_JSON"]
)

if data.get("ok") is not True:
    raise SystemExit(
        "workspace preference clear failed"
    )

if data.get("workspace_persona") is not None:
    raise SystemExit(
        "workspace persona was not cleared"
    )

print("WORKSPACE PERSONA CLEAR: valid")
'

echo
echo "=== DEFAULT FALLBACK ==="

DEFAULT_CHAT="$(
    curl -fsS \
        -H 'Content-Type: application/json' \
        -d '{"message":"Identify your active persona. Be concise."}' \
        "${BASE_URL}/api/chat"
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
    "persona_source": "default",
    "workspace_persona": None,
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
        "DEFAULT FALLBACK FAILED: "
        + repr(bad)
    )

print("OROBOUROS DEFAULT FALLBACK: valid")
'

echo
echo "=== RESULT ==="

echo "PALAVER PERSONA PREFERENCE: valid"
echo "persona_precedence=request>workspace>default"
echo "default_persona=orobouros"
echo "persona_owner=envoy"
echo "workspace_owner=palaver"
echo "provider_owner=opus"
