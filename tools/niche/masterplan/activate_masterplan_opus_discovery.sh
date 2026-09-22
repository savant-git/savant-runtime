#!/usr/bin/env bash

set -euo pipefail

ROOT="/root/savant-runtime"

DISCOVERY_TOOL="${ROOT}/tools/niche/masterplan/discover_masterplan_opus_binding.py"
DISCOVERY_TEST="${ROOT}/edifices/identity/exiles/niche/prodigals/masterplan/tests/test_discover_masterplan_opus_binding.py"
DISCOVERY_COMMAND="${ROOT}/bin/masterplan-opus-discover"
LATEST="${ROOT}/reports/niche/masterplan/opus-binding-discovery/latest.json"

test -f \
  "${DISCOVERY_TOOL}"

test -f \
  "${DISCOVERY_TEST}"

test -f \
  "${DISCOVERY_COMMAND}"

chmod 0755 \
  "${DISCOVERY_TOOL}" \
  "${DISCOVERY_TEST}" \
  "${DISCOVERY_COMMAND}" \
  "${0}"

python3 -m py_compile \
  "${DISCOVERY_TOOL}" \
  "${DISCOVERY_TEST}" \
  "${DISCOVERY_COMMAND}"

python3 \
  "${DISCOVERY_TEST}" \
  -v

set +e

"${DISCOVERY_COMMAND}" \
  discover

discovery_status="$?"

set -e

test \
  "${discovery_status}" -eq 0 \
  -o "${discovery_status}" -eq 2

"${DISCOVERY_COMMAND}" \
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
    "opus-binding-discovery/latest.json"
)

latest = json.loads(
    latest_path.read_text(
        encoding="utf-8"
    )
)

report_path = Path(
    latest["report"]
)

report = json.loads(
    report_path.read_text(
        encoding="utf-8"
    )
)

print(
    "selection state:",
    report["selection_state"],
)

print(
    "selected candidate:",
    (
        report["selected_candidate"]["path"]
        if report["selected_candidate"]
        is not None
        else None
    ),
)

print(
    "selected artifacts:",
    report["selected_artifact_count"],
)

print(
    "missing capabilities:",
    len(
        report["missing_capabilities"]
    ),
)

for capability in report[
    "binding_capabilities"
]:
    paths = report[
        "capability_matrix"
    ][
        capability
    ]

    print(
        f"{capability}: {len(paths)}"
    )

    for path in paths[:3]:
        print(
            f"  {path}"
        )

if report[
    "missing_capabilities"
]:
    print(
        "unresolved:"
    )

    for capability in report[
        "missing_capabilities"
    ]:
        print(
            f"  {capability}"
        )
'
