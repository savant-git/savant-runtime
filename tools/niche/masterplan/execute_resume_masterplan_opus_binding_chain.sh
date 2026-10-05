#!/usr/bin/env bash

set -euo pipefail

RUNNER="/root/savant-runtime/tools/niche/masterplan/run_resume_masterplan_opus_binding_chain.sh"

if [[ ! -f "${RUNNER}" ]]; then
    printf 'ERROR: runner missing: %s\n' "${RUNNER}" >&2
    exit 1
fi

chmod 0755 \
    "${RUNNER}" \
    "${0}"

bash -n \
    "${RUNNER}" \
    "${0}"

exec /usr/bin/bash \
    "${RUNNER}"
