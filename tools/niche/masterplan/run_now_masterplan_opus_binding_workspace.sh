#!/usr/bin/env bash

set -euo pipefail

RUNNER="/root/savant-runtime/tools/niche/masterplan/run_masterplan_opus_binding_workspace.sh"

if [[ ! -f "${RUNNER}" ]]; then
    printf 'ERROR: required runner missing: %s\n' "${RUNNER}" >&2
    exit 1
fi

chmod 0755 \
    "${RUNNER}"

bash -n \
    "${RUNNER}"

exec /usr/bin/bash \
    "${RUNNER}"
