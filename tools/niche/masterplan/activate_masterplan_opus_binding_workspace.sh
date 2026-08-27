#!/usr/bin/env bash

set -euo pipefail

ROOT="/root/savant-runtime"

PREREQUISITE="${ROOT}/tools/niche/masterplan/repair_masterplan_opus_queue_prerequisite.sh"
WORKSPACE_TOOL="${ROOT}/tools/niche/masterplan/compile_masterplan_opus_binding_workspace.py"
WORKSPACE_TEST="${ROOT}/hierarchies/identity/exiles/niche/prodigals/masterplan/tests/test_compile_masterplan_opus_binding_workspace.py"
WORKSPACE_COMMAND="${ROOT}/bin/masterplan-opus-workspace"
LATEST="${ROOT}/reports/niche/masterplan/opus-binding-workspace/latest.json"

test -f \
  "${PREREQUISITE}"

test -f \
  "${WORKSPACE_TOOL}"

test -f \
  "${WORKSPACE_TEST}"

test -f \
  "${WORKSPACE_COMMAND}"

chmod 0755 \
  "${PREREQUISITE}" \
  "${WORKSPACE_TOOL}" \
  "${WORKSPACE_TEST}" \
  "${WORKSPACE_COMMAND}" \
  "${0}"

python3 -m py_compile \
  "${WORKSPACE_TOOL}" \
  "${WORKSPACE_TEST}" \
  "${WORKSPACE_COMMAND}"

python3 \
  "${WORKSPACE_TEST}" \
  -v

"${PREREQUISITE}"

set +e

"${WORKSPACE_COMMAND}" \
  compile

workspace_status="$?"

set -e

test \
  "${workspace_status}" -eq 0 \
  -o "${workspace_status}" -eq 2

"${WORKSPACE_COMMAND}" \
  verify

test -f \
  "${LATEST}"

python3 -m json.tool \
  "${LATEST}" \
  >/dev/null

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
    "workspace state:",
    workspace["state"],
)

print(
    "workspace:",
    workspace["workspace_id"],
)

print(
    "task:",
    (
        workspace["task"]["id"]
        if isinstance(
            workspace["task"],
            dict,
        )
        else None
    ),
)

print(
    "selected runtime:",
    workspace["selected_runtime"],
)

print(
    "source artifacts:",
    workspace["source_artifact_count"],
)

print(
    "blockers:",
    len(
        workspace["blockers"]
    ),
)

for item in workspace[
    "capability_workspaces"
]:
    print(
        f"{item['ordinal']}. "
        f"{item['capability']}: "
        f"ready={item['ready']}; "
        f"sources={len(item['source_artifact_ids'])}"
    )

    for blocker in item[
        "blockers"
    ]:
        print(
            f"   blocker: {blocker}"
        )

if workspace["blockers"]:
    print(
        "workspace blockers:"
    )

    for blocker in workspace[
        "blockers"
    ]:
        print(
            f"  {blocker}"
        )
'
