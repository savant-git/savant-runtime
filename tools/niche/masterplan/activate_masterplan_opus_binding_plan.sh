#!/usr/bin/env bash

set -euo pipefail

ROOT="/root/savant-runtime"

DISCOVERY_RUNNER="${ROOT}/tools/niche/masterplan/run_masterplan_opus_discovery.sh"
PLAN_TOOL="${ROOT}/tools/niche/masterplan/compile_masterplan_opus_binding_plan.py"
PLAN_TEST="${ROOT}/hierarchies/identity/exiles/niche/prodigals/masterplan/tests/test_compile_masterplan_opus_binding_plan.py"
PLAN_COMMAND="${ROOT}/bin/masterplan-opus-plan"
LATEST_PLAN="${ROOT}/reports/niche/masterplan/opus-binding-plan/latest.json"

test -f \
  "${DISCOVERY_RUNNER}"

test -f \
  "${PLAN_TOOL}"

test -f \
  "${PLAN_TEST}"

test -f \
  "${PLAN_COMMAND}"

chmod 0755 \
  "${DISCOVERY_RUNNER}" \
  "${PLAN_TOOL}" \
  "${PLAN_TEST}" \
  "${PLAN_COMMAND}" \
  "${0}"

python3 -m py_compile \
  "${PLAN_TOOL}" \
  "${PLAN_TEST}" \
  "${PLAN_COMMAND}"

python3 \
  "${PLAN_TEST}" \
  -v

"${DISCOVERY_RUNNER}"

set +e

"${PLAN_COMMAND}" \
  compile

plan_status="$?"

set -e

test \
  "${plan_status}" -eq 0 \
  -o "${plan_status}" -eq 2

"${PLAN_COMMAND}" \
  verify

test -f \
  "${LATEST_PLAN}"

python3 -m json.tool \
  "${LATEST_PLAN}" \
  >/dev/null

python3 -c '
import json
from pathlib import Path

latest_path = Path(
    "/root/savant-runtime/reports/niche/masterplan/"
    "opus-binding-plan/latest.json"
)

latest = json.loads(
    latest_path.read_text(
        encoding="utf-8"
    )
)

plan_path = Path(
    latest["plan"]
)

plan = json.loads(
    plan_path.read_text(
        encoding="utf-8"
    )
)

print(
    "state:",
    plan["state"],
)

print(
    "task:",
    plan["task"]["id"],
    "-",
    plan["task"]["title"],
)

print(
    "selected runtime:",
    plan["discovery"]["selected_runtime"],
)

print(
    "blockers:",
    len(
        plan["blockers"]
    ),
)

for item in plan[
    "capability_plans"
]:
    print(
        f"{item['"'"'ordinal'"'"']}. "
        f"{item['"'"'capability'"'"']} -> "
        f"{item['"'"'layer'"'"']} -> "
        f"{item['"'"'action'"'"']}"
    )

    for blocker in item[
        "blockers"
    ]:
        print(
            f"   blocker: {blocker}"
        )

if plan["blockers"]:
    print(
        "unresolved plan blockers:"
    )

    for blocker in plan[
        "blockers"
    ]:
        print(
            f"  {blocker}"
        )
'
