#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
COALESCE="${ROOT}/bin/coalesce"
RUNTIME_ROOT="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/modus/segue/prodigals/coalesce/runtime"

python3 -m py_compile \
  "${RUNTIME_ROOT}/sliver_pool.py" \
  "${RUNTIME_ROOT}/capability_compiler.py" \
  "${RUNTIME_ROOT}/alloy_assembler.py" \
  "${RUNTIME_ROOT}/composition_adapter.py" \
  "${RUNTIME_ROOT}/application_service.py" \
  "${RUNTIME_ROOT}/coalesce_composer.py" \
  "${RUNTIME_ROOT}/mode_engine.py" \
  "${RUNTIME_ROOT}/coalesce_v2.py" \
  "${RUNTIME_ROOT}/runtime_bridge.py" \
  "${RUNTIME_ROOT}/health.py" \
  "${RUNTIME_ROOT}/validate.py" \
  "${RUNTIME_ROOT}/receipt.py"

STATUS="$(
  "${COALESCE}" \
    dispatch status
)"

python3 -c '
import json
import sys

data = json.loads(sys.stdin.read())

assert data.get("ok") is True
assert data.get("owner") == "prodigal:modus:coalesce"
assert data.get("primary_modes") == ["auto", "manual"]
assert data.get("maximum_alloys") == 3
assert data.get("maximum_slivers_per_alloy") == 9
assert data.get("reference_composition") is True
assert data.get("minimum_sufficient") is True
assert data.get("authority_effect") == "none"

print("COALESCE STATUS: valid")
' <<<"${STATUS}"

AUTO="$(
  "${COALESCE}" \
    dispatch auto \
    --payload '{"prompt":"I need search, records, workspace tools, chronology, and a responsive interface."}'
)"

python3 -c '
import json
import sys

data = json.loads(sys.stdin.read())

assert data.get("ok") is True
assert data.get("mode") == "auto"
assert 1 <= data.get("alloy_count", 0) <= 3
assert data.get("maximum_alloys") == 3
assert data.get("maximum_slivers_per_alloy") == 9
assert data.get("authority_effect") == "none"

for alloy in data.get("alloys", []):
    assert 1 <= alloy.get("sliver_count", 0) <= 9
    assert alloy.get("exiles_embedded") is False
    assert alloy.get("composition") == "reference"

print("COALESCE AUTO MODE: valid")
' <<<"${AUTO}"

MANUAL="$(
  "${COALESCE}" \
    dispatch manual \
    --payload '{"prompt":"Build functionality for temporal navigation, exact and fuzzy discovery, record inspection, saved workspace views, narrative stepping, and responsive shell behavior."}'
)"

python3 -c '
import json
import sys

data = json.loads(sys.stdin.read())

assert data.get("ok") is True
assert data.get("mode") == "manual"
assert 1 <= data.get("alloy_count", 0) <= 3
assert data.get("maximum_alloys") == 3
assert data.get("maximum_slivers_per_alloy") == 9
assert data.get("authority_effect") == "none"

for alloy in data.get("alloys", []):
    assert 1 <= alloy.get("sliver_count", 0) <= 9
    assert alloy.get("exiles_embedded") is False
    assert alloy.get("composition") == "reference"

print("COALESCE MANUAL MODE: valid")
' <<<"${MANUAL}"

PYTHONPATH="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/modus/segue/prodigals/coalesce" \
python3 -m runtime.validate

printf '%s\n' \
  'COALESCE V2: valid' \
  'modes=auto,manual' \
  'maximum_alloys=3' \
  'maximum_slivers_per_alloy=9' \
  'composition=reference' \
  'authority_effect=none'
