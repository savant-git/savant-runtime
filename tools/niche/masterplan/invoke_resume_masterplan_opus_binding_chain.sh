#!/usr/bin/env bash

set -euo pipefail

LAUNCHER="/root/savant-runtime/tools/niche/masterplan/launch_resume_masterplan_opus_binding_chain.sh"

if [[ ! -f "${LAUNCHER}" ]]; then
    printf 'ERROR: launcher missing: %s\n' "${LAUNCHER}" >&2
    exit 1
fi

chmod 0755 \
    "${LAUNCHER}" \
    "${0}"

bash -n \
    "${LAUNCHER}" \
    "${0}"

exec /usr/bin/bash \
    "${LAUNCHER}"
