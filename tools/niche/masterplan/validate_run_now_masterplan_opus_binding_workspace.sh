#!/usr/bin/env bash

set -euo pipefail

SCRIPT="/root/savant-runtime/tools/niche/masterplan/run_now_masterplan_opus_binding_workspace.sh"

test -f \
    "${SCRIPT}"

chmod 0755 \
    "${SCRIPT}"

bash -n \
    "${SCRIPT}"

exec /usr/bin/bash \
    "${SCRIPT}"
