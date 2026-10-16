#!/usr/bin/env bash

set -euo pipefail

REPAIR="/root/savant-runtime/tools/niche/masterplan/repair_masterplan_opus_binding_plan_tests.sh"

test -f \
  "${REPAIR}"

chmod 0755 \
  "${REPAIR}"

bash -n \
  "${REPAIR}"

"${REPAIR}"
