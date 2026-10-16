#!/usr/bin/env bash

set -euo pipefail

EXECUTOR="/root/savant-runtime/tools/niche/masterplan/execute_masterplan_opus_status.sh"

test -f \
  "${EXECUTOR}"

chmod 0755 \
  "${EXECUTOR}"

bash -n \
  "${EXECUTOR}"

exec /usr/bin/bash \
  "${EXECUTOR}"
