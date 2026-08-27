#!/usr/bin/env bash

set -euo pipefail

ROOT="/root/savant-runtime"
MASTERPLAN_ROOT="${ROOT}/tools/niche/masterplan"
REPORT_ROOT="${ROOT}/reports/niche/masterplan"

MASTERPLAN_PROJECT="${ROOT}/bin/masterplan-project"
PACKET_COMMAND="${ROOT}/bin/masterplan-opus-packet"
QUEUE_COMMAND="${ROOT}/bin/masterplan-opus-queue"
DISCOVERY_COMMAND="${ROOT}/bin/masterplan-opus-discover"
PLAN_COMMAND="${ROOT}/bin/masterplan-opus-plan"

PACKET_TOOL="${MASTERPLAN_ROOT}/build_masterplan_opus_packet.py"
QUEUE_TOOL="${MASTERPLAN_ROOT}/compile_masterplan_opus_queue.py"
DISCOVERY_TOOL="${MASTERPLAN_ROOT}/discover_masterplan_opus_binding.py"
PLAN_TOOL="${MASTERPLAN_ROOT}/compile_masterplan_opus_binding_plan.py"

PACKET_TEST="${ROOT}/hierarchies/identity/exiles/niche/prodigals/masterplan/tests/test_masterplan_opus_packet.py"
QUEUE_TEST="${ROOT}/hierarchies/identity/exiles/niche/prodigals/masterplan/tests/test_masterplan_opus_queue.py"
DISCOVERY_TEST="${ROOT}/hierarchies/identity/exiles/niche/prodigals/masterplan/tests/test_discover_masterplan_opus_binding.py"
PLAN_TEST="${ROOT}/hierarchies/identity/exiles/niche/prodigals/masterplan/tests/test_compile_masterplan_opus_binding_plan.py"

AGENT_CONTEXT="${REPORT_ROOT}/agent_context/latest.json"
PACKET_LATEST="${REPORT_ROOT}/opus-packets/latest.json"
QUEUE_LATEST="${REPORT_ROOT}/opus-queue/latest.json"
DISCOVERY_LATEST="${REPORT_ROOT}/opus-binding-discovery/latest.json"
PLAN_LATEST="${REPORT_ROOT}/opus-binding-plan/latest.json"

REQUIRED_FILES=(
  "${MASTERPLAN_PROJECT}"
  "${PACKET_COMMAND}"
  "${QUEUE_COMMAND}"
  "${DISCOVERY_COMMAND}"
  "${PLAN_COMMAND}"
  "${PACKET_TOOL}"
  "${QUEUE_TOOL}"
  "${DISCOVERY_TOOL}"
  "${PLAN_TOOL}"
  "${PACKET_TEST}"
  "${QUEUE_TEST}"
  "${DISCOVERY_TEST}"
  "${PLAN_TEST}"
)

for path in "${REQUIRED_FILES[@]}"; do
  if [[ ! -f "${path}" ]]; then
    printf 'ERROR: required file missing: %s\n' "${path}" >&2
    exit 1
  fi
done

chmod 0755 \
  "${MASTERPLAN_PROJECT}" \
  "${PACKET_COMMAND}" \
  "${QUEUE_COMMAND}" \
  "${DISCOVERY_COMMAND}" \
  "${PLAN_COMMAND}" \
  "${PACKET_TOOL}" \
  "${QUEUE_TOOL}" \
  "${DISCOVERY_TOOL}" \
  "${PLAN_TOOL}" \
  "${PACKET_TEST}" \
  "${QUEUE_TEST}" \
  "${DISCOVERY_TEST}" \
  "${PLAN_TEST}" \
  "${0}"

python3 -m py_compile \
  "${PACKET_COMMAND}" \
  "${QUEUE_COMMAND}" \
  "${DISCOVERY_COMMAND}" \
  "${PLAN_COMMAND}" \
  "${PACKET_TOOL}" \
  "${QUEUE_TOOL}" \
  "${DISCOVERY_TOOL}" \
  "${PLAN_TOOL}" \
  "${PACKET_TEST}" \
  "${QUEUE_TEST}" \
  "${DISCOVERY_TEST}" \
  "${PLAN_TEST}"

python3 \
  "${PACKET_TEST}" \
  -v

python3 \
  "${QUEUE_TEST}" \
  -v

python3 \
  "${DISCOVERY_TEST}" \
  -v

python3 \
  "${PLAN_TEST}" \
  -v

"${MASTERPLAN_PROJECT}" \
  agent_context

test -f \
  "${AGENT_CONTEXT}"

python3 -m json.tool \
  "${AGENT_CONTEXT}" \
  >/dev/null

"${PACKET_COMMAND}" \
  build

"${PACKET_COMMAND}" \
  verify

test -f \
  "${PACKET_LATEST}"

python3 -m json.tool \
  "${PACKET_LATEST}" \
  >/dev/null

"${QUEUE_COMMAND}" \
  compile

"${QUEUE_COMMAND}" \
  verify

test -f \
  "${QUEUE_LATEST}"

python3 -m json.tool \
  "${QUEUE_LATEST}" \
  >/dev/null

set +e

"${DISCOVERY_COMMAND}" \
  discover

discovery_status="$?"

set -e

test \
  "${discovery_status}" -eq 0 \
  -o "${discovery_status}" -eq 2

"${DISCOVERY_COMMAND}" \
  verify

test -f \
  "${DISCOVERY_LATEST}"

python3 -m json.tool \
  "${DISCOVERY_LATEST}" \
  >/dev/null

set +e

"${PLAN_COMMAND}" \
  compile

plan_status="$?"

set -e

test \
  "${plan_status}" -eq 0 \
  -o "${plan_status}" -eq 2

"${PLAN_COMMAND}" \
  verify

test -f \
  "${PLAN_LATEST}"

python3 -m json.tool \
  "${PLAN_LATEST}" \
  >/dev/null

python3 -c '
import json
from pathlib import Path

root = Path(
    "/root/savant-runtime/reports/niche/masterplan"
)

packet_latest = json.loads(
    (
        root
        / "opus-packets"
        / "latest.json"
    ).read_text(
        encoding="utf-8"
    )
)

queue_latest = json.loads(
    (
        root
        / "opus-queue"
        / "latest.json"
    ).read_text(
        encoding="utf-8"
    )
)

discovery_latest = json.loads(
    (
        root
        / "opus-binding-discovery"
        / "latest.json"
    ).read_text(
        encoding="utf-8"
    )
)

plan_latest = json.loads(
    (
        root
        / "opus-binding-plan"
        / "latest.json"
    ).read_text(
        encoding="utf-8"
    )
)

print(
    "packet:",
    packet_latest["packet_id"],
)

print(
    "queue:",
    queue_latest["queue_id"],
)

print(
    "queue records:",
    queue_latest["record_count"],
)

print(
    "discovery state:",
    discovery_latest["selection_state"],
)

print(
    "selected runtime:",
    discovery_latest["selected_candidate"],
)

print(
    "missing capabilities:",
    discovery_latest["missing_capability_count"],
)

print(
    "plan:",
    plan_latest["plan_id"],
)

print(
    "plan state:",
    plan_latest["state"],
)

print(
    "plan blockers:",
    plan_latest["blocker_count"],
)
'
