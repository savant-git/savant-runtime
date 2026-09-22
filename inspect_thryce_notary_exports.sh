#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
THRYCE="${ROOT}/runtime/thryce"
NOTARY="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/notary"

printf '%s\n' '=== THRYCE __INIT__ ==='
cat "${THRYCE}/__init__.py"

printf '\n%s\n' '=== THRYCE ENGINE PUBLIC SYMBOLS ==='
PYTHONPATH="${ROOT}" python3 -c '
import runtime.thryce.engine as engine

print([
    name
    for name in dir(engine)
    if not name.startswith("_")
])
'

printf '\n%s\n' '=== NOTARY RUNTIME FILES ==='
find "${NOTARY}" \
  -maxdepth 4 \
  -type f \
  \( -name "*.py" -o -name "*.json" \) \
  ! -path "*/__pycache__/*" \
  -print \
  2>/dev/null \
  | sort \
  | head -n 250

printf '\n%s\n' '=== NOTARY PUBLIC CLASSES / FUNCTIONS ==='
grep -RInE \
  --include='*.py' \
  '^(class|def) ' \
  "${NOTARY}" \
  2>/dev/null \
  | head -n 300 \
  || true

printf '\n%s\n' '=== THRYCE NOTARY BINDING FILES ==='
for file in \
  "${THRYCE}/notary_binding.py" \
  "${THRYCE}/notary_adapter.py"
do
    printf '\n--- %s ---\n' "${file}"
    cat "${file}"
done

printf '\n%s\n' '=== RESULT ==='
printf '%s\n' 'THRYCE / NOTARY EXPORT INSPECTION: complete'
