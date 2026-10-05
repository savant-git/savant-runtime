#!/usr/bin/env bash

set -euo pipefail

EXECUTOR="/root/savant-runtime/tools/niche/masterplan/execute_run_now_masterplan_opus_binding_workspace.sh"

if [[ ! -f "${EXECUTOR}" ]]; then
    printf 'ERROR: executor missing: %s\n' "${EXECUTOR}" >&2
    exit 1
fi

chmod 0755 \
    "${EXECUTOR}"

bash -n \
    "${EXECUTOR}"

exec /usr/bin/bash \
    "${EXECUTOR}"
