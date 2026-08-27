#!/usr/bin/env bash

set -euo pipefail

ROOT="/root/savant-runtime"

PLAN_TOOL="${ROOT}/tools/niche/masterplan/compile_masterplan_opus_binding_plan.py"
PLAN_TEST="${ROOT}/hierarchies/identity/exiles/niche/prodigals/masterplan/tests/test_compile_masterplan_opus_binding_plan.py"
PLAN_COMMAND="${ROOT}/bin/masterplan-opus-plan"
ACTIVATOR="${ROOT}/tools/niche/masterplan/activate_masterplan_opus_binding_plan.sh"

test -f \
  "${PLAN_TOOL}"

test -f \
  "${PLAN_TEST}"

test -f \
  "${PLAN_COMMAND}"

test -f \
  "${ACTIVATOR}"

chmod 0755 \
  "${PLAN_TOOL}" \
  "${PLAN_TEST}" \
  "${PLAN_COMMAND}" \
  "${ACTIVATOR}" \
  "${0}"

python3 -m py_compile \
  "${PLAN_TOOL}" \
  "${PLAN_TEST}" \
  "${PLAN_COMMAND}"

python3 \
  "${PLAN_TEST}" \
  -v

bash -n \
  "${ACTIVATOR}"

"${ACTIVATOR}"
