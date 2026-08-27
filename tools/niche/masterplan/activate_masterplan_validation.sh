#!/usr/bin/env bash

set -euo pipefail

ROOT="/root/savant-runtime"

PACKET_VALIDATOR="${ROOT}/tools/niche/masterplan/validate_masterplan_opus_packet.sh"
CYCLE_VALIDATOR="${ROOT}/tools/niche/masterplan/validate_masterplan_living_cycle.sh"
VALIDATION_RUNNER="${ROOT}/tools/niche/masterplan/run_masterplan_validation.sh"
VALIDATION_COMMAND="${ROOT}/bin/masterplan-validate"

test -f \
  "${PACKET_VALIDATOR}"

test -f \
  "${CYCLE_VALIDATOR}"

test -f \
  "${VALIDATION_RUNNER}"

test -f \
  "${VALIDATION_COMMAND}"

chmod 0755 \
  "${PACKET_VALIDATOR}" \
  "${CYCLE_VALIDATOR}" \
  "${VALIDATION_RUNNER}" \
  "${VALIDATION_COMMAND}"

bash -n \
  "${PACKET_VALIDATOR}" \
  "${CYCLE_VALIDATOR}" \
  "${VALIDATION_RUNNER}"

python3 -m py_compile \
  "${VALIDATION_COMMAND}"

"${VALIDATION_COMMAND}"
