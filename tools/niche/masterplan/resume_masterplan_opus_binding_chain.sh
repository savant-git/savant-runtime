#!/usr/bin/env bash

set -euo pipefail

ROOT="/root/savant-runtime"
MASTERPLAN_ROOT="${ROOT}/tools/niche/masterplan"
TEST_ROOT="${ROOT}/hierarchies/identity/exiles/niche/prodigals/masterplan/tests"

STATUS_TOOL="${MASTERPLAN_ROOT}/inspect_masterplan_opus_binding_state.py"
WORKSPACE_TOOL="${MASTERPLAN_ROOT}/compile_masterplan_opus_binding_workspace.py"

STATUS_TEST="${TEST_ROOT}/test_inspect_masterplan_opus_binding_state.py"
WORKSPACE_TEST="${TEST_ROOT}/test_compile_masterplan_opus_binding_workspace.py"

STATUS_COMMAND="${ROOT}/bin/masterplan-opus-status"
WORKSPACE_COMMAND="${ROOT}/bin/masterplan-opus-workspace"

PREREQUISITE_RUNNER="${MASTERPLAN_ROOT}/repair_masterplan_opus_queue_prerequisite.sh"

WORKSPACE_LATEST="${ROOT}/reports/niche/masterplan/opus-binding-workspace/latest.json"

REQUIRED_FILES=(
    "${STATUS_TOOL}"
    "${WORKSPACE_TOOL}"
    "${STATUS_TEST}"
    "${WORKSPACE_TEST}"
    "${STATUS_COMMAND}"
    "${WORKSPACE_COMMAND}"
    "${PREREQUISITE_RUNNER}"
)

fail() {
    printf 'ERROR: %s\n' "$1" >&2
    exit 1
}

for path in "${REQUIRED_FILES[@]}"; do
    if [[ ! -f "${path}" ]]; then
        fail "required file missing: ${path}"
    fi
done

chmod 0755 \
    "${STATUS_TOOL}" \
    "${WORKSPACE_TOOL}" \
    "${STATUS_TEST}" \
    "${WORKSPACE_TEST}" \
    "${STATUS_COMMAND}" \
    "${WORKSPACE_COMMAND}" \
    "${PREREQUISITE_RUNNER}"

python3 -m py_compile \
    "${STATUS_TOOL}" \
    "${WORKSPACE_TOOL}" \
    "${STATUS_TEST}" \
    "${WORKSPACE_TEST}" \
    "${STATUS_COMMAND}" \
    "${WORKSPACE_COMMAND}"

python3 \
    "${STATUS_TEST}" \
    -v

python3 \
    "${WORKSPACE_TEST}" \
    -v

printf '%s\n' \
    "========================================================================" \
    "REBUILDING MASTERPLAN-TO-OPUS PREREQUISITES" \
    "========================================================================"

"${PREREQUISITE_RUNNER}"

printf '%s\n' \
    "========================================================================" \
    "COMPILING MASTERPLAN-TO-OPUS WORKSPACE" \
    "========================================================================"

set +e

"${WORKSPACE_COMMAND}" \
    compile

workspace_status="$?"

set -e

if [[ "${workspace_status}" -ne 0 && "${workspace_status}" -ne 2 ]]; then
    fail "workspace compiler returned unexpected status ${workspace_status}"
fi

"${WORKSPACE_COMMAND}" \
    verify

test -f \
    "${WORKSPACE_LATEST}"

python3 -m json.tool \
    "${WORKSPACE_LATEST}" \
    >/dev/null

printf '%s\n' \
    "========================================================================" \
    "MASTERPLAN-TO-OPUS STATUS" \
    "========================================================================"

"${STATUS_COMMAND}"

printf '%s\n' \
    "========================================================================" \
    "WORKSPACE SUMMARY" \
    "========================================================================"

python3 -c '
import json
from pathlib import Path

latest_path = Path(
    "/root/savant-runtime/reports/niche/masterplan/"
    "opus-binding-workspace/latest.json"
)

latest = json.loads(
    latest_path.read_text(
        encoding="utf-8"
    )
)

workspace_path = Path(
    latest["workspace"]
)

workspace = json.loads(
    workspace_path.read_text(
        encoding="utf-8"
    )
)

print(
    "workspace_id:",
    workspace["workspace_id"],
)

print(
    "state:",
    workspace["state"],
)

print(
    "task_id:",
    (
        workspace["task"]["id"]
        if isinstance(
            workspace.get("task"),
            dict,
        )
        else None
    ),
)

print(
    "selected_runtime:",
    workspace["selected_runtime"],
)

print(
    "source_artifact_count:",
    workspace["source_artifact_count"],
)

print(
    "blocker_count:",
    len(
        workspace["blockers"]
    ),
)

for item in workspace["capability_workspaces"]:
    print(
        f"{item['ordinal']}. "
        f"{item['capability']}: "
        f"ready={item['ready']}; "
        f"action={item['action']}; "
        f"sources={len(item['source_artifact_ids'])}"
    )

    for blocker in item["blockers"]:
        print(
            f"   blocker: {blocker}"
        )

if workspace["blockers"]:
    print()
    print(
        "FIRST WORKSPACE BLOCKER:",
        workspace["blockers"][0],
    )
'

exit "${workspace_status}"
