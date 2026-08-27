#!/usr/bin/env bash

set -euo pipefail

ROOT="/root/savant-runtime"

PACKET_VALIDATOR="${ROOT}/tools/niche/masterplan/validate_masterplan_opus_packet.sh"
QUEUE_TOOL="${ROOT}/tools/niche/masterplan/compile_masterplan_opus_queue.py"
CYCLE_TOOL="${ROOT}/tools/niche/masterplan/run_masterplan_living_cycle.py"
QUEUE_TEST="${ROOT}/hierarchies/identity/exiles/niche/prodigals/masterplan/tests/test_masterplan_opus_queue.py"
QUEUE_COMMAND="${ROOT}/bin/masterplan-opus-queue"
LIVE_COMMAND="${ROOT}/bin/masterplan-live"

LATEST_QUEUE="${ROOT}/reports/niche/masterplan/opus-queue/latest.json"
LATEST_CYCLE="${ROOT}/reports/niche/masterplan/living-cycle/latest.json"

test -f \
  "${PACKET_VALIDATOR}"

test -f \
  "${QUEUE_TOOL}"

test -f \
  "${CYCLE_TOOL}"

test -f \
  "${QUEUE_TEST}"

test -f \
  "${QUEUE_COMMAND}"

test -f \
  "${LIVE_COMMAND}"

chmod 0755 \
  "${PACKET_VALIDATOR}" \
  "${QUEUE_TOOL}" \
  "${CYCLE_TOOL}" \
  "${QUEUE_TEST}" \
  "${QUEUE_COMMAND}" \
  "${LIVE_COMMAND}"

bash -n \
  "${PACKET_VALIDATOR}"

python3 -m py_compile \
  "${QUEUE_TOOL}" \
  "${CYCLE_TOOL}" \
  "${QUEUE_TEST}" \
  "${QUEUE_COMMAND}" \
  "${LIVE_COMMAND}"

"${PACKET_VALIDATOR}"

python3 \
  "${QUEUE_TEST}" \
  -v

"${QUEUE_COMMAND}" \
  compile

"${QUEUE_COMMAND}" \
  verify

"${LIVE_COMMAND}" \
  prepare

"${LIVE_COMMAND}" \
  verify

test -f \
  "${LATEST_QUEUE}"

test -f \
  "${LATEST_CYCLE}"

python3 -m json.tool \
  "${LATEST_QUEUE}" \
  >/dev/null

python3 -m json.tool \
  "${LATEST_CYCLE}" \
  >/dev/null

python3 -c '
import json
from pathlib import Path

queue_latest_path = Path(
    "/root/savant-runtime/reports/niche/"
    "masterplan/opus-queue/latest.json"
)

cycle_latest_path = Path(
    "/root/savant-runtime/reports/niche/"
    "masterplan/living-cycle/latest.json"
)

queue_latest = json.loads(
    queue_latest_path.read_text(
        encoding="utf-8"
    )
)

cycle_latest = json.loads(
    cycle_latest_path.read_text(
        encoding="utf-8"
    )
)

queue_path = Path(
    queue_latest["queue"]
)

queue = json.loads(
    queue_path.read_text(
        encoding="utf-8"
    )
)

print(
    "task:",
    queue["task"]["id"],
    "-",
    queue["task"]["title"],
)

print(
    "queue:",
    queue["queue_id"],
)

print(
    "records:",
    queue["record_count"],
)

print(
    "state:",
    queue_latest["state"],
)

print(
    "cycle:",
    cycle_latest["cycle_id"],
)

print(
    "cycle passed:",
    cycle_latest["passed"],
)

print(
    "provider calls performed:",
    cycle_latest["provider_calls_performed"],
)

print(
    "implementation mutation performed:",
    cycle_latest[
        "implementation_mutation_performed"
    ],
)

for record in queue["records"]:
    assignment = record["assignment"]

    print(
        f"{assignment['"'"'ordinal'"'"']}. "
        f"{assignment['"'"'key'"'"']}: "
        f"{record['"'"'state'"'"']}"
    )
'
