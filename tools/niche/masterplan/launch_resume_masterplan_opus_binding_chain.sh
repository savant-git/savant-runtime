#!/usr/bin/env bash

set -euo pipefail

RUN_NOW="/root/savant-runtime/tools/niche/masterplan/run_now_resume_masterplan_opus_binding_chain.sh"

if [[ ! -f "${RUN_NOW}" ]]; then
    printf 'ERROR: run-now script missing: %s\n' "${RUN_NOW}" >&2
    exit 1
fi

chmod 0755 \
    "${RUN_NOW}" \
    "${0}"

bash -n \
    "${RUN_NOW}" \
    "${0}"

exec /usr/bin/bash \
    "${RUN_NOW}"
