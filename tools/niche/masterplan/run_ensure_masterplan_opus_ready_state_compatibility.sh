#!/usr/bin/env bash

set -euo pipefail

ROOT="/root/savant-runtime"

REPAIR="${ROOT}/tools/niche/masterplan/ensure_masterplan_opus_ready_state_compatibility.py"
IMPLEMENTATION="${ROOT}/tools/niche/masterplan/inspect_masterplan_opus_binding_state.py"
TEST="${ROOT}/hierarchies/identity/exiles/niche/prodigals/masterplan/tests/test_inspect_masterplan_opus_binding_state.py"
COMMAND="${ROOT}/bin/masterplan-opus-status"
RESUMER="${ROOT}/tools/niche/masterplan/resume_masterplan_opus_binding_chain.sh"

REQUIRED_FILES=(
    "${REPAIR}"
    "${IMPLEMENTATION}"
    "${TEST}"
    "${COMMAND}"
    "${RESUMER}"
)

for path in "${REQUIRED_FILES[@]}"; do
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
    "inspect_masterplan_opus_binding_state_integrated_validation",
    path,
)

if specification is None or specification.loader is None:
    raise SystemExit(
        "unable to load implementation"
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

assert (
    module.TERMINAL_READY_STATES
    is module.READY_STATES
)

assert len(
    module.STAGE_KEYS
) == 9

for mapping_name in (
    "STAGE_POINTERS",
    "REQUIRED_REFERENCES",
    "READY_STATES",
    "TERMINAL_READY_STATES",
    "STATE_FIELDS",
):
    mapping = getattr(
        module,
        mapping_name,
    )

    assert set(
        mapping
    ) == set(
        module.STAGE_KEYS
    )

print(
    "ready-state compatibility: verified"
)
'

"${COMMAND}"

set +e

/usr/bin/bash \
    "${RESUMER}"

status="$?"

set -e

if [[ "${status}" -ne 0 && "${status}" -ne 2 ]]; then
    printf 'ERROR: binding-chain resumer returned %s\n' \
        "${status}" \
        >&2

    exit "${status}"
fi

exit "${status}"
