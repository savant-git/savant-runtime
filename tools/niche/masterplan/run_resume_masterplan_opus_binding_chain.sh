#!/usr/bin/env bash

set -euo pipefail

RESUMER="/root/savant-runtime/tools/niche/masterplan/resume_masterplan_opus_binding_chain.sh"

if [[ ! -f "${RESUMER}" ]]; then
    printf 'ERROR: resumer missing: %s\n' "${RESUMER}" >&2
    exit 1
fi

chmod 0755 \
    "${RESUMER}" \
    "${0}"

bash -n \
    "${RESUMER}" \
    "${0}"

set +e

/usr/bin/bash \
    "${RESUMER}"

status="$?"

set -e

if [[ "${status}" -ne 0 && "${status}" -ne 2 ]]; then
    printf 'ERROR: binding-chain resumption failed with status %s\n' \
        "${status}" \
        >&2

    exit "${status}"
fi

exit "${status}"
