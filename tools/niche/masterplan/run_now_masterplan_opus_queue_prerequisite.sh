[200~#!/usr/bin/env bash

set -euo pipefail

LAUNCHER="/root/savant-runtime/tools/niche/masterplan/launch_repair_masterplan_opus_queue_prerequisite.sh"

test -f \
  "${LAUNCHER}"

chmod 0755 \
  "${LAUNCHER}"

bash -n \
  "${LAUNCHER}"

"${LAUNCHER}"
