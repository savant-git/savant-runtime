#!/usr/bin/env bash

set -euo pipefail

COMMAND="/root/savant-runtime/tools/niche/masterplan/run_masterplan_opus_binding_chain_now.sh"

test -f \
    "${COMMAND}"

chmod 0755 \
    "${COMMAND}"

bash -n \
    "${COMMAND}"

exec /usr/bin/bash \
    "${COMMAND}"
