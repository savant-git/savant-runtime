#!/usr/bin/env bash

set -euo pipefail

RUNNER="/root/savant-runtime/tools/niche/masterplan/run_repair_masterplan_opus_queue_prerequisite.sh"

test -f \
  "${RUNNER}"

chmod 0755 \
  "${RUNNER}"

bash -n \
  "${RUNNER}"

"${RUNNER}"
