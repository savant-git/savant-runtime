#!/usr/bin/env bash
set -euo pipefail

PALAVER_SERVER="/root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/palaver/runtime/server.py"
STATUS_FILE="/tmp/palaver-bootstrap-status.json"
LOG_FILE="/tmp/palaver-runtime.log"
PORT="8787"

listener_pids() {
    ss -ltnp "sport = :${PORT}" \
        | grep -oE 'pid=[0-9]+' \
        | cut -d= -f2 \
        | sort -u
}

listener_cmdline() {
    local pid="$1"

    if [[ ! -r "/proc/${pid}/cmdline" ]]; then
        return 1
    fi

    tr '\0' ' ' <"/proc/${pid}/cmdline"
}

is_palaver_process() {
    local pid="$1"
    local cmdline

    cmdline="$(listener_cmdline "${pid}" || true)"

    [[ "${cmdline}" == *"/exiles/palaver/"* ]] \
        || [[ "${cmdline}" == *"palaver"* ]]
}

echo "=== SYNTAX ==="

python3 -m py_compile "${PALAVER_SERVER}"

echo "PALAVER SERVER SYNTAX: valid"

echo
echo "=== BOOTSTRAP / OWNERSHIP ==="

PALAVER_BOOTSTRAP_INSPECT=1 \
python3 -u "${PALAVER_SERVER}" >"${STATUS_FILE}"

cat "${STATUS_FILE}"

python3 -c '
import json

path = "/tmp/palaver-bootstrap-status.json"

with open(path, encoding="utf-8") as handle:
    data = json.load(handle)

required = {
    "canonical_main_installed": True,
    "canonical_handler_installed": True,
    "opus_inference_installed": True,
    "envoy_voice_installed": True,
    "orobouros_default_persona": True,
    "orobouros_projection_ready": True,
    "provider_owner": "opus",
    "persona_owner": "envoy",
    "default_persona": "orobouros",
    "conversation_owner": "palaver",
    "task_owner": "niche",
    "mutation_owner": "coda",
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

print("PALAVER OWNERSHIP: valid")
print("OROBOUROS BOOTSTRAP: valid")
'

echo
echo "=== EXISTING LISTENER ==="

mapfile -t OLD_PIDS < <(
    listener_pids
)

if (( ${#OLD_PIDS[@]} > 0 )); then
    for pid in "${OLD_PIDS[@]}"; do
        cmdline="$(listener_cmdline "${pid}" || true)"

        echo "PID ${pid}: ${cmdline}"

        if ! is_palaver_process "${pid}"; then
            echo "REFUSING TO TERMINATE NON-PALAVER LISTENER"
            exit 1
        fi
    done

    echo "Stopping verified Palaver listener(s): ${OLD_PIDS[*]}"

    for pid in "${OLD_PIDS[@]}"; do
        kill -TERM "${pid}" 2>/dev/null || true
    done

    for _ in {1..40}; do
        if ! ss -ltnp "sport = :${PORT}" | grep -q LISTEN; then
            break
        fi

        sleep 0.25
    done
fi

if ss -ltnp "sport = :${PORT}" | grep -q LISTEN; then
    echo "PORT ${PORT} STILL OCCUPIED"
    ss -ltnp "sport = :${PORT}"
    exit 1
fi

echo "PORT ${PORT}: free"

echo
echo "=== START CANONICAL PALAVER ==="

: >"${LOG_FILE}"

nohup python3 -u "${PALAVER_SERVER}" \
    >"${LOG_FILE}" \
    2>&1 &

NEW_PID="$!"

for _ in {1..40}; do
    if ! kill -0 "${NEW_PID}" 2>/dev/null; then
        echo "PALAVER STARTUP FAILED"
        cat "${LOG_FILE}"
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
    cat "${LOG_FILE}"
    exit 1
fi

echo "Canonical Palaver PID: ${NEW_PID}"

echo
echo "=== LISTENER ==="

ss -ltnp "sport = :${PORT}"

echo
echo "=== ROUTES ==="

ROUTES="$(
    curl -fsS \
        "http://127.0.0.1:${PORT}/api/routes"
)"

printf '%s\n' "${ROUTES}"

ROUTES_JSON="${ROUTES}" python3 -c '
import json
import os

data = json.loads(os.environ["ROUTES_JSON"])

if data.get("ok") is not True:
    raise SystemExit("routes endpoint did not return ok=true")

routes = data.get("routes") or {}

required_post = {
    "/api/chat",
    "/api/voice/synthesize",
}

missing = sorted(
    required_post
    - set(routes.get("post") or [])
)

if missing:
    raise SystemExit(
        "missing canonical routes: "
        + repr(missing)
    )

print("PALAVER ROUTES: valid")
'

echo
echo "=== OROBOUROS PROJECTION ==="

python3 -c '
import importlib.util
from pathlib import Path

path = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/palaver/runtime/server.py"
)

spec = importlib.util.spec_from_file_location(
    "palaver_live_projection_test",
    path,
)

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

legacy = module.bootstrap()

projection = (
    legacy
    .palaver_envoy_default_persona_projection(
        domains=("engineering", "analysis"),
        signals=("implement", "verify", "code"),
        cap=4,
    )
)

if projection.get("persona_id") != "orobouros":
    raise SystemExit(
        "default projection is not Orobouros"
    )

if len(
    projection.get("living_trait_crown") or []
) > 4:
    raise SystemExit(
        "Living Trait Crown exceeded cap"
    )

if getattr(
    legacy.call_openai,
    "__name__",
    "",
) != "call_opus":
    raise SystemExit(
        "Palaver inference is not delegated to Opus"
    )

print({
    "persona_id": projection["persona_id"],
    "living_trait_crown": projection["living_trait_crown"],
    "inference_delegate": legacy.call_openai.__name__,
})

print("PALAVER OROBOUROS PROJECTION: valid")
'

echo
echo "=== LIVE CHAT ==="

CHAT="$(
    curl -fsS \
        -H 'Content-Type: application/json' \
        -d '{"message":"Identify your active persona. Be concise."}' \
        "http://127.0.0.1:${PORT}/api/chat"
)"

printf '%s\n' "${CHAT}"

CHAT_JSON="${CHAT}" python3 -c '
import json
import os

data = json.loads(os.environ["CHAT_JSON"])

if data.get("ok") is not True:
    raise SystemExit(
        "chat endpoint did not return ok=true"
    )

answer = str(
    data.get("answer")
    or ""
).lower()

if "orobouros" not in answer:
    raise SystemExit(
        "live chat did not identify Orobouros"
    )

trace = str(
    data.get("trace")
    or ""
).lower()

if "openai ok" not in trace:
    raise SystemExit(
        "live inference trace did not succeed"
    )

print("PALAVER LIVE CHAT: valid")
'

echo
echo "=== RESULT ==="

echo "PALAVER OROBOUROS INTEGRATION: valid"
echo "persona_owner=envoy"
echo "provider_owner=opus"
echo "conversation_owner=palaver"
echo "default_persona=orobouros"
echo "pid=${NEW_PID}"
echo "port=${PORT}"
