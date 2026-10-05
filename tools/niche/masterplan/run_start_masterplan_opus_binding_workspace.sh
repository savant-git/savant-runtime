#!/usr/bin/env bash

set -euo pipefail

STARTER="/root/savant-runtime/tools/niche/masterplan/start_masterplan_opus_binding_workspace.sh"

test -f \
    "${STARTER}"

chmod 0755 \
    "${STARTER}"

bash -n \
    "${STARTER}"

exec /usr/bin/bash \
    "${STARTER}"
