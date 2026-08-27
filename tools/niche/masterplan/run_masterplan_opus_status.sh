#!/usr/bin/env bash

set -euo pipefail

ROOT="/root/savant-runtime"

TOOL="${ROOT}/tools/niche/masterplan/inspect_masterplan_opus_binding_state.py"
TEST="${ROOT}/hierarchies/identity/exiles/niche/prodigals/masterplan/tests/test_inspect_masterplan_opus_binding_state.py"
COMMAND="${ROOT}/bin/masterplan-opus-status"

test -f \
  "${TOOL}"

test -f \
  "${TEST}"

test -f \
  "${COMMAND}"

chmod 0755 \
  "${TOOL}" \
  "${TEST}" \
  "${COMMAND}" \
  "${0}"

python3 -m py_compile \
  "${TOOL}" \
  "${TEST}" \
  "${COMMAND}"

python3 \
  "${TEST}" \
  -v

"${COMMAND}"

"${COMMAND}" \
  --json
