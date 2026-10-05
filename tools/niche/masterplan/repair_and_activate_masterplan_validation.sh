#!/usr/bin/env bash

set -euo pipefail

ROOT="/root/savant-runtime"
MASTERPLAN_ROOT="${ROOT}/tools/niche/masterplan"

PACKET_VALIDATOR="${MASTERPLAN_ROOT}/validate_masterplan_opus_packet.sh"
CYCLE_VALIDATOR="${MASTERPLAN_ROOT}/validate_masterplan_living_cycle.sh"
VALIDATION_RUNNER="${MASTERPLAN_ROOT}/run_masterplan_validation.sh"
ACTIVATION_SCRIPT="${MASTERPLAN_ROOT}/activate_masterplan_validation.sh"
THIS_SCRIPT="${MASTERPLAN_ROOT}/repair_and_activate_masterplan_validation.sh"
VALIDATION_COMMAND="${ROOT}/bin/masterplan-validate"

REQUIRED_FILES=(
  "${PACKET_VALIDATOR}"
  "${CYCLE_VALIDATOR}"
  "${VALIDATION_RUNNER}"
  "${ACTIVATION_SCRIPT}"
  "${VALIDATION_COMMAND}"
)

for path in "${REQUIRED_FILES[@]}"; do
  if [[ ! -f "${path}" ]]; then
    printf 'ERROR: required file missing: %s\n' "${path}" >&2
    exit 1
  fi
done

chmod 0755 \
  "${THIS_SCRIPT}" \
  "${PACKET_VALIDATOR}" \
  "${CYCLE_VALIDATOR}" \
  "${VALIDATION_RUNNER}" \
  "${ACTIVATION_SCRIPT}" \
  "${VALIDATION_COMMAND}"

bash -n \
  "${THIS_SCRIPT}" \
  "${PACKET_VALIDATOR}" \
  "${CYCLE_VALIDATOR}" \
  "${VALIDATION_RUNNER}" \
  "${ACTIVATION_SCRIPT}"

python3 -m py_compile \
  "${VALIDATION_COMMAND}"

printf '%s\n' \
  "Permissions repaired." \
  "Shell syntax validated." \
  "Starting Masterplan validation."

"${ACTIVATION_SCRIPT}"
