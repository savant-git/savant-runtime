#!/usr/bin/env bash

set -euo pipefail

ROOT="/root/savant-runtime"

PALAVER="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/palaver/runtime"

OPUS="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/opus/runtime"

echo "=== PALAVER OPUS TOOL LOOP BOUNDARY ==="

echo
echo "=== PALAVER OPUS BRIDGE ==="

cat \
  "${PALAVER}/opus_bridge.py"

echo
echo "=== CANONICAL CHAT WRAPPER ==="

sed -n '430,530p' \
  "${PALAVER}/server.py"

echo
echo "=== API CHAT EXECUTION ==="

sed -n '1100,1275p' \
  "${PALAVER}/server.py"

echo
echo "=== OPUS TEXT ROUTER ==="

grep -n -A140 -B30 \
  '^def execute_text_request' \
  "${OPUS}/router.py" \
  || true

echo
echo "=== PROVIDER TEXT ADAPTERS ==="

grep -RInE \
  '^def .*text|responses|tools|tool_choice|function_call|function_call_output|execute_text_request' \
  "${OPUS}/providers" \
  "${OPUS}/runtime" \
  --include='*.py' \
  2>/dev/null \
  || true

echo
echo "=== EXISTING TOOL BROKER / SCHEMAS ==="

grep -RInE \
  'tool broker|tool_broker|tool schema|tool_schema|tool_call|function_call|capability.*schema|execution policy' \
  "${PALAVER}" \
  "${OPUS}" \
  --include='*.py' \
  --include='*.json' \
  2>/dev/null \
  || true

echo
echo "=== RESULT ==="
echo "PALAVER OPUS TOOL LOOP BOUNDARY INSPECTION: complete"
