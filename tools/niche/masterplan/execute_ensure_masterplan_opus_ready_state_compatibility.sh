#!/usr/bin/env bash

set -euo pipefail

RUNNER="/root/savant-runtime/tools/niche/masterplan/run_ensure_masterplan_opus_ready_state_compatibility.sh"

if [[ ! -s "${RUNNER}" ]]; then
    printf 'ERROR: runner missing or empty: %s\n' \
        "${RUNNER}" \
        >&2

    exit 1
fi

chmod 0755 \
    "${RUNNER}"

bash -n \
    "${RUNNER}"

exec /usr/bin/bash \
    "${RUNNER}"
