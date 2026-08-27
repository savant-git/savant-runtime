#!/usr/bin/env bash

set -euo pipefail

INVOKER="/root/savant-runtime/tools/niche/masterplan/invoke_resume_masterplan_opus_binding_chain.sh"

test -f \
    "${INVOKER}"

chmod 0755 \
    "${INVOKER}"

bash -n \
    "${INVOKER}"

exec /usr/bin/bash \
    "${INVOKER}"
