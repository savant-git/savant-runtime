#!/usr/bin/env bash

set -euo pipefail

VALIDATOR="/root/savant-runtime/tools/niche/masterplan/validate_repaired_inspector.sh"

test -s \
    "${VALIDATOR}"

chmod 0755 \
    "${VALIDATOR}"

bash -n \
    "${VALIDATOR}"

exec /usr/bin/bash \
    "${VALIDATOR}"
