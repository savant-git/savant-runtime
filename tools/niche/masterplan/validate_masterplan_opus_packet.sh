#!/usr/bin/env bash

set -euo pipefail

ROOT="/root/savant-runtime"

PACKET_TOOL="${ROOT}/tools/niche/masterplan/build_masterplan_opus_packet.py"
PACKET_TEST="${ROOT}/hierarchies/identity/exiles/niche/prodigals/masterplan/tests/test_masterplan_opus_packet.py"
PACKET_COMMAND="${ROOT}/bin/masterplan-opus-packet"
MASTERPLAN_COMMAND="${ROOT}/bin/masterplan-project"
LATEST_PACKET="${ROOT}/reports/niche/masterplan/opus-packets/latest.json"

test -f \
  "${PACKET_TOOL}"

test -f \
  "${PACKET_TEST}"

test -f \
  "${PACKET_COMMAND}"

test -f \
  "${MASTERPLAN_COMMAND}"

chmod 0755 \
  "${PACKET_TOOL}" \
  "${PACKET_TEST}" \
  "${PACKET_COMMAND}"

python3 -m py_compile \
  "${PACKET_TOOL}" \
  "${PACKET_TEST}" \
  "${PACKET_COMMAND}"

python3 \
  "${PACKET_TEST}" \
  -v

"${MASTERPLAN_COMMAND}" \
  agent_context

"${PACKET_COMMAND}" \
  build

"${PACKET_COMMAND}" \
  verify

test -f \
  "${LATEST_PACKET}"

python3 -m json.tool \
  "${LATEST_PACKET}" \
  >/dev/null

python3 -c '
import json
from pathlib import Path

latest_path = Path(
    "/root/savant-runtime/reports/niche/"
    "masterplan/opus-packets/latest.json"
)

latest = json.loads(
    latest_path.read_text(
        encoding="utf-8"
    )
)

packet_path = Path(
    latest["packet"]
)

packet = json.loads(
    packet_path.read_text(
        encoding="utf-8"
    )
)

print(
    "selected task:",
    packet["selected_task"]["id"],
    "-",
    packet["selected_task"]["title"],
)

print(
    "dependency closure:",
    len(
        packet["dependency_closure"]
    ),
)

print(
    "Opus assignments:",
    len(
        packet["assignments"]
    ),
)

print(
    "authority effect:",
    packet["authority"]["authority_effect"],
)

print(
    "provider calls performed:",
    latest["provider_calls_performed"],
)

for assignment in packet["assignments"]:
    print(
        f"{assignment['"'"'ordinal'"'"']}. "
        f"{assignment['"'"'key'"'"']}: "
        f"{assignment['"'"'title'"'"']}"
    )
'
