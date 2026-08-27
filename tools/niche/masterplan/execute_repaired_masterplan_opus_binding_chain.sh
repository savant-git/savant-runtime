#!/usr/bin/env bash

set -euo pipefail

RUNNER="/root/savant-runtime/tools/niche/masterplan/run_repair_and_resume_masterplan_opus_binding_chain.sh"

test -f \
    "${RUNNER}"

chmod 0755 \
    "${RUNNER}"

bash -n \
    "${RUNNER}"

exec /usr/bin/bash \
    "${RUNNER}"
