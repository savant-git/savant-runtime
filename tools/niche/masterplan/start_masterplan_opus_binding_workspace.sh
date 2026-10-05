#!/usr/bin/env bash

set -euo pipefail

LAUNCHER="/root/savant-runtime/tools/niche/masterplan/launch_run_now_masterplan_opus_binding_workspace.sh"

if [[ ! -f "${LAUNCHER}" ]]; then
    printf 'ERROR: launcher missing: %s\n' "${LAUNCHER}" >&2
    exit 1
fi

chmod 0755 \
    "${LAUNCHER}"

bash -n \
    "${LAUNCHER}"

exec /usr/bin/bash \
    "${LAUNCHER}"
