[200~#!/usr/bin/env bash

set -euo pipefail

EXECUTOR="/root/savant-runtime/tools/niche/masterplan/execute_repair_masterplan_opus_queue_prerequisite.sh"

test -f \
  "${EXECUTOR}"

chmod 0755 \
  "${EXECUTOR}"

bash -n \
  "${EXECUTOR}"

"${EXECUTOR}"
