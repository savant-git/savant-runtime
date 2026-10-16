#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/modus/segue/prodigals/coalesce"

printf '\n=== RUNTIME ===\n'

find "$ROOT/runtime" \
  -maxdepth 2 \
  -type f \
  -not -path '*/__pycache__/*' \
  -print \
  | sort

printf '\n=== EXISTING COALESCE.PY ===\n'

if [ -f "$ROOT/runtime/coalesce.py" ]; then
  sed -n '1,420p' "$ROOT/runtime/coalesce.py"
fi

printf '\n=== CAPABILITIES ===\n'

cat "$ROOT/interface/capabilities/capabilities.json"

printf '\n=== ENTITY ===\n'

cat "$ROOT/entity.json"

printf '\n=== TEST CONTRACT ===\n'

sed -n '1,260p' "$ROOT/tests/test_coalesce.py"

printf '\n=== API REFERENCES ===\n'

grep -RIn \
  --exclude='*.pyc' \
  --exclude-dir='__pycache__' \
  -E '/api/coalesce|compile\(|project\(|recipe|capabilit|sliver|alloy' \
  "$ROOT/runtime" \
  "$ROOT/tests" \
  "$ROOT/interface" \
  "$ROOT/static/public" \
  2>/dev/null \
  | head -n 400 \
  || true
