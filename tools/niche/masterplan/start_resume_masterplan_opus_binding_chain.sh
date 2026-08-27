[200~#!/usr/bin/env bash

set -euo pipefail

EXECUTOR="/root/savant-runtime/tools/niche/masterplan/execute_resume_masterplan_opus_binding_chain.sh"

if [[ ! -f "${EXECUTOR}" ]]; then
    printf 'ERROR: executor missing: %s\n' "${EXECUTOR}" >&2
    exit 1
fi

chmod 0755 \
    "${EXECUTOR}" \
    "${0}"

bash -n \
    "${EXECUTOR}" \
    "${0}"

exec /usr/bin/bash \
    "${EXECUTOR}"
