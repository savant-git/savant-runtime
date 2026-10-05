#!/usr/bin/env bash

set -euo pipefail

ROOT="/root/savant-runtime"

PACKET_VALIDATOR="${ROOT}/tools/niche/masterplan/validate_masterplan_opus_packet.sh"
CYCLE_VALIDATOR="${ROOT}/tools/niche/masterplan/validate_masterplan_living_cycle.sh"

test -f \
  "${PACKET_VALIDATOR}"

test -f \
  "${CYCLE_VALIDATOR}"

chmod 0755 \
  "${PACKET_VALIDATOR}" \
  "${CYCLE_VALIDATOR}"

bash -n \
  "${PACKET_VALIDATOR}" \
  "${CYCLE_VALIDATOR}"

"${CYCLE_VALIDATOR}"
