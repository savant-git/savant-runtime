#!/usr/bin/env bash
set -euo pipefail

BASE_URL="http://127.0.0.1:8787"
PROBE_PATH="runtime/reports/palaver-coda-workstation-probe.txt"
ABSOLUTE_PROBE="/root/savant-runtime/${PROBE_PATH}"
CONTENT="PALAVER_CODA_WORKSTATION_PROBE_V1"

echo "=== WRITE THROUGH PALAVER -> CODA ==="

WRITE="$(
    curl -fsS \
        -H 'Content-Type: application/json' \
        -d "$(
            python3 -c '
import json
print(json.dumps({
    "path": "runtime/reports/palaver-coda-workstation-probe.txt",
    "content": "PALAVER_CODA_WORKSTATION_PROBE_V1"
}))
'
        )" \
        "${BASE_URL}/api/file/save"
)"

printf '%s\n' "${WRITE}"

WRITE_JSON="${WRITE}" python3 -c '
import json
import os

data = json.loads(os.environ["WRITE_JSON"])

if data.get("ok") is not True:
    raise SystemExit("Palaver file save did not return ok=true")

result = data.get("file") or {}

required = {
    "path": "runtime/reports/palaver-coda-workstation-probe.txt",
    "owner": "coda",
    "atomic": True,
    "verified": True,
}

bad = {
    key: {
        "actual": result.get(key),
        "expected": expected,
    }
    for key, expected in required.items()
    if result.get(key) != expected
}

if bad:
    raise SystemExit(
        "CODA WRITE VALIDATION FAILED: "
        + repr(bad)
    )

if not result.get("receipt_id"):
    raise SystemExit("Coda mutation receipt missing")

if not result.get("after_digest"):
    raise SystemExit("Coda after_digest missing")

print("PALAVER -> CODA WRITE: valid")
print("receipt_id=" + result["receipt_id"])
print("after_digest=" + result["after_digest"])
'

echo
echo "=== FILESYSTEM READ-BACK ==="

if [[ ! -f "${ABSOLUTE_PROBE}" ]]; then
    echo "Probe file missing after successful mutation response"
    exit 1
fi

ACTUAL="$(
    cat "${ABSOLUTE_PROBE}"
)"

if [[ "${ACTUAL}" != "${CONTENT}" ]]; then
    echo "Probe contents do not match"
    exit 1
fi

printf '%s\n' "${ACTUAL}"
echo "CODA FILESYSTEM READ-BACK: valid"

echo
echo "=== PALAVER FILE READ-BACK ==="

READ="$(
    curl -fsS \
        --get \
        --data-urlencode "path=${PROBE_PATH}" \
        "${BASE_URL}/api/file"
)"

printf '%s\n' "${READ}"

READ_JSON="${READ}" EXPECTED="${CONTENT}" python3 -c '
import json
import os

data = json.loads(os.environ["READ_JSON"])

if data.get("ok") is False:
    raise SystemExit(
        "Palaver file read reported failure: "
        + repr(data)
    )

expected = os.environ["EXPECTED"]

candidates = []

for key in (
    "content",
    "text",
    "data",
):
    value = data.get(key)

    if isinstance(value, str):
        candidates.append(value)

file_value = data.get("file")

if isinstance(file_value, dict):
    for key in (
        "content",
        "text",
        "data",
    ):
        value = file_value.get(key)

        if isinstance(value, str):
            candidates.append(value)

if expected not in candidates:
    raise SystemExit(
        "Palaver file endpoint did not return exact probe content: "
        + repr(data)
    )

print("PALAVER FILE READ-BACK: valid")
'

echo
echo "=== CLEANUP ==="

rm -f "${ABSOLUTE_PROBE}"

if [[ -e "${ABSOLUTE_PROBE}" ]]; then
    echo "Probe cleanup failed"
    exit 1
fi

echo "PROBE CLEANUP: valid"

echo
echo "=== RESULT ==="
echo "PALAVER CODA WORKSTATION PATH: valid"
echo "conversation_owner=palaver"
echo "mutation_owner=coda"
echo "durable_write=verified"
echo "atomic_write=verified"
echo "receipt=verified"
