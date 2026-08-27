#!/usr/bin/env bash

set -euo pipefail

ROOT="/root/savant-runtime"

REPAIR="${ROOT}/tools/niche/masterplan/repair_masterplan_opus_status_compatibility.py"
IMPLEMENTATION="${ROOT}/tools/niche/masterplan/inspect_masterplan_opus_binding_state.py"
TEST="${ROOT}/hierarchies/identity/exiles/niche/prodigals/masterplan/tests/test_inspect_masterplan_opus_binding_state.py"
COMMAND="${ROOT}/bin/masterplan-opus-status"
RESUMER="${ROOT}/tools/niche/masterplan/resume_masterplan_opus_binding_chain.sh"

for path in \
    "${REPAIR}" \
    "${IMPLEMENTATION}" \
    "${TEST}" \
    "${COMMAND}" \
    "${RESUMER}"
do
    if [[ ! -s "${path}" ]]; then
        printf 'ERROR: required file missing or empty: %s\n' \
            "${path}" \
            >&2

        exit 1
    fi
done

chmod 0755 \
    "${REPAIR}" \
    "${IMPLEMENTATION}" \
    "${TEST}" \
    "${COMMAND}" \
    "${RESUMER}" \
    "${0}"

python3 -m py_compile \
    "${REPAIR}"

python3 \
    "${REPAIR}"

python3 -m py_compile \
    "${IMPLEMENTATION}" \
    "${TEST}" \
    "${COMMAND}"

python3 \
    "${TEST}" \
    -v

python3 -c '
import importlib.util
import sys
from pathlib import Path

path = Path(
    "/root/savant-runtime/tools/niche/masterplan/"
    "inspect_masterplan_opus_binding_state.py"
)

specification = importlib.util.spec_from_file_location(
    "inspect_masterplan_opus_binding_state_validation",
    path,
)

if specification is None or specification.loader is None:
    raise SystemExit(
        "unable to load inspector"
    )

module = importlib.util.module_from_spec(
    specification
)

sys.modules[
    specification.name
] = module

specification.loader.exec_module(
    module
)

if (
    module.TERMINAL_READY_STATES
    is not module.READY_STATES
):
    raise SystemExit(
        "compatibility alias is not an identity projection"
    )

print(
    "READY_STATES and TERMINAL_READY_STATES "
    "share one mapping instance"
)
'

"${COMMAND}"

set +e

/usr/bin/bash \
    "${RESUMER}"

status="$?"

set -e

test \
    "${status}" -eq 0 \
    -o "${status}" -eq 2

exit "${status}"
