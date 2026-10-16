#!/usr/bin/env bash

set -euo pipefail

ACTIVATOR="/root/savant-runtime/tools/niche/masterplan/activate_masterplan_opus_binding_plan.sh"

test -f \
  "${ACTIVATOR}"

chmod 0755 \
  "${ACTIVATOR}"

bash -n \
  "${ACTIVATOR}"

"${ACTIVATOR}"
