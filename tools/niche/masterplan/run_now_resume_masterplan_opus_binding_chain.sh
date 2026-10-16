#!/usr/bin/env bash

set -euo pipefail

STARTER="/root/savant-runtime/tools/niche/masterplan/start_resume_masterplan_opus_binding_chain.sh"

if [[ ! -f "${STARTER}" ]]; then
    printf 'ERROR: starter missing: %s\n' "${STARTER}" >&2
    exit 1
fi

chmod 0755 \
    "${STARTER}" \
    "${0}"

bash -n \
    "${STARTER}" \
    "${0}"

exec /usr/bin/bash \
    "${STARTER}"
